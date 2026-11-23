# Evaluation report

- Pairs: `data/releases/abo-home-reciprocal-v3-candidate/pairs.csv`
- Scores: `scores/v3_final/siglip_b16_id_test.csv`
- Selection: `fixed`
- Rule: `score >= threshold`
- Threshold: `0.04772732`
- Test splits: `test`
- Pairs: val 656, test 686
- Validation metrics omitted: not all validation pairs have scores.
- Confidence intervals: 1000 cluster-bootstrap resamples by image_anchor_group (seed 0); shown for test overall and per-test-split rows.

## Main results

| Split | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | N1 recall | N2 recall | N3 recall |
|---|---|---|---|---|---|---|---|---|---|
| All selected | 686 | 89.94% [87.76%, 92.13%] | 0.9604 [0.9482, 0.9728] | 88.05% [84.26%, 91.26%] | 91.84% [88.92%, 94.75%] | 89.94% [87.76%, 92.13%] | 98.08% | 93.63% | 50.00% |

## Matched-anchor type metrics

| Split | Type | n_pos/n_neg | Clusters | AUC | Pos recall | Neg recall | Balanced | Paired rank | Ties |
|---|---|---|---|---|---|---|---|---|---|
| test | N1 | 156/156 | 156 groups | 0.9948 [0.9891, 0.9991] | 87.18% [82.04%, 92.31%] | 98.08% [95.51%, 100.00%] | 92.63% [89.74%, 95.19%] | 100.00% [100.00%, 100.00%] | 0 |
| test | N2 | 157/157 | 157 groups | 0.9524 [0.9287, 0.9713] | 87.26% [81.53%, 91.72%] | 93.63% [89.17%, 97.45%] | 90.45% [87.26%, 92.99%] | 98.73% [96.82%, 100.00%] | 0 |
| test | N3 | 30/30 | 15 exchanges | 0.8567 [0.7889, 0.9411] | 96.67% [90.00%, 100.00%] | 50.00% [30.00%, 70.00%] | 73.33% [65.00%, 83.33%] | 100.00% [100.00%, 100.00%] | 0 |

- Each negative is compared with the positive of its own `anchor_item_id`.
- Paired ranking requires the positive score strictly above its negative; ties count as failures.
- Matched metrics are reported per test split and are not pooled across splits.
- Matched intervals use 1000 cluster resamples (seed 0): N1/N2 image-anchor groups, N3 complete reciprocal exchanges.

## By negative type

| neg_type | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| N1 | 156 | 98.08% | — | — | 98.08% | — |
| N2 | 157 | 93.63% | — | — | 93.63% | — |
| N3 | 30 | 50.00% | — | — | 50.00% | — |
| pos | 343 | 88.05% | — | 88.05% | — | — |

## By category

| Category | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| CHAIR | 162 | 93.21% | 0.9637 | 96.30% | 90.12% | 93.21% |
| HOME | 22 | 95.45% | 0.9917 | 90.91% | 100.00% | 95.45% |
| HOME_FURNITURE_AND_DECOR | 46 | 93.48% | 0.9924 | 91.30% | 95.65% | 93.48% |
| OTTOMAN | 38 | 92.11% | 0.9529 | 100.00% | 84.21% | 92.11% |
| PILLOW | 30 | 100.00% | 1.0000 | 100.00% | 100.00% | 100.00% |
| RUG | 116 | 81.03% | 0.9352 | 62.07% | 100.00% | 81.03% |
| SOFA | 70 | 87.14% | 0.9535 | 94.29% | 80.00% | 87.14% |
| STOOL_SEATING | 44 | 79.55% | 0.9318 | 81.82% | 77.27% | 79.55% |
| TABLE | 86 | 90.70% | 0.9621 | 88.37% | 93.02% | 90.70% |
| WALL_ART | 72 | 95.83% | 0.9977 | 94.44% | 97.22% | 95.83% |

## By year

No non-empty values in the selected test split(s).

## Notes

- Metrics are pair-level. Positive recall is TPR; negative recall is TNR.
- AUC is undefined for single-class groups and is shown as —.
- R@1 was not computed (pass `--r-at-1` to enable it).
