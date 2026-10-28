r"""WP4 shared evaluator for image-title matching scores.

Reads a pairs table (docs/schema.md) and a scores table (pair_id,score,
higher = more likely a match), selects one threshold on the validation split,
and reports metrics on the test split(s). Writes a long-format CSV, a Markdown
report, and a JSON sidecar with provenance.

Examples:
  python src/eval/eval.py \
    --pairs-csv docs/mini_version/pairs.csv \
    --scores-csv scores/clip_vit_b32_zero_shot.csv

  python src/eval/eval.py \
    --pairs-csv data/processed/pairs.csv \
    --scores-csv scores/lora_r8_seed0.csv \
    --drop-cross-split-images --r-at-1 --bootstrap 1000
"""
import argparse
import csv
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score

PAIR_REQUIRED = ("pair_id", "label", "neg_type", "split")
SCORE_REQUIRED = ("pair_id", "score")
NEG_TYPES = ("N1", "N2", "N3")
GROUP_DIMENSIONS = ("split", "neg_type", "category", "year")
OBJECTIVES = ("accuracy", "balanced_accuracy")
METRIC_NAMES = ("accuracy", "auc", "positive_recall", "negative_recall", "balanced_accuracy")
CSV_COLUMNS = (
    "dimension", "value", "n", "n_pos", "n_neg", "threshold",
    "accuracy", "auc", "positive_recall", "negative_recall", "balanced_accuracy",
    "recall_N1", "recall_N2", "recall_N3", "r_at_1",
    "accuracy_ci_low", "accuracy_ci_high",
    "auc_ci_low", "auc_ci_high",
    "positive_recall_ci_low", "positive_recall_ci_high",
    "negative_recall_ci_low", "negative_recall_ci_high",
    "balanced_accuracy_ci_low", "balanced_accuracy_ci_high",
    "r_at_1_ci_low", "r_at_1_ci_high",
)


def warn(message):
    print(f"warning: {message}", file=sys.stderr)


def read_csv_rows(path):
    with open(path, newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        headers = reader.fieldnames or []
        rows = list(reader)
    return headers, rows


def text_item_id(pair_id, neg_type):
    """Text-source item id: pair_id is <text_item_id>_<neg_type> per schema."""
    suffix = f"_{neg_type}"
    return pair_id[: -len(suffix)] if pair_id.endswith(suffix) else pair_id


def load_pairs(path):
    headers, rows = read_csv_rows(path)
    missing = [name for name in PAIR_REQUIRED if name not in headers]
    if missing:
        raise ValueError(f"{path}: missing columns {missing}")
    pairs = []
    seen = set()
    for line, row in enumerate(rows, start=2):
        pair_id = (row.get("pair_id") or "").strip()
        label_raw = (row.get("label") or "").strip()
        neg_type = (row.get("neg_type") or "").strip()
        split = (row.get("split") or "").strip()
        if not pair_id:
            raise ValueError(f"{path}:{line}: empty pair_id")
        if pair_id in seen:
            raise ValueError(f"{path}:{line}: duplicate pair_id {pair_id!r}")
        if label_raw not in ("0", "1"):
            raise ValueError(f"{path}:{line}: label must be 0 or 1, got {label_raw!r}")
        if not neg_type:
            raise ValueError(f"{path}:{line}: empty neg_type")
        if not split:
            raise ValueError(f"{path}:{line}: empty split")
        if not pair_id.endswith(f"_{neg_type}"):
            raise ValueError(f"{path}:{line}: pair_id {pair_id!r} must end with '_{neg_type}'")
        label = int(label_raw)
        if label == 1 and neg_type != "pos":
            raise ValueError(f"{path}:{line}: label 1 must have neg_type 'pos', got {neg_type!r}")
        if label == 0 and neg_type == "pos":
            raise ValueError(f"{path}:{line}: label 0 must not have neg_type 'pos'")
        seen.add(pair_id)
        pairs.append({
            "pair_id": pair_id,
            "label": label,
            "neg_type": neg_type,
            "split": split,
            "category": (row.get("category") or "").strip(),
            "year": (row.get("year") or "").strip(),
            "image_path": (row.get("image_path") or "").strip(),
            "text_item_id": text_item_id(pair_id, neg_type),
        })
    if not pairs:
        raise ValueError(f"{path}: no rows")
    return pairs


def load_scores(path):
    headers, rows = read_csv_rows(path)
    missing = [name for name in SCORE_REQUIRED if name not in headers]
    if missing:
        raise ValueError(f"{path}: missing columns {missing}")
    scores = {}
    for line, row in enumerate(rows, start=2):
        pair_id = (row.get("pair_id") or "").strip()
        if not pair_id:
            raise ValueError(f"{path}:{line}: empty pair_id")
        if pair_id in scores:
            raise ValueError(f"{path}:{line}: duplicate pair_id {pair_id!r}")
        raw = (row.get("score") or "").strip()
        try:
            score = float(raw)
        except ValueError:
            raise ValueError(f"{path}:{line}: score is not a number: {raw!r}") from None
        if not np.isfinite(score):
            raise ValueError(f"{path}:{line}: score must be finite, got {score!r}")
        scores[pair_id] = score
    if not scores:
        raise ValueError(f"{path}: no rows")
    return scores


def merge_scores(pairs, scores):
    pair_ids = {row["pair_id"] for row in pairs}
    extra = set(scores) - pair_ids
    if extra:
        raise ValueError(f"{len(extra)} scores have no pair (e.g. {sorted(extra)[:3]})")
    for row in pairs:
        if row["pair_id"] in scores:
            row["score"] = scores[row["pair_id"]]
    return pairs


def require_scores(rows, split):
    missing = [row["pair_id"] for row in rows if "score" not in row]
    if missing:
        raise ValueError(
            f"missing scores for {len(missing)}/{len(rows)} pairs in split {split!r} "
            f"(e.g. {missing[:3]})"
        )


def find_cross_split_images(pairs):
    splits = defaultdict(set)
    for row in pairs:
        if row["image_path"]:
            splits[row["image_path"]].add(row["split"])
    return {path: sorted(values) for path, values in splits.items() if len(values) > 1}


def read_id_list(path):
    ids = set()
    for line in Path(path).read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            ids.add(line)
    return ids


def apply_exclusions(pairs, cross_split_paths, excluded_pair_ids):
    kept = []
    dropped = defaultdict(int)
    dropped_by_split = defaultdict(lambda: defaultdict(int))
    for row in pairs:
        reasons = []
        if row["image_path"] in cross_split_paths:
            reasons.append("cross_split_image")
        if row["pair_id"] in excluded_pair_ids:
            reasons.append("excluded_pair")
        if reasons:
            for reason in reasons:
                dropped[reason] += 1
                dropped_by_split[reason][row["split"]] += 1
        else:
            kept.append(row)
    return kept, dict(dropped), {reason: dict(splits) for reason, splits in dropped_by_split.items()}


def rows_for_split(pairs, split):
    return [row for row in pairs if row["split"] == split]


def select_threshold(rows, objective):
    if objective not in OBJECTIVES:
        raise ValueError(f"unknown objective {objective!r}")
    y = np.array([row["label"] for row in rows], dtype=np.int8)
    scores = np.array([row["score"] for row in rows], dtype=np.float64)
    if y.min() == y.max():
        raise ValueError("threshold selection requires both labels in the validation split")
    n = len(y)
    n_pos = int(y.sum())
    n_neg = n - n_pos
    order = np.argsort(scores, kind="stable")
    sorted_scores = scores[order]
    sorted_y = y[order]
    # For a threshold equal to a unique score, positives are the suffix at the
    # first occurrence of that score. Sort once and use suffix counts.
    positive_suffix = np.cumsum(sorted_y[::-1])[::-1]
    unique_values, first_index = np.unique(sorted_scores, return_index=True)
    positives_ge = positive_suffix[first_index]
    negatives_ge = (n - first_index) - positives_ge
    negatives_lt = n_neg - negatives_ge
    if objective == "accuracy":
        values = (positives_ge + negatives_lt) / n
        above_max = n_neg / n
    else:
        values = (positives_ge / n_pos + negatives_lt / n_neg) / 2.0
        above_max = 0.5
    # The extra candidate above the maximum represents predicting every pair
    # negative. np.argmax returns the first maximum, i.e. the smallest threshold.
    candidates = np.append(unique_values, np.nextafter(unique_values[-1], np.inf))
    values = np.append(values, above_max)
    best = int(np.argmax(values))
    return float(candidates[best]), float(values[best])


def within_title_r_at_1(rows):
    """Fraction of titles whose positive image outranks all their negatives.

    The candidate set is the title's own pos/N1/N2 images from the pairs table,
    not the global test image pool. Ties count as failures.
    """
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["text_item_id"]].append(row)
    eligible = 0
    correct = 0
    for group in grouped.values():
        positives = [row["score"] for row in group if row["label"] == 1]
        negatives = [row["score"] for row in group if row["label"] == 0]
        if not positives or not negatives:
            continue
        eligible += 1
        if max(positives) > max(negatives):
            correct += 1
    return correct / eligible if eligible else None


def compute_metrics(rows, threshold, include_r_at_1=False):
    if not rows:
        return {
            "n": 0, "n_pos": 0, "n_neg": 0, "accuracy": None, "auc": None,
            "positive_recall": None, "negative_recall": None,
            "balanced_accuracy": None, "negatives_by_type": {},
        }
    y = np.array([row["label"] for row in rows], dtype=np.int8)
    scores = np.array([row["score"] for row in rows], dtype=np.float64)
    predicted = scores >= threshold
    n_pos = int(y.sum())
    n_neg = len(rows) - n_pos
    positive_recall = float(np.mean(predicted[y == 1])) if n_pos else None
    negative_recall = float(np.mean(~predicted[y == 0])) if n_neg else None
    balanced = (
        (positive_recall + negative_recall) / 2.0
        if positive_recall is not None and negative_recall is not None else None
    )
    auc = float(roc_auc_score(y, scores)) if n_pos and n_neg else None
    negatives_by_type = {}
    for neg_type in sorted({row["neg_type"] for row in rows if row["label"] == 0}):
        subset = [row for row in rows if row["neg_type"] == neg_type]
        negatives_by_type[neg_type] = {
            "n": len(subset),
            "recall": float(np.mean([row["score"] < threshold for row in subset])),
        }
    result = {
        "n": len(rows),
        "n_pos": n_pos,
        "n_neg": n_neg,
        "accuracy": float(np.mean(predicted == y)),
        "auc": auc,
        "positive_recall": positive_recall,
        "negative_recall": negative_recall,
        "balanced_accuracy": balanced,
        "negatives_by_type": negatives_by_type,
    }
    if include_r_at_1:
        result["r_at_1"] = within_title_r_at_1(rows)
    return result


def build_records(rows, threshold, include_r_at_1=False):
    records = [{
        "dimension": "overall",
        "value": "all",
        **compute_metrics(rows, threshold, include_r_at_1),
    }]
    for dimension in GROUP_DIMENSIONS:
        values = sorted({row[dimension] for row in rows if row[dimension]})
        for value in values:
            subset = [row for row in rows if row[dimension] == value]
            records.append({
                "dimension": dimension,
                "value": value,
                **compute_metrics(subset, threshold, include_r_at_1),
            })
    return records


def bootstrap_ci(rows, threshold, n_resamples, seed, include_r_at_1=False):
    """Percentile CI from a cluster bootstrap over text-source items."""
    if n_resamples <= 0 or not rows:
        return None
    clusters = defaultdict(list)
    for row in rows:
        clusters[row["text_item_id"]].append(row)
    keys = list(clusters)
    rng = np.random.default_rng(seed)
    names = list(METRIC_NAMES) + (["r_at_1"] if include_r_at_1 else [])
    samples = {name: [] for name in names}
    for _ in range(n_resamples):
        resampled = []
        for key in rng.choice(keys, size=len(keys), replace=True):
            resampled.extend(clusters[str(key)])
        result = compute_metrics(resampled, threshold, include_r_at_1)
        for name in names:
            value = result.get(name)
            if value is not None and np.isfinite(value):
                samples[name].append(value)
    return {
        name: {
            "low": float(np.percentile(values, 2.5)),
            "high": float(np.percentile(values, 97.5)),
            "valid_resamples": len(values),
        } if values else None
        for name, values in samples.items()
    }


def attach_ci(records, ci_by_key):
    for record in records:
        ci = ci_by_key.get((record["dimension"], record["value"]))
        if ci is not None:
            record["ci"] = ci


def describe_dropped(dropped, dropped_by_split):
    labels = {"cross_split_image": "cross-split image", "excluded_pair": "excluded pair"}
    parts = []
    for reason, count in sorted(dropped.items()):
        detail = ", ".join(
            f"{split} {n}" for split, n in sorted(dropped_by_split.get(reason, {}).items())
        )
        label = labels.get(reason, reason.replace("_", " "))
        parts.append(f"{label}: {count}" + (f" ({detail})" if detail else ""))
    return "; ".join(parts)


def format_value(value):
    if value is None:
        return ""
    if isinstance(value, float):
        return repr(value)
    return str(value)


def write_csv(path, records, threshold):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(CSV_COLUMNS)
        for record in records:
            row = {
                "dimension": record["dimension"],
                "value": record["value"],
                "n": record["n"],
                "n_pos": record["n_pos"],
                "n_neg": record["n_neg"],
                "threshold": float(threshold),
                "accuracy": record.get("accuracy"),
                "auc": record.get("auc"),
                "positive_recall": record.get("positive_recall"),
                "negative_recall": record.get("negative_recall"),
                "balanced_accuracy": record.get("balanced_accuracy"),
                "r_at_1": record.get("r_at_1"),
            }
            negatives = record.get("negatives_by_type", {})
            for neg_type in NEG_TYPES:
                row[f"recall_{neg_type}"] = (negatives.get(neg_type) or {}).get("recall")
            ci = record.get("ci") or {}
            for name in ("accuracy", "auc", "positive_recall", "negative_recall", "balanced_accuracy", "r_at_1"):
                interval = ci.get(name) or {}
                row[f"{name}_ci_low"] = interval.get("low")
                row[f"{name}_ci_high"] = interval.get("high")
            writer.writerow([format_value(row[column]) for column in CSV_COLUMNS])


def md_escape(text):
    return str(text).replace("|", "\\|")


def md_table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |",
             "|" + "|".join("---" for _ in headers) + "|"]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return lines


def fmt_pct(value):
    return "—" if value is None else f"{100 * value:.2f}%"


def fmt_num(value, digits=4):
    return "—" if value is None else f"{value:.{digits}f}"


def fmt_metric(record, name, formatter):
    value = record.get(name)
    if value is None:
        return "—"
    interval = (record.get("ci") or {}).get(name)
    if interval is None:
        return formatter(value)
    return f"{formatter(value)} [{formatter(interval['low'])}, {formatter(interval['high'])}]"


def write_markdown(path, meta, records):
    include_r_at_1 = meta["include_r_at_1"]
    lines = [
        "# Evaluation report",
        "",
        f"- Pairs: `{meta['pairs_csv']}`",
        f"- Scores: `{meta['scores_csv']}`",
        f"- Selection: `{meta['selection_split']}`"
        + (f" / `{meta['objective']}`" if meta["selection_split"] != "fixed" else ""),
        f"- Rule: `{meta['rule']}`",
        f"- Threshold: `{meta['threshold']!r}`",
        f"- Test splits: {', '.join(f'`{s}`' for s in meta['test_splits'])}",
        f"- Pairs: val {meta['n_val']}, test {meta['n_test']}",
    ]
    if meta["n_val"] and meta["val"] is None:
        lines.append("- Validation metrics omitted: not all validation pairs have scores.")
    if meta["dropped"]:
        lines.append(f"- Excluded pairs: {meta['dropped_text']}")
    if meta["cross_split_images"] and not meta["drop_cross_split_images"]:
        lines.append(
            f"- **WARNING:** {len(meta['cross_split_images'])} image paths occur in multiple splits; "
            "re-run with `--drop-cross-split-images` for leak-free test numbers."
        )
    if meta["bootstrap"]:
        lines.append(
            f"- Confidence intervals: {meta['bootstrap']['n_resamples']} cluster-bootstrap resamples "
            f"by text-source item (seed {meta['bootstrap']['seed']}); "
            "shown for test overall and per-test-split rows."
        )
    lines.append("")

    if meta.get("val"):
        val = meta["val"]
        val_negatives = val["negatives_by_type"]
        headers = ["Split", "n", "Accuracy", "AUC", "Pos recall", "Neg recall", "Balanced",
                   "N1 recall", "N2 recall", "N3 recall"]
        if include_r_at_1:
            headers.append("R@1")
        cells = [
            md_escape(meta["val_split"]),
            str(val["n"]),
            fmt_pct(val.get("accuracy")),
            fmt_num(val.get("auc")),
            fmt_pct(val.get("positive_recall")),
            fmt_pct(val.get("negative_recall")),
            fmt_pct(val.get("balanced_accuracy")),
            fmt_pct((val_negatives.get("N1") or {}).get("recall")),
            fmt_pct((val_negatives.get("N2") or {}).get("recall")),
            fmt_pct((val_negatives.get("N3") or {}).get("recall")),
        ]
        if include_r_at_1:
            cells.append(fmt_pct(val.get("r_at_1")))
        lines.append("## Validation")
        lines.append("")
        lines.extend(md_table(headers, [cells]))
        lines.append("")

    main = [r for r in records if r["dimension"] == "overall"]
    splits = [r for r in records if r["dimension"] == "split"]
    if len(splits) > 1:
        main.extend(splits)
    headers = ["Split", "n", "Accuracy", "AUC", "Pos recall", "Neg recall", "Balanced",
               "N1 recall", "N2 recall", "N3 recall"]
    if include_r_at_1:
        headers.append("R@1")
    table_rows = []
    for record in main:
        label = "All selected" if record["dimension"] == "overall" else record["value"]
        negatives = record["negatives_by_type"]
        cells = [
            md_escape(label),
            str(record["n"]),
            fmt_metric(record, "accuracy", fmt_pct),
            fmt_metric(record, "auc", fmt_num),
            fmt_metric(record, "positive_recall", fmt_pct),
            fmt_metric(record, "negative_recall", fmt_pct),
            fmt_metric(record, "balanced_accuracy", fmt_pct),
            fmt_pct((negatives.get("N1") or {}).get("recall")),
            fmt_pct((negatives.get("N2") or {}).get("recall")),
            fmt_pct((negatives.get("N3") or {}).get("recall")),
        ]
        if include_r_at_1:
            cells.append(fmt_metric(record, "r_at_1", fmt_pct))
        table_rows.append(cells)
    lines.append("## Main results")
    lines.append("")
    lines.extend(md_table(headers, table_rows))
    lines.append("")

    for dimension, title, first_header in (
        ("neg_type", "By negative type", "neg_type"),
        ("category", "By category", "Category"),
        ("year", "By year", "Year"),
    ):
        subset = [r for r in records if r["dimension"] == dimension]
        lines.append(f"## {title}")
        lines.append("")
        if not subset:
            lines.append("No non-empty values in the selected test split(s).")
            lines.append("")
            continue
        headers = [first_header, "n", "Accuracy", "AUC", "Pos recall", "Neg recall", "Balanced"]
        if include_r_at_1:
            headers.append("R@1")
        table_rows = []
        for record in subset:
            cells = [
                md_escape(record["value"]),
                str(record["n"]),
                fmt_pct(record.get("accuracy")),
                fmt_num(record.get("auc")),
                fmt_pct(record.get("positive_recall")),
                fmt_pct(record.get("negative_recall")),
                fmt_pct(record.get("balanced_accuracy")),
            ]
            if include_r_at_1:
                cells.append(fmt_pct(record.get("r_at_1")))
            table_rows.append(cells)
        lines.extend(md_table(headers, table_rows))
        lines.append("")

    lines.extend([
        "## Notes",
        "",
        "- Metrics are pair-level. Positive recall is TPR; negative recall is TNR.",
        "- AUC is undefined for single-class groups and is shown as —.",
    ])
    if include_r_at_1:
        lines.extend([
            "- R@1 is within-title 3-way ranking: the positive image must outrank the title's own",
            "  N1/N2 images. It is not global image retrieval; ties count as failures.",
        ])
    else:
        lines.append("- R@1 was not computed (pass `--r-at-1` to enable it).")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write("\n".join(lines))


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--pairs-csv", default="docs/mini_version/pairs.csv",
                        help="pairs table (default: %(default)s)")
    parser.add_argument("--scores-csv", required=True,
                        help="scores table: pair_id,score; higher means more likely a match")
    parser.add_argument("--out-csv", help="long-format metrics CSV (default: <scores>_eval.csv)")
    parser.add_argument("--out-md", help="Markdown report (default: <scores>_eval.md)")
    parser.add_argument("--out-json", help="provenance JSON (default: <scores>_eval.json)")
    parser.add_argument("--val-split", default="val",
                        help="split used to select the threshold (default: %(default)s)")
    parser.add_argument("--test-splits", nargs="+", default=["test"],
                        help="split(s) to evaluate (default: test)")
    parser.add_argument("--objective", choices=OBJECTIVES, default="accuracy",
                        help="threshold selection objective (default: %(default)s)")
    parser.add_argument("--fixed-threshold", type=float,
                        help="use a pre-registered threshold instead of selecting on val; "
                             "decide it before looking at test")
    parser.add_argument("--drop-cross-split-images", action="store_true",
                        help="drop pairs whose image_path occurs in multiple splits")
    parser.add_argument("--exclude-pair-list",
                        help="file of pair_ids to exclude, one per line (# comments allowed)")
    parser.add_argument("--r-at-1", action="store_true",
                        help="also compute within-title 3-way R@1")
    parser.add_argument("--bootstrap", type=int, default=0,
                        help="cluster-bootstrap resamples for 95 percent CI (default: %(default)s)")
    parser.add_argument("--seed", type=int, default=0,
                        help="bootstrap seed (default: %(default)s)")
    args = parser.parse_args(argv)

    if args.bootstrap < 0:
        parser.error("--bootstrap must be non-negative")
    if args.fixed_threshold is not None and not np.isfinite(args.fixed_threshold):
        parser.error("--fixed-threshold must be finite")
    test_splits = list(dict.fromkeys(args.test_splits))

    pairs = load_pairs(args.pairs_csv)
    scores = load_scores(args.scores_csv)
    pairs = merge_scores(pairs, scores)
    n_before = len(pairs)
    cross_split_images = find_cross_split_images(pairs)
    excluded_ids = read_id_list(args.exclude_pair_list) if args.exclude_pair_list else set()
    unknown_excluded = sorted(excluded_ids - {row["pair_id"] for row in pairs})
    if unknown_excluded:
        warn(f"--exclude-pair-list: {len(unknown_excluded)} ids not in pairs "
             f"(e.g. {unknown_excluded[:3]})")
    drop_paths = set(cross_split_images) if args.drop_cross_split_images else set()
    pairs, dropped, dropped_by_split = apply_exclusions(pairs, drop_paths, excluded_ids)
    if cross_split_images and not args.drop_cross_split_images:
        warn(f"{len(cross_split_images)} image paths occur in multiple splits; "
             "pass --drop-cross-split-images for leak-free test numbers")
    if args.exclude_pair_list and dropped.get("excluded_pair"):
        warn(f"excluded {dropped['excluded_pair']} pairs from --exclude-pair-list")

    val_rows = rows_for_split(pairs, args.val_split)
    if args.fixed_threshold is not None:
        threshold = float(args.fixed_threshold)
        selection_split = "fixed"
        tie_break = None
    else:
        if not val_rows:
            raise ValueError(f"no rows in validation split {args.val_split!r}")
        require_scores(val_rows, args.val_split)
        threshold, _ = select_threshold(val_rows, args.objective)
        selection_split = args.val_split
        tie_break = f"smallest threshold among maximum-{args.objective} candidates"

    test_by_split = {}
    for split in test_splits:
        rows = rows_for_split(pairs, split)
        if not rows:
            raise ValueError(f"no rows in test split {split!r}")
        if len({row["label"] for row in rows}) < 2:
            raise ValueError(f"test split {split!r} must contain both positives and negatives")
        require_scores(rows, split)
        test_by_split[split] = rows
    test_rows = [row for split in test_splits for row in test_by_split[split]]

    val_metrics = None
    if val_rows and all("score" in row for row in val_rows):
        val_metrics = compute_metrics(val_rows, threshold, args.r_at_1)
    test_metrics = compute_metrics(test_rows, threshold, args.r_at_1)
    test_split_metrics = {
        split: compute_metrics(rows, threshold, args.r_at_1)
        for split, rows in test_by_split.items()
    }
    records = build_records(test_rows, threshold, args.r_at_1)

    bootstrap = None
    if args.bootstrap > 0:
        overall_ci = bootstrap_ci(test_rows, threshold, args.bootstrap, args.seed, args.r_at_1)
        ci_by_key = {("overall", "all"): overall_ci}
        by_split = {}
        for split, rows in test_by_split.items():
            interval = bootstrap_ci(rows, threshold, args.bootstrap, args.seed, args.r_at_1)
            by_split[split] = interval
            ci_by_key[("split", split)] = interval
        attach_ci(records, ci_by_key)
        bootstrap = {
            "n_resamples": args.bootstrap,
            "cluster": "text_source_item",
            "seed": args.seed,
            "overall": overall_ci,
            "by_split": by_split,
        }

    notes = []
    if selection_split == "fixed":
        notes.append("Threshold was fixed before evaluation; the validation split was not used for selection.")
    if val_rows and val_metrics is None:
        notes.append("Validation metrics omitted: not all validation pairs have scores.")
    if selection_split != "fixed" and args.val_split in test_splits:
        warn(f"test split {args.val_split!r} is also the validation split; metrics are not held out")
        notes.append(f"Test split {args.val_split!r} is also the validation split; metrics are not held out.")
    if cross_split_images and not args.drop_cross_split_images:
        notes.append(
            f"{len(cross_split_images)} image paths occur in multiple splits; "
            "test numbers may be leaked. Re-run with --drop-cross-split-images."
        )
    if args.drop_cross_split_images and cross_split_images:
        notes.append(
            f"Dropped {dropped.get('cross_split_image', 0)} pairs using cross-split image paths."
        )
    if excluded_ids:
        notes.append(
            f"Excluded {dropped.get('excluded_pair', 0)} pairs listed in {args.exclude_pair_list}."
        )
    if not any(row["year"] for row in test_rows):
        notes.append("No non-empty year values in the selected test split(s); year grouping omitted.")

    scores_path = Path(args.scores_csv)
    stem = scores_path.stem
    out_csv = Path(args.out_csv) if args.out_csv else scores_path.parent / f"{stem}_eval.csv"
    out_md = Path(args.out_md) if args.out_md else scores_path.parent / f"{stem}_eval.md"
    out_json = Path(args.out_json) if args.out_json else scores_path.parent / f"{stem}_eval.json"

    result = {
        "tool": "src/eval/eval.py",
        "pairs_csv": args.pairs_csv,
        "scores_csv": args.scores_csv,
        "selection_split": selection_split,
        "objective": args.objective if selection_split != "fixed" else "fixed",
        "rule": "score >= threshold",
        "tie_break": tie_break,
        "threshold": threshold,
        "test_splits": test_splits,
        "input_sha256": {
            **{args.pairs_csv: sha256(args.pairs_csv), args.scores_csv: sha256(args.scores_csv)},
            **({args.exclude_pair_list: sha256(args.exclude_pair_list)} if args.exclude_pair_list else {}),
        },
        "n_pairs": {
            "before_exclusions": n_before,
            "after_exclusions": len(pairs),
            "n_scores": len(scores),
            "val": len(val_rows),
            "val_scored": sum("score" in row for row in val_rows),
            "test": len(test_rows),
            "test_scored": sum("score" in row for row in test_rows),
            "by_test_split": {split: len(rows) for split, rows in test_by_split.items()},
        },
        "exclusions": {
            "cross_split_image_paths": cross_split_images,
            "drop_cross_split_images": args.drop_cross_split_images,
            "dropped": dropped,
            "dropped_by_split": dropped_by_split,
            "exclude_pair_list": args.exclude_pair_list,
            "unknown_excluded_pair_ids": unknown_excluded,
        },
        "bootstrap": bootstrap,
        "val": val_metrics,
        "test": test_metrics,
        "test_by_split": test_split_metrics,
        "groups": records,
        "notes": notes,
    }

    write_csv(out_csv, records, threshold)
    write_markdown(out_md, {
        "pairs_csv": args.pairs_csv,
        "scores_csv": args.scores_csv,
        "selection_split": selection_split,
        "objective": args.objective if selection_split != "fixed" else "fixed",
        "rule": "score >= threshold",
        "threshold": threshold,
        "test_splits": test_splits,
        "val_split": args.val_split,
        "val": val_metrics,
        "n_val": len(val_rows),
        "n_test": len(test_rows),
        "dropped": dropped,
        "dropped_text": describe_dropped(dropped, dropped_by_split),
        "cross_split_images": cross_split_images,
        "drop_cross_split_images": args.drop_cross_split_images,
        "bootstrap": bootstrap,
        "include_r_at_1": args.r_at_1,
    }, records)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    with out_json.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False)
        stream.write("\n")

    print(f"selection={selection_split} objective={result['objective']} threshold={threshold!r}")
    if val_metrics:
        print(f"val: n={val_metrics['n']} acc={fmt_num(val_metrics['accuracy'], 6)} "
              f"auc={fmt_num(val_metrics['auc'], 6)}")
    print(f"test: n={test_metrics['n']} acc={fmt_num(test_metrics['accuracy'], 6)} "
          f"auc={fmt_num(test_metrics['auc'], 6)}")
    print(f"wrote {out_csv}")
    print(f"wrote {out_md}")
    print(f"wrote {out_json}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2) from None
