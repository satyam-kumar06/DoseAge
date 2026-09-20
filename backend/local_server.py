"""Offline dev server. No AWS account, no credentials, no dependencies.

    python backend/local_server.py --port 4000 --demo

It serves the same routes as the API Gateway Lambda (common.router), plus a
few local-only endpoints:

  PUT  /local-upload/<key>   stands in for the presigned S3 PUT
  GET  /local-file/<key>     stands in for a presigned S3 GET
  GET  /visit-card/<id>      serves the rendered visit card HTML
  POST /demo/seed            builds a realistic family in one call
  POST /demo/escalate        runs the dose escalation workflow in-process

The escalation runner is a thread with the same states as the Standard state
machine, so the Day 2 flow (remind, wait, check, nudge, alert family) can be
demonstrated before any AWS resources exist.
"""
import argparse
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import config, router, services, storage  # noqa: E402
from common.store import store  # noqa: E402

RUNS = {}


# --------------------------------------------------------------------------
# In-process stand-in for the Dose escalation Standard workflow
# --------------------------------------------------------------------------


def escalation_run(parent_id: str, slot: str, date=None, wait_seconds=None):
    from functions.escalation import handler as esc

    run_id = f"{parent_id}:{slot}:{date or 'today'}"
    wait = wait_seconds if wait_seconds is not None else config.WAIT_FIRST_SECONDS
    event = {"parentId": parent_id, "slot": slot, "date": date}
    log = []

    def step(name, fn):
        nonlocal event
        event = fn(event)
        log.append({"state": name, "at": time.strftime("%H:%M:%S"), "output": _small(event)})
        RUNS[run_id] = {"status": "RUNNING", "log": log}

    def _small(payload):
        return {
            k: v
            for k, v in payload.items()
            if k in ("attempt", "taken", "pendingCount", "alerted", "missed", "smsSent", "skipped")
        }

    def run():
        try:
            step("SendReminder", esc.send_reminder)
            if event.get("skipped"):
                RUNS[run_id] = {"status": "SKIPPED", "log": log}
                return
            time.sleep(wait)
            step("CheckTaken1", esc.check_taken)
            if event.get("taken"):
                RUNS[run_id] = {"status": "TAKEN", "log": log}
                return
            step("Nudge", esc.nudge)
            time.sleep(wait)
            step("CheckTaken2", esc.check_taken)
            if event.get("taken"):
                RUNS[run_id] = {"status": "TAKEN", "log": log}
                return
            step("AlertFamily", esc.alert_family)
            step("MarkMissed", esc.mark_missed)
            RUNS[run_id] = {"status": "MISSED", "log": log}
        except Exception as exc:  # keep the dev server alive
            RUNS[run_id] = {"status": "ERROR", "error": str(exc), "log": log}

    threading.Thread(target=run, daemon=True).start()
    RUNS[run_id] = {"status": "RUNNING", "log": log}
    return {"runId": run_id, "waitSeconds": wait}


# --------------------------------------------------------------------------
# Demo seed
# --------------------------------------------------------------------------


def seed_demo(fixture="family_demo", parent_name="Kamla Devi", caregiver_phone="+910000000000"):
    family = services.create_family(
        "Sharma family",
        {"name": "Sattu", "phone": caregiver_phone, "email": "caregiver@example.com"},
    )
    parent = services.add_parent(
        family["familyId"],
        {
            "name": parent_name,
            "phone": "+910000000001",
            "language": "hi",
            "relation": "mother",
        },
    )
    scan = services.upload_url(parent["parentId"])
    storage.put_bytes(scan["key"], b"local placeholder image", "image/jpeg")
    result = services.start_scan(parent["parentId"], scan["scanId"], fixture)
    confirmed = services.confirm_meds(parent["parentId"], result["medicines"], scan["scanId"])
    return {
        "familyId": family["familyId"],
        "parentId": parent["parentId"],
        "scanId": scan["scanId"],
        "medicines": len(confirmed["medicines"]),
        "duplicates": confirmed["duplicates"],
        "doses": confirmed["dosesCreated"],
    }


# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------


class Handler(BaseHTTPRequestHandler):
    server_version = "DoseWiseLocal/1.0"

    def log_message(self, fmt, *args):
        sys.stderr.write("  %s\n" % (fmt % args))

    # -- helpers ----------------------------------------------------------
    def _send(self, status, payload, content_type="application/json"):
        if content_type == "application/json":
            body = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        else:
            body = payload if isinstance(payload, bytes) else str(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "content-type,authorization")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _body(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        if not raw:
            return {}, b""
        try:
            return json.loads(raw.decode("utf-8")), raw
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}, raw

    # -- verbs ------------------------------------------------------------
    def do_OPTIONS(self):
        self._send(204, {})

    def do_PUT(self):
        path = urlparse(self.path).path
        if path.startswith("/local-upload/"):
            key = unquote(path[len("/local-upload/") :])
            _, raw = self._body()
            storage.put_bytes(key, raw, self.headers.get("Content-Type", "image/jpeg"))
            return self._send(200, {"key": key, "bytes": len(raw)})
        self._send(404, {"error": "not found"})

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = {k: v[0] for k, v in parse_qs(parsed.query).items()}

        if path.startswith("/local-file/"):
            key = unquote(path[len("/local-file/") :])
            try:
                data = storage.get_bytes(key)
            except FileNotFoundError:
                return self._send(404, {"error": "no such object"})
            kind = "application/pdf" if key.endswith(".pdf") else "image/jpeg"
            return self._send(200, data, kind)

        if path.startswith("/visit-card/"):
            parent_id = path[len("/visit-card/") :]
            card = services.visit_card(parent_id)
            return self._send(200, card["html"], "text/html; charset=utf-8")

        if path == "/demo/runs":
            return self._send(200, {"runs": RUNS})

        status, payload = router.dispatch("GET", path, {}, query)
        self._send(status, payload)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        body, _ = self._body()

        if path == "/demo/seed":
            return self._send(200, seed_demo(**body))
        if path == "/demo/escalate":
            return self._send(
                200,
                escalation_run(
                    body["parentId"],
                    body["slot"],
                    body.get("date"),
                    body.get("waitSeconds", 5 if config.DEMO_MODE else None),
                ),
            )
        if path == "/demo/reset":
            path_db = config.LOCAL_DB_PATH
            if os.path.exists(path_db):
                os.remove(path_db)
            outbox = os.path.join(os.path.dirname(path_db), "outbox.jsonl")
            if os.path.exists(outbox):
                os.remove(outbox)
            from common import store as store_mod

            store_mod._store = None
            RUNS.clear()
            return self._send(200, {"reset": True})

        status, payload = router.dispatch("POST", path, body, query)
        self._send(status, payload)


def main():
    parser = argparse.ArgumentParser(description="DoseWise local API")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 4000)))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--demo", action="store_true", help="30 second escalation waits")
    parser.add_argument("--seed", action="store_true", help="seed a demo family on start")
    args = parser.parse_args()

    if args.demo:
        os.environ["DEMO_MODE"] = "1"
        config.DEMO_MODE = True
        config.WAIT_FIRST_SECONDS = config.WAIT_SECOND_SECONDS = 30

    if args.seed:
        print("seeded:", json.dumps(seed_demo(), indent=2))

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"DoseWise API on http://{args.host}:{args.port}  (backend={config.BACKEND}, demo={config.DEMO_MODE})")
    print("  GET /health   POST /demo/seed   POST /demo/escalate")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")


if __name__ == "__main__":
    main()
