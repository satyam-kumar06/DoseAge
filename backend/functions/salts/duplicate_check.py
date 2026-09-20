import json
import os
from rapidfuzz import process, fuzz

DATA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../data/medicines_seed.json"))

def load_database():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)
    return {item["brand"].lower(): item for item in records}

DB = load_database()

def normalize_brand_name(raw_name: str) -> str:
    noise = ["tab", "tablet", "cap", "capsule", "syrup", "suspension", "mg", "ml"]
    name = raw_name.lower()
    for term in noise:
        name = name.replace(term, "")
    return "".join([c for c in name if not c.isdigit() and c.isalnum() or c == " "]).strip()

def find_medicine_entry(raw_brand: str):
    normalized = normalize_brand_name(raw_brand)
    match = process.extractOne(normalized, DB.keys(), scorer=fuzz.WRatio)
    if match and match[1] >= 75:
        return DB[match[0]]
    return None

def analyze_prescription(extracted_medicines):
    """
    Executes two core functions:
    1. Duplicate Salt Guard: Flags conflicting brand names sharing salts.
    2. Jan Aushadhi Saver: Calculates monthly generic cost savings.
    """
    seen_salts = {}
    alerts = []
    savings_summary = []
    total_monthly_saving = 0.0

    for item in extracted_medicines:
        raw_brand = item["brand"]
        record = find_medicine_entry(raw_brand)
        
        if not record:
            alerts.append({
                "type": "UNVERIFIED",
                "message": f"Could not verify salt for '{raw_brand}'. Check with your pharmacist."
            })
            continue

        salt = record["salt"]
        brand_name = record["brand"]

        # 1. Duplicate check
        if salt in seen_salts:
            alerts.append({
                "type": "DUPLICATE",
                "salt": salt,
                "brands": [seen_salts[salt]["brand"], brand_name],
                "message": f"{brand_name} and {seen_salts[salt]['brand']} both contain {salt}. Ask your doctor before taking both."
            })
        else:
            seen_salts[salt] = record

        # 2. Jan Aushadhi monthly savings calculation (assuming 30-day baseline)
        brand_unit_price = record["brand_price_per_strip"] / record["strip_size"]
        jan_unit_price = record["jan_aushadhi_price_per_strip"] / record["strip_size"]
        
        # Estimate monthly doses based on frequency code (e.g. 1-0-1 -> 2 doses/day * 30 days = 60 doses)
        freq = item.get("frequency_code", "1-0-0")
        doses_per_day = sum(int(x) for x in freq.split("-") if x.isdigit()) or 1
        monthly_doses = doses_per_day * 30

        brand_monthly_cost = round(brand_unit_price * monthly_doses, 2)
        jan_monthly_cost = round(jan_unit_price * monthly_doses, 2)
        monthly_diff = round(brand_monthly_cost - jan_monthly_cost, 2)

        if monthly_diff > 0:
            total_monthly_saving += monthly_diff
            savings_summary.append({
                "prescribed_brand": brand_name,
                "generic_alternative": record["jan_aushadhi_name"],
                "brand_monthly_cost": brand_monthly_cost,
                "jan_aushadhi_monthly_cost": jan_monthly_cost,
                "monthly_saving": monthly_diff
            })

    return {
        "alerts": alerts,
        "savings": {
            "total_monthly_saving_inr": round(total_monthly_saving, 2),
            "breakdown": savings_summary,
            "disclaimer": "Ask your doctor or pharmacist before switching."
        }
    }

if __name__ == "__main__":
    sample_input = [
        {"brand": "Dolo 650 tab", "frequency_code": "1-0-1"},
        {"brand": "Calpol 500", "frequency_code": "0-0-1"},
        {"brand": "Telma 40", "frequency_code": "1-0-0"}
    ]
    
    result = analyze_prescription(sample_input)
    print(json.dumps(result, indent=2))