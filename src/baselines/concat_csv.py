"""Concatenate CSV tables that share one header, refusing duplicate pair_id values.

Used to join ID and OOD pairs (or their score files) so the shared evaluator
selects each model's threshold on ID val and applies it unchanged to OOD.

Example:
  python src/baselines/concat_csv.py --out data/processed/id_ood_pairs.csv \
    data/releases/abo-home-reciprocal-v3-candidate/pairs.csv \
    data/releases/abo-ood-v3-20261115-candidate/eval_pairs.csv
"""
import argparse
import csv
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True)
    ap.add_argument("inputs", nargs="+")
    args = ap.parse_args()

    header, rows, seen = None, [], set()
    for path in args.inputs:
        with open(path, newline="", encoding="utf-8-sig") as stream:
            reader = csv.DictReader(stream)
            if header is None:
                header = reader.fieldnames
            elif reader.fieldnames != header:
                raise SystemExit(f"{path}: header differs from {args.inputs[0]}")
            for row in reader:
                if row["pair_id"] in seen:
                    raise SystemExit(f"duplicate pair_id {row['pair_id']} in {path}")
                seen.add(row["pair_id"])
                rows.append(row)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=header, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows from {len(args.inputs)} files to {out}")


if __name__ == "__main__":
    main()
