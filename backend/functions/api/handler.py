"""API Gateway HTTP API entry point. All routing lives in common.router."""
import json
from typing import Any, Dict

from common import router, util


def lambda_handler(event: Dict[str, Any], context=None) -> Dict[str, Any]:
    http = event.get("requestContext", {}).get("http", {})
    method = http.get("method") or event.get("httpMethod") or "GET"
    path = http.get("path") or event.get("rawPath") or "/"

    stage = event.get("requestContext", {}).get("stage")
    if stage and stage not in ("$default", "") and path.startswith(f"/{stage}"):
        path = path[len(stage) + 1 :] or "/"

    raw_body = event.get("body") or ""
    if event.get("isBase64Encoded") and raw_body:
        import base64

        raw_body = base64.b64decode(raw_body).decode("utf-8")
    try:
        body = json.loads(raw_body) if raw_body else {}
    except json.JSONDecodeError:
        return util.json_response(400, {"error": "body is not valid JSON"})

    query = event.get("queryStringParameters") or {}

    status, payload = router.dispatch(method, path, body, query)
    return util.json_response(status, payload)
