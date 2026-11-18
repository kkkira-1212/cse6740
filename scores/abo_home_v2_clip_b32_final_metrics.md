# Evaluation report

- Pairs: `data/releases/abo-home-v2-20261103/pairs.csv`
- Scores: `scores/abo_home_v2_clip_b32.csv`
- Selection: `val` / `accuracy`
- Rule: `score >= threshold`
- Threshold: `0.28664815`
- Test splits: `test`
- Pairs: val 656, test 686
- Confidence intervals: 1000 cluster-bootstrap resamples by image_anchor_group (seed 6740); shown for test overall and per-test-split rows.

## Validation

| Split | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | N1 recall | N2 recall | N3 recall |
|---|---|---|---|---|---|---|---|---|---|
| val | 656 | 83.84% | 0.9094 | 92.07% | 75.61% | 83.84% | 98.39% | 72.58% | 45.00% |

## Main results

| Split | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | N1 recall | N2 recall | N3 recall |
|---|---|---|---|---|---|---|---|---|---|
| All selected | 686 | 79.30% [76.53%, 81.63%] | 0.8894 [0.8686, 0.9093] | 87.46% [83.97%, 90.68%] | 71.14% [66.47%, 75.51%] | 79.30% [76.53%, 81.63%] | 94.53% | 67.97% | 41.38% |

## By negative type

| neg_type | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| N1 | 128 | 94.53% | — | — | 94.53% | — |
| N2 | 128 | 67.97% | — | — | 67.97% | — |
| N3 | 87 | 41.38% | — | — | 41.38% | — |
| pos | 343 | 87.46% | — | 87.46% | — | — |

## By category

| Category | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| CHAIR | 162 | 82.72% | 0.9189 | 95.06% | 70.37% | 82.72% |
| HOME | 22 | 77.27% | 0.9421 | 63.64% | 90.91% | 77.27% |
| HOME_FURNITURE_AND_DECOR | 46 | 78.26% | 0.9263 | 69.57% | 86.96% | 78.26% |
| OTTOMAN | 38 | 78.95% | 0.8560 | 94.74% | 63.16% | 78.95% |
| PILLOW | 30 | 80.00% | 0.9511 | 93.33% | 66.67% | 80.00% |
| RUG | 116 | 76.72% | 0.8543 | 72.41% | 81.03% | 76.72% |
| SOFA | 70 | 71.43% | 0.8580 | 97.14% | 45.71% | 71.43% |
| STOOL_SEATING | 44 | 61.36% | 0.8657 | 100.00% | 22.73% | 61.36% |
| TABLE | 86 | 84.88% | 0.9227 | 95.35% | 74.42% | 84.88% |
| WALL_ART | 72 | 88.89% | 0.9892 | 80.56% | 97.22% | 88.89% |

## By year

No non-empty values in the selected test split(s).

## Notes

- Metrics are pair-level. Positive recall is TPR; negative recall is TNR.
- AUC is undefined for single-class groups and is shown as —.
- R@1 was not computed (pass `--r-at-1` to enable it).
