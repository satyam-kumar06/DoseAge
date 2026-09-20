"""The parts that must not be wrong: salt matching, duplicate detection,
frequency parsing, dose scheduling, savings, refill, and the full flow.

    python backend/tests/test_core.py
"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from common import salts, savings, schedule, services, storage  # noqa: E402
from common.store import reset_for_tests  # noqa: E402

PASS, FAIL = [], []


def check(name, condition, detail=""):
    (PASS if condition else FAIL).append(name)
    mark = "ok  " if condition else "FAIL"
    print(f"{mark} {name}" + (f"  <- {detail}" if not condition and detail else ""))


# --------------------------------------------------------------------------
# Normalisation and lookup
# --------------------------------------------------------------------------


def test_normalise():
    check("strips strength", salts.normalise("Dolo 650") == "dolo", salts.normalise("Dolo 650"))
    check("strips form words", salts.normalise("Pan 40 Tab") == "pan", salts.normalise("Pan 40 Tab"))
    check("handles punctuation", salts.normalise("Zerodol-SP") == "zerodol sp", salts.normalise("Zerodol-SP"))
    check("empty is empty", salts.normalise("") == "")


def test_lookup():
    exact = salts.lookup("Dolo 650", "650 mg")
    check("exact brand matches", exact["matched"] and exact["salts"] == ["Paracetamol"], str(exact["salts"]))

    messy = salts.lookup("dolo-650 tab")
    check("messy spelling matches", messy["matched"] and messy["salts"] == ["Paracetamol"], str(messy))

    typo = salts.lookup("Telmakind 40")
    check("close typo matches Telmikind", typo["matched"] and "Telmisartan" in typo["salts"], str(typo))

    combo = salts.lookup("Combiflam")
    check(
        "combination splits into two salts",
        combo["matched"] and set(combo["salts"]) == {"Ibuprofen", "Paracetamol"},
        str(combo["salts"]),
    )

    unknown = salts.lookup("Zzzqqq 999")
    check("unknown brand does not match", not unknown["matched"], str(unknown))


def test_generic_prescribing():
    """Government hospitals prescribe by molecule, not brand. Found on a real
    AIIMS OPD slip: every line read correctly and every one failed to match."""
    thyroxine = salts.lookup("Tab Thyroxine")
    check(
        "a molecule name matches its salt",
        thyroxine["matched"] and thyroxine["salts"] == ["Thyroxine Sodium"],
        str(thyroxine["salts"]),
    )
    check("molecule match is labelled as such", thyroxine["source"] == "salt-name")
    check(
        "no dataset record, so no invented saving",
        thyroxine["record"] is None,
    )

    metformin = salts.lookup("Tab. Metformin SR")
    check(
        "dosage-form noise does not block the molecule",
        metformin["matched"] and metformin["salts"] == ["Metformin"],
        str(metformin),
    )

    check(
        "a brand still beats the molecule path",
        salts.lookup("Dolo 650")["source"] == "dataset",
    )
    check("nonsense still does not match", not salts.lookup("Zzzqqq 999")["matched"])

    dup = salts.find_duplicates(
        [
            {"medId": "a", "brand": "Tab Metformin", "salts": ["Metformin"]},
            {"medId": "b", "brand": "Glycomet 500", "salts": ["Metformin"]},
        ]
    )
    check("generic and brand of one molecule is a duplicate", len(dup) == 1, str(dup))


# --------------------------------------------------------------------------
# Duplicate guard
# --------------------------------------------------------------------------


def test_duplicates():
    meds = [
        {"medId": "a", "brand": "Dolo 650", "salts": ["Paracetamol"]},
        {"medId": "b", "brand": "Calpol 650", "salts": ["Paracetamol"]},
        {"medId": "c", "brand": "Telma 40", "salts": ["Telmisartan"]},
    ]
    dups = salts.find_duplicates(meds)
    check("finds one duplicate group", len(dups) == 1, str(dups))
    check("names the shared salt", dups and dups[0]["salt"] == "Paracetamol")
    check("lists both brands", dups and set(dups[0]["brands"]) == {"Dolo 650", "Calpol 650"})

    hidden = [
        {"medId": "a", "brand": "Combiflam", "salts": ["Ibuprofen", "Paracetamol"]},
        {"medId": "b", "brand": "Dolo 650", "salts": ["Paracetamol"]},
    ]
    check("catches a salt hidden in a combination", len(salts.find_duplicates(hidden)) == 1)

    check("no false positive on distinct salts", salts.find_duplicates(meds[2:]) == [])

    same_brand_twice = [
        {"medId": "a", "brand": "Dolo 650", "salts": ["Paracetamol"]},
        {"medId": "b", "brand": "Dolo 650", "salts": ["Paracetamol"]},
    ]
    check("same brand twice is not a duplicate alert", salts.find_duplicates(same_brand_twice) == [])


def test_duplicates_across_prescriptions():
    """The real scenario: a second doctor, a second sheet, the same molecule."""
    already_taking = [{"medId": "a", "brand": "Dolo 650", "salts": ["Paracetamol"]}]
    new_scan = [
        {"medId": "b", "brand": "Calpol 650", "salts": ["Paracetamol"]},
        {"medId": "c", "brand": "Telma 40", "salts": ["Telmisartan"]},
    ]

    dups = salts.find_duplicates(new_scan, existing=already_taking)
    check("a second prescription flags against the first", len(dups) == 1, str(dups))
    check("the new brand is named as new", dups and dups[0]["newBrands"] == ["Calpol 650"])
    check("the old brand is named as existing", dups and dups[0]["existingBrands"] == ["Dolo 650"])
    check(
        "the message says which one is already on the list",
        dups and "already on the list" in dups[0]["message"],
        dups and dups[0]["message"],
    )

    check(
        "a clean second prescription raises nothing",
        salts.find_duplicates(
            [{"medId": "c", "brand": "Telma 40", "salts": ["Telmisartan"]}],
            existing=already_taking,
        )
        == [],
    )

    # Two medicines already on the list overlapping each other were reported
    # when they were scanned. Repeating them on an unrelated scan is noise.
    old_pair = [
        {"medId": "a", "brand": "Dolo 650", "salts": ["Paracetamol"]},
        {"medId": "b", "brand": "Calpol 650", "salts": ["Paracetamol"]},
    ]
    check(
        "an overlap wholly inside the existing list is not re-reported",
        salts.find_duplicates(
            [{"medId": "c", "brand": "Telma 40", "salts": ["Telmisartan"]}],
            existing=old_pair,
        )
        == [],
    )

    # Re-scanning the same sheet must not make a medicine duplicate itself.
    check(
        "re-scanning the same prescription invents nothing",
        salts.find_duplicates(already_taking, existing=already_taking) == [],
    )
    check(
        "re-scanning by brand with a fresh medId invents nothing",
        salts.find_duplicates(
            [{"medId": "fresh", "brand": "Dolo 650", "salts": ["Paracetamol"]}],
            existing=already_taking,
        )
        == [],
    )

    check(
        "a hidden combination salt still crosses prescriptions",
        len(
            salts.find_duplicates(
                [{"medId": "z", "brand": "Zerodol SP", "salts": ["Aceclofenac", "Paracetamol"]}],
                existing=already_taking,
            )
        )
        == 1,
    )


# --------------------------------------------------------------------------
# Frequency and schedule
# --------------------------------------------------------------------------


def test_frequency():
    check("1-0-1", schedule.slots_for("1-0-1") == ["MORNING", "NIGHT"])
    check("0-0-1", schedule.slots_for("0-0-1") == ["NIGHT"])
    check("1-1-1", schedule.slots_for("1-1-1") == ["MORNING", "AFTERNOON", "NIGHT"])
    check("BD shorthand", schedule.slots_for("BD") == ["MORNING", "NIGHT"])
    check("TDS shorthand", schedule.slots_for("TDS") == ["MORNING", "AFTERNOON", "NIGHT"])
    check("HS shorthand", schedule.slots_for("HS") == ["NIGHT"])
    check("SOS makes no schedule", schedule.slots_for("SOS") == [])
    check("junk makes no schedule", schedule.slots_for("???") == [])
    check("doses per day counts", schedule.doses_per_day({"frequencyCode": "1-1-1"}) == 3)


def test_build_doses():
    meds = [{"medId": "m1", "brand": "Dolo 650", "frequencyCode": "1-0-1", "durationDays": 5}]
    doses = schedule.build_doses("p1", meds, days=7)
    check("duration caps the run", len(doses) == 10, f"{len(doses)} doses")
    check("all pending at first", all(d["status"] == "PENDING" for d in doses))
    check("scheduled time is set", all(d["scheduledAt"] for d in doses))

    zero = schedule.build_doses("p1", [{"medId": "m2", "frequencyCode": "SOS"}], days=7)
    check("SOS creates no doses", zero == [])


# --------------------------------------------------------------------------
# Savings and refill
# --------------------------------------------------------------------------


def test_savings():
    med = {"medId": "m1", "brand": "Telma 40", "strength": "40 mg", "frequencyCode": "1-0-0"}
    row = savings.savings_for(med)
    check("savings computed for a branded medicine", row is not None)
    check("generic is cheaper", row and row["genericMonthly"] < row["brandMonthly"])
    check("saving is positive", row and row["monthlySaving"] > 0)
    check("disclaimer present", row and "doctor" in row["disclaimer"].lower())

    summary = savings.savings_summary([med, {"medId": "m2", "brand": "Pan 40", "frequencyCode": "1-0-0"}])
    check("summary totals", summary["monthlyTotal"] > 0 and len(summary["items"]) == 2)


def test_refill():
    med = {"medId": "m1", "brand": "Dolo 650", "frequencyCode": "1-0-1", "stripSize": 15}
    row = savings.refill_for(med, doses_taken=10)
    check("days left from strip", row and row["daysLeft"] == 2, str(row))
    check("warns near the end", row and row["warn"])
    check("no warning when full", not savings.refill_for(med, doses_taken=0)["warn"])


# --------------------------------------------------------------------------
# Full flow
# --------------------------------------------------------------------------


def test_end_to_end():
    tmp = tempfile.mkdtemp()
    reset_for_tests(os.path.join(tmp, "db.json"))
    os.environ["LOCAL_FILES_PATH"] = os.path.join(tmp, "files")
    storage.config.LOCAL_FILES_PATH = os.path.join(tmp, "files")

    family = services.create_family("Test family", {"name": "Child", "phone": "+910000000000"})
    parent = services.add_parent(family["familyId"], {"name": "Kamla", "phone": "+910000000001"})
    pid = parent["parentId"]

    scan = services.upload_url(pid)
    storage.put_bytes(scan["key"], b"x", "image/jpeg")
    read = services.start_scan(pid, scan["scanId"], "family_demo")

    check("scan returns medicines", len(read["medicines"]) == 7, str(len(read["medicines"])))
    check("scan flags the paracetamol duplicate", len(read["duplicates"]) == 1, str(read["duplicates"]))
    check(
        "low confidence line is tagged",
        any(m["lowConfidence"] for m in read["medicines"]),
    )
    check("nothing saved before review", services.list_meds(pid) == [])

    confirmed = services.confirm_meds(pid, read["medicines"], scan["scanId"])
    check("medicines saved after confirm", len(services.list_meds(pid)) == 7)
    check("doses created", confirmed["dosesCreated"] > 0, str(confirmed["dosesCreated"]))
    check("schedules planned", len(confirmed["schedules"]) >= 2, str(confirmed["schedules"]))

    day = services.today(pid)
    check("today has slots", len(day["slots"]) >= 2, str(len(day["slots"])))
    check("duplicate alert reaches today screen", any(a["alertType"] == "DUPLICATE" for a in day["alerts"]))

    slot = day["slots"][0]["slot"]
    first = services.mark_taken(pid, day["date"], slot)
    check("marking taken changes doses", len(first["marked"]) > 0)
    again = services.mark_taken(pid, day["date"], slot)
    check("marking taken twice is idempotent", again["marked"] == [] and again["alreadyTaken"] > 0)

    after = services.today(pid)
    check("slot shows taken", after["slots"][0]["status"] == "TAKEN")

    services.undo_taken(pid, day["date"], slot)
    check("undo restores pending", services.today(pid)["slots"][0]["status"] == "PENDING")

    board = services.dashboard(pid)
    check("dashboard adherence is a percentage", 0 <= board["adherence"] <= 100)
    check("dashboard carries duplicates", len(board["duplicates"]) == 1)
    check("dashboard carries savings", board["savings"]["monthlyTotal"] > 0)
    check("dashboard carries refills", len(board["refills"]) > 0)

    voice_line = services.slot_voice(pid, slot)
    check("voice line mentions a medicine", any(m in voice_line["caption"] for m in ["Dolo", "Telma", "Pan", "Shelcal", "Glycomet", "Ecosprin", "Calpol"]), voice_line["caption"])
    check("voice falls back to browser without Polly", voice_line["engine"] == "browser")

    card = services.visit_card(pid)
    check("visit card has a link", bool(card["url"]))
    pdf = storage.get_bytes(card["key"])
    check("visit card is a real PDF", pdf.startswith(b"%PDF") and pdf.rstrip().endswith(b"%%EOF"))

    return pid


def test_cross_prescription_scan():
    """Two doctors, two sheets, one molecule. The whole pitch, end to end."""
    tmp = tempfile.mkdtemp()
    reset_for_tests(os.path.join(tmp, "db.json"))
    os.environ["LOCAL_FILES_PATH"] = os.path.join(tmp, "files")
    storage.config.LOCAL_FILES_PATH = os.path.join(tmp, "files")

    family = services.create_family("Cross family", {"name": "Child", "phone": "+910000000000"})
    pid = services.add_parent(family["familyId"], {"name": "Kamla", "phone": "+910000000001"})["parentId"]

    # Sheet one, from the cardiologist: Telmikind 40 is Telmisartan.
    first = services.upload_url(pid)
    storage.put_bytes(first["key"], b"x", "image/jpeg")
    read_one = services.start_scan(pid, first["scanId"], "cardiology_clean")
    check("first prescription is clean", read_one["duplicates"] == [], str(read_one["duplicates"]))
    services.confirm_meds(pid, read_one["medicines"], first["scanId"])

    # Sheet two, from the GP: Telma 40 is the same molecule under another brand.
    second = services.upload_url(pid)
    storage.put_bytes(second["key"], b"x", "image/jpeg")
    read_two = services.start_scan(pid, second["scanId"], "family_demo")

    salts_found = {d["salt"] for d in read_two["duplicates"]}
    check(
        "the second sheet flags the molecule from the first",
        "Telmisartan" in salts_found,
        str(salts_found),
    )
    cross = [d for d in read_two["duplicates"] if d["salt"] == "Telmisartan"][0]
    check("the already-active brand is named", cross["existingBrands"] == ["Telmikind 40"], str(cross))
    check("the newly scanned brand is named", cross["newBrands"] == ["Telma 40"], str(cross))
    check(
        "within-sheet duplicates still fire too",
        "Paracetamol" in salts_found,
        str(salts_found),
    )

    alerts = services.list_alerts(pid)
    check(
        "the cross-prescription duplicate raised an alert",
        any(a.get("salt") == "Telmisartan" for a in alerts),
        str([a.get("salt") for a in alerts]),
    )


def test_escalation(pid):
    from functions.escalation import handler as esc

    day = services.today(pid)
    slot = next((s["slot"] for s in day["slots"] if s["status"] == "PENDING"), day["slots"][0]["slot"])

    event = esc.send_reminder({"parentId": pid, "slot": slot})
    check("reminder sent", event.get("attempt") == 1, str(event))
    event = esc.check_taken(event)
    check("check sees it pending", not event["taken"])
    event = esc.nudge(event)
    check("nudge is attempt 2", event["attempt"] == 2)
    event = esc.alert_family(event)
    check("family alerted", event["alerted"] >= 1, str(event))
    event = esc.mark_missed(event)
    check("dose marked missed", event["missed"] >= 1)

    board = services.dashboard(pid)
    check("missed dose lands on dashboard", board["missedCount"] >= 1)
    check("missed alert recorded", any(a["alertType"] == "MISSED" for a in board["alerts"]))

    from common import notify

    check("sms landed in the outbox", len(notify.read_outbox()) >= 2, str(len(notify.read_outbox())))



def test_alert_dedupe():
    """Rescanning the same prescription must not stack identical cards on the
    parent's screen. Regression: three scans showed three banners."""
    import time

    from common import notify

    tmp = tempfile.mkdtemp()
    reset_for_tests(os.path.join(tmp, "db.json"))
    storage.config.LOCAL_FILES_PATH = os.path.join(tmp, "files")

    family = services.create_family("Dedupe family", {"name": "Child", "phone": "+910000000000"})
    parent = services.add_parent(family["familyId"], {"name": "Kamla"})
    pid = parent["parentId"]

    for _ in range(3):
        scan = services.upload_url(pid)
        storage.put_bytes(scan["key"], b"x", "image/jpeg")
        services.start_scan(pid, scan["scanId"], "family_demo")
        time.sleep(1.1)  # past the one second SK resolution

    dups = [a for a in services.today(pid)["alerts"] if a["alertType"] == "DUPLICATE"]
    check("three scans leave one duplicate alert", len(dups) == 1, f"{len(dups)} alerts")
    check("repeat occurrences are counted", dups and dups[0]["occurrences"] == 3)

    services.mark_alert_read(pid, dups[0]["SK"])
    scan = services.upload_url(pid)
    storage.put_bytes(scan["key"], b"x", "image/jpeg")
    services.start_scan(pid, scan["scanId"], "family_demo")
    unread = [a for a in services.today(pid)["alerts"] if a["alertType"] == "DUPLICATE"]
    check("a read alert recurring becomes a new card", len(unread) == 1, f"{len(unread)}")

    # Two alerts in the same second must not overwrite each other.
    for i in range(3):
        notify.record_alert(pid, "REFILL", f"refill {i}")
    refills = [a for a in services.list_alerts(pid) if a["alertType"] == "REFILL"]
    check("same-second alerts do not collide", len(refills) == 3, f"{len(refills)}")


def test_image_handling():
    """A phone photo must not be rejected for the wrong reason.

    Regression: Textract threw UnsupportedDocumentException on one real
    prescription and killed the whole scan, even though Bedrock could read it.
    Also: the file extension is the least reliable thing about an upload.
    """
    from common import extraction

    check("detects jpeg", extraction.image_format(b"\xff\xd8\xff\xe0" + b"\x00" * 20) == "jpeg")
    check("detects png", extraction.image_format(b"\x89PNG\r\n\x1a\n" + b"\x00" * 20) == "png")
    check(
        "detects webp",
        extraction.image_format(b"RIFF" + b"\x00" * 4 + b"WEBP" + b"\x00" * 20) == "webp",
    )
    check(
        "a PNG named .jpg is read as png",
        extraction.image_format(b"\x89PNG\r\n\x1a\n" + b"\x00" * 20, "scan.jpg") == "png",
    )
    check(
        "HEIC is rejected rather than mislabelled",
        extraction.image_format(b"\x00\x00\x00\x18ftypheic" + b"\x00" * 20) is None,
    )
    check("PDF is not an image", extraction.image_format(b"%PDF-1.4" + b"\x00" * 20) is None)

    import common.config as cfg

    was = cfg.TEXTRACT_ENABLED
    cfg.TEXTRACT_ENABLED = True
    try:
        lines, err = extraction.textract_lines(b"definitely not an image")
        check("a Textract failure degrades instead of raising", lines == [] and bool(err))
    finally:
        cfg.TEXTRACT_ENABLED = was


def test_unspecified_timing():
    """Real prescriptions often write a medicine with no 1-0-1 at all.

    The review screen asks the caregiver; their answer arrives as `slots`, and
    it must be what gets scheduled. Reading frequencyCode instead created zero
    doses and the medicine vanished from the parent's day.
    """
    hand_set = {
        "medId": "m1",
        "brand": "Tab Thyroxine",
        "frequencyCode": "",
        "slots": ["MORNING"],
        "countPerDose": 1,
    }
    check("a hand-set timing schedules doses", len(schedule.build_doses("p", [hand_set], days=7)) == 7)
    check("per-day count follows the slots", schedule.doses_per_day(hand_set) == 1)

    two_each = {**hand_set, "medId": "m2", "slots": ["MORNING", "NIGHT"], "countPerDose": 2}
    doses = schedule.build_doses("p", [two_each], days=7)
    check("two slots give two doses a day", len(doses) == 14, str(len(doses)))
    check("count per dose is carried", doses[0]["count"] == 2)
    check("per-day total counts pills not slots", schedule.doses_per_day(two_each) == 4)

    sos = {"medId": "m3", "brand": "Combiflam", "frequencyCode": "SOS", "asNeeded": True}
    check("as-needed schedules nothing", schedule.build_doses("p", [sos], days=7) == [])

    written = {"medId": "m4", "brand": "Dolo 650", "frequencyCode": "1-0-1", "durationDays": 5}
    check("a written code still works", len(schedule.build_doses("p", [written], days=7)) == 10)


def test_router():
    from common import router

    status, payload = router.dispatch("GET", "/health")
    check("health route works", status == 200 and payload["ok"])
    status, _ = router.dispatch("GET", "/nope")
    check("unknown route is 404", status == 404)
    status, _ = router.dispatch("POST", "/scans/upload-url", {})
    check("missing parentId is 400", status == 400)


if __name__ == "__main__":
    test_normalise()
    test_lookup()
    test_generic_prescribing()
    test_duplicates()
    test_duplicates_across_prescriptions()
    test_frequency()
    test_build_doses()
    test_savings()
    test_refill()
    pid = test_end_to_end()
    test_escalation(pid)
    test_cross_prescription_scan()
    test_alert_dedupe()
    test_image_handling()
    test_unspecified_timing()
    test_router()

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    if FAIL:
        print("failed:", ", ".join(FAIL))
        sys.exit(1)
