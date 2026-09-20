"""Brand to salt lookup and duplicate salt detection.

This is deliberately plain code over a dataset, not an LLM call. The model
reads the prescription; this file decides. That distinction is the safety
story: duplicate detection is deterministic and reproducible.
"""
import csv
import difflib
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from . import config, keys
from .store import store

try:  # rapidfuzz is nicer but we must run without it
    from rapidfuzz import fuzz as _fuzz

    def _ratio(a: str, b: str) -> float:
        return _fuzz.token_sort_ratio(a, b) / 100.0

except ImportError:  # pragma: no cover

    def _ratio(a: str, b: str) -> float:
        return difflib.SequenceMatcher(None, a, b).ratio()


# Words that carry no identity: dosage forms, pack words, strength suffixes.
_NOISE = {
    "tab", "tabs", "tablet", "tablets", "cap", "caps", "capsule", "capsules",
    "syp", "syrup", "susp", "suspension", "inj", "injection", "drops", "drop",
    "oint", "ointment", "cream", "gel", "sr", "xr", "cr", "od", "dt", "mr",
    "forte", "plus", "strip", "mg", "mcg", "ml", "gm", "g", "iu", "the", "of",
}

_SALT_SPLIT = re.compile(r"\s*[+/,]\s*|\s+and\s+", re.IGNORECASE)


def normalise(text: str) -> str:
    """Lowercase, strip strengths and dosage-form noise, squeeze spaces.

    'Dolo 650 Tab' and 'dolo-650 tablet' both become 'dolo'.
    """
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^a-z0-9+\s]", " ", text)
    text = re.sub(r"\b\d+(\.\d+)?\s*(mg|mcg|ml|gm|g|iu)\b", " ", text)
    tokens = [t for t in text.split() if t and t not in _NOISE]
    # a bare trailing number is a strength ('dolo 650'), drop it
    tokens = [t for t in tokens if not t.isdigit()]
    return " ".join(tokens)


def normalise_salt(salt: str) -> str:
    salt = re.sub(r"\b\d+(\.\d+)?\s*(mg|mcg|ml|gm|g|iu)\b", " ", salt.lower())
    salt = re.sub(r"[^a-z0-9\s]", " ", salt)
    return " ".join(salt.split()).title()


def split_salts(raw: str) -> List[str]:
    if not raw:
        return []
    parts = [normalise_salt(p) for p in _SALT_SPLIT.split(raw)]
    return [p for p in parts if p]


# --------------------------------------------------------------------------
# Dataset loading
# --------------------------------------------------------------------------

def dataset_path() -> str:
    return os.path.join(config.DATA_DIR, "medicines.csv")


def load_csv(path: Optional[str] = None) -> List[Dict[str, Any]]:
    path = path or dataset_path()
    with open(path, "r", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    out = []
    for row in rows:
        salts = split_salts(row.get("salts", ""))
        out.append(
            {
                "brand": row["brand"].strip(),
                "manufacturer": row.get("manufacturer", "").strip(),
                "salts": salts,
                "form": row.get("form", "").strip(),
                "strength": row.get("strength", "").strip(),
                "brandPrice": _num(row.get("typical_brand_price_inr")),
                "packSize": int(_num(row.get("pack_size")) or 10),
                "genericName": row.get("jan_aushadhi_generic", "").strip(),
                "genericPrice": _num(row.get("jan_aushadhi_price_inr")),
            }
        )
    return out


def _num(value) -> Optional[float]:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


_cache: Optional[List[Dict[str, Any]]] = None
_salt_cache: Optional[Dict[str, str]] = None


def catalogue() -> List[Dict[str, Any]]:
    """All brand records. Reads DynamoDB on AWS, the CSV locally."""
    global _cache
    if _cache is not None:
        return _cache
    if config.IS_AWS:
        items = store().scan_prefix("SALT#")
        _cache = [
            {
                "brand": i.get("brand"),
                "manufacturer": i.get("manufacturer", ""),
                "salts": i.get("salts", []),
                "form": i.get("form", ""),
                "strength": i.get("strength", ""),
                "brandPrice": i.get("brandPrice"),
                "packSize": i.get("packSize", 10),
                "genericName": i.get("genericName", ""),
                "genericPrice": i.get("genericPrice"),
            }
            for i in items
            if i.get("brand")
        ]
    else:
        _cache = load_csv()
    return _cache


def clear_cache() -> None:
    global _cache, _salt_cache
    _cache = None
    _salt_cache = None


def salt_index() -> Dict[str, str]:
    """Normalised salt name -> canonical salt name, built from the dataset."""
    global _salt_cache
    if _salt_cache is None:
        index: Dict[str, str] = {}
        for rec in catalogue():
            for salt in rec["salts"]:
                index.setdefault(normalise(salt), salt)
        _salt_cache = index
    return _salt_cache


def match_salt_name(query: str) -> Optional[str]:
    """Is the query itself a salt rather than a brand?

    Government hospitals and many senior doctors prescribe by molecule:
    'Tab Thyroxine 75mg', not 'Thyronorm 75'. Those lines are the EASIEST to
    get right and the brand index misses every one of them, so the molecule
    gets its own lookup. A partial name matches its full form, because
    'Thyroxine' on paper means 'Thyroxine Sodium' in the dataset.
    """
    if not query:
        return None
    index = salt_index()

    if query in index:
        return index[query]
    for key, canonical in index.items():
        if key.startswith(query + " ") or query.startswith(key + " "):
            return canonical
    best, best_score = None, 0.0
    for key, canonical in index.items():
        score = _ratio(query, key)
        if score > best_score:
            best, best_score = canonical, score
    return best if best_score >= 0.9 else None


def to_items(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Dataset rows to DynamoDB items: one per (salt, brand) pair."""
    items = []
    for rec in records:
        for salt in rec["salts"] or ["Unknown"]:
            items.append(
                {
                    "PK": keys.salt(salt),
                    "SK": keys.brand_sk(rec["brand"]),
                    "brand": rec["brand"],
                    "salt": salt,
                    "salts": rec["salts"],
                    "manufacturer": rec["manufacturer"],
                    "form": rec["form"],
                    "strength": rec["strength"],
                    "brandPrice": rec["brandPrice"],
                    "packSize": rec["packSize"],
                    "genericName": rec["genericName"],
                    "genericPrice": rec["genericPrice"],
                    "normBrand": normalise(rec["brand"]),
                }
            )
    return items


# --------------------------------------------------------------------------
# Lookup
# --------------------------------------------------------------------------

MATCH_THRESHOLD = 0.82


def lookup(brand: str, strength: str = "") -> Dict[str, Any]:
    """Find the dataset record for a brand name.

    Returns {matched, brand, salts, confidence, source, record}. An unmatched
    brand is not an error: the caregiver can type the salt in by hand and the
    medicine is flagged unverified.
    """
    query = normalise(brand)
    if not query:
        return _miss(brand)

    best: Optional[Tuple[float, Dict[str, Any]]] = None
    for rec in catalogue():
        cand = normalise(rec["brand"])
        if cand == query:
            score = 1.0
        else:
            score = _ratio(query, cand)
            # a brand written as a prefix ('telma' for 'telma 40') is common
            if cand.startswith(query) or query.startswith(cand):
                score = max(score, 0.93)
        # same strength breaks ties between Telma 40 and Telma 80
        if strength and rec.get("strength") and normalise(strength) == normalise(rec["strength"]):
            score += 0.03
        if best is None or score > best[0]:
            best = (score, rec)

    if best is None or best[0] < MATCH_THRESHOLD:
        # No brand matched. Before giving up, ask whether the prescription
        # simply named the molecule.
        salt_name = match_salt_name(query)
        if salt_name:
            return {
                "matched": True,
                "brand": brand.strip(),
                "queryBrand": brand,
                "salts": [salt_name],
                "confidence": 0.9,
                "source": "salt-name",
                # Deliberately no dataset record: the prescription already
                # names the generic, so quoting a branded price and claiming a
                # saving against it would be inventing a number.
                "record": None,
            }
        return _miss(brand, best_guess=best[1]["brand"] if best else None)

    score, rec = best
    return {
        "matched": True,
        "brand": rec["brand"],
        "queryBrand": brand,
        "salts": rec["salts"],
        "confidence": round(min(score, 1.0), 3),
        "source": "dataset",
        "record": rec,
    }


def _miss(brand: str, best_guess: Optional[str] = None) -> Dict[str, Any]:
    return {
        "matched": False,
        "brand": brand,
        "queryBrand": brand,
        "salts": [],
        "confidence": 0.0,
        "source": "unmatched",
        "bestGuess": best_guess,
        "record": None,
    }


# --------------------------------------------------------------------------
# Duplicate salt guard
# --------------------------------------------------------------------------

def find_duplicates(
    medicines: List[Dict[str, Any]],
    existing: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Group medicines that share a salt.

    Input items need 'brand' and 'salts'; 'medId' is carried through when
    present. Output is one entry per shared salt with the brands involved and
    a ready-to-show message. We never rank severity and never advise: we say
    what overlaps and send them to a doctor.

    `existing` is the medicines the parent is already on. A second
    prescription from a second doctor is exactly where duplicates come from,
    so a new scan has to be checked against the list the parent already has,
    not only against itself. Overlaps that live entirely inside `existing`
    are left out: they were reported when that prescription was scanned, and
    repeating them on an unrelated scan is noise.
    """
    existing = existing or []
    new_ids = {m.get("medId") for m in medicines if m.get("medId")}
    new_brands = {(m.get("brand") or "").strip().lower() for m in medicines}

    def is_new(med: Dict[str, Any]) -> bool:
        med_id = med.get("medId")
        if med_id and med_id in new_ids:
            return True
        return (med.get("brand") or "").strip().lower() in new_brands

    # The same medicine can arrive in both lists when a prescription is
    # re-scanned. Counting it twice would invent a duplicate with itself.
    combined: List[Dict[str, Any]] = []
    seen: set = set()
    for med in list(medicines) + list(existing):
        marker = med.get("medId") or (med.get("brand") or "").strip().lower()
        if marker in seen:
            continue
        seen.add(marker)
        combined.append(med)

    by_salt: Dict[str, List[Dict[str, Any]]] = {}
    for med in combined:
        for salt in med.get("salts") or []:
            key = normalise_salt(salt)
            if not key:
                continue
            by_salt.setdefault(key, []).append(med)

    duplicates = []
    for salt, meds in sorted(by_salt.items()):
        brands: List[str] = []
        fresh: List[str] = []
        already: List[str] = []
        for med in meds:
            label = med.get("brand") or "Unknown"
            if label in brands:
                continue
            brands.append(label)
            (fresh if is_new(med) else already).append(label)
        if len(brands) < 2:
            continue
        if not fresh:
            continue  # an overlap between two medicines already on the list

        if already and fresh:
            message = (
                f"{' and '.join(fresh)} contains {salt}, which "
                f"{'is' if len(already) == 1 else 'are'} already on the list "
                f"from {' and '.join(already)}. "
                "Ask your doctor before taking both."
            )
            message_hi = (
                f"{' aur '.join(fresh)} mein {salt} hai, jo pehle se "
                f"{' aur '.join(already)} mein hai. "
                "Dono lene se pehle apne doctor se poochhein."
            )
        else:
            message = (
                f"{' and '.join(brands)} both contain {salt}. "
                "Ask your doctor before taking both."
            )
            message_hi = (
                f"{' aur '.join(brands)} dono mein {salt} hai. "
                "Dono lene se pehle apne doctor se poochhein."
            )

        duplicates.append(
            {
                "salt": salt,
                "brands": brands,
                "newBrands": fresh,
                "existingBrands": already,
                "medIds": [m.get("medId") for m in meds if m.get("medId")],
                "message": message,
                "messageHi": message_hi,
            }
        )
    return duplicates
