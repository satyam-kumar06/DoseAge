"""SMS and family alerts.

SNS on AWS. Locally every message is appended to an outbox file and also
written into the table as an ALERT item, so the caregiver dashboard shows
exactly what would have been texted. The demo works with no SMS sandbox.
"""
import json
import os
from typing import Any, Dict, List, Optional

from . import config, keys, util
from .store import store

OUTBOX = os.path.join(os.path.dirname(config.LOCAL_DB_PATH), "outbox.jsonl")


def send_sms(phone: str, message: str) -> Dict[str, Any]:
    record = {"to": phone, "message": message, "sentAt": util.iso(util.now_utc())}

    if not config.SNS_ENABLED:
        os.makedirs(os.path.dirname(OUTBOX), exist_ok=True)
        with open(OUTBOX, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        record["channel"] = "outbox"
        return record

    import boto3

    res = boto3.client("sns", region_name=config.REGION).publish(
        PhoneNumber=phone,
        Message=message,
        MessageAttributes={
            "AWS.SNS.SMS.SMSType": {"DataType": "String", "StringValue": "Transactional"}
        },
    )
    record["channel"] = "sns"
    record["messageId"] = res.get("MessageId")
    return record


def read_outbox(limit: int = 50) -> List[Dict[str, Any]]:
    if not os.path.exists(OUTBOX):
        return []
    with open(OUTBOX, "r", encoding="utf-8") as fh:
        lines = fh.readlines()[-limit:]
    return [json.loads(line) for line in lines if line.strip()]


def record_alert(
    parent_id: str,
    alert_type: str,
    message: str,
    message_hi: str = "",
    extra: Optional[Dict[str, Any]] = None,
    dedupe_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Write an ALERT item. Types: DUPLICATE, MISSED, REFILL.

    `dedupe_key` names the fact the alert is about, not the moment it fired.
    Rescanning the same prescription, or two doses missed in the same slot,
    must not stack identical cards on the parent's screen, so an existing
    unread alert with the same key is refreshed in place instead. Once the
    caregiver has read an alert, a later occurrence is genuinely new and gets
    its own card.
    """
    timestamp = util.iso(util.now_utc())

    if dedupe_key:
        for existing in store().query(keys.parent(parent_id), keys.ALERT_PREFIX):
            if existing.get("dedupeKey") == dedupe_key and not existing.get("read"):
                changes = {
                    "message": message,
                    "messageHi": message_hi or message,
                    "createdAt": timestamp,
                    "occurrences": int(existing.get("occurrences", 1)) + 1,
                }
                if extra:
                    changes.update(extra)
                return store().update(keys.parent(parent_id), existing["SK"], changes)

    item = {
        # A bare second-resolution timestamp collides when two alerts land in
        # the same second, and the second one silently overwrites the first.
        "PK": keys.parent(parent_id),
        "SK": keys.alert_sk(timestamp) + "#" + util.new_id()[:6],
        "type": "ALERT",
        "alertType": alert_type,
        "parentId": parent_id,
        "message": message,
        "messageHi": message_hi or message,
        "read": False,
        "createdAt": timestamp,
        "dedupeKey": dedupe_key,
        "occurrences": 1,
    }
    if extra:
        item.update(extra)
    store().put(item)
    return item


def alert_family(parent: Dict[str, Any], caregivers: List[Dict[str, Any]], message: str) -> List[Dict[str, Any]]:
    sent = []
    for caregiver in caregivers:
        phone = caregiver.get("phone")
        if phone:
            sent.append(send_sms(phone, message))
    return sent
