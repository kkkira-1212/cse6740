"""Run the three pre-registered V3 LoRA seeds without test inference."""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TRAINER = ROOT / "src/models/train_clip_lora.py"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_manifest(path):
    manifest = json.loads(Path(path).read_text())
    if manifest["release_id"] != "abo-home-v3-20261115" or manifest["test_inference"]:
        raise ValueError("expected frozen V3 validation-only protocol")
    if digest(ROOT / manifest["pairs_csv"]) != manifest["pairs_sha256"]:
        raise ValueError("frozen V3 pairs hash mismatch")
    if digest(TRAINER) != manifest["trainer_sha256"]:
        raise ValueError("trainer differs from pre-registered hash")
    seeds = set()
    invariant = None
    for entry in manifest["runs"]:
        config = json.loads((ROOT / entry["config"]).read_text())
        if config["release_id"] != manifest["release_id"] or config["pairs_csv"] != manifest["pairs_csv"]:
            raise ValueError("run does not bind the frozen release")
        if (config["rank"], config["towers"]) != (16, "both"):
            raise ValueError("V3 protocol requires rank-16 both-tower LoRA")
        if config["seed"] in seeds:
            raise ValueError("duplicate seed")
        seeds.add(config["seed"])
        fixed = {key: value for key, value in config.items() if key != "seed"}
        if invariant is not None and fixed != invariant:
            raise ValueError("non-seed settings differ")
        invariant = fixed
    if seeds != {0, 1, 2}:
        raise ValueError("expected exactly seeds 0, 1, and 2")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default="configs/clip_lora_v3_fixed_runs.json")
    parser.add_argument("--device", choices=["auto", "cpu", "mps", "cuda"], default="auto")
    args = parser.parse_args()
    manifest = load_manifest(ROOT / args.manifest)
    for index, entry in enumerate(manifest["runs"], 1):
        run_dir = ROOT / entry["run_dir"]
        if run_dir.exists():
            raise ValueError(f"refusing to reuse or overwrite {entry['run_dir']}")
        print(f"START {index}/3 {entry['name']}", flush=True)
        subprocess.run([
            sys.executable, str(TRAINER), "--config", entry["config"],
            "--run-dir", entry["run_dir"], "--device", args.device,
        ], cwd=ROOT, check=True)
        metadata = json.loads((run_dir / "training.json").read_text())
        if metadata.get("status") != "complete" or metadata.get("test_evaluated"):
            raise ValueError(f"{entry['name']} did not complete validation-only training")
        print(f"DONE {index}/3 {entry['name']} val_auc={metadata['best_val_auc']:.6f}", flush=True)


if __name__ == "__main__":
    main()
