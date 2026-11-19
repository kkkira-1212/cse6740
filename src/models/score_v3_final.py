"""Score frozen V3 CLIP selections on ID val/test or adopted ABO OOD."""
import argparse
import csv
import hashlib
import json
import math
import time
from pathlib import Path

import torch
from peft import PeftModel
from transformers import CLIPModel, CLIPProcessor

from train_clip_lora import score_rows

ROOT = Path(__file__).resolve().parents[2]
OOD = ROOT / "data/releases/abo-ood-v3-20261115-candidate"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_pairs(path, splits):
    with path.open(newline="") as stream:
        rows = [row for row in csv.DictReader(stream) if row["split"] in splits]
    ids = [row["pair_id"] for row in rows]
    if not rows or len(ids) != len(set(ids)) or any(not row["text"] for row in rows):
        raise ValueError("invalid pair coverage")
    return rows


def verify(manifest, dataset):
    pairs = ROOT / manifest["pairs_csv"] if dataset != "ood" else OOD / "eval_pairs.csv"
    expected = manifest["pairs_sha256"] if dataset != "ood" else json.loads((OOD / "evaluation_freeze.json").read_text())["sha256"]["eval_pairs.csv"]
    if digest(pairs) != expected:
        raise ValueError("pair table hash differs from freeze")
    for entry in manifest["models"]:
        for path_key, hash_key in (("score_path", "score_sha256"), ("config_path", "config_sha256"),
                                   ("metadata_path", "metadata_sha256"), ("checkpoint_path", "checkpoint_sha256")):
            if entry.get(path_key) and digest(ROOT / entry[path_key]) != entry[hash_key]:
                raise ValueError(f"{entry['name']}: {path_key} hash mismatch")
        if entry.get("metadata_path"):
            metadata = json.loads((ROOT / entry["metadata_path"]).read_text())
            config = json.loads((ROOT / entry["config_path"]).read_text())
            if metadata["config"] != config or metadata["pairs_sha256"] != manifest["pairs_sha256"] or metadata.get("test_evaluated"):
                raise ValueError(f"{entry['name']}: training metadata mismatch")
    return pairs


def score_one(entry, rows, image_root, device, dataset, pairs, output_dir, tolerance):
    config = json.loads((ROOT / entry["config_path"]).read_text()) if entry.get("config_path") else entry
    model_id, revision = config["model_id"], config["model_revision"]
    processor = CLIPProcessor.from_pretrained(model_id, revision=revision)
    if entry["family"] == "zero_shot":
        model = CLIPModel.from_pretrained(model_id, revision=revision)
    elif entry["family"] == "lora":
        base = CLIPModel.from_pretrained(model_id, revision=revision)
        model = PeftModel.from_pretrained(base, (ROOT / entry["checkpoint_path"]).parent)
    else:
        model = CLIPModel.from_pretrained((ROOT / entry["checkpoint_path"]).parent)
    model.to(device).eval()
    started = time.monotonic()
    scores = score_rows(model, processor, rows, image_root, device, 32)
    if len(scores) != len(rows) or not all(math.isfinite(value) for value in scores):
        raise ValueError("nonfinite or incomplete scores")
    if dataset == "val":
        with (ROOT / entry["score_path"]).open(newline="") as stream:
            reference = {row["pair_id"]: float(row["score"]) for row in csv.DictReader(stream)}
        if set(reference) != {row["pair_id"] for row in rows}:
            raise ValueError("validation pair IDs differ")
        error = max(abs(value - reference[row["pair_id"]]) for row, value in zip(rows, scores))
        if error > tolerance:
            raise ValueError(f"{entry['name']}: validation reload error {error} exceeds {tolerance}")
    else:
        error = None
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"{entry['name']}_{dataset}.csv"
    if output.exists():
        raise FileExistsError(output)
    with output.open("w", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(("pair_id", "score"))
        writer.writerows((row["pair_id"], f"{value:.8f}") for row, value in zip(rows, scores))
    metadata = {"name": entry["name"], "dataset": dataset, "splits": sorted({row["split"] for row in rows}),
                "pairs": len(rows), "pairs_sha256": digest(pairs), "scores_sha256": digest(output),
                "selection_manifest_sha256": digest(ROOT / "configs/clip_v3_final_selection.json"),
                "checkpoint_sha256": entry.get("checkpoint_sha256"), "threshold": entry["threshold"],
                "model_id": model_id, "revision": revision, "device": device,
                "elapsed_seconds": time.monotonic() - started, "val_max_abs_error": error}
    output.with_suffix(".meta.json").write_text(json.dumps(metadata, indent=2) + "\n")
    del model
    if device == "mps":
        torch.mps.empty_cache()
    print(entry["name"], dataset, len(rows), "val_error", error, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=("val", "id", "ood"), required=True)
    parser.add_argument("--device", choices=("auto", "mps", "cpu", "cuda"), default="auto")
    parser.add_argument("--output-dir", default="scores/v3_final")
    parser.add_argument("--tolerance", type=float, default=1e-5)
    args = parser.parse_args()
    manifest = json.loads((ROOT / "configs/clip_v3_final_selection.json").read_text())
    pairs = verify(manifest, args.dataset)
    splits = {"val"} if args.dataset == "val" else {"test"} if args.dataset == "id" else {"ood_near", "ood_far"}
    rows = read_pairs(pairs, splits)
    image_root = ROOT / "data/releases/abo-home-v2-20261103/images" if args.dataset != "ood" else OOD / "images"
    if any(not (image_root / row["image_path"]).is_file() for row in rows):
        raise FileNotFoundError("dataset images are incomplete")
    device = args.device
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
    for entry in manifest["models"]:
        score_one(entry, rows, image_root, device, args.dataset, pairs, ROOT / args.output_dir, args.tolerance)


if __name__ == "__main__":
    main()
