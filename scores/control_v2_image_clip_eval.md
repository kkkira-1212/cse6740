# Evaluation report

- Pairs: `data/releases/abo-home-v2-20261103/pairs.csv`
- Scores: `scores/control_v2_image_clip.csv`
- Selection: `val` / `accuracy`
- Rule: `score >= threshold`
- Threshold: `0.5`
- Test splits: `test`
- Pairs: val 656, test 686
- Confidence intervals: 1000 cluster-bootstrap resamples by image_anchor_group (seed 0); shown for test overall and per-test-split rows.

## Validation

| Split | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | N1 recall | N2 recall | N3 recall |
|---|---|---|---|---|---|---|---|---|---|
| val | 656 | 50.00% | 0.5000 | 100.00% | 0.00% | 50.00% | 0.00% | 0.00% | 0.00% |

## Main results

| Split | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | N1 recall | N2 recall | N3 recall |
|---|---|---|---|---|---|---|---|---|---|
| All selected | 686 | 50.00% [50.00%, 50.00%] | 0.5000 [0.5000, 0.5000] | 100.00% [100.00%, 100.00%] | 0.00% [0.00%, 0.00%] | 50.00% [50.00%, 50.00%] | 0.00% | 0.00% | 0.00% |

## By negative type

| neg_type | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| N1 | 128 | 0.00% | — | — | 0.00% | — |
| N2 | 128 | 0.00% | — | — | 0.00% | — |
| N3 | 87 | 0.00% | — | — | 0.00% | — |
| pos | 343 | 100.00% | — | 100.00% | — | — |

## By category

| Category | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| CHAIR | 162 | 50.00% | 0.5000 | 100.00% | 0.00% | 50.00% |
| HOME | 22 | 50.00% | 0.5000 | 100.00% | 0.00% | 50.00% |
| HOME_FURNITURE_AND_DECOR | 46 | 50.00% | 0.5000 | 100.00% | 0.00% | 50.00% |
| OTTOMAN | 38 | 50.00% | 0.5000 | 100.00% | 0.00% | 50.00% |
| PILLOW | 30 | 50.00% | 0.5000 | 100.00% | 0.00% | 50.00% |
| RUG | 116 | 50.00% | 0.5000 | 100.00% | 0.00% | 50.00% |
| SOFA | 70 | 50.00% | 0.5000 | 100.00% | 0.00% | 50.00% |
| STOOL_SEATING | 44 | 50.00% | 0.5000 | 100.00% | 0.00% | 50.00% |
| TABLE | 86 | 50.00% | 0.5000 | 100.00% | 0.00% | 50.00% |
| WALL_ART | 72 | 50.00% | 0.5000 | 100.00% | 0.00% | 50.00% |

## By year

No non-empty values in the selected test split(s).

## Notes

- Metrics are pair-level. Positive recall is TPR; negative recall is TNR.
- AUC is undefined for single-class groups and is shown as —.
- R@1 was not computed (pass `--r-at-1` to enable it).
