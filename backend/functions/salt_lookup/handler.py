"""Brand to salt lookup as its own Lambda, callable from the state machine."""
from typing import Any, Dict

from common import salts


def lambda_handler(event: Dict[str, Any], context=None) -> Dict[str, Any]:
    if "brand" in event:
        return salts.lookup(event["brand"], event.get("strength", ""))
    return {
        "results": [
            salts.lookup(m.get("brand", ""), m.get("strength", ""))
            for m in event.get("medicines", [])
        ]
    }
