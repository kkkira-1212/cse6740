# Evaluation report

- Pairs: `data/releases/abo-home-reciprocal-v3-candidate/pairs.csv`
- Scores: `scores/v3_final/align_b_id_test.csv`
- Selection: `fixed`
- Rule: `score >= threshold`
- Threshold: `0.15929934`
- Test splits: `test`
- Pairs: val 656, test 686
- Validation metrics omitted: not all validation pairs have scores.
- Confidence intervals: 1000 cluster-bootstrap resamples by image_anchor_group (seed 0); shown for test overall and per-test-split rows.

## Main results

| Split | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | N1 recall | N2 recall | N3 recall |
|---|---|---|---|---|---|---|---|---|---|
| All selected | 686 | 89.94% [87.90%, 92.13%] | 0.9616 [0.9497, 0.9742] | 93.00% [90.08%, 95.92%] | 86.88% [83.38%, 90.67%] | 89.94% [87.90%, 92.13%] | 98.08% | 87.26% | 26.67% |

## Matched-anchor type metrics

| Split | Type | n_pos/n_neg | Clusters | AUC | Pos recall | Neg recall | Balanced | Paired rank | Ties |
|---|---|---|---|---|---|---|---|---|---|
| test | N1 | 156/156 | 156 groups | 0.9949 [0.9882, 0.9995] | 92.31% [87.82%, 96.15%] | 98.08% [95.51%, 100.00%] | 95.19% [92.63%, 97.44%] | 98.72% [96.79%, 100.00%] | 0 |
| test | N2 | 157/157 | 157 groups | 0.9530 [0.9312, 0.9723] | 92.36% [87.90%, 96.18%] | 87.26% [81.53%, 92.36%] | 89.81% [86.62%, 92.36%] | 100.00% [100.00%, 100.00%] | 0 |
| test | N3 | 30/30 | 15 exchanges | 0.8889 [0.8433, 0.9489] | 100.00% [100.00%, 100.00%] | 26.67% [10.00%, 46.67%] | 63.33% [55.00%, 73.33%] | 100.00% [100.00%, 100.00%] | 0 |

- Each negative is compared with the positive of its own `anchor_item_id`.
- Paired ranking requires the positive score strictly above its negative; ties count as failures.
- Matched metrics are reported per test split and are not pooled across splits.
- Matched intervals use 1000 cluster resamples (seed 0): N1/N2 image-anchor groups, N3 complete reciprocal exchanges.

## By negative type

| neg_type | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| N1 | 156 | 98.08% | — | — | 98.08% | — |
| N2 | 157 | 87.26% | — | — | 87.26% | — |
| N3 | 30 | 26.67% | — | — | 26.67% | — |
| pos | 343 | 93.00% | — | 93.00% | — | — |

## By category

| Category | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| CHAIR | 162 | 89.51% | 0.9698 | 95.06% | 83.95% | 89.51% |
| HOME | 22 | 95.45% | 0.9917 | 90.91% | 100.00% | 95.45% |
| HOME_FURNITURE_AND_DECOR | 46 | 95.65% | 0.9849 | 95.65% | 95.65% | 95.65% |
| OTTOMAN | 38 | 86.84% | 0.9695 | 100.00% | 73.68% | 86.84% |
| PILLOW | 30 | 96.67% | 1.0000 | 100.00% | 93.33% | 96.67% |
| RUG | 116 | 85.34% | 0.9432 | 82.76% | 87.93% | 85.34% |
| SOFA | 70 | 88.57% | 0.9273 | 97.14% | 80.00% | 88.57% |
| STOOL_SEATING | 44 | 86.36% | 0.9008 | 95.45% | 77.27% | 86.36% |
| TABLE | 86 | 91.86% | 0.9784 | 97.67% | 86.05% | 91.86% |
| WALL_ART | 72 | 93.06% | 1.0000 | 86.11% | 100.00% | 93.06% |

## By year

No non-empty values in the selected test split(s).

## Notes

- Metrics are pair-level. Positive recall is TPR; negative recall is TNR.
- AUC is undefined for single-class groups and is shown as —.
- R@1 was not computed (pass `--r-at-1` to enable it).
