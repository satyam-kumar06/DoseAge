"""Load the medicine dataset into DynamoDB (or the local store).

    python data/load_dataset.py                 # local store
    DOSEWISE_BACKEND=aws TABLE_NAME=DoseWise \
      python data/load_dataset.py               # real table

Dataset credits live in docs/DATASET.md. Check each source's licence before
shipping: the CSV in this repo is a small curated seed, not a full dump.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))

from common import salts  # noqa: E402
from common.store import store  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default=None, help="path to medicines.csv")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    records = salts.load_csv(args.csv)
    items = salts.to_items(records)
    print(f"{len(records)} brands -> {len(items)} salt/brand items")

    if args.dry_run:
        for item in items[:5]:
            print(" ", item["PK"], item["SK"], item["salts"])
        return

    written = store().batch_put(items)
    print(f"wrote {written} items")

    missing = [r["brand"] for r in records if not r["salts"]]
    if missing:
        print("brands with no salt listed:", ", ".join(missing))


if __name__ == "__main__":
    main()
