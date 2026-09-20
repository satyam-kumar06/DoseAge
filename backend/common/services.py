"""Business logic, shared by the API Lambda, the Step Functions tasks and the
local dev server. Nothing in here knows about HTTP.
"""
import datetime as dt
import os
from typing import Any, Dict, List, Optional

from . import config, extraction, keys, notify, salts, savings, schedule, storage, util, voice
from .store import store
from .util import ApiError

# --------------------------------------------------------------------------
# Families, caregivers, parents
# --------------------------------------------------------------------------


def create_family(name: str, caregiver: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    family_id = util.new_id()
    now = util.iso(util.now_utc())
    store().put(
        {
            "PK": keys.family(family_id),
            "SK": keys.PROFILE,
            "type": "FAMILY",
            "familyId": family_id,
            "name": name,
            "createdAt": now,
        }
    )
    result = {"familyId": family_id, "name": name, "createdAt": now}
    if caregiver:
        result["caregiver"] = add_caregiver(family_id, caregiver)
    return result


def add_caregiver(family_id: str, caregiver: Dict[str, Any]) -> Dict[str, Any]:
    user_id = caregiver.get("userId") or util.new_id()
    item = {
        "PK": keys.family(family_id),
        "SK": keys.caregiver_sk(user_id),
        "type": "CAREGIVER",
        "familyId": family_id,
        "userId": user_id,
        "name": caregiver.get("name", ""),
        "phone": caregiver.get("phone", ""),
        "email": caregiver.get("email", ""),
        "role": caregiver.get("role", "primary"),
        "createdAt": util.iso(util.now_utc()),
    }
    store().put(item)
    return item


def add_parent(family_id: str, parent: Dict[str, Any]) -> Dict[str, Any]:
    if not store().get(keys.family(family_id), keys.PROFILE):
        raise ApiError(404, "family not found")
    parent_id = parent.get("parentId") or util.new_id()
    item = {
        "PK": keys.family(family_id),
        "SK": keys.parent_sk(parent_id),
        "type": "PARENT",
        "familyId": family_id,
        "parentId": parent_id,
        "name": parent.get("name", ""),
        "phone": parent.get("phone", ""),
        "language": parent.get("language", "hi"),
        "timezone": parent.get("timezone", config.DEFAULT_TIMEZONE),
        "relation": parent.get("relation", ""),
        "GSI1PK": f"PHONE#{parent.get('phone','')}",
        "GSI1SK": keys.parent(parent_id),
        "createdAt": util.iso(util.now_utc()),
    }
    store().put(item)
    return item


def get_parent(parent_id: str) -> Dict[str, Any]:
    for item in store().scan_prefix("FAMILY#"):
        if item.get("type") == "PARENT" and item.get("parentId") == parent_id:
            return item
    raise ApiError(404, "parent not found")


def list_parents(family_id: str) -> List[Dict[str, Any]]:
    return store().query(keys.family(family_id), "PARENT#")


def list_caregivers(family_id: str) -> List[Dict[str, Any]]:
    return store().query(keys.family(family_id), "CAREGIVER#")


# --------------------------------------------------------------------------
# Scanning
# --------------------------------------------------------------------------


def upload_url(parent_id: str, content_type: str = "image/jpeg") -> Dict[str, Any]:
    get_parent(parent_id)
    scan_id = util.new_id()
    ext = "png" if "png" in content_type else "jpg"
    key = storage.scan_key(parent_id, scan_id, ext)
    presigned = storage.presigned_upload(key, content_type)

    store().put(
        {
            "PK": keys.parent(parent_id),
            "SK": keys.scan_sk(scan_id),
            "type": "SCAN",
            "parentId": parent_id,
            "scanId": scan_id,
            "s3Key": key,
            "status": "AWAITING_UPLOAD",
            "createdAt": util.iso(util.now_utc()),
            "expiresAt": int((util.now_utc() + dt.timedelta(days=30)).timestamp()),
        }
    )
    return {"scanId": scan_id, "key": key, "upload": presigned}


def start_scan(parent_id: str, scan_id: str, fixture_name: Optional[str] = None) -> Dict[str, Any]:
    """Kick off the scan pipeline.

    On AWS this starts the Express state machine and returns immediately with
    status READING; the client polls GET /scans/{id}. Starting it here rather
    than from an S3 event notification keeps the trigger explicit and avoids a
    CloudFormation circular dependency between the bucket and the Lambda.

    Locally the same steps run inline, so the first poll already returns the
    finished result and the flow works end to end with no AWS account.
    """
    scan = store().get(keys.parent(parent_id), keys.scan_sk(scan_id))
    if not scan:
        raise ApiError(404, "scan not found")

    store().update(
        keys.parent(parent_id),
        keys.scan_sk(scan_id),
        {"status": "READING", "startedAt": util.iso(util.now_utc())},
    )

    state_machine = os.environ.get("SCAN_STATE_MACHINE_ARN")
    if config.IS_AWS and state_machine:
        import json

        import boto3

        boto3.client("stepfunctions", region_name=config.REGION).start_execution(
            stateMachineArn=state_machine,
            input=json.dumps(
                {
                    "parentId": parent_id,
                    "scanId": scan_id,
                    "key": scan.get("s3Key"),
                    "fixture": fixture_name,
                }
            ),
        )
        return get_scan(parent_id, scan_id)

    return run_scan_pipeline(parent_id, scan_id, fixture_name)


def run_scan_pipeline(parent_id: str, scan_id: str, fixture_name: Optional[str] = None) -> Dict[str, Any]:
    scan = store().get(keys.parent(parent_id), keys.scan_sk(scan_id))
    if not scan:
        raise ApiError(404, "scan not found")

    try:
        result = extraction.extract(image_key=scan.get("s3Key"), fixture_name=fixture_name)
    except Exception as exc:  # the review screen is the safety net
        store().update(
            keys.parent(parent_id),
            keys.scan_sk(scan_id),
            {"status": "FAILED", "error": str(exc)[:500]},
        )
        raise

    drafts = []
    for index, med in enumerate(result["medicines"]):
        match = salts.lookup(med["brand"], med.get("strength", ""))
        drafts.append(
            {
                "medId": util.new_id(),
                "brand": match["brand"] if match["matched"] else med["brand"],
                "scannedBrand": med["brand"],
                "salts": match["salts"],
                "saltMatched": match["matched"],
                "saltConfidence": match["confidence"],
                "saltSuggestion": match.get("bestGuess"),
                "strength": med["strength"] or (match["record"] or {}).get("strength", ""),
                "form": med["form"],
                "frequencyCode": med["frequencyCode"],
                "slots": schedule.slots_for(med["frequencyCode"]),
                "food": med["food"],
                "durationDays": med["durationDays"],
                "confidence": med["confidence"],
                "lowConfidence": med["lowConfidence"],
                "sourceText": med["sourceText"],
                "cropKey": storage.crop_key(scan_id, index),
                "stripSize": (match["record"] or {}).get("packSize"),
                "status": "NEEDS_REVIEW",
            }
        )

    # A duplicate is usually the second doctor's prescription overlapping the
    # first one, so check this scan against what the parent is already on.
    duplicates = salts.find_duplicates(drafts, existing=list_meds(parent_id))
    for dup in duplicates:
        notify.record_alert(
            parent_id,
            "DUPLICATE",
            dup["message"],
            dup["messageHi"],
            {"salt": dup["salt"], "brands": dup["brands"], "scanId": scan_id},
            dedupe_key=f"DUPLICATE#{dup['salt']}",
        )

    store().update(
        keys.parent(parent_id),
        keys.scan_sk(scan_id),
        {
            "status": "NEEDS_REVIEW",
            "engine": result.get("engine"),
            "repaired": result.get("repaired", False),
            "rawText": "\n".join(result.get("ocrLines", []))[:4000],
            "extractedJson": {
                "medicines": drafts,
                "duplicates": duplicates,
                "unreadableLines": result["unreadableLines"],
                "doctorName": result["doctorName"],
                "prescriptionDate": result["prescriptionDate"],
            },
            "finishedAt": util.iso(util.now_utc()),
        },
    )
    return get_scan(parent_id, scan_id)


def get_scan(parent_id: str, scan_id: str) -> Dict[str, Any]:
    scan = store().get(keys.parent(parent_id), keys.scan_sk(scan_id))
    if not scan:
        raise ApiError(404, "scan not found")
    extracted = scan.get("extractedJson") or {}
    return {
        "scanId": scan_id,
        "parentId": parent_id,
        "status": scan.get("status"),
        "engine": scan.get("engine"),
        "imageUrl": storage.presigned_get(scan["s3Key"]) if scan.get("s3Key") else None,
        "medicines": extracted.get("medicines", []),
        "duplicates": extracted.get("duplicates", []),
        "unreadableLines": extracted.get("unreadableLines", []),
        "doctorName": extracted.get("doctorName", ""),
        "prescriptionDate": extracted.get("prescriptionDate", ""),
        "error": scan.get("error"),
    }


# --------------------------------------------------------------------------
# Confirming medicines
# --------------------------------------------------------------------------


def confirm_meds(
    parent_id: str,
    medicines: List[Dict[str, Any]],
    scan_id: Optional[str] = None,
    days: int = 7,
) -> Dict[str, Any]:
    """Human check screen said yes. Nothing is saved before this point."""
    parent = get_parent(parent_id)
    timezone = parent.get("timezone", config.DEFAULT_TIMEZONE)
    now = util.iso(util.now_utc())
    saved: List[Dict[str, Any]] = []

    for med in medicines:
        med_id = med.get("medId") or util.new_id()
        salt_list = med.get("salts") or []
        manual = bool(med.get("saltsManual"))
        if not salt_list:
            match = salts.lookup(med.get("brand", ""), med.get("strength", ""))
            salt_list = match["salts"]
            manual = not match["matched"]

        item = {
            "PK": keys.parent(parent_id),
            "SK": keys.med_sk(med_id),
            "type": "MED",
            "parentId": parent_id,
            "medId": med_id,
            "brand": med.get("brand", "").strip(),
            "salts": salt_list,
            "saltsVerified": bool(salt_list) and not manual,
            "strength": med.get("strength", ""),
            "form": med.get("form", "tablet"),
            "frequencyCode": med.get("frequencyCode", ""),
            "slots": med.get("slots") or schedule.slots_for(med.get("frequencyCode", "")),
            "food": med.get("food", "any"),
            "countPerDose": int(med.get("countPerDose") or 1),
            "asNeeded": bool(med.get("asNeeded")),
            "startDate": med.get("startDate") or util.today_str(timezone),
            "endDate": med.get("endDate"),
            "durationDays": int(med.get("durationDays") or 0),
            "stripSize": med.get("stripSize"),
            "photoKey": med.get("photoKey"),
            "cropKey": med.get("cropKey"),
            "scanId": scan_id,
            "status": "ACTIVE",
            "confirmedAt": now,
        }
        store().put(item)
        saved.append(item)

    doses = schedule.build_doses(parent_id, saved, days=days, timezone=timezone)
    store().batch_put(doses)

    # The saved items are ACTIVE by now, so this reads the parent's whole
    # list and matches what the dashboard will show.
    duplicates = salts.find_duplicates(saved, existing=list_meds(parent_id))
    schedules = ensure_schedules(parent_id, saved)

    if scan_id:
        store().update(keys.parent(parent_id), keys.scan_sk(scan_id), {"status": "CONFIRMED"})

    return {
        "parentId": parent_id,
        "medicines": saved,
        "dosesCreated": len(doses),
        "duplicates": duplicates,
        "schedules": schedules,
    }


def ensure_schedules(parent_id: str, medicines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """One EventBridge Scheduler rule per slot that actually has medicine."""
    parent = get_parent(parent_id)
    timezone = parent.get("timezone", config.DEFAULT_TIMEZONE)
    wanted = sorted({slot for med in medicines for slot in (med.get("slots") or [])})
    created = []

    for slot in wanted:
        name = f"dosewise-{parent_id}-{slot.lower()}"
        entry = {
            "name": name,
            "slot": slot,
            "cron": schedule.slot_cron(slot),
            "timezone": timezone,
            "parentId": parent_id,
        }
        if config.IS_AWS:
            import json
            import os

            import boto3

            client = boto3.client("scheduler", region_name=config.REGION)
            params = {
                "Name": name,
                "GroupName": os.environ.get("SCHEDULER_GROUP", "default"),
                "ScheduleExpression": entry["cron"],
                "ScheduleExpressionTimezone": timezone,
                "FlexibleTimeWindow": {"Mode": "OFF"},
                "Target": {
                    "Arn": os.environ["ESCALATION_STATE_MACHINE_ARN"],
                    "RoleArn": os.environ["SCHEDULER_ROLE_ARN"],
                    "Input": json.dumps({"parentId": parent_id, "slot": slot}),
                },
            }
            try:
                client.create_schedule(**params)
                entry["action"] = "created"
            except client.exceptions.ConflictException:
                client.update_schedule(**params)
                entry["action"] = "updated"
        else:
            entry["action"] = "local"
        created.append(entry)

    store().put(
        {
            "PK": keys.parent(parent_id),
            "SK": "SCHEDULES",
            "type": "SCHEDULES",
            "parentId": parent_id,
            "entries": created,
            "updatedAt": util.iso(util.now_utc()),
        }
    )
    return created


def list_meds(parent_id: str, active_only: bool = True) -> List[Dict[str, Any]]:
    meds = store().query(keys.parent(parent_id), keys.MED_PREFIX)
    return [m for m in meds if not active_only or m.get("status") == "ACTIVE"]


# --------------------------------------------------------------------------
# The parent's day
# --------------------------------------------------------------------------


def today(parent_id: str, date: Optional[str] = None) -> Dict[str, Any]:
    parent = get_parent(parent_id)
    timezone = parent.get("timezone", config.DEFAULT_TIMEZONE)
    date = date or util.today_str(timezone)
    doses = store().query(keys.parent(parent_id), keys.dose_day_prefix(date))
    now = util.now_local(timezone)

    slots = []
    for slot in config.SLOT_ORDER:
        slot_doses = [d for d in doses if d.get("slot") == slot]
        if not slot_doses:
            continue
        hour, minute = (int(x) for x in schedule.slot_time(slot).split(":"))
        slot_local = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        pending = [d for d in slot_doses if d.get("status") == "PENDING"]
        slots.append(
            {
                "slot": slot,
                "time": schedule.slot_time(slot),
                "status": _slot_status(slot_doses),
                "isPast": slot_local < now,
                "doses": [
                    {
                        "medId": d["medId"],
                        "brand": d.get("brand"),
                        "strength": d.get("strength"),
                        "salts": d.get("salts", []),
                        "count": d.get("count", 1),
                        "food": d.get("food", "any"),
                        "status": d.get("status"),
                        "takenAt": d.get("takenAt"),
                        "photoUrl": storage.presigned_get(d["photoKey"]) if d.get("photoKey") else None,
                    }
                    for d in slot_doses
                ],
                "pillCount": sum(int(d.get("count", 1)) for d in slot_doses),
                "pendingCount": len(pending),
            }
        )

    next_slot = next(
        (s for s in slots if s["status"] == "PENDING" and not s["isPast"]),
        next((s for s in slots if s["status"] == "PENDING"), None),
    )
    return {
        "parentId": parent_id,
        "parentName": parent.get("name", ""),
        "language": parent.get("language", "hi"),
        "date": date,
        "slots": slots,
        "nextSlot": next_slot["slot"] if next_slot else None,
        "alerts": list_alerts(parent_id, unread_only=True),
    }


def _slot_status(doses: List[Dict[str, Any]]) -> str:
    statuses = {d.get("status") for d in doses}
    if statuses == {"TAKEN"}:
        return "TAKEN"
    if "PENDING" in statuses:
        return "PENDING"
    if "MISSED" in statuses:
        return "MISSED"
    return "TAKEN"


def mark_taken(
    parent_id: str,
    date: Optional[str] = None,
    slot: Optional[str] = None,
    med_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Idempotent. Pressing 'Le liya' twice is not an error, and a dose
    already marked TAKEN keeps its original timestamp."""
    parent = get_parent(parent_id)
    timezone = parent.get("timezone", config.DEFAULT_TIMEZONE)
    date = date or util.today_str(timezone)
    doses = store().query(keys.parent(parent_id), keys.dose_day_prefix(date))
    if slot:
        doses = [d for d in doses if d.get("slot") == slot]
    if med_id:
        doses = [d for d in doses if d.get("medId") == med_id]
    if not doses:
        raise ApiError(404, "no doses for that slot")

    now = util.iso(util.now_utc())
    changed = []
    for dose in doses:
        if dose.get("status") == "TAKEN":
            continue
        store().update(
            keys.parent(parent_id),
            dose["SK"],
            {"status": "TAKEN", "takenAt": now},
        )
        changed.append(dose["medId"])

    next_time = _next_slot_time(slot or doses[0].get("slot"))
    return {
        "parentId": parent_id,
        "date": date,
        "slot": slot,
        "marked": changed,
        "alreadyTaken": len(doses) - len(changed),
        "praise": voice.praise_text(slot or "", next_time, parent.get("language", "hi")),
    }


def undo_taken(parent_id: str, date: str, slot: str, med_id: Optional[str] = None) -> Dict[str, Any]:
    """Backs the five second Undo toast. Nothing in DoseWise is destructive.

    Undo has to mirror what was ticked: undoing a single medicine must not
    quietly un-take the rest of the slot.
    """
    doses = [
        d
        for d in store().query(keys.parent(parent_id), keys.dose_day_prefix(date))
        if d.get("slot") == slot and (med_id is None or d.get("medId") == med_id)
    ]
    for dose in doses:
        store().update(keys.parent(parent_id), dose["SK"], {"status": "PENDING", "takenAt": None})
    return {"parentId": parent_id, "date": date, "slot": slot, "medId": med_id, "reverted": len(doses)}


def _next_slot_time(slot: str) -> str:
    if slot in config.SLOT_ORDER:
        index = config.SLOT_ORDER.index(slot)
        if index + 1 < len(config.SLOT_ORDER):
            return schedule.slot_time(config.SLOT_ORDER[index + 1])
    return schedule.slot_time(config.SLOT_ORDER[0])


# --------------------------------------------------------------------------
# Alerts
# --------------------------------------------------------------------------


def list_alerts(parent_id: str, unread_only: bool = False, limit: int = 20) -> List[Dict[str, Any]]:
    alerts = store().query(keys.parent(parent_id), keys.ALERT_PREFIX)
    alerts.sort(key=lambda a: a.get("createdAt", ""), reverse=True)
    if unread_only:
        alerts = [a for a in alerts if not a.get("read")]
    return alerts[:limit]


def mark_alert_read(parent_id: str, sk: str) -> Dict[str, Any]:
    updated = store().update(keys.parent(parent_id), sk, {"read": True})
    if not updated:
        raise ApiError(404, "alert not found")
    return updated


# --------------------------------------------------------------------------
# Dashboard
# --------------------------------------------------------------------------


def dashboard(parent_id: str, days: int = 7) -> Dict[str, Any]:
    parent = get_parent(parent_id)
    timezone = parent.get("timezone", config.DEFAULT_TIMEZONE)
    today_date = dt.datetime.strptime(util.today_str(timezone), "%Y-%m-%d").date()
    meds = list_meds(parent_id)
    all_doses = store().query(keys.parent(parent_id), keys.DOSE_PREFIX)

    window_start = today_date - dt.timedelta(days=days - 1)
    timeline, taken_total, missed_total, pending_total = [], 0, 0, 0
    for offset in range(days):
        day = window_start + dt.timedelta(days=offset)
        key = day.strftime("%Y-%m-%d")
        day_doses = [d for d in all_doses if d.get("date") == key]
        taken = sum(1 for d in day_doses if d.get("status") == "TAKEN")
        missed = sum(1 for d in day_doses if d.get("status") == "MISSED")
        pending = sum(1 for d in day_doses if d.get("status") == "PENDING")
        taken_total += taken
        missed_total += missed
        pending_total += pending
        timeline.append(
            {
                "date": key,
                "weekday": day.strftime("%a"),
                "taken": taken,
                "missed": missed,
                "pending": pending,
                "total": len(day_doses),
            }
        )

    settled = taken_total + missed_total
    adherence = round(100 * taken_total / settled) if settled else 100

    taken_by_med: Dict[str, int] = {}
    for dose in all_doses:
        if dose.get("status") == "TAKEN":
            taken_by_med[dose["medId"]] = taken_by_med.get(dose["medId"], 0) + int(dose.get("count", 1))

    return {
        "parentId": parent_id,
        "parentName": parent.get("name", ""),
        "adherence": adherence,
        "takenCount": taken_total,
        "missedCount": missed_total,
        "pendingCount": pending_total,
        "timeline": timeline,
        "medicines": meds,
        "duplicates": salts.find_duplicates(meds),
        "savings": savings.savings_summary(meds),
        "refills": savings.refill_summary(meds, taken_by_med),
        "alerts": list_alerts(parent_id),
    }


def family_dashboard(family_id: str) -> Dict[str, Any]:
    parents = list_parents(family_id)
    return {
        "familyId": family_id,
        "parents": [dashboard(p["parentId"]) for p in parents],
        "caregivers": list_caregivers(family_id),
    }


def refresh_refill_alerts(parent_id: str) -> List[Dict[str, Any]]:
    data = dashboard(parent_id)
    created = []
    for refill in data["refills"]:
        if not refill["warn"]:
            continue
        created.append(
            notify.record_alert(
                parent_id,
                "REFILL",
                f"{refill['brand']} runs out in {refill['daysLeft']} days ({refill['runsOutOn']}).",
                f"{refill['brand']} {refill['daysLeft']} din mein khatam ho jayegi.",
                {"medId": refill["medId"], "daysLeft": refill["daysLeft"]},
                dedupe_key=f"REFILL#{refill['medId']}",
            )
        )
    return created


# --------------------------------------------------------------------------
# Voice
# --------------------------------------------------------------------------


def slot_voice(parent_id: str, slot: str, date: Optional[str] = None) -> Dict[str, Any]:
    parent = get_parent(parent_id)
    language = parent.get("language", "hi")
    timezone = parent.get("timezone", config.DEFAULT_TIMEZONE)
    date = date or util.today_str(timezone)
    doses = [
        d
        for d in store().query(keys.parent(parent_id), keys.dose_day_prefix(date))
        if d.get("slot") == slot
    ]
    text = voice.reminder_text(slot, doses, parent.get("name", ""), language)
    audio = voice.synthesize(text["spoken"], language)
    return {**text, **audio, "slot": slot, "date": date}


# --------------------------------------------------------------------------
# Doctor Visit Card
# --------------------------------------------------------------------------


def visit_card(parent_id: str) -> Dict[str, Any]:
    from . import visitcard

    data = dashboard(parent_id, days=30)
    card_id = util.new_id()
    html = visitcard.render_html(data)
    pdf_bytes = visitcard.render_pdf(html, data)

    key = storage.visit_card_key(parent_id, card_id)
    storage.put_bytes(key, pdf_bytes, "application/pdf")
    url = storage.presigned_get(key, expires=24 * 3600)

    store().put(
        {
            "PK": keys.parent(parent_id),
            "SK": f"VISITCARD#{card_id}",
            "type": "VISITCARD",
            "parentId": parent_id,
            "cardId": card_id,
            "s3Key": key,
            "createdAt": util.iso(util.now_utc()),
            "expiresAt": int((util.now_utc() + dt.timedelta(hours=24)).timestamp()),
        }
    )
    return {"cardId": card_id, "key": key, "url": url, "expiresInHours": 24, "html": html}
