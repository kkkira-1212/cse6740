"""Aggregate the frozen held-out CLIP comparison across seeds."""
import csv
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
GROUPS = {
    "LoRA r16 both": [f"clip_lora_v2_r16_both_seed{seed}" for seed in range(3)],
    "Full both lr3e-5": [f"clip_full_v2_both_seed{seed}_fair" for seed in range(3)],
}
FIELDS = ["accuracy", "auc", "positive_recall", "negative_recall", "recall_N1", "recall_N2", "recall_N3"]


def overall(name, suffix="test_metrics"):
    with (ROOT / "scores" / f"{name}_{suffix}.csv").open(newline="") as stream:
        row = next(row for row in csv.DictReader(stream) if row["dimension"] == "overall")
    return {field: float(row[field]) for field in FIELDS} | {
        "threshold": float(row["threshold"]),
        "accuracy_ci_low": float(row["accuracy_ci_low"]), "accuracy_ci_high": float(row["accuracy_ci_high"]),
        "auc_ci_low": float(row["auc_ci_low"]), "auc_ci_high": float(row["auc_ci_high"]),
    }


def main():
    runs, summaries = [], []
    for method, names in GROUPS.items():
        group = []
        for seed, name in enumerate(names):
            row = {"method": method, "seed": seed, "name": name, **overall(name)}
            runs.append(row)
            group.append(row)
        summary = {"method": method, "n_seeds": len(group)}
        for field in FIELDS:
            values = [row[field] for row in group]
            summary[field + "_mean"] = float(np.mean(values))
            summary[field + "_std"] = float(np.std(values, ddof=1))
        summaries.append(summary)
    zero = overall("abo_home_v2_clip_b32", "final_metrics")
    with (ROOT / "scores/clip_v2_selected_test_runs.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(runs[0]))
        writer.writeheader()
        writer.writerows(runs)
    with (ROOT / "scores/clip_v2_selected_test_summary.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(summaries[0]))
        writer.writeheader()
        writer.writerows(summaries)
    lines = ["# Frozen held-out CLIP comparison", "",
             "Model/configuration selection was frozen from validation before test inference. Thresholds are selected independently per checkpoint on validation accuracy and then fixed on test. Each seed's 95% interval uses 1,000 image-anchor-group bootstrap resamples (seed 6740). Across-seed deviations below are sample SDs, not confidence intervals.", "",
             "| Method | Seeds | Test accuracy mean ± SD | Test AUC mean ± SD | Positive recall | N1 recall | N2 recall | N3 recall |",
             "|---|---:|---:|---:|---:|---:|---:|---:|",
             f"| Zero-shot CLIP | 1 | {zero['accuracy']:.6f} | {zero['auc']:.6f} | {zero['positive_recall']:.6f} | {zero['recall_N1']:.6f} | {zero['recall_N2']:.6f} | {zero['recall_N3']:.6f} |"]
    for row in summaries:
        lines.append(f"| {row['method']} | {row['n_seeds']} | {row['accuracy_mean']:.6f} ± {row['accuracy_std']:.6f} | {row['auc_mean']:.6f} ± {row['auc_std']:.6f} | {row['positive_recall_mean']:.6f} | {row['recall_N1_mean']:.6f} | {row['recall_N2_mean']:.6f} | {row['recall_N3_mean']:.6f} |")
    lines.extend(["", "Per-seed results and bootstrap intervals are recorded in `clip_v2_selected_test_runs.csv` and the individual evaluator reports. N3 retains the frozen dataset's known text shortcut, so its strong recall is not clean evidence of visual color reasoning.", ""])
    (ROOT / "scores/clip_v2_selected_test_summary.md").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
