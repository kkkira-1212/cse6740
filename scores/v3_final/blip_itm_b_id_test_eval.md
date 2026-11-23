# Evaluation report

- Pairs: `data/releases/abo-home-reciprocal-v3-candidate/pairs.csv`
- Scores: `scores/v3_final/blip_itm_b_id_test.csv`
- Selection: `fixed`
- Rule: `score >= threshold`
- Threshold: `0.26430228`
- Test splits: `test`
- Pairs: val 656, test 686
- Validation metrics omitted: not all validation pairs have scores.
- Confidence intervals: 1000 cluster-bootstrap resamples by image_anchor_group (seed 0); shown for test overall and per-test-split rows.

## Main results

| Split | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | N1 recall | N2 recall | N3 recall |
|---|---|---|---|---|---|---|---|---|---|
| All selected | 686 | 93.29% [91.54%, 95.19%] | 0.9775 [0.9674, 0.9869] | 94.17% [91.55%, 96.50%] | 92.42% [89.50%, 95.34%] | 93.29% [91.54%, 95.19%] | 99.36% | 89.17% | 73.33% |

## Matched-anchor type metrics

| Split | Type | n_pos/n_neg | Clusters | AUC | Pos recall | Neg recall | Balanced | Paired rank | Ties |
|---|---|---|---|---|---|---|---|---|---|
| test | N1 | 156/156 | 156 groups | 0.9964 [0.9887, 1.0000] | 94.23% [89.74%, 97.44%] | 99.36% [98.08%, 100.00%] | 96.79% [94.55%, 98.72%] | 99.36% [98.08%, 100.00%] | 0 |
| test | N2 | 157/157 | 157 groups | 0.9606 [0.9397, 0.9786] | 92.99% [88.54%, 96.82%] | 89.17% [84.08%, 93.63%] | 91.08% [87.89%, 93.95%] | 96.82% [93.63%, 99.36%] | 0 |
| test | N3 | 30/30 | 15 exchanges | 0.9844 [0.9600, 1.0000] | 100.00% [100.00%, 100.00%] | 73.33% [53.33%, 90.00%] | 86.67% [76.67%, 95.00%] | 100.00% [100.00%, 100.00%] | 0 |

- Each negative is compared with the positive of its own `anchor_item_id`.
- Paired ranking requires the positive score strictly above its negative; ties count as failures.
- Matched metrics are reported per test split and are not pooled across splits.
- Matched intervals use 1000 cluster resamples (seed 0): N1/N2 image-anchor groups, N3 complete reciprocal exchanges.

## By negative type

| neg_type | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| N1 | 156 | 99.36% | — | — | 99.36% | — |
| N2 | 157 | 89.17% | — | — | 89.17% | — |
| N3 | 30 | 73.33% | — | — | 73.33% | — |
| pos | 343 | 94.17% | — | 94.17% | — | — |

## By category

| Category | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| CHAIR | 162 | 93.83% | 0.9739 | 96.30% | 91.36% | 93.83% |
| HOME | 22 | 95.45% | 0.9917 | 100.00% | 90.91% | 95.45% |
| HOME_FURNITURE_AND_DECOR | 46 | 97.83% | 1.0000 | 95.65% | 100.00% | 97.83% |
| OTTOMAN | 38 | 92.11% | 1.0000 | 100.00% | 84.21% | 92.11% |
| PILLOW | 30 | 93.33% | 0.9956 | 100.00% | 86.67% | 93.33% |
| RUG | 116 | 88.79% | 0.9596 | 84.48% | 93.10% | 88.79% |
| SOFA | 70 | 90.00% | 0.9380 | 91.43% | 88.57% | 90.00% |
| STOOL_SEATING | 44 | 93.18% | 0.9793 | 95.45% | 90.91% | 93.18% |
| TABLE | 86 | 94.19% | 0.9827 | 93.02% | 95.35% | 94.19% |
| WALL_ART | 72 | 98.61% | 0.9992 | 100.00% | 97.22% | 98.61% |

## By year

No non-empty values in the selected test split(s).

## Notes

- Metrics are pair-level. Positive recall is TPR; negative recall is TNR.
- AUC is undefined for single-class groups and is shown as —.
- R@1 was not computed (pass `--r-at-1` to enable it).
