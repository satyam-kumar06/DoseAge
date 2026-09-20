"""
backend/functions/salts/app.py
Lambda handler for the DoseWise Duplicate Salt Check step.

Consumes the output from the Extraction Lambda (via Step Functions pass-through),
runs the RapidFuzz-based salt deduplication engine, calculates Jan Aushadhi savings,
and returns an enriched payload for the next step (SaveToDynamo).

Event shape expected (passed by Step Functions from ExtractLambda output):
{
    "scanId":    "scan-xxx",
    "s3Key":     "uploads/user-id/filename.jpg",
    "medicines": [
        {
            "brand":          "Dolo 650 tab",
            "strength":       "650 mg",
            "form":           "tablet",
            "frequency_code": "1-0-1",
            "food":           "after",
            "duration_days":  5,
            "confidence":     0.93,
            "source_text":    "Dolo 650 1-0-1 x 5d"
        },
        ...
    ],
    "unreadable_lines": ["..."]
}

Returns the same payload with an added "ai_analysis" key.
"""

import json
import logging
import os
import re

from rapidfuzz import process, fuzz

# ─── Logging ──────────────────────────────────────────────────────────────────
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# ─── Database Bootstrapping ───────────────────────────────────────────────────
# In Lambda, __file__ resolves to /var/task/app.py
# medicines_seed.json must be co-located in the same directory.
_SEED_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "medicines_seed.json")


def _load_database() -> dict:
    """
    Load the medicines seed JSON once at module init time (Lambda init phase).
    Returns a dict keyed by lowercased brand name for O(1) lookup.
    Raises RuntimeError if the seed file is missing so the Lambda fails fast.
    """
    try:
        with open(_SEED_PATH, "r", encoding="utf-8") as fh:
            records = json.load(fh)
        logger.info("Loaded %d medicines from seed database.", len(records))
        return {item["brand"].lower(): item for item in records}
    except FileNotFoundError:
        logger.error("medicines_seed.json not found at %s", _SEED_PATH)
        raise RuntimeError(
            f"Seed database not found. Expected at: {_SEED_PATH}. "
            "Ensure medicines_seed.json is bundled in the Lambda deployment package."
        )


# Module-level singleton — loaded once per container lifetime
_DB: dict = _load_database()


# ─── Normalisation ────────────────────────────────────────────────────────────
_NOISE_WORDS = frozenset(
    ["tab", "tablet", "cap", "capsule", "syrup", "suspension", "mg", "ml", "inj", "drops"]
)


def _normalize_brand_name(raw: str) -> str:
    """
    Strip dosage form words, numeric digits, and punctuation from a raw brand
    name so that fuzzy matching is not confused by dose suffix noise.

    Example: "Dolo 650 tab" → "dolo"
    """
    name = raw.lower()
    # Remove noise words (whole-word match to avoid clipping 'tablet' from brand)
    pattern = r"\b(" + "|".join(re.escape(w) for w in _NOISE_WORDS) + r")\b"
    name = re.sub(pattern, "", name)
    # Remove digits and non-alphanumeric chars except spaces
    name = re.sub(r"[^a-z\s]", "", name)
    # Collapse multiple spaces
    return re.sub(r"\s+", " ", name).strip()


# ─── Lookup ───────────────────────────────────────────────────────────────────
_FUZZY_THRESHOLD = 75  # WRatio score threshold (0–100)


def _find_medicine_entry(raw_brand: str) -> dict | None:
    """
    Fuzzy-match a raw brand name against the seed database.
    Returns the matching record dict or None if no confident match is found.
    """
    normalized = _normalize_brand_name(raw_brand)
    if not normalized:
        return None
    match = process.extractOne(normalized, _DB.keys(), scorer=fuzz.WRatio)
    if match and match[1] >= _FUZZY_THRESHOLD:
        return _DB[match[0]]
    return None


# ─── Core Analysis ────────────────────────────────────────────────────────────
def analyze_prescription(medicines: list[dict]) -> dict:
    """
    Two core checks:
      1. Duplicate Salt Guard — flags brands sharing the same active ingredient.
      2. Jan Aushadhi Saver  — computes monthly savings if switching to generic.

    Args:
        medicines: List of medicine dicts as extracted by Bedrock/Textract.

    Returns:
        {
            "alerts":  [...],
            "savings": { "total_monthly_saving_inr": X, "breakdown": [...], "disclaimer": "..." }
        }
    """
    seen_salts: dict[str, dict] = {}
    alerts: list[dict] = []
    savings_breakdown: list[dict] = []
    total_monthly_saving = 0.0

    for item in medicines:
        raw_brand = item.get("brand", "")
        record = _find_medicine_entry(raw_brand)

        if not record:
            logger.warning("Could not match '%s' in seed database.", raw_brand)
            alerts.append(
                {
                    "type": "UNVERIFIED",
                    "brand": raw_brand,
                    "message": (
                        f"Could not verify salt for '{raw_brand}'. "
                        "Check with your pharmacist."
                    ),
                }
            )
            continue

        salt = record["salt"]
        brand_name = record["brand"]

        # ── 1. Duplicate Salt Check ────────────────────────────────────────
        if salt in seen_salts:
            prior_brand = seen_salts[salt]["brand"]
            alerts.append(
                {
                    "type": "DUPLICATE",
                    "salt": salt,
                    "brands": [prior_brand, brand_name],
                    "message": (
                        f"{brand_name} and {prior_brand} both contain {salt}. "
                        "Ask your doctor before taking both."
                    ),
                }
            )
            logger.warning(
                "DUPLICATE SALT detected: %s (brands: %s, %s)",
                salt,
                prior_brand,
                brand_name,
            )
        else:
            seen_salts[salt] = record

        # ── 2. Jan Aushadhi Savings (30-day estimate) ─────────────────────
        try:
            brand_unit = record["brand_price_per_strip"] / record["strip_size"]
            jan_unit = record["jan_aushadhi_price_per_strip"] / record["strip_size"]

            # frequency_code e.g. "1-0-1" → 2 doses/day
            freq = item.get("frequency_code", "1-0-0")
            doses_per_day = max(
                sum(int(x) for x in freq.split("-") if x.isdigit()), 1
            )
            monthly_doses = doses_per_day * 30

            brand_monthly = round(brand_unit * monthly_doses, 2)
            jan_monthly = round(jan_unit * monthly_doses, 2)
            saving = round(brand_monthly - jan_monthly, 2)

            if saving > 0:
                total_monthly_saving += saving
                savings_breakdown.append(
                    {
                        "prescribed_brand": brand_name,
                        "generic_alternative": record["jan_aushadhi_name"],
                        "brand_monthly_cost": brand_monthly,
                        "jan_aushadhi_monthly_cost": jan_monthly,
                        "monthly_saving": saving,
                    }
                )
        except (KeyError, ZeroDivisionError, ValueError) as exc:
            logger.warning(
                "Could not compute savings for '%s': %s", brand_name, exc
            )

    return {
        "alerts": alerts,
        "savings": {
            "total_monthly_saving_inr": round(total_monthly_saving, 2),
            "breakdown": savings_breakdown,
            "disclaimer": "Ask your doctor or pharmacist before switching to a generic.",
        },
    }


# ─── Lambda Handler ───────────────────────────────────────────────────────────
def handler(event: dict, context) -> dict:  # noqa: ANN001
    """
    AWS Lambda entrypoint — called by Step Functions.

    Input  : extraction payload (see module docstring).
    Output : same payload with 'ai_analysis' key appended.
    Raises : Exception on validation errors (Step Functions will catch and
             route to the Fail state).
    """
    logger.info("SaltCheck Lambda invoked. scanId=%s", event.get("scanId", "unknown"))

    medicines = event.get("medicines")
    if not isinstance(medicines, list):
        raise ValueError(
            "'medicines' key is missing or not a list in the Step Functions event. "
            f"Received type: {type(medicines).__name__}"
        )

    if len(medicines) == 0:
        logger.warning("No medicines in payload — returning empty analysis.")
        event["ai_analysis"] = {
            "alerts": [],
            "savings": {
                "total_monthly_saving_inr": 0.0,
                "breakdown": [],
                "disclaimer": "No medicines to analyse.",
            },
        }
        return event

    analysis = analyze_prescription(medicines)
    event["ai_analysis"] = analysis

    logger.info(
        "Analysis complete. %d alert(s), ₹%.2f monthly savings.",
        len(analysis["alerts"]),
        analysis["savings"]["total_monthly_saving_inr"],
    )

    return event


# ─── Local Test Harness ───────────────────────────────────────────────────────
if __name__ == "__main__":
    _sample_event = {
        "scanId": "local-test-001",
        "s3Key": "uploads/test/prescription.jpg",
        "medicines": [
            {"brand": "Dolo 650 tab", "frequency_code": "1-0-1"},
            {"brand": "Calpol 500",   "frequency_code": "0-0-1"},
            {"brand": "Telma 40",     "frequency_code": "1-0-0"},
        ],
        "unreadable_lines": [],
    }
    result = handler(_sample_event, None)
    print(json.dumps(result, indent=2))
