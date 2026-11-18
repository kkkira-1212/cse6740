# Evaluation report

- Pairs: `data/releases/abo-home-v2-20261103/pairs.csv`
- Scores: `scores/clip_lora_v2_r16_both_seed1_selected_eval.csv`
- Selection: `val` / `accuracy`
- Rule: `score >= threshold`
- Threshold: `0.36497563`
- Test splits: `test`
- Pairs: val 656, test 686
- Confidence intervals: 1000 cluster-bootstrap resamples by image_anchor_group (seed 6740); shown for test overall and per-test-split rows.

## Validation

| Split | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | N1 recall | N2 recall | N3 recall |
|---|---|---|---|---|---|---|---|---|---|
| val | 656 | 94.05% | 0.9755 | 92.68% | 95.43% | 94.05% | 100.00% | 90.32% | 96.25% |

## Main results

| Split | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | N1 recall | N2 recall | N3 recall |
|---|---|---|---|---|---|---|---|---|---|
| All selected | 686 | 93.59% [91.84%, 95.34%] | 0.9797 [0.9718, 0.9875] | 93.00% [90.38%, 95.63%] | 94.17% [91.55%, 96.50%] | 93.59% [91.84%, 95.34%] | 97.66% | 89.06% | 96.55% |

## By negative type

| neg_type | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| N1 | 128 | 97.66% | — | — | 97.66% | — |
| N2 | 128 | 89.06% | — | — | 89.06% | — |
| N3 | 87 | 96.55% | — | — | 96.55% | — |
| pos | 343 | 93.00% | — | 93.00% | — | — |

## By category

| Category | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| CHAIR | 162 | 96.91% | 0.9890 | 96.30% | 97.53% | 96.91% |
| HOME | 22 | 90.91% | 0.9835 | 90.91% | 90.91% | 90.91% |
| HOME_FURNITURE_AND_DECOR | 46 | 89.13% | 0.9868 | 78.26% | 100.00% | 89.13% |
| OTTOMAN | 38 | 94.74% | 0.9945 | 100.00% | 89.47% | 94.74% |
| PILLOW | 30 | 96.67% | 0.9911 | 100.00% | 93.33% | 96.67% |
| RUG | 116 | 90.52% | 0.9747 | 84.48% | 96.55% | 90.52% |
| SOFA | 70 | 90.00% | 0.9755 | 97.14% | 82.86% | 90.00% |
| STOOL_SEATING | 44 | 90.91% | 0.9876 | 95.45% | 86.36% | 90.91% |
| TABLE | 86 | 94.19% | 0.9648 | 93.02% | 95.35% | 94.19% |
| WALL_ART | 72 | 97.22% | 0.9961 | 97.22% | 97.22% | 97.22% |

## By year

No non-empty values in the selected test split(s).

## Notes

- Metrics are pair-level. Positive recall is TPR; negative recall is TNR.
- AUC is undefined for single-class groups and is shown as —.
- R@1 was not computed (pass `--r-at-1` to enable it).
