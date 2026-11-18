"""Freeze V3 validation thresholds, protocol smoke metrics and selected artifacts."""
import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eval import eval as shared_eval
from src.eval.final_protocol import (matched_metrics, n3_exchange_bootstrap,
                                     prediction_transitions, ranking_transitions)

PAIRS = ROOT / "data/releases/abo-home-reciprocal-v3-candidate/pairs.csv"
PROVENANCE = PAIRS.with_name("n3_provenance.csv")
RELEASE_ID = "abo-home-v3-20261115"
PAIRS_SHA256 = "14814aa6bba905c07377a929c44e7d28b76893497c9c59eb86b8b6a9da334003"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_csv(path):
    with Path(path).open(newline="") as stream:
        return list(csv.DictReader(stream))


def model_entries():
    entries = [{
        "name": "clip_zero_shot_v3", "family": "zero_shot", "seed": None,
        "score_path": "scores/clip_zero_shot_v3_seed0_val.csv",
        "model_id": "openai/clip-vit-base-patch32",
        "model_revision": "3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268",
        "config_path": None, "metadata_path": None, "checkpoint_path": None,
    }]
    for family in ("lora", "full"):
        for seed in range(3):
            name = (f"clip_lora_v3_r16_both_seed{seed}" if family == "lora"
                    else f"clip_full_v3_both_seed{seed}")
            entries.append({
                "name": name, "family": family, "seed": seed,
                "score_path": f"scores/{name}_val.csv",
                "config_path": f"configs/{name}.json",
                "metadata_path": f"scores/{name}_meta.json",
                "checkpoint_path": (f"runs/{name}/best_adapter/adapter_model.safetensors"
                                    if family == "lora" else f"runs/{name}/best_model/model.safetensors"),
            })
    return entries


def scored_validation(base_rows, score_path):
    scores = {row["pair_id"]: float(row["score"]) for row in load_csv(score_path)}
    expected = {row["pair_id"] for row in base_rows}
    if set(scores) != expected:
        raise ValueError(f"{score_path}: validation score coverage mismatch")
    return [{**row, "label": int(row["label"]), "score": scores[row["pair_id"]]} for row in base_rows]


def main():
    if digest(PAIRS) != PAIRS_SHA256:
        raise ValueError("frozen V3 pairs hash changed")
    base_rows = [row for row in load_csv(PAIRS) if row["split"] == "val"]
    exchange_by_pair = {row["pair_id"]: row["exchange_id"] for row in load_csv(PROVENANCE)}
    entries, scored = model_entries(), {}
    thresholds, smoke = [], {"status": "validation_only_protocol_smoke", "models": {}}
    for entry in entries:
        rows = scored_validation(base_rows, ROOT / entry["score_path"])
        threshold, selected_accuracy = shared_eval.select_threshold(rows, "accuracy")
        overall = shared_eval.compute_metrics(rows, threshold)
        by_type = {kind: matched_metrics(rows, kind, threshold) for kind in ("N1", "N2", "N3")}
        bootstrap = n3_exchange_bootstrap(rows, exchange_by_pair, threshold, 1000, 20261116)
        scored[entry["name"]] = rows
        record = {
            "name": entry["name"], "family": entry["family"], "seed": entry["seed"],
            "threshold": threshold, "selection_objective": "accuracy",
            "selection_value": selected_accuracy, "tie_break": "smallest threshold among maxima",
            "validation_pairs": len(rows), "score_sha256": digest(ROOT / entry["score_path"]),
        }
        thresholds.append(record)
        smoke["models"][entry["name"]] = {
            "threshold": threshold, "overall": overall, "matched_by_type": by_type,
            "n3_exchange_bootstrap": bootstrap,
        }

    reference_name = "clip_zero_shot_v3"
    reference_threshold = next(row["threshold"] for row in thresholds if row["name"] == reference_name)
    changed_rows = []
    for entry in entries[1:]:
        threshold = next(row["threshold"] for row in thresholds if row["name"] == entry["name"])
        transitions = prediction_transitions(scored[reference_name], scored[entry["name"]],
                                             reference_threshold, threshold, {"N2", "N3"})
        smoke["models"][entry["name"]]["versus_zero_shot"] = {
            "prediction_transitions_N2_N3": {k: v for k, v in transitions.items() if k != "changed"},
            "ranking_transitions": ranking_transitions(scored[reference_name], scored[entry["name"]], {"N2", "N3"}),
        }
        metadata = {row["pair_id"]: row for row in base_rows}
        for row in transitions["changed"]:
            source = metadata[row["pair_id"]]
            changed_rows.append({"model": entry["name"], **row, "text": source["text"],
                                 "category": source["category"],
                                 "exchange_id": exchange_by_pair.get(row["pair_id"], "")})

    scores_dir = ROOT / "scores"
    threshold_fields = list(thresholds[0])
    with (scores_dir / "clip_v3_id_val_thresholds.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=threshold_fields); writer.writeheader(); writer.writerows(thresholds)
    (scores_dir / "clip_v3_id_val_thresholds.json").write_text(json.dumps({
        "release_id": RELEASE_ID, "pairs_sha256": PAIRS_SHA256, "split": "val",
        "prediction_rule": "score >= threshold", "test_or_ood_evaluated": False,
        "models": thresholds,
    }, indent=2) + "\n")
    (scores_dir / "clip_v3_final_protocol_val_smoke.json").write_text(json.dumps(smoke, indent=2) + "\n")
    if changed_rows:
        with (scores_dir / "clip_v3_id_val_error_transitions.csv").open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(changed_rows[0])); writer.writeheader(); writer.writerows(changed_rows)

    manifest_entries = []
    for entry, threshold in zip(entries, thresholds):
        item = {**entry, "threshold": threshold["threshold"],
                "score_sha256": threshold["score_sha256"]}
        for key in ("config_path", "metadata_path", "checkpoint_path"):
            if item.get(key):
                item[key.replace("_path", "_sha256")] = digest(ROOT / item[key])
        if item.get("metadata_path"):
            metadata = json.loads((ROOT / item["metadata_path"]).read_text())
            if metadata.get("status") != "complete" or metadata.get("test_evaluated"):
                raise ValueError(f"{item['name']}: selected run is not validation-only complete")
            if metadata["checkpoint_sha256"] != item["checkpoint_sha256"]:
                raise ValueError(f"{item['name']}: checkpoint hash mismatch")
        manifest_entries.append(item)
    cost_files = ["scores/clip_v3_compute_costs.csv", "scores/clip_v3_compute_costs.md"]
    manifest = {
        "status": "frozen_locally_before_test_or_ood", "release_id": RELEASE_ID,
        "pairs_csv": str(PAIRS.relative_to(ROOT)), "pairs_sha256": PAIRS_SHA256,
        "selection_split": "val", "threshold_objective": "accuracy",
        "prediction_rule": "score >= threshold", "test_evaluated": False,
        "ood_evaluated": False, "models": manifest_entries,
        "cost_artifacts": [{"path": path, "sha256": digest(ROOT / path)} for path in cost_files],
    }
    (ROOT / "configs/clip_v3_final_selection.json").write_text(json.dumps(manifest, indent=2) + "\n")

    lines = ["# Frozen V3 ID-validation selection", "",
             "Seven evaluation entries are frozen locally before ID-test or OOD inference: one deterministic zero-shot baseline, three rank-16 both-tower LoRA seeds, and three full-tuning seeds at LR 3e-5.", "",
             "Thresholds maximize ID-validation accuracy; ties select the smallest threshold. Prediction uses `score >= threshold`. The protocol smoke output verifies matched N1/N2/N3 metrics, strict paired ranking, zero-shot-to-adapted error transitions, and 1,000-resample reciprocal-exchange N3 intervals on validation only.", "",
             "| Model | Threshold | Val accuracy |", "|---|---:|---:|"]
    for record in thresholds:
        lines.append(f"| {record['name']} | {record['threshold']:.10f} | {record['selection_value']:.6f} |")
    lines.extend(["", "No ID-test or OOD scores were read or generated.", ""])
    (scores_dir / "clip_v3_final_selection.md").write_text("\n".join(lines))
    print(f"froze {len(entries)} entries; wrote {len(changed_rows)} validation error-transition rows")


if __name__ == "__main__":
    main()
