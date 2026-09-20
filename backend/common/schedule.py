"""Turning a confirmed prescription into dated dose items.

A frequency code is the Indian shorthand: 1-0-1 means one in the morning,
none in the afternoon, one at night.
"""
import datetime as dt
import re
from typing import Any, Dict, List, Optional

from . import config, keys, util

SLOTS = config.SLOT_ORDER


def parse_frequency(code: str) -> Dict[str, int]:
    """'1-0-1' -> {MORNING: 1, AFTERNOON: 0, NIGHT: 1}.

    Tolerates '1 0 1', '1/0/1', 'SOS', 'OD', 'BD', 'TDS', 'HS'.
    """
    empty = {slot: 0 for slot in SLOTS}
    if not code:
        return empty
    text = str(code).strip().upper()

    words = {
        "OD": (1, 0, 0),
        "ONCE DAILY": (1, 0, 0),
        "BD": (1, 0, 1),
        "BID": (1, 0, 1),
        "TWICE DAILY": (1, 0, 1),
        "TDS": (1, 1, 1),
        "TID": (1, 1, 1),
        "THRICE DAILY": (1, 1, 1),
        "HS": (0, 0, 1),
        "AT NIGHT": (0, 0, 1),
        "SOS": (0, 0, 0),
    }
    if text in words:
        return dict(zip(SLOTS, words[text]))

    parts = [p for p in re.split(r"[-/\s]+", text) if p != ""]
    nums: List[int] = []
    for part in parts:
        try:
            nums.append(int(float(part)))
        except ValueError:
            frac = {"1/2": 1, "½": 1}.get(part)
            nums.append(frac if frac else 0)
    if len(nums) == 3:
        return dict(zip(SLOTS, nums))
    if len(nums) == 2:  # morning and night is the usual reading
        return {"MORNING": nums[0], "AFTERNOON": 0, "NIGHT": nums[1]}
    if len(nums) == 1:
        return {"MORNING": nums[0], "AFTERNOON": 0, "NIGHT": 0}
    return empty


def slots_for(code: str) -> List[str]:
    counts = parse_frequency(code)
    return [slot for slot in SLOTS if counts.get(slot, 0) > 0]


def slot_time(slot: str) -> str:
    return config.SLOT_TIMES.get(slot, "08:00")


def scheduled_at(date: str, slot: str, timezone: Optional[str] = None) -> str:
    hour, minute = (int(x) for x in slot_time(slot).split(":"))
    local = dt.datetime.strptime(date, "%Y-%m-%d").replace(
        hour=hour, minute=minute, tzinfo=util.tz(timezone)
    )
    return util.iso(local)


def slot_counts(med: Dict[str, Any]) -> Dict[str, int]:
    """How many units in each slot.

    An explicit `slots` list wins over the written frequency code. The review
    screen lets a caregiver set the timing by hand when the prescription did
    not say ("Tab Thyroxine" with no 1-0-1 on the page), and their answer has
    to be what actually gets scheduled - reading the code instead silently
    produced no doses at all.
    """
    chosen = med.get("slots")
    if chosen:
        per = int(med.get("countPerDose") or 1)
        return {slot: (per if slot in chosen else 0) for slot in SLOTS}
    return parse_frequency(med.get("frequencyCode", ""))


def doses_per_day(med: Dict[str, Any]) -> int:
    counts = slot_counts(med)
    return sum(counts.get(slot, 0) for slot in SLOTS)


def build_doses(
    parent_id: str,
    medicines: List[Dict[str, Any]],
    days: int = 7,
    start_date: Optional[str] = None,
    timezone: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """DOSE items for the next `days` days, honouring each medicine's duration."""
    timezone = timezone or config.DEFAULT_TIMEZONE
    start = dt.datetime.strptime(start_date or util.today_str(timezone), "%Y-%m-%d").date()
    items: List[Dict[str, Any]] = []

    for med in medicines:
        if med.get("asNeeded"):
            continue  # SOS medicines have no clock; nothing to schedule
        med_id = med["medId"]
        duration = int(med.get("durationDays") or days)
        counts = slot_counts(med)
        for offset in range(min(days, duration) if duration > 0 else days):
            date = (start + dt.timedelta(days=offset)).strftime("%Y-%m-%d")
            for slot in SLOTS:
                count = counts.get(slot, 0)
                if count <= 0:
                    continue
                items.append(
                    {
                        "PK": keys.parent(parent_id),
                        "SK": keys.dose_sk(date, slot, med_id),
                        "type": "DOSE",
                        "parentId": parent_id,
                        "medId": med_id,
                        "brand": med.get("brand"),
                        "salts": med.get("salts", []),
                        "strength": med.get("strength"),
                        "food": med.get("food"),
                        "count": count,
                        "date": date,
                        "slot": slot,
                        "photoKey": med.get("photoKey"),
                        "scheduledAt": scheduled_at(date, slot, timezone),
                        "status": "PENDING",
                        "takenAt": None,
                    }
                )
    return items


def slot_cron(slot: str) -> str:
    """EventBridge Scheduler expression for a slot, in the parent's timezone."""
    hour, minute = slot_time(slot).split(":")
    return f"cron({int(minute)} {int(hour)} * * ? *)"
