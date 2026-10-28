"""Draw a stratified subset of a pairs table for expensive models (e.g. Luna).

Sampling unit is the text-source item: all of its rows (pos / N1 / N2 / N3)
are kept together, so per-type recall stays balanced and the evaluator's
3-way R@1 still works. Items are sampled per category in proportion to the
category's size, with a fixed seed.

Every model that is compared with Luna must be evaluated on the same subset
file, so run the evaluator on the subset for those models too.

Example:
  python src/baselines/sample_subset.py \
    --pairs-csv docs/mini_version/pairs.csv --splits test \
    --target-pairs 2000 --seed 0 \
    --out-csv data/processed/luna_subset_test.csv
"""
import argparse
import csv
import random
from collections import Counter, defaultdict
from pathlib import Path

from common import text_item_id


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pairs-csv", default="docs/mini_version/pairs.csv")
    ap.add_argument("--splits", nargs="+", default=["test"])
    ap.add_argument("--target-pairs", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out-csv", default="data/processed/luna_subset_test.csv")
    args = ap.parse_args()

    with open(args.pairs_csv, newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames
        rows = [row for row in reader if row["split"] in set(args.splits)]
    if not rows:
        raise SystemExit(f"no rows with split in {args.splits}")

    # Group rows by text-source item, then items by category.
    by_item = defaultdict(list)
    for row in rows:
        by_item[text_item_id(row)].append(row)
    by_category = defaultdict(list)
    for item, item_rows in by_item.items():
        by_category[item_rows[0]["category"]].append(item)

    total_items = len(by_item)
    rows_per_item = len(rows) / total_items
    target_items = min(total_items, round(args.target_pairs / rows_per_item))

    rng = random.Random(args.seed)
    chosen = []
    # Largest-remainder allocation so category quotas sum exactly to target_items.
    quotas = {cat: target_items * len(items) / total_items for cat, items in by_category.items()}
    alloc = {cat: int(q) for cat, q in quotas.items()}
    leftover = target_items - sum(alloc.values())
    for cat in sorted(quotas, key=lambda c: (quotas[c] - alloc[c], c), reverse=True)[:leftover]:
        alloc[cat] += 1
    for cat in sorted(by_category):
        items = sorted(by_category[cat])
        rng.shuffle(items)
        chosen.extend(items[: alloc[cat]])

    keep = set(chosen)
    subset = [row for row in rows if text_item_id(row) in keep]
    out = Path(args.out_csv)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(subset)

    print(f"wrote {len(subset)} pairs from {len(keep)} text items to {out}")
    print("neg_type counts:", dict(sorted(Counter(r["neg_type"] for r in subset).items())))
    print("split counts:", dict(sorted(Counter(r["split"] for r in subset).items())))


if __name__ == "__main__":
    main()
