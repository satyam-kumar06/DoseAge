"""Small helpers shared by every Lambda."""
import datetime as dt
import json
import uuid
from typing import Any, Dict, Optional

from . import config

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - Python < 3.9
    ZoneInfo = None  # type: ignore


def new_id(prefix: str = "") -> str:
    raw = uuid.uuid4().hex[:12]
    return f"{prefix}{raw}" if prefix else raw


def tz(name: Optional[str] = None):
    name = name or config.DEFAULT_TIMEZONE
    if ZoneInfo is None:
        return dt.timezone(dt.timedelta(hours=5, minutes=30))
    try:
        return ZoneInfo(name)
    except Exception:
        return dt.timezone(dt.timedelta(hours=5, minutes=30))


def now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def now_local(timezone: Optional[str] = None) -> dt.datetime:
    return now_utc().astimezone(tz(timezone))


def iso(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def today_str(timezone: Optional[str] = None) -> str:
    return now_local(timezone).strftime("%Y-%m-%d")


def parse_iso(value: str) -> dt.datetime:
    value = value.replace("Z", "+00:00")
    parsed = dt.datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed


def json_response(status: int, body: Any, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """API Gateway HTTP API proxy response.

    No CORS headers here on purpose. The HTTP API's own CorsConfiguration adds
    them, and if the integration returns them too the browser sees
    "Access-Control-Allow-Origin: *, *", rejects the response, and the fetch
    fails with the unhelpful message "Failed to fetch". The local dev server
    sets its own headers separately, so both paths stay correct.
    """
    base = {"Content-Type": "application/json"}
    if headers:
        base.update(headers)
    return {
        "statusCode": status,
        "headers": base,
        "body": json.dumps(body, ensure_ascii=False, default=str),
    }


def ok(body: Any):
    return json_response(200, body)


def bad_request(message: str, **extra):
    return json_response(400, {"error": message, **extra})


def not_found(message: str = "not found"):
    return json_response(404, {"error": message})


class ApiError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message
