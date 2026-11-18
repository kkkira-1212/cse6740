"""Run three deterministic V3 zero-shot validation repetitions."""
import csv
import hashlib
import subprocess
import sys
import time
from pathlib import Path

from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[2]
PAIRS = ROOT / "data/releases/abo-home-reciprocal-v3-candidate/pairs.csv"
IMAGE_ROOT = ROOT / "data/releases/abo-home-v2-20261103/images"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    with PAIRS.open(newline="") as stream:
        labels = {row["pair_id"]: int(row["label"]) for row in csv.DictReader(stream)
                  if row["split"] == "val"}
    outputs, timings = [], []
    for seed in range(3):
        output = ROOT / f"scores/clip_zero_shot_v3_seed{seed}_val.csv"
        started = time.monotonic()
        subprocess.run([
            sys.executable, str(ROOT / "src/models/zero_shot_clip.py"),
            "--pairs-csv", str(PAIRS), "--image-root", str(IMAGE_ROOT),
            "--out-csv", str(output), "--splits", "val", "--seed", str(seed),
            "--device", "mps",
        ], cwd=ROOT, check=True)
        timings.append(time.monotonic() - started)
        with output.open(newline="") as stream:
            scores = {row["pair_id"]: float(row["score"]) for row in csv.DictReader(stream)}
        if set(scores) != set(labels):
            raise ValueError("zero-shot validation coverage mismatch")
        outputs.append((output, roc_auc_score([labels[k] for k in labels], [scores[k] for k in labels])))
    hashes = [digest(path) for path, _ in outputs]
    if len(set(hashes)) != 1:
        raise ValueError("deterministic zero-shot repetitions unexpectedly differ")
    with (ROOT / "scores/clip_zero_shot_v3_costs.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["seed", "device", "validation_pairs", "elapsed_seconds"])
        writer.writeheader()
        writer.writerows({"seed": seed, "device": "mps", "validation_pairs": len(labels),
                          "elapsed_seconds": seconds} for seed, seconds in enumerate(timings))
    summary = ROOT / "scores/clip_zero_shot_v3_summary.md"
    summary.write_text(
        "# V3 zero-shot validation\n\n"
        f"CLIP ViT-B/32 validation AUC: {outputs[0][1]:.6f}.\n\n"
        "Seeds 0/1/2 produced byte-identical score files. Zero-shot inference has no "
        "training or stochastic sampling, so these are deterministic reproducibility "
        "checks rather than independent experimental seeds. Test was not scored.\n"
    )
    print(f"complete: val_auc={outputs[0][1]:.6f} sha256={hashes[0]}")


if __name__ == "__main__":
    main()
