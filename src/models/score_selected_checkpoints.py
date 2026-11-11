"""Score test once for the validation-selected LoRA/full checkpoints."""
import argparse
import csv
import hashlib
import importlib.util
import json
from pathlib import Path

import torch
from peft import PeftModel
from transformers import CLIPModel, CLIPProcessor

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("clip_training", ROOT / "src/models/train_clip_lora.py")
training = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(training)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def artifact_file(entry):
    filename = "adapter_model.safetensors" if entry["kind"] == "lora" else "model.safetensors"
    return ROOT / entry["checkpoint"] / filename


def load_manifest(path):
    manifest = json.loads(Path(path).read_text())
    if not manifest.get("test_inference") or manifest.get("selection_frozen_from") != "validation only":
        raise ValueError("test manifest must freeze selection from validation only")
    models = manifest.get("models", [])
    expected = {(kind, seed) for kind in ["lora", "full"] for seed in range(3)}
    actual = set()
    for entry in models:
        config = json.loads((ROOT / entry["config"]).read_text())
        key = (entry["kind"], config["seed"])
        if key in actual:
            raise ValueError("duplicate kind/seed in selected test matrix")
        actual.add(key)
        if config.get("training_mode", "lora") != entry["kind"]:
            raise ValueError("checkpoint kind/config mismatch")
        if entry["kind"] == "lora" and (config["rank"], config["towers"]) != (16, "both"):
            raise ValueError("only validation-selected rank-16 both-tower LoRA is allowed")
        if entry["kind"] == "full" and (config["learning_rate"], config["towers"]) != (3e-5, "both"):
            raise ValueError("only definitive full-tuning control is allowed")
    if actual != expected:
        raise ValueError("selected test matrix must contain three seeds of each adapted model")
    return manifest


def read_scores(path):
    with Path(path).open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    scores = {row["pair_id"]: float(row["score"]) for row in rows}
    if len(scores) != len(rows):
        raise ValueError("duplicate validation score ID")
    return scores


def score_entry(entry, dataset_version, pairs_csv, device):
    config = json.loads((ROOT / entry["config"]).read_text())
    metadata_path = ROOT / entry["training_meta"]
    metadata = json.loads(metadata_path.read_text())
    checkpoint = artifact_file(entry)
    if metadata["config"] != config or metadata.get("test_evaluated"):
        raise ValueError(f"{entry['name']}: training metadata mismatch or test already marked evaluated")
    recorded_checkpoint = metadata.get("checkpoint_sha256", metadata.get("adapter_sha256"))
    if recorded_checkpoint != entry["checkpoint_sha256"] or digest(checkpoint) != entry["checkpoint_sha256"]:
        raise ValueError(f"{entry['name']}: checkpoint differs from frozen selection")
    if metadata["pairs_sha256"] != digest(ROOT / pairs_csv):
        raise ValueError(f"{entry['name']}: dataset changed")
    rows, anchors = training.read_dataset(ROOT / pairs_csv, dataset_version)
    test_rows = [row for pair in anchors["test"] for row in pair]
    processor = CLIPProcessor.from_pretrained(config["model_id"], revision=config["model_revision"])
    if entry["kind"] == "full":
        model = CLIPModel.from_pretrained(ROOT / entry["checkpoint"])
    else:
        base = CLIPModel.from_pretrained(config["model_id"], revision=config["model_revision"])
        model = PeftModel.from_pretrained(base, ROOT / entry["checkpoint"])
    model.to(device)
    test_scores = training.score_rows(model, processor, test_rows, ROOT / config["image_root"], device,
                                      config["batch_size"] * 2)
    combined = read_scores(ROOT / entry["validation_scores"])
    combined.update({row["pair_id"]: score for row, score in zip(test_rows, test_scores)})
    selected_rows = [row for row in rows if row["split"] in {"val", "test"}]
    if set(combined) != {row["pair_id"] for row in selected_rows}:
        raise ValueError("combined validation/test score coverage mismatch")
    output = ROOT / "scores" / f"{entry['name']}_selected_eval.csv"
    with output.open("w", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["pair_id", "score"])
        writer.writerows((row["pair_id"], f"{combined[row['pair_id']]:.8f}") for row in selected_rows)
    result = {
        "name": entry["name"], "kind": entry["kind"], "seed": config["seed"],
        "selection": "frozen from validation before test inference",
        "dataset_version": dataset_version, "pairs_sha256": digest(ROOT / pairs_csv),
        "training_metadata": entry["training_meta"], "training_metadata_sha256": digest(metadata_path),
        "checkpoint": entry["checkpoint"], "checkpoint_sha256": entry["checkpoint_sha256"],
        "validation_scores": entry["validation_scores"],
        "validation_scores_sha256": digest(ROOT / entry["validation_scores"]),
        "test_pairs": len(test_rows), "output_scores_sha256": digest(output),
        "test_evaluated": True,
    }
    (ROOT / "scores" / f"{entry['name']}_selected_eval_meta.json").write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n"
    )
    del model
    if device == "mps":
        torch.mps.empty_cache()
    print(f"scored {entry['name']}: {len(test_rows)} test pairs -> {output}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default="configs/clip_v2_selected_test.json")
    parser.add_argument("--device", choices=["auto", "cpu", "mps", "cuda"], default="auto")
    args = parser.parse_args()
    manifest = load_manifest(ROOT / args.manifest)
    device = args.device
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
    for entry in manifest["models"]:
        score_entry(entry, manifest["dataset_version"], manifest["pairs_csv"], device)


if __name__ == "__main__":
    main()
