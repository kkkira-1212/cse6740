# Evaluation report

- Pairs: `data/releases/abo-home-v2-20261103/pairs.csv`
- Scores: `scores/control_v2_text_tfidf.csv`
- Selection: `val` / `accuracy`
- Rule: `score >= threshold`
- Threshold: `0.4087591`
- Test splits: `test`
- Pairs: val 656, test 686
- Confidence intervals: 1000 cluster-bootstrap resamples by image_anchor_group (seed 0); shown for test overall and per-test-split rows.

## Validation

| Split | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | N1 recall | N2 recall | N3 recall |
|---|---|---|---|---|---|---|---|---|---|
| val | 656 | 60.06% | 0.6197 | 96.34% | 23.78% | 60.06% | 5.65% | 0.00% | 88.75% |

## Main results

| Split | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | N1 recall | N2 recall | N3 recall |
|---|---|---|---|---|---|---|---|---|---|
| All selected | 686 | 61.22% [58.60%, 63.85%] | 0.6230 [0.5816, 0.6622] | 96.79% [94.75%, 98.54%] | 25.66% [20.99%, 30.32%] | 61.22% [58.60%, 63.85%] | 3.91% | 2.34% | 91.95% |

## By negative type

| neg_type | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| N1 | 128 | 3.91% | — | — | 3.91% | — |
| N2 | 128 | 2.34% | — | — | 2.34% | — |
| N3 | 87 | 91.95% | — | — | 91.95% | — |
| pos | 343 | 96.79% | — | 96.79% | — | — |

## By category

| Category | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| CHAIR | 162 | 63.58% | 0.6135 | 93.83% | 33.33% | 63.58% |
| HOME | 22 | 63.64% | 0.8099 | 100.00% | 27.27% | 63.64% |
| HOME_FURNITURE_AND_DECOR | 46 | 56.52% | 0.5577 | 100.00% | 13.04% | 56.52% |
| OTTOMAN | 38 | 60.53% | 0.6524 | 100.00% | 21.05% | 60.53% |
| PILLOW | 30 | 53.33% | 0.5644 | 80.00% | 26.67% | 53.33% |
| RUG | 116 | 58.62% | 0.6103 | 96.55% | 20.69% | 58.62% |
| SOFA | 70 | 67.14% | 0.6596 | 97.14% | 37.14% | 67.14% |
| STOOL_SEATING | 44 | 70.45% | 0.6901 | 100.00% | 40.91% | 70.45% |
| TABLE | 86 | 62.79% | 0.6263 | 100.00% | 25.58% | 62.79% |
| WALL_ART | 72 | 52.78% | 0.6478 | 100.00% | 5.56% | 52.78% |

## By year

No non-empty values in the selected test split(s).

## Notes

- Metrics are pair-level. Positive recall is TPR; negative recall is TNR.
- AUC is undefined for single-class groups and is shown as —.
- R@1 was not computed (pass `--r-at-1` to enable it).
