"""Run the three frozen V3 full-fine-tuning validation controls."""
import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[2]
TRAINER = ROOT / "src/models/train_clip_lora.py"
TRAINER_SHA256 = "2f69190031b28e7974faaac94ebd16c829527c6cad098f43871110015d5ec5be"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    if digest(TRAINER) != TRAINER_SHA256:
        raise ValueError("trainer differs from frozen V3 protocol")
    records = []
    for seed in range(3):
        name = f"clip_full_v3_both_seed{seed}"
        config_path = ROOT / f"configs/{name}.json"
        config = json.loads(config_path.read_text())
        run = ROOT / f"runs/{name}"
        if not run.exists():
            subprocess.run([sys.executable, str(TRAINER), "--config", str(config_path),
                            "--run-dir", str(run), "--device", "mps"], cwd=ROOT, check=True)
        meta = json.loads((run / "training.json").read_text())
        if meta.get("status") != "complete" or meta.get("test_evaluated") or meta["config"] != config:
            raise ValueError(f"{name}: invalid completed run")
        if meta["script_sha256"] != TRAINER_SHA256 or meta["pairs_sha256"] != digest(ROOT / config["pairs_csv"]):
            raise ValueError(f"{name}: trainer or dataset hash mismatch")
        checkpoint = run / "best_model/model.safetensors"
        if meta["checkpoint_sha256"] != digest(checkpoint) or meta["reload_max_error"] > 1e-5:
            raise ValueError(f"{name}: checkpoint verification failed")
        destination = ROOT / f"scores/{name}_val.csv"
        destination.write_bytes((run / "val_scores.csv").read_bytes())
        (ROOT / f"scores/{name}_meta.json").write_text(json.dumps(meta, indent=2) + "\n")
        records.append({"seed": seed, "best_epoch": meta["best_epoch"],
                        "val_auc": meta["best_val_auc"], "seconds": meta["elapsed_seconds"]})
    values = [r["val_auc"] for r in records]
    with (ROOT / "scores/clip_full_v3_runs.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0])); writer.writeheader(); writer.writerows(records)
    (ROOT / "scores/clip_full_v3_summary.md").write_text(
        "# V3 full fine-tuning validation\n\n"
        f"Seeds 0/1/2: mean AUC {np.mean(values):.6f} ± {np.std(values, ddof=1):.6f} "
        "(sample SD). Checkpoints were selected on validation only; test was not scored.\n"
    )
    print(f"complete: mean={np.mean(values):.6f} sd={np.std(values, ddof=1):.6f}")


if __name__ == "__main__":
    main()
