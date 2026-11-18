"""Verify and export the three completed V3 LoRA validation runs."""
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[2]
NAMES = [f"clip_lora_v3_r16_both_seed{seed}" for seed in range(3)]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    manifest = json.loads((ROOT / "configs/clip_lora_v3_fixed_runs.json").read_text())
    with (ROOT / manifest["pairs_csv"]).open(newline="") as stream:
        val_rows = [row for row in csv.DictReader(stream) if row["split"] == "val"]
    records = []
    for name in NAMES:
        run = ROOT / "runs" / name
        metadata = json.loads((run / "training.json").read_text())
        config = json.loads((ROOT / "configs" / f"{name}.json").read_text())
        checkpoint = run / "best_adapter/adapter_model.safetensors"
        if metadata["config"] != config or metadata["status"] != "complete" or metadata["test_evaluated"]:
            raise ValueError(f"{name}: not a complete validation-only frozen-config run")
        if metadata["pairs_sha256"] != manifest["pairs_sha256"] or metadata["script_sha256"] != manifest["trainer_sha256"]:
            raise ValueError(f"{name}: data or trainer hash mismatch")
        if metadata["checkpoint_sha256"] != digest(checkpoint) or metadata["adapter_reload_max_error"] > 1e-5:
            raise ValueError(f"{name}: checkpoint verification failed")
        with (run / "val_scores.csv").open(newline="") as stream:
            score_rows = list(csv.DictReader(stream))
        scores = {row["pair_id"]: float(row["score"]) for row in score_rows}
        if len(scores) != len(score_rows) or set(scores) != {row["pair_id"] for row in val_rows}:
            raise ValueError(f"{name}: validation score coverage mismatch")
        metrics = {"all": float(roc_auc_score([int(row["label"]) for row in val_rows],
                                                [scores[row["pair_id"]] for row in val_rows]))}
        for kind in ["N1", "N2", "N3"]:
            anchors = {row["anchor_item_id"] for row in val_rows if row["neg_type"] == kind}
            subset = [row for row in val_rows if row["anchor_item_id"] in anchors]
            metrics[kind] = float(roc_auc_score([int(row["label"]) for row in subset],
                                                 [scores[row["pair_id"]] for row in subset]))
        if abs(metrics["all"] - metadata["best_val_auc"]) > 1e-7:
            raise ValueError(f"{name}: validation AUC does not reproduce metadata")
        destination = ROOT / "scores" / f"{name}_val.csv"
        destination.write_bytes((run / "val_scores.csv").read_bytes())
        exported = dict(metadata, release_id=manifest["release_id"], checkpoint_path=f"runs/{name}/best_adapter",
                        validation_scores_sha256=digest(destination), validation_auc_matched_by_type=metrics)
        (ROOT / "scores" / f"{name}_meta.json").write_text(json.dumps(exported, indent=2, allow_nan=False) + "\n")
        records.append({"name": name, "seed": config["seed"], "best_epoch": metadata["best_epoch"],
                        "val_auc": metrics["all"], "val_auc_N1": metrics["N1"],
                        "val_auc_N2": metrics["N2"], "val_auc_N3": metrics["N3"],
                        "trainable_parameters": metadata["trainable_parameters"],
                        "seconds": metadata["elapsed_seconds"], "checkpoint_sha256": metadata["checkpoint_sha256"]})
    with (ROOT / "scores/clip_lora_v3_r16_both_runs.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader(); writer.writerows(records)
    summary = {"configuration": "LoRA r16 both", "n_seeds": 3,
               "trainable_parameters": records[0]["trainable_parameters"]}
    for field in ["val_auc", "val_auc_N1", "val_auc_N2", "val_auc_N3", "seconds"]:
        values = [row[field] for row in records]
        summary[field + "_mean"] = float(np.mean(values))
        summary[field + "_std"] = float(np.std(values, ddof=1))
    with (ROOT / "scores/clip_lora_v3_r16_both_summary.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(summary))
        writer.writeheader(); writer.writerow(summary)
    lines = ["# V3 fixed-config LoRA validation summary", "",
             "Rank 16 on both CLIP towers was selected by the historical V2 validation ablation before V3 model runs. These three V3 runs use the frozen `abo-home-v3-20261115` snapshot and perform no held-out test inference.", "",
             f"Across seeds 0/1/2, validation AUC is {summary['val_auc_mean']:.6f} ± {summary['val_auc_std']:.6f} (sample SD). Matched-anchor per-type validation AUC means are N1 {summary['val_auc_N1_mean']:.6f}, N2 {summary['val_auc_N2_mean']:.6f}, and N3 {summary['val_auc_N3_mean']:.6f}.", "",
             "Exact configs, histories, data/trainer/checkpoint hashes, reload checks and validation predictions are stored in the adjacent files. Test evaluation remains deferred pending the team meeting.", ""]
    (ROOT / "scores/clip_lora_v3_r16_both_summary.md").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
