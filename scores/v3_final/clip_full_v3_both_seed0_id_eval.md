# Evaluation report

- Pairs: `data/releases/abo-home-reciprocal-v3-candidate/pairs.csv`
- Scores: `scores/v3_final/clip_full_v3_both_seed0_id.csv`
- Selection: `fixed`
- Rule: `score >= threshold`
- Threshold: `0.41758221`
- Test splits: `test`
- Pairs: val 656, test 686
- Validation metrics omitted: not all validation pairs have scores.
- Confidence intervals: 1000 cluster-bootstrap resamples by image_anchor_group (seed 0); shown for test overall and per-test-split rows.

## Main results

| Split | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | N1 recall | N2 recall | N3 recall |
|---|---|---|---|---|---|---|---|---|---|
| All selected | 686 | 93.73% [91.98%, 95.48%] | 0.9839 [0.9761, 0.9909] | 95.34% [92.71%, 97.38%] | 92.13% [89.21%, 94.75%] | 93.73% [91.98%, 95.48%] | 99.36% | 87.26% | 80.00% |

## Matched-anchor type metrics

| Split | Type | n_pos/n_neg | Clusters | AUC | Pos recall | Neg recall | Balanced | Paired rank | Ties |
|---|---|---|---|---|---|---|---|---|---|
| test | N1 | 156/156 | 156 groups | 0.9983 [0.9949, 1.0000] | 96.15% [92.95%, 98.72%] | 99.36% [98.08%, 100.00%] | 97.76% [96.15%, 99.36%] | 99.36% [98.08%, 100.00%] | 0 |
| test | N2 | 157/157 | 157 groups | 0.9712 [0.9546, 0.9854] | 93.63% [89.81%, 96.82%] | 87.26% [82.17%, 92.36%] | 90.45% [87.58%, 93.31%] | 98.09% [95.54%, 100.00%] | 0 |
| test | N3 | 30/30 | 15 exchanges | 0.9944 [0.9822, 1.0000] | 100.00% [100.00%, 100.00%] | 80.00% [66.67%, 90.00%] | 90.00% [83.33%, 95.00%] | 100.00% [100.00%, 100.00%] | 0 |

- Each negative is compared with the positive of its own `anchor_item_id`.
- Paired ranking requires the positive score strictly above its negative; ties count as failures.
- Matched metrics are reported per test split and are not pooled across splits.
- Matched intervals use 1000 cluster resamples (seed 0): N1/N2 image-anchor groups, N3 complete reciprocal exchanges.

## By negative type

| neg_type | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| N1 | 156 | 99.36% | — | — | 99.36% | — |
| N2 | 157 | 87.26% | — | — | 87.26% | — |
| N3 | 30 | 80.00% | — | — | 80.00% | — |
| pos | 343 | 95.34% | — | 95.34% | — | — |

## By category

| Category | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| CHAIR | 162 | 93.83% | 0.9803 | 95.06% | 92.59% | 93.83% |
| HOME | 22 | 90.91% | 0.9587 | 90.91% | 90.91% | 90.91% |
| HOME_FURNITURE_AND_DECOR | 46 | 91.30% | 0.9905 | 86.96% | 95.65% | 91.30% |
| OTTOMAN | 38 | 92.11% | 0.9834 | 100.00% | 84.21% | 92.11% |
| PILLOW | 30 | 90.00% | 1.0000 | 100.00% | 80.00% | 90.00% |
| RUG | 116 | 93.10% | 0.9935 | 91.38% | 94.83% | 93.10% |
| SOFA | 70 | 94.29% | 0.9935 | 100.00% | 88.57% | 94.29% |
| STOOL_SEATING | 44 | 95.45% | 0.9876 | 100.00% | 90.91% | 95.45% |
| TABLE | 86 | 94.19% | 0.9832 | 97.67% | 90.70% | 94.19% |
| WALL_ART | 72 | 97.22% | 0.9985 | 94.44% | 100.00% | 97.22% |

## By year

No non-empty values in the selected test split(s).

## Notes

- Metrics are pair-level. Positive recall is TPR; negative recall is TNR.
- AUC is undefined for single-class groups and is shown as —.
- R@1 was not computed (pass `--r-at-1` to enable it).
