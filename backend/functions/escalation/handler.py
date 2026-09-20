"""Dose escalation tasks (Standard state machine, one execution per dose slot).

  SendReminder -> Wait30 -> CheckTaken -> Nudge -> Wait30 -> CheckTaken
                                       -> AlertFamily -> MarkMissed

Waits live in the state machine, not in Lambda, so nothing bills while the
family is getting on with their evening. Demo mode drops the waits to 30
seconds; the state machine reads the wait length from this module's output.
"""
from typing import Any, Dict, List

from common import config, keys, notify, services, util, voice
from common.store import store


def _doses(parent_id: str, date: str, slot: str) -> List[Dict[str, Any]]:
    return [
        d
        for d in store().query(keys.parent(parent_id), keys.dose_day_prefix(date))
        if d.get("slot") == slot
    ]


def _context(event: Dict[str, Any]) -> Dict[str, Any]:
    parent = services.get_parent(event["parentId"])
    timezone = parent.get("timezone", config.DEFAULT_TIMEZONE)
    date = event.get("date") or util.today_str(timezone)
    return {"parent": parent, "date": date, "slot": event["slot"]}


def send_reminder(event: Dict[str, Any], context=None) -> Dict[str, Any]:
    """In-app voice first, SMS second. Voice is free; SMS costs money."""
    ctx = _context(event)
    parent, date, slot = ctx["parent"], ctx["date"], ctx["slot"]
    doses = _doses(parent["parentId"], date, slot)
    if not doses:
        return {**event, "date": date, "skipped": "no doses in this slot", "waitSeconds": 0}

    language = parent.get("language", "hi")
    text = voice.reminder_text(slot, doses, parent.get("name", ""), language)
    audio = voice.synthesize(text["spoken"], language)

    sms = None
    if parent.get("phone"):
        sms = notify.send_sms(parent["phone"], text["caption"])

    return {
        **event,
        "date": date,
        "attempt": 1,
        "voiceKey": audio.get("key"),
        "caption": text["caption"],
        "smsSent": bool(sms),
        "waitSeconds": config.WAIT_FIRST_SECONDS,
    }


def check_taken(event: Dict[str, Any], context=None) -> Dict[str, Any]:
    ctx = _context(event)
    doses = _doses(ctx["parent"]["parentId"], ctx["date"], ctx["slot"])
    pending = [d for d in doses if d.get("status") == "PENDING"]
    return {
        **event,
        "date": ctx["date"],
        "taken": len(pending) == 0,
        "pendingCount": len(pending),
    }


def nudge(event: Dict[str, Any], context=None) -> Dict[str, Any]:
    """Second, gentler reminder. Amber, never red: a missed dose is not an
    emergency and the parent should not be frightened by their phone."""
    ctx = _context(event)
    parent, date, slot = ctx["parent"], ctx["date"], ctx["slot"]
    doses = _doses(parent["parentId"], date, slot)
    language = parent.get("language", "hi")
    text = voice.reminder_text(slot, doses, parent.get("name", ""), language)
    voice.synthesize(text["spoken"], language)
    if parent.get("phone"):
        notify.send_sms(parent["phone"], text["caption"])
    return {**event, "date": date, "attempt": 2, "waitSeconds": config.WAIT_SECOND_SECONDS}


def alert_family(event: Dict[str, Any], context=None) -> Dict[str, Any]:
    ctx = _context(event)
    parent, date, slot = ctx["parent"], ctx["date"], ctx["slot"]
    doses = _doses(parent["parentId"], date, slot)
    names = ", ".join(sorted({d.get("brand", "") for d in doses if d.get("brand")}))
    time_label = {"MORNING": "morning", "AFTERNOON": "afternoon", "NIGHT": "night"}.get(slot, slot)
    who = parent.get("name") or "Your parent"
    message = f"{who} has not taken the {time_label} medicine ({names})."

    caregivers = services.list_caregivers(parent["familyId"])
    sent = notify.alert_family(parent, caregivers, message)
    alert = notify.record_alert(
        parent["parentId"],
        "MISSED",
        message,
        f"{who} ne {time_label} ki dawa nahin li.",
        {"slot": slot, "date": date},
        dedupe_key=f"MISSED#{date}#{slot}",
    )
    return {**event, "date": date, "alerted": len(sent), "alertSk": alert["SK"]}


def mark_missed(event: Dict[str, Any], context=None) -> Dict[str, Any]:
    ctx = _context(event)
    parent_id, date, slot = ctx["parent"]["parentId"], ctx["date"], ctx["slot"]
    changed = 0
    for dose in _doses(parent_id, date, slot):
        if dose.get("status") == "PENDING":
            store().update(keys.parent(parent_id), dose["SK"], {"status": "MISSED"})
            changed += 1
    return {**event, "date": date, "missed": changed, "done": True}


def top_up_doses(event: Dict[str, Any], context=None) -> Dict[str, Any]:
    """Nightly: keep a rolling 7 days of DOSE items so the schedule never
    runs dry, and refresh Refill Radar alerts."""
    created, refills = 0, 0
    for item in store().scan_prefix("FAMILY#"):
        if item.get("type") != "PARENT":
            continue
        parent_id = item["parentId"]
        meds = services.list_meds(parent_id)
        if not meds:
            continue
        from common import schedule

        doses = schedule.build_doses(parent_id, meds, days=7, timezone=item.get("timezone"))
        existing = {d["SK"] for d in store().query(keys.parent(parent_id), keys.DOSE_PREFIX)}
        fresh = [d for d in doses if d["SK"] not in existing]
        created += store().batch_put(fresh) if fresh else 0
        refills += len(services.refresh_refill_alerts(parent_id))
    return {"dosesCreated": created, "refillAlerts": refills}
