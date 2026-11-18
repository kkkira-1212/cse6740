"""Validation-only diagnostics for a score file (never reads test labels or scores).

Use this before the benchmark is frozen: it reports threshold-free AUC on the
val split only, overall and per negative type. Each negative type is compared
with the positives of the SAME image anchors, because every anchor in the
fixed-image releases (v2 / v3) has exactly one positive and one negative.

Example:
  python src/baselines/val_diagnostics.py \
    --pairs-csv data/releases/abo-home-reciprocal-v3-candidate/pairs.csv \
    --scores-csv scores/abo-home-reciprocal-v3-candidate_siglip_b16_val.csv
"""
import argparse
import csv
import json
from pathlib import Path

from sklearn.metrics import roc_auc_score


def auc(pos, neg):
    if not pos or not neg:
        return None
    return float(roc_auc_score([1] * len(pos) + [0] * len(neg), pos + neg))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pairs-csv", required=True)
    ap.add_argument("--scores-csv", required=True)
    ap.add_argument("--split", default="val", choices=["train", "val"], help="test is deliberately not allowed")
    ap.add_argument("--out-json", help="default: <scores>_diag.json")
    args = ap.parse_args()

    with open(args.pairs_csv, newline="", encoding="utf-8-sig") as stream:
        rows = [r for r in csv.DictReader(stream) if r["split"] == args.split]
    with open(args.scores_csv, newline="", encoding="utf-8-sig") as stream:
        scores = {r["pair_id"]: float(r["score"]) for r in csv.DictReader(stream)}
    missing = [r["pair_id"] for r in rows if r["pair_id"] not in scores]
    if missing:
        raise SystemExit(f"missing scores for {len(missing)} {args.split} pairs, e.g. {missing[:3]}")

    anchor_key = "anchor_item_id" if rows and "anchor_item_id" in rows[0] else None
    pos_by_anchor = {r.get(anchor_key) if anchor_key else r["pair_id"]: scores[r["pair_id"]]
                     for r in rows if r["neg_type"] == "pos"}
    all_pos = list(pos_by_anchor.values())
    all_neg = [scores[r["pair_id"]] for r in rows if r["label"] == "0"]

    report = {"pairs_csv": args.pairs_csv, "scores_csv": args.scores_csv, "split": args.split,
              "n_pairs": len(rows), "auc_overall": auc(all_pos, all_neg), "by_neg_type": {}}
    for neg_type in sorted({r["neg_type"] for r in rows if r["label"] == "0"}):
        negs = [r for r in rows if r["neg_type"] == neg_type]
        neg_scores = [scores[r["pair_id"]] for r in negs]
        paired = None
        if anchor_key:
            # Positives of the same anchors: same images, only the title differs.
            paired_pos = [pos_by_anchor[r[anchor_key]] for r in negs if r[anchor_key] in pos_by_anchor]
            paired = auc(paired_pos, neg_scores)
            wins = sum(pos_by_anchor[r[anchor_key]] > scores[r["pair_id"]]
                       for r in negs if r[anchor_key] in pos_by_anchor)
        report["by_neg_type"][neg_type] = {
            "n": len(negs),
            "auc_vs_all_positives": auc(all_pos, neg_scores),
            "auc_vs_same_anchor_positives": paired,
            "same_anchor_pos_ranked_higher": (wins / len(negs)) if anchor_key and negs else None,
        }

    out = Path(args.out_json or Path(args.scores_csv).with_name(Path(args.scores_csv).stem + "_diag.json"))
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"{args.split}: n={len(rows)} AUC={report['auc_overall']:.4f}")
    for neg_type, d in report["by_neg_type"].items():
        same = d["same_anchor_pos_ranked_higher"]
        print(f"  {neg_type}: n={d['n']} AUC={d['auc_vs_all_positives']:.4f}"
              + (f"  same-image positive ranked higher {same:.1%}" if same is not None else ""))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
