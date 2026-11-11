# Evaluation report

- Pairs: `data/releases/abo-home-v2-20261103/pairs.csv`
- Scores: `scores/clip_full_v2_both_seed1_fair_selected_eval.csv`
- Selection: `val` / `accuracy`
- Rule: `score >= threshold`
- Threshold: `0.45290214`
- Test splits: `test`
- Pairs: val 656, test 686
- Confidence intervals: 1000 cluster-bootstrap resamples by image_anchor_group (seed 6740); shown for test overall and per-test-split rows.

## Validation

| Split | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | N1 recall | N2 recall | N3 recall |
|---|---|---|---|---|---|---|---|---|---|
| val | 656 | 94.36% | 0.9830 | 94.21% | 94.51% | 94.36% | 99.19% | 87.90% | 97.50% |

## Main results

| Split | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | N1 recall | N2 recall | N3 recall |
|---|---|---|---|---|---|---|---|---|---|
| All selected | 686 | 94.90% [93.29%, 96.50%] | 0.9843 [0.9764, 0.9913] | 93.00% [90.37%, 95.34%] | 96.79% [94.75%, 98.54%] | 94.90% [93.29%, 96.50%] | 99.22% | 93.75% | 97.70% |

## By negative type

| neg_type | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| N1 | 128 | 99.22% | — | — | 99.22% | — |
| N2 | 128 | 93.75% | — | — | 93.75% | — |
| N3 | 87 | 97.70% | — | — | 97.70% | — |
| pos | 343 | 93.00% | — | 93.00% | — | — |

## By category

| Category | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| CHAIR | 162 | 96.30% | 0.9820 | 95.06% | 97.53% | 96.30% |
| HOME | 22 | 90.91% | 0.9504 | 90.91% | 90.91% | 90.91% |
| HOME_FURNITURE_AND_DECOR | 46 | 89.13% | 0.9792 | 82.61% | 95.65% | 89.13% |
| OTTOMAN | 38 | 97.37% | 0.9723 | 100.00% | 94.74% | 97.37% |
| PILLOW | 30 | 100.00% | 1.0000 | 100.00% | 100.00% | 100.00% |
| RUG | 116 | 93.10% | 0.9893 | 86.21% | 100.00% | 93.10% |
| SOFA | 70 | 95.71% | 0.9951 | 100.00% | 91.43% | 95.71% |
| STOOL_SEATING | 44 | 93.18% | 0.9731 | 95.45% | 90.91% | 93.18% |
| TABLE | 86 | 94.19% | 0.9832 | 90.70% | 97.67% | 94.19% |
| WALL_ART | 72 | 97.22% | 0.9992 | 94.44% | 100.00% | 97.22% |

## By year

No non-empty values in the selected test split(s).

## Notes

- Metrics are pair-level. Positive recall is TPR; negative recall is TNR.
- AUC is undefined for single-class groups and is shown as —.
- R@1 was not computed (pass `--r-at-1` to enable it).
