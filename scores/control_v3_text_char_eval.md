# Evaluation report

- Pairs: `data/releases/abo-home-reciprocal-v3-candidate/pairs.csv`
- Scores: `scores/control_v3_text_char.csv`
- Selection: `val` / `accuracy`
- Rule: `score >= threshold`
- Threshold: `0.49939115`
- Test splits: `test`
- Pairs: val 656, test 686
- Confidence intervals: 1000 cluster-bootstrap resamples by image_anchor_group (seed 0); shown for test overall and per-test-split rows.

## Validation

| Split | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | N1 recall | N2 recall | N3 recall |
|---|---|---|---|---|---|---|---|---|---|
| val | 656 | 51.22% | 0.5135 | 61.89% | 40.55% | 51.22% | 37.50% | 38.16% | 75.00% |

## Main results

| Split | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | N1 recall | N2 recall | N3 recall |
|---|---|---|---|---|---|---|---|---|---|
| All selected | 686 | 51.60% [48.10%, 54.96%] | 0.5204 [0.4803, 0.5600] | 62.39% [57.14%, 67.93%] | 40.82% [35.57%, 46.36%] | 51.60% [48.10%, 54.96%] | 33.97% | 41.40% | 73.33% |

## By negative type

| neg_type | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| N1 | 156 | 33.97% | — | — | 33.97% | — |
| N2 | 157 | 41.40% | — | — | 41.40% | — |
| N3 | 30 | 73.33% | — | — | 73.33% | — |
| pos | 343 | 62.39% | — | 62.39% | — | — |

## By category

| Category | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| CHAIR | 162 | 48.77% | 0.4889 | 62.96% | 34.57% | 48.77% |
| HOME | 22 | 59.09% | 0.6736 | 72.73% | 45.45% | 59.09% |
| HOME_FURNITURE_AND_DECOR | 46 | 50.00% | 0.4943 | 47.83% | 52.17% | 50.00% |
| OTTOMAN | 38 | 60.53% | 0.6357 | 68.42% | 52.63% | 60.53% |
| PILLOW | 30 | 43.33% | 0.3689 | 26.67% | 60.00% | 43.33% |
| RUG | 116 | 47.41% | 0.4851 | 63.79% | 31.03% | 47.41% |
| SOFA | 70 | 55.71% | 0.5841 | 65.71% | 45.71% | 55.71% |
| STOOL_SEATING | 44 | 50.00% | 0.5031 | 27.27% | 72.73% | 50.00% |
| TABLE | 86 | 53.49% | 0.5443 | 72.09% | 34.88% | 53.49% |
| WALL_ART | 72 | 56.94% | 0.5814 | 83.33% | 30.56% | 56.94% |

## By year

No non-empty values in the selected test split(s).

## Notes

- Metrics are pair-level. Positive recall is TPR; negative recall is TNR.
- AUC is undefined for single-class groups and is shown as —.
- R@1 was not computed (pass `--r-at-1` to enable it).
