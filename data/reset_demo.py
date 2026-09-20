"""Wipe the families, parents, medicines, doses and alerts. Start clean.

The medicine dataset (SALT# items) is KEPT by default, because reloading it is
a separate, slower step and it is not what anyone means by "start again".

    python data/reset_demo.py                      # local store
    $env:AWS_PROFILE="dosewise"
    $env:DOSEWISE_BACKEND="aws"
    $env:TABLE_NAME="DoseWise-dev"
    $env:AWS_REGION="ap-south-1"
    python data/reset_demo.py                      # the deployed table

It lists what it will delete and asks before doing it. --yes skips the
question, --all also drops the medicine dataset.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))

from common import config  # noqa: E402
from common.store import store  # noqa: E402

KEEP_PREFIX = "SALT#"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--yes", action="store_true", help="do not ask")
    parser.add_argument("--all", action="store_true", help="also delete the medicine dataset")
    args = parser.parse_args()

    everything = store().scan_prefix("")
    doomed = [i for i in everything if args.all or not str(i.get("PK", "")).startswith(KEEP_PREFIX)]
    kept = len(everything) - len(doomed)

    counts = {}
    for item in doomed:
        counts[item.get("type", "?")] = counts.get(item.get("type", "?"), 0) + 1

    where = f"DynamoDB table {config.TABLE_NAME}" if config.IS_AWS else f"local file {config.LOCAL_DB_PATH}"
    print(f"Target: {where}")
    if not doomed:
        print("Nothing to delete. Already clean.")
        return
    print(f"\nWill delete {len(doomed)} items:")
    for kind, n in sorted(counts.items()):
        print(f"  {n:5}  {kind}")
    if kept:
        print(f"\nKeeping {kept} medicine dataset items (use --all to drop those too).")

    if not args.yes:
        if input("\nType 'delete' to confirm: ").strip().lower() != "delete":
            print("Cancelled. Nothing was touched.")
            return

    for item in doomed:
        store().delete(item["PK"], item["SK"])
    print(f"\nDeleted {len(doomed)} items. Open the app and clear site data to start from the landing page.")


if __name__ == "__main__":
    main()
