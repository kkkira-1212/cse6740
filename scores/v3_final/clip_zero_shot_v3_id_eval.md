# Evaluation report

- Pairs: `data/releases/abo-home-reciprocal-v3-candidate/pairs.csv`
- Scores: `scores/v3_final/clip_zero_shot_v3_id.csv`
- Selection: `fixed`
- Rule: `score >= threshold`
- Threshold: `0.28604528`
- Test splits: `test`
- Pairs: val 656, test 686
- Validation metrics omitted: not all validation pairs have scores.
- Confidence intervals: 1000 cluster-bootstrap resamples by image_anchor_group (seed 0); shown for test overall and per-test-split rows.

## Main results

| Split | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | N1 recall | N2 recall | N3 recall |
|---|---|---|---|---|---|---|---|---|---|
| All selected | 686 | 82.22% [79.59%, 85.13%] | 0.9103 [0.8930, 0.9293] | 87.46% [83.67%, 90.96%] | 76.97% [72.59%, 81.63%] | 82.22% [79.59%, 85.13%] | 94.87% | 64.97% | 46.67% |

## Matched-anchor type metrics

| Split | Type | n_pos/n_neg | Clusters | AUC | Pos recall | Neg recall | Balanced | Paired rank | Ties |
|---|---|---|---|---|---|---|---|---|---|
| test | N1 | 156/156 | 156 groups | 0.9797 [0.9624, 0.9922] | 86.54% [81.41%, 91.67%] | 94.87% [91.03%, 98.08%] | 90.71% [87.50%, 93.59%] | 98.72% [96.79%, 100.00%] | 0 |
| test | N2 | 157/157 | 157 groups | 0.8515 [0.8173, 0.8859] | 85.99% [80.25%, 91.08%] | 64.97% [57.95%, 71.97%] | 75.48% [71.65%, 79.62%] | 92.99% [88.54%, 96.82%] | 0 |
| test | N3 | 30/30 | 15 exchanges | 0.9189 [0.8700, 0.9700] | 100.00% [100.00%, 100.00%] | 46.67% [30.00%, 63.33%] | 73.33% [65.00%, 81.67%] | 100.00% [100.00%, 100.00%] | 0 |

- Each negative is compared with the positive of its own `anchor_item_id`.
- Paired ranking requires the positive score strictly above its negative; ties count as failures.
- Matched metrics are reported per test split and are not pooled across splits.
- Matched intervals use 1000 cluster resamples (seed 0): N1/N2 image-anchor groups, N3 complete reciprocal exchanges.

## By negative type

| neg_type | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| N1 | 156 | 94.87% | — | — | 94.87% | — |
| N2 | 157 | 64.97% | — | — | 64.97% | — |
| N3 | 30 | 46.67% | — | — | 46.67% | — |
| pos | 343 | 87.46% | — | 87.46% | — | — |

## By category

| Category | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| CHAIR | 162 | 84.57% | 0.9284 | 95.06% | 74.07% | 84.57% |
| HOME | 22 | 77.27% | 0.9504 | 63.64% | 90.91% | 77.27% |
| HOME_FURNITURE_AND_DECOR | 46 | 82.61% | 0.9584 | 69.57% | 95.65% | 82.61% |
| OTTOMAN | 38 | 78.95% | 0.8837 | 94.74% | 63.16% | 78.95% |
| PILLOW | 30 | 83.33% | 0.9733 | 93.33% | 73.33% | 83.33% |
| RUG | 116 | 76.72% | 0.8680 | 72.41% | 81.03% | 76.72% |
| SOFA | 70 | 80.00% | 0.8727 | 97.14% | 62.86% | 80.00% |
| STOOL_SEATING | 44 | 72.73% | 0.9008 | 100.00% | 45.45% | 72.73% |
| TABLE | 86 | 88.37% | 0.9362 | 95.35% | 81.40% | 88.37% |
| WALL_ART | 72 | 88.89% | 0.9892 | 80.56% | 97.22% | 88.89% |

## By year

No non-empty values in the selected test split(s).

## Notes

- Metrics are pair-level. Positive recall is TPR; negative recall is TNR.
- AUC is undefined for single-class groups and is shown as —.
- R@1 was not computed (pass `--r-at-1` to enable it).
