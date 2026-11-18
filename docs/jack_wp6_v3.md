# WP5/WP6: CLIP adaptation on frozen V3

This study reruns the CLIP zero-shot baseline, LoRA ablation and full-parameter
control on the frozen `abo-home-v3-20261115` benchmark. All results in this
handoff are ID-validation development results. No V3 ID-test or OOD model scores
were read or generated.

## Fixed experiments

- Zero-shot: `openai/clip-vit-base-patch32` at revision
  `3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268`. Three executions verify
  deterministic reproduction; they are not independent seeds.
- LoRA ablation: ranks 4/8/16 on both towers, plus rank-8 text-only and
  vision-only, each at seeds 0/1/2. All runs use five epochs and LR 1e-4.
- Full tuning: both towers, five epochs, LR 3e-5, seeds 0/1/2.

Rank-16 both-tower LoRA has the highest three-seed mean validation AUC in the
LoRA matrix and is selected for final evaluation. Full tuning is retained as
the all-parameter control.

| Method | Validation AUC |
|---|---:|
| Zero-shot CLIP | 0.924059 |
| LoRA rank 16, both towers | 0.972911 ± 0.000692 |
| Full tuning, LR 3e-5 | 0.979250 ± 0.002269 |

Deviations are sample standard deviations across seeds. Zero-shot is reported
once because its three executions are byte-identical.

## Pre-test freeze

`configs/clip_v3_final_selection.json` binds the exact data, score, config,
metadata, checkpoint and compute-cost artifacts by SHA-256. Each model/seed has
its own threshold selected by maximum ID-validation accuracy; ties choose the
smallest threshold, and prediction uses `score >= threshold`.

The validation-only protocol smoke test covers matched-anchor N1/N2/N3 AUC,
positive and negative recall, balanced accuracy, strict paired ranking and ties,
paired error transitions, and 1,000-resample complete-exchange N3 intervals.
These smoke outputs verify the reporting implementation; they are not held-out
claims. Final ID-test and OOD evaluation remain gated on adoption of the final
reporting protocol and the hash-pinned OOD table.

## Reproduction and cost

Runs used the local `cse6740` Conda environment on Apple MPS with Hugging Face
offline mode. Checkpoints remain under ignored `runs/`; committed metadata record
the environment, histories, selected epochs, hashes and reload errors. The full
validation study used approximately 1.5471 local MPS device-hours. See
`scores/clip_v3_compute_costs.csv` for per-run timings.
