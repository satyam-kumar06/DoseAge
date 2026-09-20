"""Scan pipeline tasks (Express state machine).

Each function is one state, so the Step Functions graph in the console reads
like the story: extract, structure, match salts, check duplicates, save.
"""
from typing import Any, Dict
from urllib.parse import unquote_plus

from common import extraction, keys, notify, salts, schedule, storage, util
from common.store import store


def _scan_from_key(key: str) -> Dict[str, str]:
    """scans/<parentId>/<scanId>.<ext>"""
    parts = key.split("/")
    if len(parts) < 3 or parts[0] != "scans":
        raise ValueError(f"unexpected key {key}")
    return {"parentId": parts[1], "scanId": parts[2].rsplit(".", 1)[0], "key": key}


def on_upload(event: Dict[str, Any], context=None) -> Dict[str, Any]:
    """S3 ObjectCreated -> start the Express workflow."""
    import json
    import os

    import boto3

    client = boto3.client("stepfunctions")
    started = []
    for record in event.get("Records", []):
        key = unquote_plus(record["s3"]["object"]["key"])
        payload = _scan_from_key(key)
        client.start_execution(
            stateMachineArn=os.environ["SCAN_STATE_MACHINE_ARN"],
            input=json.dumps(payload),
        )
        started.append(payload)
    return {"started": started}


def extract_text(event: Dict[str, Any], context=None) -> Dict[str, Any]:
    """Textract plus Bedrock vision, returning the strict JSON contract."""
    parent_id, scan_id = event["parentId"], event["scanId"]
    store().update(
        keys.parent(parent_id),
        keys.scan_sk(scan_id),
        {"status": "READING", "startedAt": util.iso(util.now_utc())},
    )
    result = extraction.extract(image_key=event.get("key"), fixture_name=event.get("fixture"))
    return {**event, "extracted": result}


def match_salts(event: Dict[str, Any], context=None) -> Dict[str, Any]:
    """Brand to salt lookup over the dataset. Plain code, no model."""
    scan_id = event["scanId"]
    drafts = []
    for index, med in enumerate(event["extracted"]["medicines"]):
        match = salts.lookup(med["brand"], med.get("strength", ""))
        record = match.get("record") or {}
        drafts.append(
            {
                "medId": util.new_id(),
                "brand": match["brand"] if match["matched"] else med["brand"],
                "scannedBrand": med["brand"],
                "salts": match["salts"],
                "saltMatched": match["matched"],
                "saltConfidence": match["confidence"],
                "saltSuggestion": match.get("bestGuess"),
                "strength": med["strength"] or record.get("strength", ""),
                "form": med["form"],
                "frequencyCode": med["frequencyCode"],
                "slots": schedule.slots_for(med["frequencyCode"]),
                "food": med["food"],
                "durationDays": med["durationDays"],
                "confidence": med["confidence"],
                "lowConfidence": med["lowConfidence"],
                "sourceText": med["sourceText"],
                "cropKey": storage.crop_key(scan_id, index),
                "stripSize": record.get("packSize"),
                "status": "NEEDS_REVIEW",
            }
        )
    return {**event, "medicines": drafts}


def check_duplicates(event: Dict[str, Any], context=None) -> Dict[str, Any]:
    """Deterministic same-salt detection. We flag, we never advise."""
    duplicates = salts.find_duplicates(event["medicines"])
    for dup in duplicates:
        notify.record_alert(
            event["parentId"],
            "DUPLICATE",
            dup["message"],
            dup["messageHi"],
            {"salt": dup["salt"], "brands": dup["brands"], "scanId": event["scanId"]},
            dedupe_key=f"DUPLICATE#{dup['salt']}",
        )
    return {**event, "duplicates": duplicates}


def save_draft(event: Dict[str, Any], context=None) -> Dict[str, Any]:
    """Nothing becomes a real medicine here: status stays NEEDS_REVIEW until
    a human confirms it on the review screen."""
    parent_id, scan_id = event["parentId"], event["scanId"]
    extracted = event["extracted"]
    store().update(
        keys.parent(parent_id),
        keys.scan_sk(scan_id),
        {
            "status": "NEEDS_REVIEW",
            "engine": extracted.get("engine"),
            "repaired": extracted.get("repaired", False),
            "rawText": "\n".join(extracted.get("ocrLines", []))[:4000],
            "extractedJson": {
                "medicines": event["medicines"],
                "duplicates": event.get("duplicates", []),
                "unreadableLines": extracted.get("unreadableLines", []),
                "doctorName": extracted.get("doctorName", ""),
                "prescriptionDate": extracted.get("prescriptionDate", ""),
            },
            "finishedAt": util.iso(util.now_utc()),
        },
    )
    return {
        "parentId": parent_id,
        "scanId": scan_id,
        "status": "NEEDS_REVIEW",
        "medicineCount": len(event["medicines"]),
        "duplicateCount": len(event.get("duplicates", [])),
    }


def on_failure(event: Dict[str, Any], context=None) -> Dict[str, Any]:
    """Catch state: the scan is marked failed so the UI can offer a retake."""
    parent_id, scan_id = event.get("parentId"), event.get("scanId")
    if parent_id and scan_id:
        store().update(
            keys.parent(parent_id),
            keys.scan_sk(scan_id),
            {"status": "FAILED", "error": str(event.get("error", ""))[:500]},
        )
    return {"parentId": parent_id, "scanId": scan_id, "status": "FAILED"}
