"""Prescription reading: Textract for text, Bedrock vision for structure.

Textract runs first because it is cheap and handles printed lines well; its
output goes into the Bedrock prompt as a hint, which cuts tokens and raises
accuracy on handwriting. If Bedrock returns malformed JSON we send one repair
prompt before giving up.

With no AWS account the same function returns a fixture, so every screen
downstream can be built and demoed offline.
"""
import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from . import config, storage

PROMPT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "prompts")
EXTRACTION_PROMPT = "extraction_v2.txt"
REPAIR_PROMPT = "repair_v1.txt"

VALID_FOOD = {"before", "after", "any"}
VALID_FORMS = {"tablet", "capsule", "syrup", "injection", "drops", "cream", "other"}


# Magic bytes -> the format name Bedrock's Converse API expects. A phone photo
# saved as ".jpg" is not always a JPEG, and the extension is the least reliable
# thing about an uploaded file.
_MAGIC = [
    (b"\xff\xd8\xff", "jpeg"),
    (b"\x89PNG\r\n\x1a\n", "png"),
    (b"GIF87a", "gif"),
    (b"GIF89a", "gif"),
]


def image_format(image_bytes: bytes, key: str = "") -> Optional[str]:
    """jpeg | png | gif | webp, or None when it is something else (HEIC, PDF)."""
    for magic, name in _MAGIC:
        if image_bytes.startswith(magic):
            return name
    if image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
        return "webp"
    return None


def load_prompt(name: str) -> str:
    with open(os.path.join(PROMPT_DIR, name), "r", encoding="utf-8") as fh:
        return fh.read()


# --------------------------------------------------------------------------
# Step 1: Textract
# --------------------------------------------------------------------------

def textract_lines(image_bytes: bytes) -> Tuple[List[str], Optional[str]]:
    """Printed lines, plus the reason if we could not get them.

    Textract is an optimisation: its output goes into the prompt as a hint and
    cuts tokens. It is NOT required to read a prescription, so a Textract
    failure must never fail the scan. Some phone photos come back as
    UnsupportedDocumentException here while Bedrock reads them perfectly well.
    """
    if not config.TEXTRACT_ENABLED:
        return [], None
    import boto3

    try:
        client = boto3.client("textract", region_name=config.REGION)
        res = client.detect_document_text(Document={"Bytes": image_bytes})
        return [b["Text"] for b in res.get("Blocks", []) if b["BlockType"] == "LINE"], None
    except Exception as exc:  # noqa: BLE001 - degrade, never fail
        return [], f"{type(exc).__name__}: {exc}"[:300]


# --------------------------------------------------------------------------
# Step 2: Bedrock vision
# --------------------------------------------------------------------------

def _bedrock_call(image_bytes: bytes, prompt: str, fmt: str = "jpeg") -> str:
    """One vision call, through Bedrock's Converse API.

    Converse is model-agnostic: the same request works for Anthropic Claude,
    Amazon Nova and the rest. That matters here because which model an account
    can actually reach varies (Marketplace subscriptions, Legacy retirement,
    seller-of-record rules), so the model is a deploy-time parameter and no
    code changes when it moves.
    """
    import boto3

    client = boto3.client("bedrock-runtime", region_name=config.BEDROCK_REGION)
    res = client.converse(
        modelId=config.BEDROCK_MODEL_ID,
        messages=[
            {
                "role": "user",
                "content": [
                    {"image": {"format": fmt, "source": {"bytes": image_bytes}}},
                    {"text": prompt},
                ],
            }
        ],
        inferenceConfig={"maxTokens": 4000, "temperature": 0},
    )
    parts = res.get("output", {}).get("message", {}).get("content", [])
    return "".join(part.get("text", "") for part in parts if "text" in part)


def _parse_json(text: str) -> Dict[str, Any]:
    """Models sometimes wrap JSON in a fence or add a sentence. Dig it out."""
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object in response")
    return json.loads(text[start : end + 1])


# --------------------------------------------------------------------------
# Normalisation
# --------------------------------------------------------------------------

def normalise_result(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Coerce whatever came back into the shape the frontend can rely on."""
    medicines = []
    for entry in raw.get("medicines") or []:
        if not isinstance(entry, dict):
            continue
        brand = str(entry.get("brand") or "").strip()
        if not brand:
            continue
        try:
            confidence = float(entry.get("confidence", 0.5))
        except (TypeError, ValueError):
            confidence = 0.5
        try:
            duration = int(float(entry.get("duration_days") or 0))
        except (TypeError, ValueError):
            duration = 0
        food = str(entry.get("food") or "any").strip().lower()
        form = str(entry.get("form") or "tablet").strip().lower()
        medicines.append(
            {
                "brand": brand,
                "strength": str(entry.get("strength") or "").strip(),
                "form": form if form in VALID_FORMS else "other",
                "frequencyCode": str(entry.get("frequency_code") or "").strip(),
                "food": food if food in VALID_FOOD else "any",
                "durationDays": max(duration, 0),
                "confidence": min(max(confidence, 0.0), 1.0),
                "sourceText": str(entry.get("source_text") or "").strip(),
                "lowConfidence": min(max(confidence, 0.0), 1.0) < config.LOW_CONFIDENCE,
            }
        )
    return {
        "medicines": medicines,
        "unreadableLines": [str(x) for x in (raw.get("unreadable_lines") or [])],
        "doctorName": str(raw.get("doctor_name") or "").strip(),
        "prescriptionDate": str(raw.get("prescription_date") or "").strip(),
    }


# --------------------------------------------------------------------------
# Offline fixture
# --------------------------------------------------------------------------

FIXTURE_DIR = os.path.join(config.DATA_DIR, "sample_prescriptions")


def fixture(name: Optional[str] = None) -> Dict[str, Any]:
    """Canned extraction so the product runs with no AWS account.

    The default fixture is the demo story: three doctors, two paracetamols.
    """
    name = name or os.environ.get("MOCK_SCAN_FIXTURE", "family_demo")
    path = os.path.join(FIXTURE_DIR, f"{name}.json")
    if not os.path.exists(path):
        path = os.path.join(FIXTURE_DIR, "family_demo.json")
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def list_fixtures() -> List[str]:
    if not os.path.isdir(FIXTURE_DIR):
        return []
    return sorted(f[:-5] for f in os.listdir(FIXTURE_DIR) if f.endswith(".json"))


# --------------------------------------------------------------------------
# The one function everything else calls
# --------------------------------------------------------------------------

def extract(
    image_key: Optional[str] = None,
    image_bytes: Optional[bytes] = None,
    fixture_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Read a prescription image into structured medicines.

    Returns {medicines, unreadableLines, doctorName, prescriptionDate,
    ocrLines, engine, repaired}.
    """
    if not config.BEDROCK_ENABLED:
        result = normalise_result(fixture(fixture_name))
        result.update({"ocrLines": [], "engine": "fixture", "repaired": False})
        return result

    if image_bytes is None:
        if not image_key:
            raise ValueError("extract needs image_bytes or image_key")
        image_bytes = storage.get_bytes(image_key)

    fmt = image_format(image_bytes, image_key or "")
    if fmt is None:
        raise ValueError(
            "That file is not a JPEG, PNG, GIF or WEBP image. Photos from some "
            "phones save as HEIC; re-save or screenshot it and try again."
        )

    lines, ocr_error = textract_lines(image_bytes)
    prompt = load_prompt(EXTRACTION_PROMPT).replace("{ocr_text}", "\n".join(lines) or "(none)")

    response = _bedrock_call(image_bytes, prompt, fmt)

    repaired = False
    try:
        raw = _parse_json(response)
    except (ValueError, json.JSONDecodeError) as exc:
        repair = (
            load_prompt(REPAIR_PROMPT)
            .replace("{error}", str(exc))
            .replace("{previous}", response[:4000])
        )
        response = _bedrock_call(image_bytes, repair, fmt)
        raw = _parse_json(response)
        repaired = True

    result = normalise_result(raw)
    result.update(
        {
            "ocrLines": lines,
            "ocrError": ocr_error,
            "imageFormat": fmt,
            "engine": "bedrock",
            "repaired": repaired,
        }
    )
    return result
