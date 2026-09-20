"""Polly Hindi voice, cached in S3 so the same line is never paid for twice."""
from typing import Any, Dict

from common import services, util, voice


def lambda_handler(event: Dict[str, Any], context=None) -> Dict[str, Any]:
    parent_id = event.get("parentId")
    slot = event.get("slot")
    if not parent_id or not slot:
        return util.json_response(400, {"error": "parentId and slot are required"})
    return util.json_response(200, services.slot_voice(parent_id, slot, event.get("date")))


def synthesize(event: Dict[str, Any], context=None) -> Dict[str, Any]:
    """Direct text synthesis, used to pre-warm the cache after confirmation."""
    return voice.synthesize(event["text"], event.get("language", "hi"))
