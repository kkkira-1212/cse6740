# Evaluation report

- Pairs: `data/releases/abo-home-v2-20261103/pairs.csv`
- Scores: `scores/clip_full_v2_both_seed0_fair_selected_eval.csv`
- Selection: `val` / `accuracy`
- Rule: `score >= threshold`
- Threshold: `0.47689342`
- Test splits: `test`
- Pairs: val 656, test 686
- Confidence intervals: 1000 cluster-bootstrap resamples by image_anchor_group (seed 6740); shown for test overall and per-test-split rows.

## Validation

| Split | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | N1 recall | N2 recall | N3 recall |
|---|---|---|---|---|---|---|---|---|---|
| val | 656 | 94.05% | 0.9830 | 91.77% | 96.34% | 94.05% | 99.19% | 92.74% | 97.50% |

## Main results

| Split | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | N1 recall | N2 recall | N3 recall |
|---|---|---|---|---|---|---|---|---|---|
| All selected | 686 | 94.61% [92.86%, 96.21%] | 0.9864 [0.9788, 0.9929] | 92.71% [90.09%, 95.05%] | 96.50% [94.46%, 98.25%] | 94.61% [92.86%, 96.21%] | 99.22% | 92.19% | 98.85% |

## By negative type

| neg_type | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| N1 | 128 | 99.22% | — | — | 99.22% | — |
| N2 | 128 | 92.19% | — | — | 92.19% | — |
| N3 | 87 | 98.85% | — | — | 98.85% | — |
| pos | 343 | 92.71% | — | 92.71% | — | — |

## By category

| Category | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| CHAIR | 162 | 95.68% | 0.9831 | 92.59% | 98.77% | 95.68% |
| HOME | 22 | 86.36% | 0.9669 | 81.82% | 90.91% | 86.36% |
| HOME_FURNITURE_AND_DECOR | 46 | 89.13% | 0.9773 | 82.61% | 95.65% | 89.13% |
| OTTOMAN | 38 | 97.37% | 0.9806 | 100.00% | 94.74% | 97.37% |
| PILLOW | 30 | 100.00% | 1.0000 | 100.00% | 100.00% | 100.00% |
| RUG | 116 | 91.38% | 0.9884 | 86.21% | 96.55% | 91.38% |
| SOFA | 70 | 97.14% | 1.0000 | 100.00% | 94.29% | 97.14% |
| STOOL_SEATING | 44 | 97.73% | 0.9917 | 100.00% | 95.45% | 97.73% |
| TABLE | 86 | 94.19% | 0.9827 | 95.35% | 93.02% | 94.19% |
| WALL_ART | 72 | 95.83% | 0.9985 | 91.67% | 100.00% | 95.83% |

## By year

No non-empty values in the selected test split(s).

## Notes

- Metrics are pair-level. Positive recall is TPR; negative recall is TNR.
- AUC is undefined for single-class groups and is shown as —.
- R@1 was not computed (pass `--r-at-1` to enable it).
