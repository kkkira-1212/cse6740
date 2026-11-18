"""WP4 shortcut controls for fixed-image ABO home releases.

Both controls train on the release's train split only, select a threshold on
val, and evaluate test once. The text-only control uses TF-IDF + logistic
regression; the image-only control uses frozen CLIP image embeddings + logistic
regression. v2/v3 are fixed-image layouts: each anchor's positive and negative
share the same image_path, so the image-only AUC is a structural 0.5 and serves
as a data-integrity check.

For v3, per-type AUC uses matched-anchor positives: each negative is compared
with the positive of the same anchor_item_id, never with the donor text_item_id.
N3 intervals resample reciprocal exchanges (both directions together); N1/N2
intervals resample image-anchor groups. Test scoring requires a frozen protocol
file containing the pairs SHA-256.

Usage:
  python src/eval/controls.py --splits val
  python src/eval/controls.py --splits val test --protocol-file docs/controls_v3.md
  python src/eval/controls.py --image-mode identity --no-eval --limit-anchors 16
"""
import argparse
import csv
import hashlib
import json
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src" / "baselines"))
from common import pick_device, read_pairs, write_scores  # noqa: E402

_EVAL_DIR = str(Path(__file__).resolve().parent)
if _EVAL_DIR not in sys.path:
    sys.path.insert(0, _EVAL_DIR)
import matched_metrics  # noqa: E402

V2_PAIRS = REPO / "data" / "releases" / "abo-home-v2-20261103" / "pairs.csv"
V2_IMAGES = REPO / "data" / "releases" / "abo-home-v2-20261103" / "images"
V2_DATASET_VERSION = "abo-home-v2-20261103"
V3_PAIRS = REPO / "data" / "releases" / "abo-home-reciprocal-v3-candidate" / "pairs.csv"
V3_IMAGE_ROOT = V2_IMAGES  # v3 deliberately reuses the v2 image directory
V3_DATASET_VERSION = "abo-home-reciprocal-v3-candidate"
V3_PAIRS_SHA256 = "14814aa6bba905c07377a929c44e7d28b76893497c9c59eb86b8b6a9da334003"
CLIP_MODEL_ID = "openai/clip-vit-base-patch32"
CLIP_REVISION = "3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268"
REQUIRED_COLUMNS = (
    "label", "neg_type", "split", "anchor_item_id", "anchor_group_id", "text_item_id",
)
UNCERTAIN_LEDGER = (
    REPO / "data" / "reviews" / "reciprocal-v3-model-assisted" / "fallback_train_adjudications.csv"
)


def display_path(path):
    try:
        return Path(path).resolve().relative_to(REPO).as_posix()
    except ValueError:
        return str(path)


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def git_state():
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO, text=True, stderr=subprocess.DEVNULL,
        ).strip()
        dirty = bool(subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=REPO, text=True, stderr=subprocess.DEVNULL,
        ).strip())
        return {"commit": commit, "dirty": dirty}
    except (OSError, subprocess.SubprocessError):
        return {"commit": None, "dirty": None}


def validate_rows(rows):
    for line, row in enumerate(rows, start=2):
        missing = [name for name in REQUIRED_COLUMNS if row.get(name) in (None, "")]
        if missing:
            raise ValueError(f"row {line}: missing required columns {missing}")
        try:
            label = int(row["label"])
        except ValueError:
            raise ValueError(f"row {line}: label must be 0 or 1, got {row['label']!r}") from None
        if label not in (0, 1):
            raise ValueError(f"row {line}: label must be 0 or 1, got {label}")
        if (label == 1) != (row["neg_type"] == "pos"):
            raise ValueError(f"row {line}: label/neg_type contradiction")
        row["label"] = label
    return rows


def check_fixed_image_layout(rows):
    """Every anchor must have exactly one positive and one negative, same image."""
    by_anchor = defaultdict(list)
    for row in rows:
        by_anchor[row["anchor_item_id"]].append(row)
    problems = []
    for anchor, group in by_anchor.items():
        positives = [row for row in group if row["label"] == 1]
        negatives = [row for row in group if row["label"] == 0]
        if len(positives) != 1 or len(negatives) != 1:
            problems.append(f"{anchor}: {len(positives)} pos / {len(negatives)} neg")
        elif positives[0]["image_path"] != negatives[0]["image_path"]:
            problems.append(
                f"{anchor}: image mismatch {positives[0]['image_path']} vs {negatives[0]['image_path']}"
            )
    if problems:
        raise ValueError("not a fixed-image layout: " + "; ".join(problems[:5]))
    return len(by_anchor)


def split_rows(rows):
    splits = {
        name: [row for row in rows if row["split"] == name]
        for name in ("train", "val", "test")
    }
    for name, subset in splits.items():
        if not subset:
            raise ValueError(f"no rows in split {name!r}")
        if {row["label"] for row in subset} != {0, 1}:
            raise ValueError(f"split {name!r} must contain both labels")
    return splits


def limit_anchors(rows, per_split):
    kept = []
    for name in ("train", "val", "test"):
        subset = [row for row in rows if row["split"] == name]
        anchors = list(dict.fromkeys(row["anchor_item_id"] for row in subset))[:per_split]
        wanted = set(anchors)
        kept.extend(row for row in subset if row["anchor_item_id"] in wanted)
    return kept


def fit_text(train_rows, seed, analyzer="word"):
    if analyzer == "word":
        vectorizer = TfidfVectorizer(
            ngram_range=(1, 2), min_df=2, sublinear_tf=True, strip_accents="unicode",
        )
    elif analyzer == "char":
        vectorizer = TfidfVectorizer(
            analyzer="char", ngram_range=(3, 5), min_df=2, sublinear_tf=True,
            strip_accents="unicode",
        )
    else:
        raise ValueError(f"unknown text analyzer {analyzer!r}")
    matrix = vectorizer.fit_transform([row["text"] for row in train_rows])
    classifier = LogisticRegression(max_iter=1000, random_state=seed)
    classifier.fit(matrix, [row["label"] for row in train_rows])
    return vectorizer, classifier


def score_text(rows, vectorizer, classifier):
    matrix = vectorizer.transform([row["text"] for row in rows])
    probabilities = classifier.predict_proba(matrix)[:, 1]
    return {row["pair_id"]: float(value) for row, value in zip(rows, probabilities)}


def text_train_auc(train_rows, vectorizer, classifier):
    matrix = vectorizer.transform([row["text"] for row in train_rows])
    probabilities = classifier.predict_proba(matrix)[:, 1]
    return float(roc_auc_score([row["label"] for row in train_rows], probabilities))


def top_text_features(vectorizer, classifier, n=15):
    names = vectorizer.get_feature_names_out()
    coefficients = classifier.coef_[0]
    order = np.argsort(coefficients)
    return {
        "negative": [[str(names[index]), float(coefficients[index])] for index in order[:n]],
        "positive": [[str(names[index]), float(coefficients[index])]
                     for index in order[-n:][::-1]],
    }


def required_image_paths(rows):
    return sorted({row["image_path"] for row in rows})


def _as_tensor(output):
    import torch

    if isinstance(output, torch.Tensor):
        return output
    for name in ("pooler_output", "image_embeds"):
        value = getattr(output, name, None)
        if value is not None:
            return value
    raise TypeError(f"cannot find an image embedding in {type(output).__name__}")


def compute_clip_features(paths, image_root, batch_size, device):
    import torch
    from PIL import Image
    try:
        from transformers import CLIPModel, CLIPProcessor
    except ImportError as error:
        raise RuntimeError(
            "CLIP image features need a compatible transformers/huggingface-hub install; "
            "see the environment note in docs/controls.md"
        ) from error

    processor = CLIPProcessor.from_pretrained(CLIP_MODEL_ID, revision=CLIP_REVISION)
    model = CLIPModel.from_pretrained(CLIP_MODEL_ID, revision=CLIP_REVISION).to(device).eval()
    features = {}
    for start in range(0, len(paths), batch_size):
        batch = paths[start:start + batch_size]
        images = []
        for relative in batch:
            path = Path(image_root) / relative
            if not path.is_file():
                raise FileNotFoundError(
                    f"{path} is missing; run "
                    "data/releases/abo-home-v2-20261103/tools/download_images.py"
                )
            with Image.open(path) as image:
                images.append(image.convert("RGB"))
        inputs = processor(images=images, return_tensors="pt").to(device)
        with torch.inference_mode():
            vectors = _as_tensor(model.get_image_features(**inputs))
            vectors = torch.nn.functional.normalize(vectors.float(), dim=-1)
        for relative, vector in zip(batch, vectors.cpu().numpy()):
            features[relative] = vector.astype(np.float32)
        if start % (batch_size * 10) == 0:
            print(f"images {min(start + batch_size, len(paths))}/{len(paths)}", flush=True)
    return features


def load_or_compute_features(
    paths, image_root, cache_path, batch_size, device, recompute,
    dataset_version, pairs_sha256,
):
    if cache_path.exists():
        data = np.load(cache_path, allow_pickle=False)
        cache_version = str(data["dataset_version"]) if "dataset_version" in data else None
        cache_pairs = str(data["pairs_sha256"]) if "pairs_sha256" in data else None
        if cache_version != dataset_version or cache_pairs != pairs_sha256:
            raise ValueError(
                f"image cache {cache_path} is bound to {cache_version!r}/{cache_pairs!r}, "
                f"not {dataset_version!r}/{pairs_sha256!r}; choose a new --cache path"
            )
        if not recompute:
            cache_paths = [str(path) for path in data["paths"]]
            if set(paths).issubset(cache_paths):
                lookup = {path: index for index, path in enumerate(cache_paths)}
                features = {
                    path: data["features"][lookup[path]].astype(np.float32) for path in paths
                }
                print(f"loaded {len(features)} image features from {cache_path}")
                return features, "cache"
            print("image cache does not cover all required paths; recomputing")
    start = time.monotonic()
    features = compute_clip_features(paths, image_root, batch_size, device)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        cache_path,
        paths=np.array(paths),
        features=np.stack([features[path] for path in paths]).astype(np.float32),
        dataset_version=np.array(dataset_version),
        pairs_sha256=np.array(pairs_sha256),
    )
    print(f"computed {len(features)} image features in {time.monotonic() - start:.1f}s")
    return features, "computed"


def fit_image(train_rows, features, seed):
    matrix = np.stack([features[row["image_path"]] for row in train_rows])
    classifier = LogisticRegression(max_iter=1000, random_state=seed)
    classifier.fit(matrix, [row["label"] for row in train_rows])
    return classifier


def score_image(rows, classifier, features):
    matrix = np.stack([features[row["image_path"]] for row in rows])
    probabilities = classifier.predict_proba(matrix)[:, 1]
    return {row["pair_id"]: float(value) for row, value in zip(rows, probabilities)}


def image_train_auc(train_rows, classifier, features):
    matrix = np.stack([features[row["image_path"]] for row in train_rows])
    probabilities = classifier.predict_proba(matrix)[:, 1]
    return float(roc_auc_score([row["label"] for row in train_rows], probabilities))


def identity_scores(rows):
    """Per-image constant score; any image-only model is equivalent on fixed-image data."""
    def hash_score(image_path):
        digest = hashlib.sha256(image_path.encode("utf-8")).digest()
        return int.from_bytes(digest[:8], "big") / 2 ** 64

    return {row["pair_id"]: hash_score(row["image_path"]) for row in rows}


def assert_constant_per_anchor(rows, scores):
    by_anchor = defaultdict(list)
    for row in rows:
        by_anchor[row["anchor_item_id"]].append(row)
    for anchor, group in by_anchor.items():
        values = {round(scores[row["pair_id"]], 12) for row in group}
        if len(values) != 1:
            raise ValueError(f"image-only scores differ within anchor {anchor}: {sorted(values)}")


def load_exchange_map(pairs_csv):
    path = Path(pairs_csv).with_name("n3_provenance.csv")
    if not path.is_file():
        return {}
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return {row["pair_id"]: row["exchange_id"] for row in csv.DictReader(stream)}


def matched_negatives(test_rows, neg_type, exchange_map):
    """Pair negatives with their own anchor positives.

    Kept as a thin compatibility wrapper; the implementation lives in
    ``matched_metrics`` and is shared with the full evaluator.
    """
    units = matched_metrics.matched_units(test_rows, neg_type, exchange_map)
    if not units:
        return [], "none"
    cluster = units[0].cluster
    return [
        (unit.cluster_key, unit.positive, unit.negative, unit.cluster)
        for unit in units
    ], cluster


def matched_auc(test_rows, scores, neg_type, exchange_map, n_resamples, seed):
    scored_rows = [dict(row, score=scores[row["pair_id"]]) for row in test_rows]
    units = matched_metrics.matched_units(scored_rows, neg_type, exchange_map)
    if not units:
        return None
    metrics = matched_metrics.matched_metrics(units, threshold=None)
    intervals = matched_metrics.matched_bootstrap(
        units, threshold=None, n_resamples=n_resamples, seed=seed
    )
    auc_interval = (intervals or {}).get("auc") or {}
    return {
        "auc": metrics["auc"],
        "ci_low": auc_interval.get("low"),
        "ci_high": auc_interval.get("high"),
        "n_pos": metrics["n_pos"],
        "n_neg": metrics["n_neg"],
        "n_clusters": metrics["n_clusters"],
        "cluster": metrics["cluster"],
        "n_resamples": auc_interval.get("valid_resamples", 0),
    }


def load_uncertain_cases(rows):
    if not UNCERTAIN_LEDGER.is_file():
        return []
    by_pair = {row["pair_id"]: row for row in rows}
    with UNCERTAIN_LEDGER.open(newline="", encoding="utf-8-sig") as stream:
        ledger = list(csv.DictReader(stream))
    cases = []
    for row in ledger:
        if row.get("proposed_decision") != "uncertain":
            continue
        pair_id = row["pair_id"]
        pair = by_pair.get(pair_id)
        cases.append({
            "pair_id": pair_id,
            "split": row.get("split"),
            "neg_type": pair_id.rsplit("_", 1)[-1],
            "previous_decision": row.get("previous_decision"),
            "proposed_decision": row.get("proposed_decision"),
            "disposition": row.get("disposition"),
            "reason": row.get("reason"),
            "label_status": pair.get("label_status") if pair else None,
            "included_in_training": bool(pair and pair["split"] == "train"),
            "applied_to_training_labels": row.get("applied_to_training_labels"),
            "source": display_path(UNCERTAIN_LEDGER),
        })
    return cases


def n3_metadata(rows, pairs_csv):
    n3_rows = [row for row in rows if row["neg_type"] == "N3"]
    counts = Counter(row["split"] for row in n3_rows)
    status = Counter(row.get("label_status", "") for row in n3_rows)
    exchange_map = load_exchange_map(pairs_csv)
    split_by_pair = {row["pair_id"]: row["split"] for row in rows}
    exchanges = defaultdict(set)
    for row in n3_rows:
        exchange = exchange_map.get(row["pair_id"])
        if exchange:
            exchanges[split_by_pair[row["pair_id"]]].add(exchange)
    return {
        "counts_by_split": dict(sorted(counts.items())),
        "retained_val_test": counts.get("val", 0) + counts.get("test", 0),
        "exchanges_by_split": {
            split: len(ids) for split, ids in sorted(exchanges.items())
        },
        "total_exchanges": len(set().union(*exchanges.values())) if exchanges else 0,
        "label_status": dict(sorted(status.items())),
    }


def label_status_counts(rows):
    return {
        "overall": dict(sorted(Counter(row.get("label_status", "") for row in rows).items())),
        "by_neg_type": {
            neg_type: dict(sorted(Counter(
                row.get("label_status", "") for row in rows if row["neg_type"] == neg_type
            ).items()))
            for neg_type in sorted({row["neg_type"] for row in rows})
        },
    }


def load_shared_eval():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "shared_eval", REPO / "src" / "eval" / "eval.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_evaluator(pairs_csv, scores_csv, bootstrap, seed, pairs_sha256):
    stem = scores_csv.stem
    out_csv = scores_csv.with_name(f"{stem}_eval.csv")
    out_md = scores_csv.with_name(f"{stem}_eval.md")
    out_json = scores_csv.with_name(f"{stem}_eval.json")
    command = [
        sys.executable, str(REPO / "src" / "eval" / "eval.py"),
        "--pairs-csv", display_path(pairs_csv),
        "--scores-csv", display_path(scores_csv),
        "--val-split", "val",
        "--test-splits", "test",
        "--objective", "accuracy",
        "--bootstrap", str(bootstrap),
        "--seed", str(seed),
        "--out-csv", str(out_csv),
        "--out-md", str(out_md),
        "--out-json", str(out_json),
    ]
    subprocess.run(command, check=True, cwd=REPO)
    report = json.loads(out_json.read_text(encoding="utf-8"))
    pairs_display = display_path(pairs_csv)
    scores_display = display_path(scores_csv)
    if report.get("selection_split") != "val":
        raise ValueError("evaluator did not select the threshold on val")
    if report.get("objective") != "accuracy":
        raise ValueError("evaluator did not use the accuracy objective")
    if report.get("test_splits") != ["test"]:
        raise ValueError("evaluator did not evaluate exactly the test split")
    if report.get("pair_layout") != "fixed_image_v2":
        raise ValueError("evaluator did not detect the fixed-image layout")
    if report.get("input_sha256", {}).get(pairs_display) != pairs_sha256:
        raise ValueError("evaluator input pairs hash does not match this run")
    if report.get("input_sha256", {}).get(scores_display) != sha256_file(scores_csv):
        raise ValueError("evaluator input scores hash does not match this run")
    if bootstrap > 0 and report.get("bootstrap", {}).get("cluster") != "image_anchor_group":
        raise ValueError("evaluator did not use image-anchor bootstrap clusters")
    return report


def val_metrics_for_result(rows, scores_map, shared_eval):
    scored = [dict(row, score=scores_map[row["pair_id"]]) for row in rows]
    threshold, _ = shared_eval.select_threshold(scored, "accuracy")
    return {
        "threshold": float(threshold),
        "metrics": shared_eval.compute_metrics(scored, threshold, False),
    }


def fmt_pct(value):
    return "—" if value is None else f"{100 * value:.2f}%"


def fmt_num(value, digits=4):
    return "—" if value is None else f"{value:.{digits}f}"


def fmt_auc_detail(detail):
    if detail is None:
        return "—"
    if detail["ci_low"] is None:
        interval = ""
    else:
        interval = f" [{detail['ci_low']:.4f}, {detail['ci_high']:.4f}]"
    return (
        f"{detail['auc']:.4f}{interval} "
        f"({detail['n_pos']}/{detail['n_neg']}, {detail['n_clusters']} {detail['cluster']})"
    )


def summary_lines(results, uncertain_cases):
    headers = [
        "control", "test n", "Acc", "AUC", "Balanced",
        "N1 AUC", "N2 AUC", "N3 AUC", "N1 recall", "N2 recall", "N3 recall",
    ]
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    for result in results:
        report = result["report"]
        test = report["test"]
        negatives = test["negatives_by_type"]
        per_type = result["per_type"]
        cells = [
            result["name"],
            str(test["n"]),
            fmt_pct(test["accuracy"]),
            fmt_num(test["auc"]),
            fmt_pct(test["balanced_accuracy"]),
            fmt_num((per_type.get("N1") or {}).get("auc")),
            fmt_num((per_type.get("N2") or {}).get("auc")),
            fmt_num((per_type.get("N3") or {}).get("auc")),
            fmt_pct((negatives.get("N1") or {}).get("recall")),
            fmt_pct((negatives.get("N2") or {}).get("recall")),
            fmt_pct((negatives.get("N3") or {}).get("recall")),
        ]
        lines.append("| " + " | ".join(cells) + " |")

    lines.extend([
        "",
        "Matched-anchor detail (each negative compared with its own anchor's positive):",
        "",
        "| control | N1 | N2 | N3 |",
        "|---|---|---|---|",
    ])
    for result in results:
        per_type = result["per_type"]
        lines.append(
            "| " + " | ".join([
                result["name"],
                fmt_auc_detail(per_type.get("N1")),
                fmt_auc_detail(per_type.get("N2")),
                fmt_auc_detail(per_type.get("N3")),
            ]) + " |"
        )

    if uncertain_cases:
        ids = ", ".join(f"`{case['pair_id']}`" for case in uncertain_cases)
        lines.extend([
            "",
            f"Four remaining uncertainty flags are train fallback N1/N2, not N3: {ids}. "
            "They are generated/unreviewed and are included in training.",
        ])
    else:
        lines.extend(["", "No uncertainty ledger was found for this release."])
    return lines


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--pairs-csv", default=str(V3_PAIRS))
    parser.add_argument("--image-root", default=str(V3_IMAGE_ROOT))
    parser.add_argument("--expected-dataset-version", default=V3_DATASET_VERSION)
    parser.add_argument("--out-dir", default=str(REPO / "scores"))
    parser.add_argument("--output-prefix", default="control_v3")
    parser.add_argument("--cache", help="default: data/processed/<prefix>_clip_image_features.npz")
    parser.add_argument("--image-mode", choices=("clip", "identity"), default="clip")
    parser.add_argument("--text-features", choices=("word", "char", "both"), default="both")
    parser.add_argument("--splits", nargs="+", choices=("val", "test"), default=["val", "test"])
    parser.add_argument("--protocol-file", help="required before test; must contain the pairs SHA-256")
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--device", choices=("auto", "cuda", "mps", "cpu"), default="auto")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--bootstrap", type=int, default=1000)
    parser.add_argument("--limit-anchors", type=int, help="smoke run: keep N anchors per split")
    parser.add_argument("--recompute", action="store_true")
    parser.add_argument("--no-eval", action="store_true")
    args = parser.parse_args(argv)
    if args.batch_size < 1 or args.bootstrap < 0:
        parser.error("--batch-size must be positive and --bootstrap non-negative")
    if args.limit_anchors is not None and args.limit_anchors < 1:
        parser.error("--limit-anchors must be positive")
    splits_requested = list(dict.fromkeys(args.splits))
    if "val" not in splits_requested:
        parser.error("--splits must include val for threshold selection")
    pairs_sha256 = sha256_file(args.pairs_csv)
    if "test" in splits_requested:
        if not args.protocol_file:
            parser.error("--protocol-file is required before scoring test")
        protocol_path = Path(args.protocol_file)
        if not protocol_path.is_file():
            parser.error(f"protocol file not found: {protocol_path}")
        if pairs_sha256 not in protocol_path.read_text(encoding="utf-8"):
            parser.error("protocol file does not contain this pairs SHA-256")

    rows = validate_rows(read_pairs(args.pairs_csv))
    check_fixed_image_layout(rows)
    if args.limit_anchors:
        rows = limit_anchors(rows, args.limit_anchors)
    n_anchors = check_fixed_image_layout(rows)
    splits = split_rows(rows)
    train_rows, val_rows, test_rows = splits["train"], splits["val"], splits["test"]
    versions = sorted({row.get("dataset_version", "") for row in rows if row.get("dataset_version")})
    if versions != [args.expected_dataset_version]:
        raise ValueError(
            f"dataset versions {versions} do not match --expected-dataset-version "
            f"{args.expected_dataset_version!r}"
        )
    dataset_version = versions[0]
    if dataset_version == V3_DATASET_VERSION and pairs_sha256 != V3_PAIRS_SHA256:
        raise ValueError(
            f"pairs SHA-256 {pairs_sha256} does not match the pinned v3 candidate "
            f"{V3_PAIRS_SHA256}"
        )
    if args.output_prefix.startswith("control_v2") and dataset_version != V2_DATASET_VERSION:
        parser.error("--output-prefix control_v2* cannot be used with non-v2 data")
    if args.output_prefix.startswith("control_v3") and dataset_version != V3_DATASET_VERSION:
        parser.error("--output-prefix control_v3* cannot be used with non-v3 data")

    scored_rows = val_rows + (test_rows if "test" in splits_requested else [])
    out_dir = Path(args.out_dir)
    pairs_display = display_path(args.pairs_csv)
    cache_path = (
        Path(args.cache) if args.cache
        else REPO / "data" / "processed" / f"{args.output_prefix}_clip_image_features.npz"
    )
    print(
        f"dataset={dataset_version} pairs={len(rows)} anchors={n_anchors} "
        f"train={len(train_rows)} val={len(val_rows)} test={len(test_rows)} "
        f"splits={splits_requested}",
        flush=True,
    )

    text_analyzers = ["word", "char"] if args.text_features == "both" else [args.text_features]
    text_results = []
    for analyzer in text_analyzers:
        vectorizer, classifier = fit_text(train_rows, args.seed, analyzer)
        scores = score_text(scored_rows, vectorizer, classifier)
        train_auc = text_train_auc(train_rows, vectorizer, classifier)
        path = out_dir / f"{args.output_prefix}_text_{analyzer}.csv"
        write_scores(path, scored_rows, scores)
        print(f"wrote {path} (train AUC {train_auc:.4f})", flush=True)
        text_results.append({
            "name": f"text-only {analyzer}",
            "scores": path,
            "scores_map": scores,
            "analyzer": analyzer,
            "vectorizer": vectorizer,
            "classifier": classifier,
            "train_auc": train_auc,
        })

    if args.image_mode == "clip":
        image_paths = required_image_paths(rows)
        device = pick_device(args.device)
        features, feature_source = load_or_compute_features(
            image_paths, args.image_root, cache_path, args.batch_size, device,
            args.recompute, dataset_version, pairs_sha256,
        )
        image_classifier = fit_image(train_rows, features, args.seed)
        image_scores = score_image(scored_rows, image_classifier, features)
        image_train = image_train_auc(train_rows, image_classifier, features)
        assert_constant_per_anchor(scored_rows, image_scores)
        image_path = out_dir / f"{args.output_prefix}_image_clip.csv"
        print(
            f"image features={len(image_paths)} device={device} source={feature_source} "
            f"train AUC {image_train:.4f} (expected ~0.5: fixed-image layout)",
            flush=True,
        )
    else:
        image_scores = identity_scores(scored_rows)
        assert_constant_per_anchor(scored_rows, image_scores)
        image_train = None
        image_path = out_dir / f"{args.output_prefix}_image_identity.csv"
        print("image mode=identity (per-image constant; expected AUC 0.5)", flush=True)
    write_scores(image_path, scored_rows, image_scores)
    print(f"wrote {image_path}", flush=True)

    results = text_results + [{
        "name": "image-only " + ("CLIP" if args.image_mode == "clip" else "identity"),
        "scores": image_path,
        "scores_map": image_scores,
        "train_auc": image_train,
    }]
    exchange_map = load_exchange_map(args.pairs_csv)
    uncertain_cases = load_uncertain_cases(rows) if dataset_version == V3_DATASET_VERSION else []
    if "test" in splits_requested:
        for result in results:
            result["per_type"] = {
                neg_type: matched_auc(
                    test_rows, result["scores_map"], neg_type, exchange_map,
                    args.bootstrap, args.seed,
                )
                for neg_type in ("N1", "N2", "N3")
            }

    reports = {}
    val_report = None
    if "test" in splits_requested:
        if not args.no_eval:
            for result in results:
                print(f"evaluating {result['scores'].name}", flush=True)
                result["report"] = run_evaluator(
                    Path(args.pairs_csv), result["scores"], args.bootstrap, args.seed, pairs_sha256,
                )
                reports[result["name"]] = result["report"]
            lines = [
                f"# Shortcut controls ({dataset_version})",
                "",
                f"- Pairs: `{pairs_display}`",
                f"- Dataset version: `{dataset_version}`",
                f"- Pairs SHA-256: `{pairs_sha256}`",
                f"- Splits: train {len(train_rows)}, val {len(val_rows)}, test {len(test_rows)}",
                f"- Protocol: train fit; val accuracy threshold; rule `score >= threshold`; test once",
                f"- Text models: {', '.join(text_analyzers)} TF-IDF + logistic regression (seed {args.seed})",
                f"- Image model: {args.image_mode}"
                + (f" / {CLIP_MODEL_ID}@{CLIP_REVISION}" if args.image_mode == "clip" else ""),
                "",
            ] + summary_lines(results, uncertain_cases) + [
                "",
                "Image-only scores are constant per anchor because this fixed-image release's "
                "positive and negative pairs share the same image; its AUC is a structural 0.5.",
                "N1/N2/N3 AUC uses matched-anchor positives. N3 intervals resample reciprocal "
                "exchanges; N1/N2 intervals resample image-anchor groups. Overall eval.py "
                "intervals use image-anchor groups and do not capture exchange dependence.",
                "Overall metrics are not directly comparable across releases with different "
                "negative type mixes.",
                "",
            ]
            summary_path = out_dir / f"{args.output_prefix}_summary.md"
            summary_path.write_text("\n".join(lines), encoding="utf-8")
            print(f"wrote {summary_path}", flush=True)
            print("\n".join(summary_lines(results, uncertain_cases)), flush=True)
    else:
        if not args.no_eval:
            shared_eval = load_shared_eval()
            val_report = {
                "tool": "src/eval/controls.py",
                "pairs_csv": pairs_display,
                "pairs_sha256": pairs_sha256,
                "dataset_version": dataset_version,
                "protocol": {
                    "fit_split": "train",
                    "selection_split": "val",
                    "objective": "accuracy",
                    "rule": "score >= threshold",
                    "tie_break": "smallest threshold among maximum-accuracy candidates",
                    "test_evaluated": False,
                    "per_type_auc": "matched_anchor_positives",
                },
                "controls": {},
            }
            for result in results:
                val_result = val_metrics_for_result(val_rows, result["scores_map"], shared_eval)
                val_report["controls"][result["name"]] = val_result
                print(
                    f"{result['name']}: val threshold={val_result['threshold']!r} "
                    f"acc={fmt_num(val_result['metrics']['accuracy'], 6)} "
                    f"auc={fmt_num(val_result['metrics']['auc'], 6)}",
                    flush=True,
                )
            val_path = out_dir / f"{args.output_prefix}_val.json"
            val_path.write_text(
                json.dumps(val_report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8",
            )
            print(f"wrote {val_path}", flush=True)

    manifest_path = Path(args.pairs_csv).with_name("manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {}
    expected_pairs = manifest.get("output_sha256", {}).get("pairs.csv")
    if expected_pairs and expected_pairs != pairs_sha256:
        raise ValueError("pairs SHA-256 does not match the release manifest")
    n3_info = n3_metadata(rows, args.pairs_csv)
    n3_info["rejected_heldout_exchanges"] = manifest.get("rejected_heldout_exchanges")
    metadata = {
        "tool": "src/eval/controls.py",
        "pairs_csv": pairs_display,
        "pairs_sha256": pairs_sha256,
        "manifest_sha256": sha256_file(manifest_path) if manifest_path.is_file() else None,
        "dataset_version": dataset_version,
        "dataset_status": manifest.get("status"),
        "git": git_state(),
        "splits": {name: len(subset) for name, subset in splits.items()},
        "anchors": n_anchors,
        "protocol": {
            "fit_split": "train",
            "selection_split": "val",
            "objective": "accuracy",
            "rule": "score >= threshold",
            "tie_break": "smallest threshold among maximum-accuracy candidates",
            "test_split": "test" if "test" in splits_requested else None,
            "test_evaluated": "test" in splits_requested and not args.no_eval,
            "per_type_auc": "matched_anchor_positives",
            "per_type_ci": "N3 reciprocal_exchange; N1/N2 image_anchor_group",
            "bootstrap_resamples": args.bootstrap,
            "seed": args.seed,
            "protocol_file": display_path(args.protocol_file) if args.protocol_file else None,
        },
        "environment": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "sklearn": sklearn.__version__,
        },
        "text": {
            result["analyzer"]: {
                "features": (
                    "tfidf word 1-2gram min_df=2 sublinear_tf"
                    if result["analyzer"] == "word"
                    else "tfidf char 3-5gram min_df=2 sublinear_tf"
                ),
                "classifier": "logistic regression",
                "seed": args.seed,
                "train_rows": len(train_rows),
                "vocabulary": len(result["vectorizer"].vocabulary_),
                "train_auc": result["train_auc"],
                "top_features": top_text_features(result["vectorizer"], result["classifier"]),
            }
            for result in text_results
        },
        "image": {
            "mode": args.image_mode,
            "model": CLIP_MODEL_ID if args.image_mode == "clip" else None,
            "revision": CLIP_REVISION if args.image_mode == "clip" else None,
            "seed": args.seed,
            "train_rows": len(train_rows),
            "train_auc": image_train,
            "images": len(required_image_paths(rows)) if args.image_mode == "clip" else None,
            "image_root": display_path(args.image_root) if args.image_mode == "clip" else None,
            "cache": display_path(cache_path) if args.image_mode == "clip" else None,
            "cache_sha256": sha256_file(cache_path)
            if args.image_mode == "clip" and cache_path.exists() else None,
            "unique_scores": len({round(value, 12) for value in image_scores.values()}),
        },
        "n3": n3_info,
        "uncertain_cases": uncertain_cases,
        "label_status": label_status_counts(rows),
        "score_files": {result["name"]: display_path(result["scores"]) for result in results},
        "score_sha256": {
            result["name"]: sha256_file(result["scores"]) for result in results
        },
        "val_report": display_path(out_dir / f"{args.output_prefix}_val.json")
        if (out_dir / f"{args.output_prefix}_val.json").exists() else None,
        "eval_report_files": {
            result["name"]: display_path(
                result["scores"].with_name(f"{result['scores'].stem}_eval.json")
            ) for result in results
        } if reports else None,
        "thresholds": {
            name: report.get("threshold") for name, report in reports.items()
        } if reports else {
            name: value["threshold"] for name, value in (val_report or {}).get("controls", {}).items()
        },
        "per_type_auc": {
            result["name"]: result.get("per_type") for result in results
        } if "test" in splits_requested else None,
        "eval_reports": {name: report.get("test") for name, report in reports.items()},
    }
    if args.image_mode == "clip":
        import huggingface_hub
        import torch
        import transformers

        metadata["environment"]["torch"] = torch.__version__
        metadata["environment"]["transformers"] = transformers.__version__
        metadata["environment"]["huggingface_hub"] = huggingface_hub.__version__
    meta_path = out_dir / f"{args.output_prefix}_meta.json"
    meta_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {meta_path}", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2) from None
