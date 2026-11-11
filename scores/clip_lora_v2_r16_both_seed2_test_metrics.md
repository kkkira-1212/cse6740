# Evaluation report

- Pairs: `data/releases/abo-home-v2-20261103/pairs.csv`
- Scores: `scores/clip_lora_v2_r16_both_seed2_selected_eval.csv`
- Selection: `val` / `accuracy`
- Rule: `score >= threshold`
- Threshold: `0.35075971`
- Test splits: `test`
- Pairs: val 656, test 686
- Confidence intervals: 1000 cluster-bootstrap resamples by image_anchor_group (seed 6740); shown for test overall and per-test-split rows.

## Validation

| Split | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | N1 recall | N2 recall | N3 recall |
|---|---|---|---|---|---|---|---|---|---|
| val | 656 | 93.75% | 0.9754 | 93.29% | 94.21% | 93.75% | 100.00% | 87.90% | 95.00% |

## Main results

| Split | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | N1 recall | N2 recall | N3 recall |
|---|---|---|---|---|---|---|---|---|---|
| All selected | 686 | 93.88% [92.13%, 95.48%] | 0.9793 [0.9710, 0.9871] | 93.59% [91.25%, 95.92%] | 94.17% [91.83%, 96.50%] | 93.88% [92.13%, 95.48%] | 97.66% | 89.06% | 96.55% |

## By negative type

| neg_type | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| N1 | 128 | 97.66% | — | — | 97.66% | — |
| N2 | 128 | 89.06% | — | — | 89.06% | — |
| N3 | 87 | 96.55% | — | — | 96.55% | — |
| pos | 343 | 93.59% | — | 93.59% | — | — |

## By category

| Category | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| CHAIR | 162 | 96.91% | 0.9869 | 96.30% | 97.53% | 96.91% |
| HOME | 22 | 90.91% | 0.9835 | 90.91% | 90.91% | 90.91% |
| HOME_FURNITURE_AND_DECOR | 46 | 91.30% | 0.9887 | 82.61% | 100.00% | 91.30% |
| OTTOMAN | 38 | 94.74% | 0.9945 | 100.00% | 89.47% | 94.74% |
| PILLOW | 30 | 96.67% | 0.9956 | 100.00% | 93.33% | 96.67% |
| RUG | 116 | 92.24% | 0.9768 | 86.21% | 98.28% | 92.24% |
| SOFA | 70 | 90.00% | 0.9812 | 97.14% | 82.86% | 90.00% |
| STOOL_SEATING | 44 | 90.91% | 0.9835 | 95.45% | 86.36% | 90.91% |
| TABLE | 86 | 91.86% | 0.9643 | 90.70% | 93.02% | 91.86% |
| WALL_ART | 72 | 98.61% | 0.9954 | 100.00% | 97.22% | 98.61% |

## By year

No non-empty values in the selected test split(s).

## Notes

- Metrics are pair-level. Positive recall is TPR; negative recall is TNR.
- AUC is undefined for single-class groups and is shown as —.
- R@1 was not computed (pass `--r-at-1` to enable it).
