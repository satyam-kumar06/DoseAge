"""One router, two front doors.

The API Gateway Lambda and the local dev server both call `dispatch`, so the
offline build exercises exactly the same code path that runs on AWS.
"""
import re
from typing import Any, Callable, Dict, List, Optional, Tuple

from . import notify, services
from .util import ApiError

Handler = Callable[..., Any]
ROUTES: List[Tuple[str, re.Pattern, Handler]] = []


def route(method: str, pattern: str):
    regex = re.compile("^" + re.sub(r"\{(\w+)\}", r"(?P<\1>[^/]+)", pattern) + "$")

    def wrap(fn: Handler):
        ROUTES.append((method.upper(), regex, fn))
        return fn

    return wrap


def dispatch(
    method: str, path: str, body: Optional[Dict[str, Any]] = None, query: Optional[Dict[str, str]] = None
) -> Tuple[int, Any]:
    body = body or {}
    query = query or {}
    path = "/" + path.strip("/")
    if method.upper() == "OPTIONS":
        return 204, {}

    for route_method, regex, fn in ROUTES:
        match = regex.match(path)
        if not match:
            continue
        if route_method != method.upper():
            continue
        try:
            return 200, fn(body=body, query=query, **match.groupdict())
        except ApiError as exc:
            return exc.status, {"error": exc.message}
        except KeyError as exc:
            return 400, {"error": f"missing field {exc}"}
        except ValueError as exc:
            return 400, {"error": str(exc)}
    return 404, {"error": f"no route for {method} {path}"}


# --------------------------------------------------------------------------
# Health and demo helpers
# --------------------------------------------------------------------------


@route("GET", "/health")
def health(**_):
    from . import config, extraction

    return {
        "ok": True,
        "backend": config.BACKEND,
        "demoMode": config.DEMO_MODE,
        "bedrock": config.BEDROCK_ENABLED,
        "polly": config.POLLY_ENABLED,
        "sms": config.SNS_ENABLED,
        "fixtures": extraction.list_fixtures(),
    }


@route("GET", "/outbox")
def outbox(**_):
    """What would have been texted. Local mode only, handy in the demo."""
    return {"messages": notify.read_outbox()}


# --------------------------------------------------------------------------
# Families and parents
# --------------------------------------------------------------------------


@route("POST", "/families")
def post_families(body, **_):
    return services.create_family(body.get("name", "My family"), body.get("caregiver"))


@route("POST", "/families/{familyId}/caregivers")
def post_caregiver(body, familyId, **_):
    return services.add_caregiver(familyId, body)


@route("GET", "/families/{familyId}")
def get_family(familyId, **_):
    return {
        "familyId": familyId,
        "parents": services.list_parents(familyId),
        "caregivers": services.list_caregivers(familyId),
    }


@route("GET", "/families/{familyId}/dashboard")
def get_family_dashboard(familyId, **_):
    return services.family_dashboard(familyId)


@route("POST", "/parents")
def post_parents(body, **_):
    family_id = body.get("familyId")
    if not family_id:
        raise ApiError(400, "familyId is required")
    return services.add_parent(family_id, body)


@route("GET", "/parents/{parentId}")
def get_parent(parentId, **_):
    return services.get_parent(parentId)


# --------------------------------------------------------------------------
# Scanning and review
# --------------------------------------------------------------------------


@route("POST", "/scans/upload-url")
def post_upload_url(body, **_):
    parent_id = body.get("parentId")
    if not parent_id:
        raise ApiError(400, "parentId is required")
    return services.upload_url(parent_id, body.get("contentType", "image/jpeg"))


@route("POST", "/scans/{scanId}/start")
def post_start_scan(body, scanId, **_):
    parent_id = body.get("parentId")
    if not parent_id:
        raise ApiError(400, "parentId is required")
    return services.start_scan(parent_id, scanId, body.get("fixture"))


@route("GET", "/scans/{scanId}")
def get_scan(scanId, query, **_):
    parent_id = query.get("parentId")
    if not parent_id:
        raise ApiError(400, "parentId query param is required")
    return services.get_scan(parent_id, scanId)


@route("POST", "/meds/confirm")
def post_confirm(body, **_):
    parent_id = body.get("parentId")
    if not parent_id:
        raise ApiError(400, "parentId is required")
    return services.confirm_meds(parent_id, body.get("medicines", []), body.get("scanId"))


@route("GET", "/parents/{parentId}/meds")
def get_meds(parentId, **_):
    return {"medicines": services.list_meds(parentId)}


# --------------------------------------------------------------------------
# The parent's day
# --------------------------------------------------------------------------


@route("GET", "/parents/{parentId}/today")
def get_today(parentId, query, **_):
    return services.today(parentId, query.get("date"))


@route("POST", "/doses/{parentId}/taken")
def post_taken(body, parentId, **_):
    return services.mark_taken(parentId, body.get("date"), body.get("slot"), body.get("medId"))


@route("POST", "/doses/{parentId}/undo")
def post_undo(body, parentId, **_):
    return services.undo_taken(parentId, body["date"], body["slot"], body.get("medId"))


@route("GET", "/parents/{parentId}/voice")
def get_voice(parentId, query, **_):
    slot = query.get("slot")
    if not slot:
        raise ApiError(400, "slot query param is required")
    return services.slot_voice(parentId, slot, query.get("date"))


# --------------------------------------------------------------------------
# Caregiver views
# --------------------------------------------------------------------------


@route("GET", "/parents/{parentId}/dashboard")
def get_dashboard(parentId, query, **_):
    return services.dashboard(parentId, int(query.get("days", 7)))


@route("GET", "/parents/{parentId}/alerts")
def get_alerts(parentId, query, **_):
    return {"alerts": services.list_alerts(parentId, query.get("unread") == "1")}


@route("POST", "/parents/{parentId}/alerts/read")
def post_alert_read(body, parentId, **_):
    return services.mark_alert_read(parentId, body["sk"])


@route("POST", "/parents/{parentId}/visit-card")
def post_visit_card(parentId, **_):
    return services.visit_card(parentId)


@route("POST", "/parents/{parentId}/refills/check")
def post_refill_check(parentId, **_):
    return {"alerts": services.refresh_refill_alerts(parentId)}
