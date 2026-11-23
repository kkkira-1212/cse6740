# Evaluation report

- Pairs: `data/releases/abo-home-reciprocal-v3-candidate/pairs.csv`
- Scores: `scores/v3_final/clip_full_v3_both_seed2_id.csv`
- Selection: `fixed`
- Rule: `score >= threshold`
- Threshold: `0.47414356`
- Test splits: `test`
- Pairs: val 656, test 686
- Validation metrics omitted: not all validation pairs have scores.
- Confidence intervals: 1000 cluster-bootstrap resamples by image_anchor_group (seed 0); shown for test overall and per-test-split rows.

## Main results

| Split | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | N1 recall | N2 recall | N3 recall |
|---|---|---|---|---|---|---|---|---|---|
| All selected | 686 | 93.59% [91.69%, 95.34%] | 0.9851 [0.9787, 0.9910] | 91.55% [88.34%, 94.46%] | 95.63% [93.29%, 97.67%] | 93.59% [91.69%, 95.34%] | 99.36% | 92.99% | 90.00% |

## Matched-anchor type metrics

| Split | Type | n_pos/n_neg | Clusters | AUC | Pos recall | Neg recall | Balanced | Paired rank | Ties |
|---|---|---|---|---|---|---|---|---|---|
| test | N1 | 156/156 | 156 groups | 0.9965 [0.9904, 0.9998] | 89.74% [84.62%, 94.23%] | 99.36% [98.08%, 100.00%] | 94.55% [91.98%, 96.79%] | 99.36% [98.08%, 100.00%] | 0 |
| test | N2 | 157/157 | 157 groups | 0.9759 [0.9616, 0.9880] | 92.36% [87.90%, 96.18%] | 92.99% [88.54%, 96.82%] | 92.68% [89.81%, 95.22%] | 98.73% [96.82%, 100.00%] | 0 |
| test | N3 | 30/30 | 15 exchanges | 0.9933 [0.9767, 1.0000] | 96.67% [90.00%, 100.00%] | 90.00% [80.00%, 100.00%] | 93.33% [88.33%, 98.33%] | 100.00% [100.00%, 100.00%] | 0 |

- Each negative is compared with the positive of its own `anchor_item_id`.
- Paired ranking requires the positive score strictly above its negative; ties count as failures.
- Matched metrics are reported per test split and are not pooled across splits.
- Matched intervals use 1000 cluster resamples (seed 0): N1/N2 image-anchor groups, N3 complete reciprocal exchanges.

## By negative type

| neg_type | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| N1 | 156 | 99.36% | — | — | 99.36% | — |
| N2 | 157 | 92.99% | — | — | 92.99% | — |
| N3 | 30 | 90.00% | — | — | 90.00% | — |
| pos | 343 | 91.55% | — | 91.55% | — | — |

## By category

| Category | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| CHAIR | 162 | 94.44% | 0.9863 | 92.59% | 96.30% | 94.44% |
| HOME | 22 | 90.91% | 0.9504 | 90.91% | 90.91% | 90.91% |
| HOME_FURNITURE_AND_DECOR | 46 | 89.13% | 0.9830 | 82.61% | 95.65% | 89.13% |
| OTTOMAN | 38 | 92.11% | 0.9945 | 100.00% | 84.21% | 92.11% |
| PILLOW | 30 | 100.00% | 1.0000 | 100.00% | 100.00% | 100.00% |
| RUG | 116 | 93.10% | 0.9938 | 86.21% | 100.00% | 93.10% |
| SOFA | 70 | 94.29% | 0.9869 | 97.14% | 91.43% | 94.29% |
| STOOL_SEATING | 44 | 95.45% | 0.9938 | 100.00% | 90.91% | 95.45% |
| TABLE | 86 | 93.02% | 0.9811 | 90.70% | 95.35% | 93.02% |
| WALL_ART | 72 | 93.06% | 1.0000 | 86.11% | 100.00% | 93.06% |

## By year

No non-empty values in the selected test split(s).

## Notes

- Metrics are pair-level. Positive recall is TPR; negative recall is TNR.
- AUC is undefined for single-class groups and is shown as —.
- R@1 was not computed (pass `--r-at-1` to enable it).
