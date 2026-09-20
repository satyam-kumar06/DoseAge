"""Duplicate salt guard as its own Lambda. Deterministic: same input, same
answer, every time. This is the claim we make to judges about safety."""
from typing import Any, Dict

from common import notify, salts


def lambda_handler(event: Dict[str, Any], context=None) -> Dict[str, Any]:
    duplicates = salts.find_duplicates(event.get("medicines", []))
    if event.get("recordAlerts") and event.get("parentId"):
        for dup in duplicates:
            notify.record_alert(
                event["parentId"],
                "DUPLICATE",
                dup["message"],
                dup["messageHi"],
                {"salt": dup["salt"], "brands": dup["brands"]},
                dedupe_key=f"DUPLICATE#{dup['salt']}",
            )
    return {"duplicates": duplicates, "count": len(duplicates)}
