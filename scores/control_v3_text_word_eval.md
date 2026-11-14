# Evaluation report

- Pairs: `data/releases/abo-home-reciprocal-v3-candidate/pairs.csv`
- Scores: `scores/control_v3_text_word.csv`
- Selection: `val` / `accuracy`
- Rule: `score >= threshold`
- Threshold: `0.5222853`
- Test splits: `test`
- Pairs: val 656, test 686
- Confidence intervals: 1000 cluster-bootstrap resamples by image_anchor_group (seed 0); shown for test overall and per-test-split rows.

## Validation

| Split | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | N1 recall | N2 recall | N3 recall |
|---|---|---|---|---|---|---|---|---|---|
| val | 656 | 51.07% | 0.5110 | 34.45% | 67.68% | 51.07% | 64.47% | 66.45% | 95.83% |

## Main results

| Split | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | N1 recall | N2 recall | N3 recall |
|---|---|---|---|---|---|---|---|---|---|
| All selected | 686 | 50.87% [47.52%, 54.52%] | 0.5160 [0.4757, 0.5574] | 36.44% [31.49%, 41.41%] | 65.31% [60.64%, 70.26%] | 50.87% [47.52%, 54.52%] | 65.38% | 61.78% | 83.33% |

## By negative type

| neg_type | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| N1 | 156 | 65.38% | — | — | 65.38% | — |
| N2 | 157 | 61.78% | — | — | 61.78% | — |
| N3 | 30 | 83.33% | — | — | 83.33% | — |
| pos | 343 | 36.44% | — | 36.44% | — | — |

## By category

| Category | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| CHAIR | 162 | 49.38% | 0.4876 | 37.04% | 61.73% | 49.38% |
| HOME | 22 | 63.64% | 0.6157 | 54.55% | 72.73% | 63.64% |
| HOME_FURNITURE_AND_DECOR | 46 | 47.83% | 0.5038 | 26.09% | 69.57% | 47.83% |
| OTTOMAN | 38 | 50.00% | 0.5388 | 26.32% | 73.68% | 50.00% |
| PILLOW | 30 | 43.33% | 0.3689 | 6.67% | 80.00% | 43.33% |
| RUG | 116 | 50.00% | 0.4985 | 37.93% | 62.07% | 50.00% |
| SOFA | 70 | 51.43% | 0.5400 | 31.43% | 71.43% | 51.43% |
| STOOL_SEATING | 44 | 45.45% | 0.5320 | 9.09% | 81.82% | 45.45% |
| TABLE | 86 | 53.49% | 0.5270 | 58.14% | 48.84% | 53.49% |
| WALL_ART | 72 | 56.94% | 0.5938 | 47.22% | 66.67% | 56.94% |

## By year

No non-empty values in the selected test split(s).

## Notes

- Metrics are pair-level. Positive recall is TPR; negative recall is TNR.
- AUC is undefined for single-class groups and is shown as —.
- R@1 was not computed (pass `--r-at-1` to enable it).
