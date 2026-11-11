"""Run the fixed five-configuration, three-seed LoRA matrix sequentially.

Completed runs are reused only after validating their configuration, trainer,
dataset and checkpoint hashes. Incomplete directories are never overwritten.
Each successful run exports validation scores and metadata, then updates the
partial/final aggregate report. Test inference is outside this script.
"""
import argparse
import csv
import hashlib
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[2]
TRAINER = ROOT / "src/models/train_clip_lora.py"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    tmp.replace(path)


def load_manifest(path):
    manifest = json.loads(Path(path).read_text())
    if manifest["test_inference"] or len(manifest["runs"]) != 15:
        raise ValueError("expected exactly 15 validation-only runs")
    expected = {(tower, rank, seed) for tower, rank in
                [("both", 4), ("both", 8), ("both", 16), ("text", 8), ("vision", 8)]
                for seed in [0, 1, 2]}
    actual, invariants, names = set(), None, set()
    for entry in manifest["runs"]:
        config = json.loads((ROOT / entry["config"]).read_text())
        key = (config["towers"], config["rank"], config["seed"])
        if key in actual or entry["name"] in names:
            raise ValueError("duplicate experiment")
        actual.add(key)
        names.add(entry["name"])
        if config["alpha"] != 2 * config["rank"]:
            raise ValueError("alpha/rank must stay at two")
        fixed = {k: v for k, v in config.items() if k not in {"towers", "rank", "seed", "alpha"}}
        if invariants is not None and fixed != invariants:
            raise ValueError("non-ablation hyperparameters differ")
        invariants = fixed
        if config["dataset_version"] != manifest["dataset_version"]:
            raise ValueError("dataset version mismatch")
    if actual != expected:
        raise ValueError("configuration/seed matrix is incomplete")
    return manifest


def export_completed(entry, trainer_sha256=None):
    config = json.loads((ROOT / entry["config"]).read_text())
    run = ROOT / entry["run_dir"]
    metadata = json.loads((run / "training.json").read_text())
    if metadata.get("status") != "complete" or metadata.get("smoke") or metadata.get("test_evaluated"):
        raise ValueError(f"{entry['name']}: not a completed validation-only full run")
    expected_trainer = trainer_sha256 or digest(TRAINER)
    if metadata["config"] != config or metadata["script_sha256"] != expected_trainer:
        raise ValueError("stored config/trainer differs from the frozen matrix")
    if metadata["pairs_sha256"] != digest(ROOT / config["pairs_csv"]):
        raise ValueError("dataset changed")
    if metadata["adapter_sha256"] != digest(run / "best_adapter/adapter_model.safetensors"):
        raise ValueError("checkpoint hash mismatch")
    if metadata["adapter_reload_max_error"] > 1e-5 or len(metadata["history"]) != config["epochs"] + 1:
        raise ValueError("incomplete epoch or checkpoint validation")
    history = metadata["history"]
    best = max(history, key=lambda h: h["val_auc"])
    if best["epoch"] != metadata["best_epoch"] or best["val_auc"] != metadata["best_val_auc"]:
        raise ValueError("checkpoint selection is inconsistent with epoch history")
    expected_params = config["rank"] * {"both": 61440, "text": 24576, "vision": 36864}[config["towers"]]
    if metadata["trainable_parameters"] != expected_params:
        raise ValueError("unexpected trainable parameter count")
    if config["towers"] != "both" and any(not n.startswith(config["towers"] + "_model.") for n in metadata["target_modules"]):
        raise ValueError("adapter target belongs to the wrong tower")
    with (ROOT / config["pairs_csv"]).open(newline="") as stream:
        rows = [r for r in csv.DictReader(stream) if r["split"] == "val"]
    with (run / "val_scores.csv").open(newline="") as stream:
        score_rows = list(csv.DictReader(stream))
    scores = {r["pair_id"]: float(r["score"]) for r in score_rows}
    if len(scores) != len(score_rows) or set(scores) != {r["pair_id"] for r in rows}:
        raise ValueError("validation score coverage mismatch")
    if not np.isfinite(list(scores.values())).all():
        raise ValueError("nonfinite validation score")
    metrics = {}
    for kind in ["all", "N1", "N2", "N3"]:
        subset = [r for r in rows if kind == "all" or r["neg_type"] in {"pos", kind}]
        metrics[kind] = float(roc_auc_score([int(r["label"]) for r in subset], [scores[r["pair_id"]] for r in subset]))
    if abs(metrics["all"] - metadata["best_val_auc"]) > 1e-7:
        raise ValueError("saved predictions do not match selected validation AUC")
    destination = ROOT / "scores" / (entry["name"] + "_val.csv")
    destination.write_bytes((run / "val_scores.csv").read_bytes())
    metadata.update(validation_scores_sha256=digest(destination), checkpoint_path=entry["run_dir"] + "/best_adapter",
                    validation_auc_by_type=metrics)
    write_json(ROOT / "scores" / (entry["name"] + "_meta.json"), metadata)
    return {"name": entry["name"], "towers": config["towers"], "rank": config["rank"],
            "seed": config["seed"], "best_epoch": metadata["best_epoch"],
            "trainable_parameters": expected_params, "seconds": metadata["elapsed_seconds"],
            "initial_val_auc": history[0]["val_auc"],
            **{"val_auc" if k == "all" else "val_auc_" + k: v for k, v in metrics.items()}}


def summarize(records, total):
    scores = ROOT / "scores"
    path = scores / "clip_lora_v2_ablation_runs.csv"
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    groups = defaultdict(list)
    for record in records:
        groups[(record["towers"], record["rank"])].append(record)
    aggregates = []
    for (tower, rank), group in groups.items():
        row = {"towers": tower, "rank": rank, "n_seeds": len(group),
               "trainable_parameters": group[0]["trainable_parameters"]}
        for field in ["val_auc", "val_auc_N1", "val_auc_N2", "val_auc_N3", "seconds"]:
            values = [r[field] for r in group]
            row[field + "_mean"] = float(np.mean(values))
            row[field + "_std"] = float(np.std(values, ddof=1)) if len(values) > 1 else None
        aggregates.append(row)
    with (scores / "clip_lora_v2_ablation_summary.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(aggregates[0]))
        writer.writeheader()
        writer.writerows(aggregates)
    lines = ["# LoRA validation ablation matrix", "", f"Completed: {len(records)}/{total} runs.", "",
             "Five configurations, seeds 0/1/2, five training epochs each. All hyperparameters except tower/rank/seed are shared; alpha/rank stays at 2. Each checkpoint is selected by validation AUC, including epoch 0. These are development validation results; test was not scored.", "",
             "Reported deviations are sample standard deviations across seeds (ddof=1), not test confidence intervals. Each per-type AUC uses all validation positives and the specified negative type. N3 retains its known text shortcut.", "",
             "| Towers | Rank | Seeds | Trainable params | Val AUC mean ± SD | N1 AUC | N2 AUC | N3 AUC | Mean seconds |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for row in aggregates:
        std = "pending" if row['val_auc_std'] is None else f"{row['val_auc_std']:.6f}"
        lines.append(f"| {row['towers']} | {row['rank']} | {row['n_seeds']} | {row['trainable_parameters']:,} | {row['val_auc_mean']:.6f} ± {std} | {row['val_auc_N1_mean']:.6f} | {row['val_auc_N2_mean']:.6f} | {row['val_auc_N3_mean']:.6f} | {row['seconds_mean']:.1f} |")
    lines.extend(["", "Timings include epoch training and validation, excluding initial model load and final adapter reload verification. Runs execute sequentially on the same device; this is not a hardware-controlled speed benchmark.", "",
                  "The initial zero-shot validation AUC is " + f"{records[0]['initial_val_auc']:.6f}. " + "Frozen data, exact configs, per-run histories and checkpoint hashes are recorded in the adjacent metadata files. Adapter weights remain local under ignored runs/.", ""])
    (scores / "clip_lora_v2_ablation_summary.md").write_text("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default="configs/clip_lora_v2_ablation.json")
    parser.add_argument("--device", default="mps", choices=["mps", "cuda", "cpu", "auto"])
    args = parser.parse_args()
    manifest = load_manifest(ROOT / args.manifest)
    frozen_trainer = manifest["trainer_sha256"]
    progress = ROOT / "runs/lora_ablation/progress.json"
    log_dir = progress.parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for index, entry in enumerate(manifest["runs"], 1):
        run = ROOT / entry["run_dir"]
        write_json(progress, {"status": "running", "current": entry["name"], "index": index,
                              "total": len(manifest["runs"]), "completed": records})
        if run.exists():
            # export_completed below refuses partial or incompatible runs.
            print(f"CHECK EXISTING {entry['name']}", flush=True)
        else:
            if digest(TRAINER) != frozen_trainer:
                raise ValueError(
                    "a frozen LoRA run is missing, but the current trainer differs; "
                    "restore the recorded trainer before creating a replacement"
                )
            print(f"START {index}/{len(manifest['runs'])} {entry['name']}", flush=True)
            command = [sys.executable, str(TRAINER), "--config", entry["config"],
                       "--run-dir", entry["run_dir"], "--device", args.device]
            with (log_dir / (entry["name"] + ".log")).open("w") as log:
                process = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE,
                                           stderr=subprocess.STDOUT, text=True, bufsize=1)
                for line in process.stdout:
                    log.write(line)
                    log.flush()
                    print(line, end="", flush=True)
                if process.wait() != 0:
                    write_json(progress, {"status": "failed", "current": entry["name"], "completed": records})
                    raise RuntimeError(f"training failed: {entry['name']}; see {log.name}")
        record = export_completed(entry, frozen_trainer)
        records.append(record)
        summarize(records, len(manifest["runs"]))
        print(f"DONE {index}/{len(manifest['runs'])} {entry['name']} val_auc={record['val_auc']:.6f} epoch={record['best_epoch']}", flush=True)
    write_json(progress, {"status": "complete", "total": len(records), "completed": records})
    print("COMPLETE: all 15 configurations/seeds validated and exported; test not scored.", flush=True)


if __name__ == "__main__":
    main()
