"""Key builders for the single DynamoDB table. One place, no typos."""


def family(family_id: str) -> str:
    return f"FAMILY#{family_id}"


def parent(parent_id: str) -> str:
    return f"PARENT#{parent_id}"


def salt(name: str) -> str:
    return f"SALT#{name.strip().upper()}"


PROFILE = "PROFILE"


def caregiver_sk(user_id: str) -> str:
    return f"CAREGIVER#{user_id}"


def parent_sk(parent_id: str) -> str:
    return f"PARENT#{parent_id}"


def med_sk(med_id: str) -> str:
    return f"MED#{med_id}"


def scan_sk(scan_id: str) -> str:
    return f"SCAN#{scan_id}"


def dose_sk(date: str, slot: str, med_id: str) -> str:
    return f"DOSE#{date}#{slot}#{med_id}"


def dose_day_prefix(date: str) -> str:
    return f"DOSE#{date}"


def alert_sk(timestamp: str) -> str:
    return f"ALERT#{timestamp}"


def brand_sk(brand: str) -> str:
    return f"BRAND#{brand.strip().upper()}"


MED_PREFIX = "MED#"
SCAN_PREFIX = "SCAN#"
DOSE_PREFIX = "DOSE#"
ALERT_PREFIX = "ALERT#"
