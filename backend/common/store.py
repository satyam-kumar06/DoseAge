"""Single-table store.

Two interchangeable backends behind one tiny API:
  * DynamoDB, used on AWS.
  * A JSON file, used locally so the whole product runs with no AWS account.

Key design (from the build plan):
  FAMILY#id        / PROFILE | CAREGIVER#userId | PARENT#parentId
  PARENT#parentId  / MED#medId | SCAN#scanId | DOSE#date#slot#medId | ALERT#ts
  SALT#name        / BRAND#brand
"""
import json
import os
import threading
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional

from . import config

_lock = threading.Lock()
KEY_SEP = "::"


def _clean(obj: Any) -> Any:
    """DynamoDB hands back Decimals; JSON wants plain numbers."""
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    if isinstance(obj, list):
        return [_clean(v) for v in obj]
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    return obj


def _to_ddb(obj: Any) -> Any:
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, list):
        return [_to_ddb(v) for v in obj]
    if isinstance(obj, dict):
        return {k: _to_ddb(v) for k, v in obj.items()}
    return obj


class LocalStore:
    """File-backed stand-in for DynamoDB. Good enough for one machine."""

    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        if not os.path.exists(path):
            self._write({})

    def _read(self) -> Dict[str, Dict[str, Any]]:
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _write(self, data: Dict[str, Any]) -> None:
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2, default=str)
        os.replace(tmp, self.path)

    @staticmethod
    def _key(pk: str, sk: str) -> str:
        return f"{pk}{KEY_SEP}{sk}"

    def put(self, item: Dict[str, Any]) -> Dict[str, Any]:
        with _lock:
            data = self._read()
            data[self._key(item["PK"], item["SK"])] = item
            self._write(data)
        return item

    def batch_put(self, items: Iterable[Dict[str, Any]]) -> int:
        with _lock:
            data = self._read()
            n = 0
            for item in items:
                data[self._key(item["PK"], item["SK"])] = item
                n += 1
            self._write(data)
        return n

    def get(self, pk: str, sk: str) -> Optional[Dict[str, Any]]:
        return self._read().get(self._key(pk, sk))

    def query(self, pk: str, sk_prefix: str = "") -> List[Dict[str, Any]]:
        out = [
            item
            for item in self._read().values()
            if item.get("PK") == pk and str(item.get("SK", "")).startswith(sk_prefix)
        ]
        return sorted(out, key=lambda i: i.get("SK", ""))

    def scan_prefix(self, pk_prefix: str) -> List[Dict[str, Any]]:
        return [i for i in self._read().values() if str(i.get("PK", "")).startswith(pk_prefix)]

    def update(self, pk: str, sk: str, changes: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        with _lock:
            data = self._read()
            key = self._key(pk, sk)
            item = data.get(key)
            if item is None:
                return None
            item.update(changes)
            data[key] = item
            self._write(data)
        return item

    def delete(self, pk: str, sk: str) -> None:
        with _lock:
            data = self._read()
            data.pop(self._key(pk, sk), None)
            self._write(data)


class DynamoStore:
    def __init__(self, table_name: str):
        import boto3  # lazy, so local mode needs no boto3 at all

        self._table = boto3.resource("dynamodb", region_name=config.REGION).Table(table_name)

    def put(self, item: Dict[str, Any]) -> Dict[str, Any]:
        self._table.put_item(Item=_to_ddb(item))
        return item

    def batch_put(self, items: Iterable[Dict[str, Any]]) -> int:
        n = 0
        with self._table.batch_writer() as batch:
            for item in items:
                batch.put_item(Item=_to_ddb(item))
                n += 1
        return n

    def get(self, pk: str, sk: str) -> Optional[Dict[str, Any]]:
        res = self._table.get_item(Key={"PK": pk, "SK": sk})
        item = res.get("Item")
        return _clean(item) if item else None

    def query(self, pk: str, sk_prefix: str = "") -> List[Dict[str, Any]]:
        from boto3.dynamodb.conditions import Key

        cond = Key("PK").eq(pk)
        if sk_prefix:
            cond = cond & Key("SK").begins_with(sk_prefix)
        items, kwargs = [], {"KeyConditionExpression": cond}
        while True:
            res = self._table.query(**kwargs)
            items.extend(res.get("Items", []))
            if "LastEvaluatedKey" not in res:
                break
            kwargs["ExclusiveStartKey"] = res["LastEvaluatedKey"]
        return _clean(items)

    def scan_prefix(self, pk_prefix: str) -> List[Dict[str, Any]]:
        items, kwargs = [], {}
        while True:
            res = self._table.scan(**kwargs)
            items.extend(res.get("Items", []))
            if "LastEvaluatedKey" not in res:
                break
            kwargs["ExclusiveStartKey"] = res["LastEvaluatedKey"]
        return [i for i in _clean(items) if str(i.get("PK", "")).startswith(pk_prefix)]

    def update(self, pk: str, sk: str, changes: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        names = {f"#k{i}": k for i, k in enumerate(changes)}
        values = {f":v{i}": _to_ddb(v) for i, v in enumerate(changes.values())}
        expr = "SET " + ", ".join(f"#k{i} = :v{i}" for i in range(len(changes)))
        res = self._table.update_item(
            Key={"PK": pk, "SK": sk},
            UpdateExpression=expr,
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=values,
            ReturnValues="ALL_NEW",
        )
        return _clean(res.get("Attributes"))

    def delete(self, pk: str, sk: str) -> None:
        self._table.delete_item(Key={"PK": pk, "SK": sk})


_store = None


def store():
    global _store
    if _store is None:
        _store = DynamoStore(config.TABLE_NAME) if config.IS_AWS else LocalStore(config.LOCAL_DB_PATH)
    return _store


def reset_for_tests(path: str) -> None:
    """Point the store at a throwaway file."""
    global _store
    _store = LocalStore(path)
