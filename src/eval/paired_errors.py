"""Paired corrected/introduced error analysis between two models.

Joins two score files on the same pairs rows and compares predictions under each
model's own frozen ID-val threshold. Reports pair-level wrong->correct
(corrected) and correct->wrong (introduced) counts, matched-anchor type scopes,
and anchor-level ranking changes.

This is a descriptive comparison, not a significance test or a selection rule.
"""
import argparse
import csv
import hashlib
import importlib.util
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

_EVAL_DIR = str(Path(__file__).resolve().parent)
if _EVAL_DIR not in sys.path:
    sys.path.insert(0, _EVAL_DIR)
import matched_metrics  # noqa: E402

OUTCOMES = ("win", "tie", "loss")
SUMMARY_COLUMNS = (
    "split", "scope", "neg_type", "n_pairs", "n_pos", "n_neg",
    "n_anchors", "n_clusters", "n_exchanges", "cluster",
    "baseline_correct", "adapted_correct", "corrected", "introduced",
    "both_correct", "both_wrong", "baseline_accuracy", "adapted_accuracy",
    "accuracy_delta",
)
RANKING_COLUMNS = (
    "split", "neg_type", "n_anchors", "n_clusters", "cluster",
    "baseline_outcome", "adapted_outcome", "count",
)
CHANGED_COLUMNS = (
    "split", "pair_id", "anchor_item_id", "neg_type", "matched_neg_type",
    "label", "category", "label_status", "change_type",
    "baseline_score", "adapted_score", "baseline_threshold", "adapted_threshold",
    "baseline_prediction", "adapted_prediction", "text", "original_text",
    "image_path", "exchange_id",
)


def load_shared_eval():
    spec = importlib.util.spec_from_file_location(
        "shared_eval", Path(__file__).resolve().parent / "eval.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


shared_eval = load_shared_eval()


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def md_table(headers, rows):
    lines = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return lines


def fmt_pct(value):
    return "—" if value is None else f"{100 * value:.2f}%"


def fmt_delta(value):
    if value is None:
        return "—"
    return f"{100 * value:+.2f} pp"


def predicted_match(score, threshold):
    return score >= threshold


def is_correct(row, score, threshold):
    matched = predicted_match(score, threshold)
    return int(matched) == int(row["label"])


def pair_summary(rows, baseline_threshold, adapted_threshold):
    counts = Counter()
    for row in rows:
        baseline_ok = is_correct(row, row["baseline_score"], baseline_threshold)
        adapted_ok = is_correct(row, row["adapted_score"], adapted_threshold)
        counts["n_pairs"] += 1
        counts["n_pos"] += int(row["label"])
        counts["baseline_correct"] += int(baseline_ok)
        counts["adapted_correct"] += int(adapted_ok)
        if not baseline_ok and adapted_ok:
            counts["corrected"] += 1
        elif baseline_ok and not adapted_ok:
            counts["introduced"] += 1
        elif baseline_ok and adapted_ok:
            counts["both_correct"] += 1
        else:
            counts["both_wrong"] += 1
    n_pairs = counts["n_pairs"]
    baseline_accuracy = counts["baseline_correct"] / n_pairs if n_pairs else None
    adapted_accuracy = counts["adapted_correct"] / n_pairs if n_pairs else None
    return {
        "n_pairs": n_pairs,
        "n_pos": counts["n_pos"],
        "n_neg": n_pairs - counts["n_pos"],
        "baseline_correct": counts["baseline_correct"],
        "adapted_correct": counts["adapted_correct"],
        "corrected": counts["corrected"],
        "introduced": counts["introduced"],
        "both_correct": counts["both_correct"],
        "both_wrong": counts["both_wrong"],
        "baseline_accuracy": baseline_accuracy,
        "adapted_accuracy": adapted_accuracy,
        "accuracy_delta": (
            adapted_accuracy - baseline_accuracy
            if n_pairs else None
        ),
    }


def ranking_outcome(positive_score, negative_score):
    if positive_score > negative_score:
        return "win"
    if positive_score == negative_score:
        return "tie"
    return "loss"


def ranking_summary(units):
    if not units:
        return None
    anchors = [(unit.split, unit.anchor_item_id) for unit in units]
    if len(set(anchors)) != len(anchors):
        raise ValueError(
            "multiple negative rows share an anchor; anchor-level ranking is ambiguous"
        )
    matrix = {baseline: {adapted: 0 for adapted in OUTCOMES} for baseline in OUTCOMES}
    for unit in units:
        baseline = ranking_outcome(
            unit.positive["baseline_score"], unit.negative["baseline_score"]
        )
        adapted = ranking_outcome(
            unit.positive["adapted_score"], unit.negative["adapted_score"]
        )
        matrix[baseline][adapted] += 1
    return {
        "n_anchors": len(units),
        "n_clusters": len({unit.cluster_key for unit in units}),
        "n_exchanges": (
            len({unit.cluster_key for unit in units})
            if units[0].cluster == matched_metrics.EXCHANGE_CLUSTER else None
        ),
        "cluster": units[0].cluster,
        "matrix": matrix,
        "improved": sum(
            matrix[baseline][adapted]
            for baseline in OUTCOMES if baseline != "win"
            for adapted in OUTCOMES if adapted == "win"
        ),
        "worsened": sum(
            matrix[baseline][adapted]
            for baseline in OUTCOMES if baseline == "win"
            for adapted in OUTCOMES if adapted != "win"
        ),
        "both_win": matrix["win"]["win"],
        "both_not_win": sum(
            matrix[baseline][adapted]
            for baseline in OUTCOMES if baseline != "win"
            for adapted in OUTCOMES if adapted != "win"
        ),
        "ties_introduced": sum(
            matrix[baseline]["tie"] for baseline in OUTCOMES if baseline != "tie"
        ),
        "ties_removed": sum(
            matrix["tie"][adapted] for adapted in OUTCOMES if adapted != "tie"
        ),
    }


def attach_scores(pairs, scores, key, label, required_rows):
    pair_ids = {row["pair_id"] for row in pairs}
    extra = set(scores) - pair_ids
    if extra:
        raise ValueError(
            f"{label} scores: {len(extra)} pair_ids are not in the pairs table "
            f"(e.g. {sorted(extra)[:3]})"
        )
    missing = [row["pair_id"] for row in required_rows if row["pair_id"] not in scores]
    if missing:
        raise ValueError(
            f"{label} scores: missing {len(missing)}/{len(required_rows)} selected pairs "
            f"(e.g. {missing[:3]})"
        )
    for row in pairs:
        if row["pair_id"] in scores:
            row[key] = scores[row["pair_id"]]


def exchange_lookups(rows, provenance_rows):
    exchange_by_pair = matched_metrics.build_exchange_map(rows, provenance_rows)
    exchange_by_anchor = {}
    for row in rows:
        if row["label"] != 0 or row["neg_type"] != "N3":
            continue
        exchange_by_anchor[(row["split"], row["anchor_item_id"])] = (
            exchange_by_pair[row["pair_id"]]
        )
    return exchange_by_pair, exchange_by_anchor


def original_title(row, provenance_by_pair, provenance_by_anchor):
    """Original title for a changed row; N3 may carry it in provenance."""
    if row["label"] != 0 or row["neg_type"] != "N3":
        return row["text"]
    provenance = (
        provenance_by_pair.get(row["pair_id"])
        or provenance_by_anchor.get(row["anchor_item_id"])
    )
    if provenance and provenance.get("original_text"):
        return provenance["original_text"].strip()
    return row["text"]


def write_csv(path, columns, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(columns)
        for row in rows:
            writer.writerow([_format(row.get(column)) for column in columns])


def _format(value):
    if value is None:
        return ""
    if isinstance(value, float):
        return repr(value)
    return str(value)


def write_markdown(path, meta, summary_rows, ranking_rows, changed_counts):
    lines = [
        "# Paired error analysis",
        "",
        f"- Pairs: `{meta['pairs_csv']}`",
        f"- Baseline scores: `{meta['baseline']['scores_csv']}` "
        f"(threshold `{meta['baseline']['threshold']!r}`)",
        f"- Adapted scores: `{meta['adapted']['scores_csv']}` "
        f"(threshold `{meta['adapted']['threshold']!r}`)",
        f"- Test splits: {', '.join(f'`{s}`' for s in meta['test_splits'])}",
        f"- Rule: `score >= model-specific ID-val threshold`",
        "",
        "## Pair prediction changes",
        "",
    ]
    headers = [
        "Split", "Scope", "Type", "n", "Corrected", "Introduced",
        "Both correct", "Both wrong", "Baseline acc", "Adapted acc", "Delta acc",
    ]
    table_rows = []
    for row in summary_rows:
        table_rows.append([
            row["split"], row["scope"], row["neg_type"], str(row["n_pairs"]),
            str(row["corrected"]), str(row["introduced"]),
            str(row["both_correct"]), str(row["both_wrong"]),
            fmt_pct(row["baseline_accuracy"]), fmt_pct(row["adapted_accuracy"]),
            fmt_delta(row["accuracy_delta"]),
        ])
    lines.extend(md_table(headers, table_rows))
    lines.append("")
    lines.extend([
        "## Anchor ranking changes",
        "",
    ])
    headers = [
        "Split", "Type", "n anchors", "Improved", "Worsened",
        "Both win", "Both not win", "Ties introduced", "Ties removed",
    ]
    table_rows = []
    for row in ranking_rows:
        table_rows.append([
            row["split"], row["neg_type"], str(row["n_anchors"]),
            str(row["improved"]), str(row["worsened"]), str(row["both_win"]),
            str(row["both_not_win"]), str(row["ties_introduced"]),
            str(row["ties_removed"]),
        ])
    lines.extend(md_table(headers, table_rows))
    lines.append("")
    lines.extend([
        "## Changed IDs",
        "",
        f"- Total changed pairs: {changed_counts['total']}",
        f"- Corrected (wrong -> correct): {changed_counts['corrected']}",
        f"- Introduced (correct -> wrong): {changed_counts['introduced']}",
        f"- Details: `{meta['out_changed_csv']}`",
        "",
        "## Notes",
        "",
        "- Rows are joined by `pair_id`; each model uses its own frozen ID-val threshold.",
        "- Prediction is 1 for match (`score >= threshold`) and 0 otherwise.",
        "- Matched scopes compare each negative with the positive of its own `anchor_item_id`.",
        "- Corrected = baseline wrong and adapted correct; introduced = baseline correct and adapted wrong.",
        "- Anchor ranking uses strict `positive > negative`; ties are counted separately.",
        "- Improved/worsened include moves into and out of ties; the tie columns isolate those cases.",
        "- Counts describe where adaptation helps or hurts, not a selection rule or significance test.",
        "- Model-assisted data QC flags remain in `label_status`; they are not relabeled here.",
        "",
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write("\n".join(lines))


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--pairs-csv", required=True)
    parser.add_argument("--baseline-scores", required=True)
    parser.add_argument("--adapted-scores", required=True)
    parser.add_argument("--baseline-threshold", type=float, required=True,
                        help="baseline model's frozen ID-val threshold")
    parser.add_argument("--adapted-threshold", type=float, required=True,
                        help="adapted model's frozen ID-val threshold")
    parser.add_argument("--test-splits", nargs="+", default=["test"])
    parser.add_argument("--n3-provenance",
                        help="N3 provenance CSV with exchange_id; required when "
                             "N3 negatives are present")
    parser.add_argument("--out-csv", help="summary CSV (default: <stem>.csv)")
    parser.add_argument("--out-ranking-csv",
                        help="ranking matrix CSV (default: <stem>_ranking.csv)")
    parser.add_argument("--out-changed-csv",
                        help="changed pair IDs CSV (default: <stem>_changed.csv)")
    parser.add_argument("--out-json", help="provenance JSON (default: <stem>.json)")
    parser.add_argument("--out-md", help="Markdown report (default: <stem>.md)")
    args = parser.parse_args(argv)

    for name in ("baseline_threshold", "adapted_threshold"):
        if not math.isfinite(getattr(args, name)):
            parser.error(f"--{name.replace('_', '-')} must be finite")
    test_splits = list(dict.fromkeys(args.test_splits))

    pairs = shared_eval.load_pairs(args.pairs_csv)
    baseline_scores = shared_eval.load_scores(args.baseline_scores)
    adapted_scores = shared_eval.load_scores(args.adapted_scores)

    selected = [row for row in pairs if row["split"] in test_splits]
    for split in test_splits:
        rows = [row for row in selected if row["split"] == split]
        if not rows:
            raise ValueError(f"no rows in test split {split!r}")
        if len({row["label"] for row in rows}) < 2:
            raise ValueError(
                f"test split {split!r} must contain both positives and negatives"
            )
    attach_scores(
        pairs, baseline_scores, "baseline_score", "baseline", required_rows=selected
    )
    attach_scores(
        pairs, adapted_scores, "adapted_score", "adapted", required_rows=selected
    )

    n3_present = any(
        row["label"] == 0 and row["neg_type"] == "N3" for row in selected
    )
    if n3_present and not args.n3_provenance:
        parser.error(
            "--n3-provenance is required when the selected test splits contain N3 negatives"
        )
    provenance_rows = []
    if args.n3_provenance:
        _, provenance_rows = shared_eval.read_csv_rows(args.n3_provenance)
    provenance_by_pair = {}
    provenance_by_anchor = {}
    for provenance in provenance_rows:
        pair_id = (provenance.get("pair_id") or "").strip()
        if pair_id:
            provenance_by_pair[pair_id] = provenance
        anchor = (provenance.get("anchor_item_id") or "").strip()
        if anchor:
            provenance_by_anchor[anchor] = provenance
    exchange_by_pair, exchange_by_anchor = exchange_lookups(
        selected, provenance_rows
    )

    anchor_types = defaultdict(set)
    for row in selected:
        if row["label"] == 0:
            anchor_types[(row["split"], row["anchor_item_id"])].add(row["neg_type"])

    baseline_threshold = args.baseline_threshold
    adapted_threshold = args.adapted_threshold
    summary_rows = []
    ranking_rows = []
    changed_rows = []

    for split in test_splits:
        rows = [row for row in selected if row["split"] == split]
        all_summary = pair_summary(rows, baseline_threshold, adapted_threshold)
        summary_rows.append({
            "split": split,
            "scope": "all_pairs",
            "neg_type": "all",
            "n_anchors": None,
            "n_clusters": None,
            "n_exchanges": None,
            "cluster": None,
            **all_summary,
        })
        for neg_type in matched_metrics.negative_types(rows):
            units = matched_metrics.matched_units(rows, neg_type, exchange_by_pair)
            matched_rows = (
                [unit.positive for unit in units]
                + [unit.negative for unit in units]
            )
            matched_summary = pair_summary(
                matched_rows, baseline_threshold, adapted_threshold
            )
            if matched_summary["n_pos"] != len(units):
                raise ValueError(
                    f"{split}/{neg_type}: matched positives do not match unit count"
                )
            ranking = ranking_summary(units)
            summary_rows.append({
                "split": split,
                "scope": "matched_anchor",
                "neg_type": neg_type,
                "n_anchors": ranking["n_anchors"],
                "n_clusters": ranking["n_clusters"],
                "n_exchanges": ranking["n_exchanges"],
                "cluster": ranking["cluster"],
                **matched_summary,
            })
            ranking_rows.append({
                "split": split,
                "neg_type": neg_type,
                **ranking,
            })

        for row in rows:
            baseline_ok = is_correct(row, row["baseline_score"], baseline_threshold)
            adapted_ok = is_correct(row, row["adapted_score"], adapted_threshold)
            if baseline_ok == adapted_ok:
                continue
            matched_type = ";".join(sorted(
                anchor_types.get((split, row["anchor_item_id"]), {row["neg_type"]})
            ))
            exchange_id = exchange_by_pair.get(row["pair_id"])
            if exchange_id is None:
                exchange_id = exchange_by_anchor.get(
                    (split, row["anchor_item_id"]), ""
                )
            original_text = original_title(
                row, provenance_by_pair, provenance_by_anchor
            )
            changed_rows.append({
                "split": split,
                "pair_id": row["pair_id"],
                "anchor_item_id": row["anchor_item_id"],
                "neg_type": row["neg_type"],
                "matched_neg_type": matched_type,
                "label": row["label"],
                "category": row["category"],
                "label_status": row["label_status"],
                "change_type": "corrected" if adapted_ok else "introduced",
                "baseline_score": row["baseline_score"],
                "adapted_score": row["adapted_score"],
                "baseline_threshold": baseline_threshold,
                "adapted_threshold": adapted_threshold,
                "baseline_prediction": int(
                    predicted_match(row["baseline_score"], baseline_threshold)
                ),
                "adapted_prediction": int(
                    predicted_match(row["adapted_score"], adapted_threshold)
                ),
                "text": row["text"],
                "original_text": original_text,
                "image_path": row["image_path"],
                "exchange_id": exchange_id,
            })

    changed_rows.sort(key=lambda row: (
        row["split"], row["change_type"], row["neg_type"], row["pair_id"]
    ))
    change_counts = Counter(row["change_type"] for row in changed_rows)

    adapted_path = Path(args.adapted_scores)
    baseline_path = Path(args.baseline_scores)
    stem = f"{adapted_path.stem}_vs_{baseline_path.stem}_paired"
    out_csv = (
        Path(args.out_csv) if args.out_csv
        else adapted_path.parent / f"{stem}.csv"
    )
    out_ranking_csv = (
        Path(args.out_ranking_csv) if args.out_ranking_csv
        else out_csv.with_name(f"{out_csv.stem}_ranking.csv")
    )
    out_changed_csv = (
        Path(args.out_changed_csv) if args.out_changed_csv
        else out_csv.with_name(f"{out_csv.stem}_changed.csv")
    )
    out_json = (
        Path(args.out_json) if args.out_json
        else out_csv.with_suffix(".json")
    )
    out_md = (
        Path(args.out_md) if args.out_md
        else out_csv.with_suffix(".md")
    )

    ranking_by_split = defaultdict(dict)
    ranking_csv_rows = []
    for row in ranking_rows:
        ranking_by_split[row["split"]][row["neg_type"]] = {
            key: value for key, value in row.items()
            if key not in ("split", "neg_type")
        }
        for baseline_outcome in OUTCOMES:
            for adapted_outcome in OUTCOMES:
                ranking_csv_rows.append({
                    "split": row["split"],
                    "neg_type": row["neg_type"],
                    "n_anchors": row["n_anchors"],
                    "n_clusters": row["n_clusters"],
                    "cluster": row["cluster"],
                    "baseline_outcome": baseline_outcome,
                    "adapted_outcome": adapted_outcome,
                    "count": row["matrix"][baseline_outcome][adapted_outcome],
                })

    result = {
        "tool": "src/eval/paired_errors.py",
        "pairs_csv": args.pairs_csv,
        "baseline": {
            "scores_csv": args.baseline_scores,
            "threshold": baseline_threshold,
            "sha256": sha256(args.baseline_scores),
        },
        "adapted": {
            "scores_csv": args.adapted_scores,
            "threshold": adapted_threshold,
            "sha256": sha256(args.adapted_scores),
        },
        "test_splits": test_splits,
        "n3_provenance": args.n3_provenance,
        "n3_provenance_sha256": (
            sha256(args.n3_provenance) if args.n3_provenance else None
        ),
        "input_sha256": {
            args.pairs_csv: sha256(args.pairs_csv),
            args.baseline_scores: sha256(args.baseline_scores),
            args.adapted_scores: sha256(args.adapted_scores),
            **({args.n3_provenance: sha256(args.n3_provenance)}
               if args.n3_provenance else {}),
        },
        "n_pairs": {
            "selected": len(selected),
            "by_split": {
                split: sum(row["split"] == split for row in selected)
                for split in test_splits
            },
        },
        "summary": summary_rows,
        "ranking": dict(ranking_by_split),
        "changed_counts": {
            "total": len(changed_rows),
            "corrected": change_counts.get("corrected", 0),
            "introduced": change_counts.get("introduced", 0),
            "by_split": dict(Counter(row["split"] for row in changed_rows)),
            "by_neg_type": dict(Counter(row["neg_type"] for row in changed_rows)),
            "by_matched_neg_type": dict(
                Counter(row["matched_neg_type"] for row in changed_rows)
            ),
        },
        "out_changed_csv": str(out_changed_csv),
        "notes": [
            "Each model uses its own frozen ID-val threshold with rule score >= threshold.",
            "Matched scopes pair each negative with its own anchor_item_id positive.",
            "Anchor ranking uses strict positive > negative; ties are counted separately.",
            "Counts describe where adaptation helps or hurts, not a selection rule.",
        ],
    }

    write_csv(out_csv, SUMMARY_COLUMNS, summary_rows)
    write_csv(out_ranking_csv, RANKING_COLUMNS, ranking_csv_rows)
    write_csv(out_changed_csv, CHANGED_COLUMNS, changed_rows)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    with out_json.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    write_markdown(
        out_md,
        {
            "pairs_csv": args.pairs_csv,
            "baseline": result["baseline"],
            "adapted": result["adapted"],
            "test_splits": test_splits,
            "out_changed_csv": str(out_changed_csv),
        },
        summary_rows,
        ranking_rows,
        result["changed_counts"],
    )

    print(
        f"selected={len(selected)} corrected={result['changed_counts']['corrected']} "
        f"introduced={result['changed_counts']['introduced']}"
    )
    print(f"wrote {out_csv}")
    print(f"wrote {out_ranking_csv}")
    print(f"wrote {out_changed_csv}")
    print(f"wrote {out_json}")
    print(f"wrote {out_md}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2) from None
