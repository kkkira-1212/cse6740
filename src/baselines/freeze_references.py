"""Freeze the pretrained reference models (BLIP, SigLIP, ALIGN) before final test/OOD scoring.

For each model this binds, in one JSON record:
  - the exact Hugging Face commit used for the saved V3 val predictions
    (from configs/wp8_hf_revisions_recovered.json),
  - the val score file and its SHA-256,
  - the ID-val threshold: maximum val accuracy, ties -> smallest threshold,
    computed with the shared evaluator's own select_threshold,
  - the environment recorded when the val scores were produced.

A model whose revision was not recovered is left out (listed under
"not_frozen"); its val split must be rerun with --revision <commit> before
it can be frozen (handoff item 3). The other models are still frozen.

  python src/baselines/freeze_references.py
Writes configs/wp8_v3_reference_freeze.json.
"""
import argparse
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "eval"))
import eval as shared_eval  # noqa: E402

ID_PAIRS = "data/releases/abo-home-reciprocal-v3-candidate/pairs.csv"
ID_PAIRS_SHA256 = "14814aa6bba905c07377a929c44e7d28b76893497c9c59eb86b8b6a9da334003"
VERSION = "abo-home-reciprocal-v3-candidate"
ROLES = {"blip-itm-b": "main", "siglip-b16": "main", "align-b": "appendix"}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--revisions", default="configs/wp8_hf_revisions_recovered.json")
    ap.add_argument("--out", default="configs/wp8_v3_reference_freeze.json")
    args = ap.parse_args()

    if sha256(ID_PAIRS) != ID_PAIRS_SHA256:
        raise SystemExit(f"{ID_PAIRS} does not match the adopted V3 hash")
    revisions = json.loads(Path(args.revisions).read_text())["models"]
    with open(ID_PAIRS, newline="", encoding="utf-8") as stream:
        pairs = {r["pair_id"]: r for r in csv.DictReader(stream)}

    models, problems = {}, []
    for key, role in ROLES.items():
        rec = revisions.get(key, {})
        commit = rec.get("recovered_commit")
        if not (commit and re.fullmatch(r"[0-9a-f]{40}", commit)):
            problems.append(f"{key}: revision not recovered ({rec.get('status')}); rerun val pinned first")
            continue
        stem = f"scores/{VERSION}_{key.replace('-', '_')}_val"
        with open(f"{stem}.csv", newline="", encoding="utf-8") as stream:
            scores = {r["pair_id"]: float(r["score"]) for r in csv.DictReader(stream)}
        val_ids = [p for p, r in pairs.items() if r["split"] == "val"]
        missing = sorted(set(val_ids) - set(scores))
        if missing or set(scores) - set(val_ids):
            problems.append(f"{key}: val score file does not cover exactly the val split")
            continue
        rows = [{"label": int(pairs[p]["label"]), "score": scores[p]} for p in val_ids]
        threshold, val_accuracy = shared_eval.select_threshold(rows, "accuracy")
        meta = json.loads(Path(f"{stem}_meta.json").read_text())
        models[key] = {
            "role": role,
            "hf_id": rec["hf_id"],
            "revision": commit,
            "revision_evidence": "only full cached snapshot, equal to refs/main, predating the val run (record_hf_revisions.py)",
            "loaded_weights_file": rec.get("loaded_weights_file"),
            "loaded_weights_sha256": rec.get("loaded_weights_sha256"),
            "snapshot_file_sha256": next(s["file_sha256"] for s in rec["snapshots"] if s["commit"] == commit),
            "val_scores": f"{stem}.csv",
            "val_scores_sha256": sha256(f"{stem}.csv"),
            "n_val": len(rows),
            "id_val_threshold": threshold,
            "id_val_accuracy_at_threshold": val_accuracy,
            "threshold_rule": "maximum ID-val accuracy, ties -> smallest threshold; apply as score >= threshold",
            "val_environment": {k: meta.get(k) for k in ("torch", "transformers", "device", "n_params")},
            "batch_size": 16,
        }
    if not models:
        raise SystemExit("nothing frozen:\n  " + "\n  ".join(problems))

    record = {
        "id_dataset": VERSION, "id_pairs_sha256": ID_PAIRS_SHA256,
        "selection_note": "Thresholds come from saved val scores only; no test or OOD scores were read.",
        "models": models,
        "not_frozen": problems,
    }
    Path(args.out).write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    for key, m in models.items():
        print(f"{key} ({m['role']}): revision {m['revision'][:12]} threshold {m['id_val_threshold']:.8f} "
              f"val acc {m['id_val_accuracy_at_threshold']:.4f}")
    for problem in problems:
        print(f"NOT FROZEN  {problem}")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
