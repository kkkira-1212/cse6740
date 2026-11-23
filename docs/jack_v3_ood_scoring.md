# Frozen CLIP scoring on adopted ABO OOD

The selected CLIP models from `configs/clip_v3_final_selection.json` were scored
once on the adopted 568-pair OOD evaluation table. The local scorer verifies
the frozen ID/OOD pairs, configs, validation scores, metadata and checkpoint
hashes before inference. All seven models reproduced their saved ID-validation
scores within 6.2e-8 before OOD scoring. OOD images were verified against the
300-image manifest. No model, checkpoint or threshold was selected on OOD.

The score files and Aaron's shared evaluator reports are under
`scores/v3_final/`. Each score CSV has exactly the 568 frozen pair IDs and
finite scores. The evaluator used each model's frozen ID-validation threshold,
matched-type metrics, N3 exchange provenance, 1,000 bootstrap resamples and
separate `ood_near` and `ood_far` splits.

| Model | Near AUC | Near accuracy | Far AUC | Far accuracy |
|---|---:|---:|---:|---:|
| Zero-shot CLIP | 0.881748 | 0.771739 | 0.928223 | 0.876712 |
| LoRA r16 both seed 0 | 0.911153 | 0.844203 | 0.896979 | 0.821918 |
| LoRA r16 both seed 1 | 0.904327 | 0.833333 | 0.902561 | 0.835616 |
| LoRA r16 both seed 2 | 0.905902 | 0.844203 | 0.905001 | 0.821918 |
| Full tuning seed 0 | 0.784972 | 0.717391 | 0.805592 | 0.705479 |
| Full tuning seed 1 | 0.783816 | 0.721014 | 0.801651 | 0.671233 |
| Full tuning seed 2 | 0.793636 | 0.702899 | 0.809814 | 0.654110 |

These descriptive OOD results suggest a large full-tuning regression on both
categories. Near/far negative mixes and category distributions differ; avoid
interpreting pooled differences as causal effects. N3 has only six near and five
far reciprocal exchanges, and candidate labels are not fully human certified.
The same seven frozen CLIP configurations were subsequently scored on the
686-pair V3 ID test. Each score file covers exactly the frozen test pair IDs;
evaluation uses its previously selected ID-validation threshold. Per-seed
score, metadata, overall, and matched-type reports are under `scores/v3_final/`.

| Model | ID test AUC | ID test accuracy |
|---|---:|---:|
| Zero-shot CLIP | 0.910263 | 0.822157 |
| LoRA r16 both seed 0 | 0.978878 | 0.927114 |
| LoRA r16 both seed 1 | 0.979762 | 0.937318 |
| LoRA r16 both seed 2 | 0.979906 | 0.931487 |
| Full tuning seed 0 | 0.983910 | 0.937318 |
| Full tuning seed 1 | 0.986927 | 0.946064 |
| Full tuning seed 2 | 0.985108 | 0.935860 |

To reproduce the scorer after restoring the local ignored checkpoints and OOD
images, run `python src/models/score_v3_final.py --dataset val` first, then
`python src/models/score_v3_final.py --dataset ood`. See
`docs/final_evaluation_handoff.md` for the shared evaluator arguments.
