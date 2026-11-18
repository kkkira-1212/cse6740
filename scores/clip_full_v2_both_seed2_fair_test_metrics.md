# Evaluation report

- Pairs: `data/releases/abo-home-v2-20261103/pairs.csv`
- Scores: `scores/clip_full_v2_both_seed2_fair_selected_eval.csv`
- Selection: `val` / `accuracy`
- Rule: `score >= threshold`
- Threshold: `0.46708807`
- Test splits: `test`
- Pairs: val 656, test 686
- Confidence intervals: 1000 cluster-bootstrap resamples by image_anchor_group (seed 6740); shown for test overall and per-test-split rows.

## Validation

| Split | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | N1 recall | N2 recall | N3 recall |
|---|---|---|---|---|---|---|---|---|---|
| val | 656 | 94.51% | 0.9822 | 93.60% | 95.43% | 94.51% | 98.39% | 91.13% | 97.50% |

## Main results

| Split | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | N1 recall | N2 recall | N3 recall |
|---|---|---|---|---|---|---|---|---|---|
| All selected | 686 | 94.90% [93.29%, 96.36%] | 0.9851 [0.9777, 0.9915] | 94.17% [91.55%, 96.50%] | 95.63% [93.29%, 97.67%] | 94.90% [93.29%, 96.36%] | 99.22% | 90.62% | 97.70% |

## By negative type

| neg_type | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| N1 | 128 | 99.22% | — | — | 99.22% | — |
| N2 | 128 | 90.62% | — | — | 90.62% | — |
| N3 | 87 | 97.70% | — | — | 97.70% | — |
| pos | 343 | 94.17% | — | 94.17% | — | — |

## By category

| Category | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| CHAIR | 162 | 97.53% | 0.9863 | 96.30% | 98.77% | 97.53% |
| HOME | 22 | 90.91% | 0.9587 | 90.91% | 90.91% | 90.91% |
| HOME_FURNITURE_AND_DECOR | 46 | 91.30% | 0.9698 | 86.96% | 95.65% | 91.30% |
| OTTOMAN | 38 | 97.37% | 0.9945 | 100.00% | 94.74% | 97.37% |
| PILLOW | 30 | 93.33% | 0.9956 | 100.00% | 86.67% | 93.33% |
| RUG | 116 | 93.10% | 0.9929 | 87.93% | 98.28% | 93.10% |
| SOFA | 70 | 95.71% | 0.9927 | 100.00% | 91.43% | 95.71% |
| STOOL_SEATING | 44 | 93.18% | 0.9814 | 95.45% | 90.91% | 93.18% |
| TABLE | 86 | 91.86% | 0.9811 | 90.70% | 93.02% | 91.86% |
| WALL_ART | 72 | 98.61% | 1.0000 | 97.22% | 100.00% | 98.61% |

## By year

No non-empty values in the selected test split(s).

## Notes

- Metrics are pair-level. Positive recall is TPR; negative recall is TNR.
- AUC is undefined for single-class groups and is shown as —.
- R@1 was not computed (pass `--r-at-1` to enable it).
