"""Export auditable local-compute costs for the completed V3 validation study."""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    rows = []
    for path in sorted((ROOT / "scores").glob("clip_lora_v3_*_meta.json")):
        meta = json.loads(path.read_text())
        config = meta["config"]
        rows.append({
            "family": "lora", "run": path.name.removesuffix("_meta.json"),
            "seed": config["seed"], "configuration": f"r{config['rank']}_{config['towers']}",
            "device": meta["device"], "epochs": config["epochs"],
            "trainable_parameters": meta["trainable_parameters"],
            "total_parameters": meta["total_parameters"],
            "elapsed_seconds": meta["elapsed_seconds"],
            "device_hours": meta["elapsed_seconds"] / 3600,
            "monetary_cost_usd": "", "cost_note": "local Apple MPS; no metered cloud charge",
        })
    for path in sorted((ROOT / "scores").glob("clip_full_v3_both_seed*_meta.json")):
        meta = json.loads(path.read_text())
        config = meta["config"]
        rows.append({
            "family": "full", "run": path.name.removesuffix("_meta.json"),
            "seed": config["seed"], "configuration": "both_lr3e-5",
            "device": meta["device"], "epochs": config["epochs"],
            "trainable_parameters": meta["trainable_parameters"],
            "total_parameters": meta["total_parameters"],
            "elapsed_seconds": meta["elapsed_seconds"],
            "device_hours": meta["elapsed_seconds"] / 3600,
            "monetary_cost_usd": "", "cost_note": "local Apple MPS; no metered cloud charge",
        })
    zero_path = ROOT / "scores/clip_zero_shot_v3_costs.csv"
    with zero_path.open(newline="") as stream:
        for record in csv.DictReader(stream):
            seconds = float(record["elapsed_seconds"])
            rows.append({
                "family": "zero_shot", "run": f"clip_zero_shot_v3_seed{record['seed']}",
                "seed": record["seed"], "configuration": "clip_vit_b32",
                "device": record["device"], "epochs": 0,
                "trainable_parameters": 0, "total_parameters": 151277313,
                "elapsed_seconds": seconds, "device_hours": seconds / 3600,
                "monetary_cost_usd": "", "cost_note": "local Apple MPS inference; no metered cloud charge",
            })
    fields = list(rows[0])
    output = ROOT / "scores/clip_v3_compute_costs.csv"
    with output.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader(); writer.writerows(rows)
    totals = {family: sum(float(row["elapsed_seconds"]) for row in rows if row["family"] == family)
              for family in ("zero_shot", "lora", "full")}
    total = sum(totals.values())
    lines = [
        "# V3 validation compute cost", "",
        "Measured wall-clock time on local Apple MPS. These are device-time proxies, not cloud billing costs; monetary cost is not applicable. Model loading, validation, checkpoint saving and reload verification are included in each recorded run where performed.", "",
        "| Family | Runs | Seconds | Device-hours |", "|---|---:|---:|---:|",
    ]
    counts = {family: sum(row["family"] == family for row in rows) for family in totals}
    for family in ("zero_shot", "lora", "full"):
        lines.append(f"| {family} | {counts[family]} | {totals[family]:.1f} | {totals[family] / 3600:.4f} |")
    lines.extend([f"| **total** | **{len(rows)}** | **{total:.1f}** | **{total / 3600:.4f}** |", "",
                  "The detailed CSV contains every run, seed, parameter count and elapsed time. Test inference is not included because test was not scored.", ""])
    (ROOT / "scores/clip_v3_compute_costs.md").write_text("\n".join(lines))
    print(f"exported {len(rows)} rows, total_device_hours={total / 3600:.4f}")


if __name__ == "__main__":
    main()
