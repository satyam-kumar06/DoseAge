"""Doctor Visit Card: render, store in S3, hand back a 24 hour link."""
from typing import Any, Dict

from common import services, util


def lambda_handler(event: Dict[str, Any], context=None) -> Dict[str, Any]:
    parent_id = event.get("parentId") or (event.get("pathParameters") or {}).get("parentId")
    if not parent_id:
        return util.json_response(400, {"error": "parentId is required"})
    card = services.visit_card(parent_id)
    card.pop("html", None)  # the link serves the page; keep the response small
    return util.json_response(200, card)
