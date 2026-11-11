"""WP4 shortcut controls for ABO home v2: text-only and image-only.

v2 is a fixed-image layout: every image anchor has one positive and one
negative pair, and both pairs use the same image_path. An image-only model
therefore cannot distinguish them; its AUC is a structural 0.5 and serves as
a data-integrity check. The text-only model is the substantive shortcut check,
especially for N3 color substitutions.

Both controls train on the v2 train split only, score val/test, and (by
default) run the shared src/eval/eval.py evaluator on the exact v2 pairs.

Usage:
  python src/eval/controls.py
  python src/eval/controls.py --image-mode identity
  python src/eval/controls.py --limit-anchors 64 --no-eval
"""
import argparse
import hashlib
import json
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src" / "baselines"))
from common import pick_device, read_pairs, write_scores  # noqa: E402

V2_PAIRS = REPO / "data" / "releases" / "abo-home-v2-20261103" / "pairs.csv"
V2_IMAGES = REPO / "data" / "releases" / "abo-home-v2-20261103" / "images"
CLIP_MODEL_ID = "openai/clip-vit-base-patch32"
CLIP_REVISION = "3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268"
REQUIRED_V2_COLUMNS = (
    "label", "neg_type", "split", "anchor_item_id", "anchor_group_id", "text_item_id",
)


def display_path(path):
    try:
        return Path(path).resolve().relative_to(REPO).as_posix()
    except ValueError:
        return str(path)


def validate_rows(rows):
    for line, row in enumerate(rows, start=2):
        missing = [name for name in REQUIRED_V2_COLUMNS if row.get(name) in (None, "")]
        if missing:
            raise ValueError(f"row {line}: missing v2 columns {missing}")
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
        raise ValueError("not a fixed-image v2 layout: " + "; ".join(problems[:5]))
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


def fit_text(train_rows, seed):
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2), min_df=2, sublinear_tf=True, strip_accents="unicode",
    )
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


def load_or_compute_features(paths, image_root, cache_path, batch_size, device, recompute):
    if cache_path.exists() and not recompute:
        data = np.load(cache_path, allow_pickle=False)
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
    """Per-image constant score; any image-only model is equivalent on v2."""
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


def per_neg_type_auc(test_rows, scores):
    positives = [row for row in test_rows if row["label"] == 1]
    result = {}
    for neg_type in sorted({row["neg_type"] for row in test_rows if row["label"] == 0}):
        subset = positives + [row for row in test_rows if row["neg_type"] == neg_type]
        labels = [row["label"] for row in subset]
        values = [scores[row["pair_id"]] for row in subset]
        result[neg_type] = float(roc_auc_score(labels, values))
    return result


def run_evaluator(pairs_csv, scores_csv, bootstrap):
    stem = scores_csv.stem
    out_csv = scores_csv.with_name(f"{stem}_eval.csv")
    out_md = scores_csv.with_name(f"{stem}_eval.md")
    out_json = scores_csv.with_name(f"{stem}_eval.json")
    command = [
        sys.executable, str(REPO / "src" / "eval" / "eval.py"),
        "--pairs-csv", display_path(pairs_csv),
        "--scores-csv", display_path(scores_csv),
        "--bootstrap", str(bootstrap),
        "--out-csv", str(out_csv),
        "--out-md", str(out_md),
        "--out-json", str(out_json),
    ]
    subprocess.run(command, check=True, cwd=REPO)
    return json.loads(out_json.read_text(encoding="utf-8"))


def fmt_pct(value):
    return "—" if value is None else f"{100 * value:.2f}%"


def fmt_num(value):
    return "—" if value is None else f"{value:.4f}"


def summary_lines(results):
    headers = [
        "control", "test n", "Acc", "AUC", "Balanced",
        "N1 AUC", "N2 AUC", "N3 AUC", "N1 recall", "N2 recall", "N3 recall",
    ]
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    for result in results:
        report = result["report"]
        test = report["test"]
        negatives = test["negatives_by_type"]
        aucs = result["per_type_auc"]
        cells = [
            result["name"],
            str(test["n"]),
            fmt_pct(test["accuracy"]),
            fmt_num(test["auc"]),
            fmt_pct(test["balanced_accuracy"]),
            fmt_num(aucs.get("N1")),
            fmt_num(aucs.get("N2")),
            fmt_num(aucs.get("N3")),
            fmt_pct((negatives.get("N1") or {}).get("recall")),
            fmt_pct((negatives.get("N2") or {}).get("recall")),
            fmt_pct((negatives.get("N3") or {}).get("recall")),
        ]
        lines.append("| " + " | ".join(cells) + " |")
    return lines


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--pairs-csv", default=str(V2_PAIRS))
    parser.add_argument("--image-root", default=str(V2_IMAGES))
    parser.add_argument("--out-dir", default=str(REPO / "scores"))
    parser.add_argument(
        "--cache", default=str(REPO / "data" / "processed" / "control_v2_clip_image_features.npz"),
    )
    parser.add_argument("--image-mode", choices=("clip", "identity"), default="clip")
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

    rows = validate_rows(read_pairs(args.pairs_csv))
    check_fixed_image_layout(rows)
    if args.limit_anchors:
        rows = limit_anchors(rows, args.limit_anchors)
    n_anchors = check_fixed_image_layout(rows)
    splits = split_rows(rows)
    train_rows, val_rows, test_rows = splits["train"], splits["val"], splits["test"]
    scored_rows = val_rows + test_rows
    out_dir = Path(args.out_dir)
    pairs_display = display_path(args.pairs_csv)
    print(
        f"pairs={len(rows)} anchors={n_anchors} "
        f"train={len(train_rows)} val={len(val_rows)} test={len(test_rows)}",
        flush=True,
    )

    vectorizer, text_classifier = fit_text(train_rows, args.seed)
    text_scores = score_text(scored_rows, vectorizer, text_classifier)
    text_train = text_train_auc(train_rows, vectorizer, text_classifier)
    text_path = out_dir / "control_v2_text_tfidf.csv"
    write_scores(text_path, scored_rows, text_scores)
    print(f"wrote {text_path} (train AUC {text_train:.4f})", flush=True)

    if args.image_mode == "clip":
        image_paths = required_image_paths(rows)
        device = pick_device(args.device)
        features, feature_source = load_or_compute_features(
            image_paths, args.image_root, Path(args.cache), args.batch_size, device, args.recompute,
        )
        image_classifier = fit_image(train_rows, features, args.seed)
        image_scores = score_image(scored_rows, image_classifier, features)
        image_train = image_train_auc(train_rows, image_classifier, features)
        assert_constant_per_anchor(scored_rows, image_scores)
        image_path = out_dir / "control_v2_image_clip.csv"
        print(
            f"image features={len(image_paths)} device={device} source={feature_source} "
            f"train AUC {image_train:.4f} (expected ~0.5: fixed-image v2)",
            flush=True,
        )
    else:
        image_scores = identity_scores(scored_rows)
        assert_constant_per_anchor(scored_rows, image_scores)
        image_train = None
        image_path = out_dir / "control_v2_image_identity.csv"
        print("image mode=identity (per-image constant; expected AUC 0.5)", flush=True)
    write_scores(image_path, scored_rows, image_scores)
    print(f"wrote {image_path}", flush=True)

    results = [
        {"name": "text-only tf-idf", "scores": text_path, "scores_map": text_scores},
        {
            "name": "image-only " + ("CLIP" if args.image_mode == "clip" else "identity"),
            "scores": image_path,
            "scores_map": image_scores,
        },
    ]
    for result in results:
        result["per_type_auc"] = per_neg_type_auc(test_rows, result["scores_map"])

    reports = {}
    if not args.no_eval:
        for result in results:
            print(f"evaluating {result['scores'].name}", flush=True)
            result["report"] = run_evaluator(Path(args.pairs_csv), result["scores"], args.bootstrap)
            reports[result["name"]] = result["report"]
        lines = [
            "# Shortcut controls (ABO home v2)",
            "",
            f"- Pairs: `{pairs_display}`",
            f"- Splits: train {len(train_rows)}, val {len(val_rows)}, test {len(test_rows)}",
            f"- Text model: TF-IDF word 1-2gram, min_df=2 + logistic regression (seed {args.seed})",
            f"- Image model: {args.image_mode}"
            + (f" / {CLIP_MODEL_ID}@{CLIP_REVISION}" if args.image_mode == "clip" else ""),
            "",
        ] + summary_lines(results) + [
            "",
            "Image-only scores are constant per anchor because v2 positive and negative pairs share "
            "the same image; its AUC is a structural 0.5, not a learned shortcut.",
            "N1/N2/N3 AUC compares positives against that negative type only. "
            "Threshold-dependent recalls come from the shared evaluator's val-selected threshold.",
            "",
        ]
        summary_path = out_dir / "control_v2_summary.md"
        summary_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"wrote {summary_path}", flush=True)
        print("\n".join(summary_lines(results)), flush=True)

    cache_path = Path(args.cache)
    metadata = {
        "tool": "src/eval/controls.py",
        "pairs_csv": pairs_display,
        "dataset_versions": sorted({row.get("dataset_version", "") for row in rows if row.get("dataset_version")}),
        "splits": {name: len(subset) for name, subset in splits.items()},
        "anchors": n_anchors,
        "environment": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "sklearn": sklearn.__version__,
        },
        "text": {
            "features": "tfidf word 1-2gram min_df=2 sublinear_tf",
            "classifier": "logistic regression",
            "seed": args.seed,
            "train_rows": len(train_rows),
            "vocabulary": len(vectorizer.vocabulary_),
            "train_auc": text_train,
            "top_features": top_text_features(vectorizer, text_classifier),
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
            "cache_sha256": hashlib.sha256(cache_path.read_bytes()).hexdigest()
            if args.image_mode == "clip" and cache_path.exists() else None,
            "unique_scores": len({round(value, 12) for value in image_scores.values()}),
        },
        "score_files": {result["name"]: display_path(result["scores"]) for result in results},
        "score_sha256": {
            result["name"]: hashlib.sha256(Path(result["scores"]).read_bytes()).hexdigest()
            for result in results
        },
        "eval_report_files": {
            result["name"]: display_path(
                result["scores"].with_name(f"{result['scores'].stem}_eval.json")
            ) for result in results
        } if reports else None,
        "eval_reports": {name: report.get("test") for name, report in reports.items()},
    }
    if args.image_mode == "clip":
        import huggingface_hub
        import torch
        import transformers

        metadata["environment"]["torch"] = torch.__version__
        metadata["environment"]["transformers"] = transformers.__version__
        metadata["environment"]["huggingface_hub"] = huggingface_hub.__version__
    meta_path = out_dir / "control_v2_meta.json"
    meta_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {meta_path}", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2) from None
