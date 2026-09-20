"""Jan Aushadhi savings and Refill Radar maths.

Both are plain arithmetic over the dataset. Every savings number is shown
with 'ask your doctor or pharmacist before switching'. We never tell anyone
to change a medicine.
"""
import datetime as dt
from typing import Any, Dict, List, Optional

from . import salts as salt_lib
from . import schedule, util

DISCLAIMER = "Estimated. Ask your doctor or pharmacist before switching."
DISCLAIMER_HI = "Anumaanit. Badalne se pehle apne doctor ya chemist se poochhein."


def _unit_price(price: Optional[float], pack_size: Optional[int]) -> Optional[float]:
    if price is None or not pack_size:
        return None
    return price / float(pack_size)


def same_molecule(salts: List[str], generic_name: str) -> bool:
    """Does the suggested generic actually contain the brand's salts?

    A saving is only a saving if the substitute is the same medicine. Naming a
    different molecule as an 'equivalent' would be exactly the advice DoseWise
    promises never to give, so this is checked rather than trusted: a bad row
    in the dataset produces no saving instead of a dangerous suggestion.
    """
    if not salts or not generic_name:
        return False
    haystack = generic_name.lower()
    return all(salt.lower() in haystack for salt in salts)


def savings_for(med: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Monthly saving if this branded medicine were bought as its generic."""
    match = salt_lib.lookup(med.get("brand", ""), med.get("strength", ""))
    rec = match.get("record")
    if not rec or not rec.get("genericPrice") or not rec.get("brandPrice"):
        return None
    if not same_molecule(rec.get("salts") or [], rec.get("genericName") or ""):
        return None

    per_day = schedule.doses_per_day(med)
    if per_day <= 0:
        return None

    brand_unit = _unit_price(rec["brandPrice"], rec["packSize"])
    generic_unit = _unit_price(rec["genericPrice"], rec["packSize"])
    if brand_unit is None or generic_unit is None or generic_unit >= brand_unit:
        return None

    monthly_units = per_day * 30
    brand_monthly = round(brand_unit * monthly_units, 2)
    generic_monthly = round(generic_unit * monthly_units, 2)
    return {
        "medId": med.get("medId"),
        "brand": rec["brand"],
        "generic": rec["genericName"] or ", ".join(rec["salts"]),
        "salts": rec["salts"],
        "brandMonthly": brand_monthly,
        "genericMonthly": generic_monthly,
        "monthlySaving": round(brand_monthly - generic_monthly, 2),
        "disclaimer": DISCLAIMER,
        "disclaimerHi": DISCLAIMER_HI,
    }


def savings_summary(medicines: List[Dict[str, Any]]) -> Dict[str, Any]:
    rows = [s for s in (savings_for(m) for m in medicines) if s]
    total = round(sum(r["monthlySaving"] for r in rows), 2)
    return {
        "monthlyTotal": total,
        "yearlyTotal": round(total * 12, 2),
        "items": sorted(rows, key=lambda r: r["monthlySaving"], reverse=True),
        "disclaimer": DISCLAIMER,
        "disclaimerHi": DISCLAIMER_HI,
    }


# --------------------------------------------------------------------------
# Refill Radar
# --------------------------------------------------------------------------

WARN_DAYS = 3


def refill_for(med: Dict[str, Any], doses_taken: int = 0, as_of: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Days left from strip size, doses per day, and doses already taken."""
    strip = med.get("stripSize")
    if not strip:
        match = salt_lib.lookup(med.get("brand", ""), med.get("strength", ""))
        rec = match.get("record")
        strip = rec.get("packSize") if rec else None
    if not strip:
        return None

    per_day = schedule.doses_per_day(med)
    if per_day <= 0:
        return None

    remaining_units = max(int(strip) - int(doses_taken), 0)
    days_left = remaining_units // per_day
    today = dt.datetime.strptime(as_of or util.today_str(), "%Y-%m-%d").date()
    return {
        "medId": med.get("medId"),
        "brand": med.get("brand"),
        "unitsLeft": remaining_units,
        "perDay": per_day,
        "daysLeft": days_left,
        "runsOutOn": (today + dt.timedelta(days=days_left)).strftime("%Y-%m-%d"),
        "warn": days_left <= WARN_DAYS,
    }


def refill_summary(medicines: List[Dict[str, Any]], taken_by_med: Dict[str, int]) -> List[Dict[str, Any]]:
    rows = []
    for med in medicines:
        row = refill_for(med, taken_by_med.get(med.get("medId"), 0))
        if row:
            rows.append(row)
    return sorted(rows, key=lambda r: r["daysLeft"])
