"""Recover which Hugging Face revisions the saved V3 val predictions actually used.

The val run on 2026-11-14 loaded each model with revision "main", so the score
metadata does not name a commit. This script inspects the local Hugging Face
cache on the machine that produced those scores and records, per model:

  - the commit that refs/main points to now,
  - every cached snapshot with its modification time,
  - SHA-256 of the weight and processor/tokenizer files in each snapshot.

A model counts as recovered only when exactly one snapshot exists and it was
already on disk before the val run finished (VAL_RUN_END). Otherwise it is
flagged as ambiguous, and the val split must be rerun with a pinned revision
before any test inference (docs/final_evaluation_handoff.md, item 3).

Run on the same Mac that produced the val scores, from the repository root:
  python src/baselines/record_hf_revisions.py
Writes configs/wp8_hf_revisions_recovered.json. Reads the cache only.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path

MODELS = {
    "siglip-b16": "google/siglip-base-patch16-224",
    "blip-itm-b": "Salesforce/blip-itm-base-coco",
    "align-b": "kakaobrain/align-base",
}
# The V3 val run log (logs/run_v3_val.log) finished at 13:13:21 EST on 2026-11-14.
VAL_RUN_END = dt.datetime(2026, 11, 14, 18, 13, 21, tzinfo=dt.timezone.utc)
HASHED_SUFFIXES = (".safetensors", ".bin", ".json", ".txt", ".model")


def cache_root():
    try:
        from huggingface_hub import constants
        return Path(constants.HF_HUB_CACHE)
    except Exception:
        base = os.environ.get("HF_HOME", str(Path.home() / ".cache" / "huggingface"))
        return Path(os.environ.get("HF_HUB_CACHE", Path(base) / "hub"))


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def inspect(hf_id, root):
    repo = root / f"models--{hf_id.replace('/', '--')}"
    record = {"hf_id": hf_id, "cache_dir": str(repo), "refs_main": None, "snapshots": []}
    ref = repo / "refs" / "main"
    if ref.is_file():
        record["refs_main"] = ref.read_text().strip()
    snapshots_dir = repo / "snapshots"
    if snapshots_dir.is_dir():
        for snap in sorted(p for p in snapshots_dir.iterdir() if p.is_dir()):
            # Snapshot entries are symlinks into blobs/; the blob mtime is the download time.
            files, times = {}, []
            for entry in sorted(snap.rglob("*")):
                if entry.is_file() and entry.name.endswith(HASHED_SUFFIXES):
                    real = entry.resolve()
                    times.append(real.stat().st_mtime)
                    files[str(entry.relative_to(snap))] = sha256(real)
            downloaded = dt.datetime.fromtimestamp(max(times), dt.timezone.utc) if times else None
            record["snapshots"].append({
                "commit": snap.name,
                "latest_file_time_utc": downloaded.isoformat() if downloaded else None,
                "present_before_val_run_end": bool(downloaded and downloaded <= VAL_RUN_END),
                "file_sha256": files,
            })
    usable = [s for s in record["snapshots"] if s["present_before_val_run_end"]]
    if len(record["snapshots"]) == 1 and len(usable) == 1:
        record["status"] = "recovered"
        record["recovered_commit"] = usable[0]["commit"]
    else:
        record["status"] = "ambiguous"
        record["recovered_commit"] = None
    return record


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="configs/wp8_hf_revisions_recovered.json")
    args = ap.parse_args()

    root = cache_root()
    report = {
        "recorded_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "hf_cache": str(root),
        "val_run_end_utc": VAL_RUN_END.isoformat(),
        "rule": "recovered only if exactly one cached snapshot exists and it predates the val run end",
        "models": {key: inspect(hf_id, root) for key, hf_id in MODELS.items()},
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for key, rec in report["models"].items():
        print(f"{key}: {rec['status']} commit={rec['recovered_commit']} "
              f"snapshots={len(rec['snapshots'])} refs/main={rec['refs_main']}")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
