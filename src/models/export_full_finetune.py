"""Validate and export the completed full-fine-tuning development runs."""
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[2]
DEFINITIVE = [f"clip_full_v2_both_seed{seed}_fair" for seed in range(3)]
INITIAL = [f"clip_full_v2_both_seed{seed}" for seed in range(3)]
PILOTS = ["clip_full_v2_both_seed0_lr1e-6", "clip_full_v2_both_seed0_lr3e-6",
          "clip_full_v2_both_seed0_lr1e-5", "clip_full_v2_both_seed0_lr3e-5"]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def validate(name, export=False):
    run = ROOT / "runs" / name
    metadata = json.loads((run / "training.json").read_text())
    config = metadata["config"]
    checkpoint = run / "best_model/model.safetensors"
    if metadata.get("status") != "complete" or metadata.get("smoke") or metadata.get("test_evaluated"):
        raise ValueError(f"{name}: not a complete validation-only run")
    if config.get("training_mode") != "full" or metadata["training_mode"] != "full":
        raise ValueError(f"{name}: not full fine-tuning")
    if metadata["pairs_sha256"] != digest(ROOT / config["pairs_csv"]):
        raise ValueError(f"{name}: dataset changed")
    if metadata["checkpoint_sha256"] != digest(checkpoint) or metadata["reload_max_error"] > 1e-5:
        raise ValueError(f"{name}: checkpoint verification failed")
    history = metadata["history"]
    best = max(history, key=lambda row: row["val_auc"])
    if best["epoch"] != metadata["best_epoch"] or best["val_auc"] != metadata["best_val_auc"]:
        raise ValueError(f"{name}: checkpoint selection mismatch")
    result = {"name": name, "seed": config["seed"], "learning_rate": config["learning_rate"],
              "epochs": config["epochs"], "best_epoch": metadata["best_epoch"],
              "val_auc": metadata["best_val_auc"], "trainable_parameters": metadata["trainable_parameters"],
              "seconds": metadata["elapsed_seconds"], "checkpoint_sha256": metadata["checkpoint_sha256"]}
    if not export:
        return result
    with (ROOT / config["pairs_csv"]).open(newline="") as stream:
        rows = [row for row in csv.DictReader(stream) if row["split"] == "val"]
    with (run / "val_scores.csv").open(newline="") as stream:
        score_rows = list(csv.DictReader(stream))
    scores = {row["pair_id"]: float(row["score"]) for row in score_rows}
    if len(scores) != len(score_rows) or set(scores) != {row["pair_id"] for row in rows}:
        raise ValueError(f"{name}: validation score coverage mismatch")
    metrics = {}
    for kind in ["all", "N1", "N2", "N3"]:
        subset = [row for row in rows if kind == "all" or row["neg_type"] in {"pos", kind}]
        metrics[kind] = float(roc_auc_score([int(row["label"]) for row in subset],
                                            [scores[row["pair_id"]] for row in subset]))
    if abs(metrics["all"] - metadata["best_val_auc"]) > 1e-7:
        raise ValueError(f"{name}: predictions do not reproduce selected AUC")
    destination = ROOT / "scores" / f"{name}_val.csv"
    destination.write_bytes((run / "val_scores.csv").read_bytes())
    exported = dict(metadata, checkpoint_path=f"runs/{name}/best_model",
                    validation_scores_sha256=digest(destination), validation_auc_by_type=metrics)
    write_json(ROOT / "scores" / f"{name}_meta.json", exported)
    result.update(**{"val_auc" if key == "all" else f"val_auc_{key}": value
                     for key, value in metrics.items()})
    return result


def write_csv(path, records):
    with Path(path).open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def main():
    definitive = [validate(name, export=True) for name in DEFINITIVE]
    initial = [validate(name) for name in INITIAL]
    pilots = [validate(name) for name in PILOTS]
    write_csv(ROOT / "scores/clip_full_v2_definitive_runs.csv", definitive)
    write_csv(ROOT / "scores/clip_full_v2_lr_development.csv", pilots + initial)
    fields = ["val_auc", "val_auc_N1", "val_auc_N2", "val_auc_N3", "seconds"]
    summary = {"configuration": "full_both_lr3e-5", "n_seeds": 3,
               "trainable_parameters": definitive[0]["trainable_parameters"]}
    for field in fields:
        values = [row[field] for row in definitive]
        summary[field + "_mean"] = float(np.mean(values))
        summary[field + "_std"] = float(np.std(values, ddof=1))
    write_csv(ROOT / "scores/clip_full_v2_summary.csv", [summary])
    lines = ["# Full fine-tuning validation summary", "",
             "The definitive control trains both CLIP towers for five epochs at learning rate 3e-5. Checkpoints are selected by validation AUC, including epoch 0. Test was not scored.", "",
             f"Across seeds 0/1/2, validation AUC is {summary['val_auc_mean']:.6f} ± {summary['val_auc_std']:.6f} (sample SD). Per-type means are N1 {summary['val_auc_N1_mean']:.6f}, N2 {summary['val_auc_N2_mean']:.6f}, and N3 {summary['val_auc_N3_mean']:.6f}.", "",
             "The learning rate was chosen using seed-0 three-epoch development pilots (1e-6, 3e-6, 1e-5, 3e-5). An earlier three-seed run at the LoRA learning rate 1e-4 is retained as development evidence, not pooled with the definitive control. N3 retains its known text shortcut.", "",
             "Exact histories, hashes, reload checks and validation predictions are in the adjacent per-run files. Full checkpoints remain under ignored `runs/`.", ""]
    (ROOT / "scores/clip_full_v2_summary.md").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
