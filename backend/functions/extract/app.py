"""
backend/functions/extract/app.py
Lambda handler for the DoseWise Prescription Extraction step.

Reads a prescription image from S3, calls Amazon Textract for OCR,
then passes the image + OCR text to Bedrock (Claude 3) to extract
structured medicine data matching the schema in extraction_v1.txt.

Event shape expected (from Step Functions / S3 trigger bridge):
{
    "scanId": "scan-xxx",
    "s3Bucket": "dosewise-uploads-bucket",
    "s3Key":    "uploads/user-id/filename.jpg"
}

Returns:
{
    "scanId":           "scan-xxx",
    "s3Key":            "uploads/user-id/filename.jpg",
    "medicines":        [...],
    "unreadable_lines": [...]
}
"""

import base64
import json
import logging
import os
import re

import boto3

# ─── Logging ──────────────────────────────────────────────────────────────────
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# ─── AWS Clients (module-level for Lambda container reuse) ────────────────────
_REGION = os.environ.get("AWS_REGION", "ap-south-1")
_s3 = boto3.client("s3", region_name=_REGION)
_textract = boto3.client("textract", region_name=_REGION)
_bedrock = boto3.client("bedrock-runtime", region_name=_REGION)

# ─── Config ───────────────────────────────────────────────────────────────────
_MODEL_ID = os.environ.get(
    "BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0"
)
_PROMPT_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "extraction_v1.txt"
)

# Load prompt once at init time
try:
    with open(_PROMPT_PATH, "r", encoding="utf-8") as _fh:
        _SYSTEM_PROMPT: str = _fh.read()
    logger.info("Loaded extraction prompt (%d chars).", len(_SYSTEM_PROMPT))
except FileNotFoundError:
    _SYSTEM_PROMPT = (
        "Extract medicines from the prescription as JSON with keys: "
        "brand, strength, form, frequency_code, food, duration_days, confidence, source_text."
    )
    logger.warning("extraction_v1.txt not found — using fallback prompt.")


# ─── Helpers ──────────────────────────────────────────────────────────────────
def _get_image_bytes(bucket: str, key: str) -> bytes:
    logger.info("Fetching s3://%s/%s", bucket, key)
    obj = _s3.get_object(Bucket=bucket, Key=key)
    return obj["Body"].read()


def _textract_ocr(image_bytes: bytes) -> str:
    logger.info("Calling Textract DetectDocumentText …")
    response = _textract.detect_document_text(Document={"Bytes": image_bytes})
    lines = [
        block["Text"]
        for block in response.get("Blocks", [])
        if block["BlockType"] == "LINE"
    ]
    return "\n".join(lines)


def _bedrock_extract(image_bytes: bytes, ocr_text: str) -> str:
    logger.info("Calling Bedrock model=%s …", _MODEL_ID)
    b64_image = base64.b64encode(image_bytes).decode("utf-8")

    # Infer media type from first bytes (JPEG magic bytes FF D8; else assume PNG)
    media_type = "image/jpeg" if image_bytes[:2] == b"\xff\xd8" else "image/png"

    body = json.dumps(
        {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1500,
            "system": _SYSTEM_PROMPT,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": b64_image,
                            },
                        },
                        {
                            "type": "text",
                            "text": (
                                f"Raw OCR text from Textract:\n<ocr>\n{ocr_text}\n</ocr>\n\n"
                                "Extract all medicines as instructed. Return ONLY valid JSON."
                            ),
                        },
                    ],
                }
            ],
        }
    )

    response = _bedrock.invoke_model(
        modelId=_MODEL_ID,
        body=body,
        contentType="application/json",
        accept="application/json",
    )
    body_str = response["body"].read()
    response_body = json.loads(body_str)
    return response_body["content"][0]["text"]


def _parse_bedrock_response(raw: str) -> dict:
    """
    Extract the JSON object from Bedrock's response.
    Claude may wrap the JSON in markdown code fences — strip them first.
    """
    # Remove ```json ... ``` fences
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse Bedrock JSON: %s\nRaw: %s", exc, raw[:500])
        raise ValueError(f"Bedrock returned non-JSON: {exc}") from exc


# ─── Lambda Handler ───────────────────────────────────────────────────────────
def handler(event: dict, context) -> dict:  # noqa: ANN001
    """
    AWS Lambda entrypoint — called by Step Functions.

    Input  : { scanId, s3Bucket, s3Key }
    Output : { scanId, s3Key, medicines, unreadable_lines }
    """
    scan_id = event.get("scanId", "unknown")
    bucket = event.get("s3Bucket")
    key = event.get("s3Key")

    logger.info("ExtractLambda invoked. scanId=%s, s3Key=%s", scan_id, key)

    if not bucket or not key:
        raise ValueError("'s3Bucket' and 's3Key' are required in the event payload.")

    # 1. Fetch image from S3
    image_bytes = _get_image_bytes(bucket, key)

    # 2. OCR via Textract
    ocr_text = _textract_ocr(image_bytes)
    logger.info("Textract returned %d lines.", ocr_text.count("\n") + 1)

    # 3. Extraction via Bedrock
    raw_response = _bedrock_extract(image_bytes, ocr_text)

    # 4. Parse structured output
    parsed = _parse_bedrock_response(raw_response)

    medicines = parsed.get("medicines", [])
    unreadable = parsed.get("unreadable_lines", [])

    logger.info(
        "Extraction complete. %d medicines, %d unreadable lines.",
        len(medicines),
        len(unreadable),
    )

    return {
        "scanId": scan_id,
        "s3Bucket": bucket,
        "s3Key": key,
        "medicines": medicines,
        "unreadable_lines": unreadable,
    }


# ─── Local Test Harness ───────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 4:
        print("Usage: python app.py <bucket> <key> <scan_id>")
        sys.exit(1)

    _test_event = {
        "s3Bucket": sys.argv[1],
        "s3Key": sys.argv[2],
        "scanId": sys.argv[3],
    }
    result = handler(_test_event, None)
    print(json.dumps(result, indent=2))
