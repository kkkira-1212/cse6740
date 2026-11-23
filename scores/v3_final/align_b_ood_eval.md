# Evaluation report

- Pairs: `data/releases/abo-ood-v3-20261115-candidate/eval_pairs.csv`
- Scores: `scores/v3_final/align_b_ood.csv`
- Selection: `fixed`
- Rule: `score >= threshold`
- Threshold: `0.15929934`
- Test splits: `ood_near`, `ood_far`
- Pairs: val 0, test 568
- Confidence intervals: 1000 cluster-bootstrap resamples by image_anchor_group (seed 0); shown for test overall and per-test-split rows.

## Main results

| Split | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | N1 recall | N2 recall | N3 recall |
|---|---|---|---|---|---|---|---|---|---|
| All selected | 568 | 91.90% [89.61%, 94.01%] | 0.9657 [0.9513, 0.9784] | 94.01% [91.20%, 96.83%] | 89.79% [86.27%, 93.31%] | 91.90% [89.61%, 94.01%] | 99.24% | 86.92% | 50.00% |
| ood_far | 292 | 89.04% [85.27%, 92.47%] | 0.9483 [0.9206, 0.9698] | 89.04% [83.56%, 93.84%] | 89.04% [83.56%, 93.17%] | 89.04% [85.27%, 92.47%] | 98.53% | 82.35% | 70.00% |
| ood_near | 276 | 94.93% [92.39%, 97.10%] | 0.9848 [0.9721, 0.9947] | 99.28% [97.83%, 100.00%] | 90.58% [85.51%, 94.93%] | 94.93% [92.39%, 97.10%] | 100.00% | 91.94% | 33.33% |

## Matched-anchor type metrics

| Split | Type | n_pos/n_neg | Clusters | AUC | Pos recall | Neg recall | Balanced | Paired rank | Ties |
|---|---|---|---|---|---|---|---|---|---|
| ood_near | N1 | 64/64 | 64 groups | 1.0000 [1.0000, 1.0000] | 98.44% [95.31%, 100.00%] | 100.00% [100.00%, 100.00%] | 99.22% [97.66%, 100.00%] | 100.00% [100.00%, 100.00%] | 0 |
| ood_near | N2 | 62/62 | 62 groups | 0.9912 [0.9711, 1.0000] | 100.00% [100.00%, 100.00%] | 91.94% [83.87%, 98.39%] | 95.97% [91.94%, 99.19%] | 98.39% [95.16%, 100.00%] | 0 |
| ood_near | N3 | 12/12 | 6 exchanges | 0.8958 [0.8333, 1.0000] | 100.00% [100.00%, 100.00%] | 33.33% [8.33%, 66.67%] | 66.67% [54.17%, 83.33%] | 100.00% [100.00%, 100.00%] | 0 |
| ood_far | N1 | 68/68 | 68 groups | 0.9831 [0.9544, 0.9998] | 92.65% [85.29%, 98.53%] | 98.53% [95.59%, 100.00%] | 95.59% [91.91%, 98.53%] | 98.53% [95.59%, 100.00%] | 0 |
| ood_far | N2 | 68/68 | 68 groups | 0.9167 [0.8709, 0.9587] | 83.82% [75.00%, 92.65%] | 82.35% [73.53%, 91.18%] | 83.09% [77.21%, 88.97%] | 91.18% [83.82%, 97.06%] | 0 |
| ood_far | N3 | 10/10 | 5 exchanges | 0.9000 [0.8700, 0.9800] | 100.00% [100.00%, 100.00%] | 70.00% [50.00%, 90.00%] | 85.00% [75.00%, 95.00%] | 100.00% [100.00%, 100.00%] | 0 |

- Each negative is compared with the positive of its own `anchor_item_id`.
- Paired ranking requires the positive score strictly above its negative; ties count as failures.
- Matched metrics are reported per test split and are not pooled across splits.
- Matched intervals use 1000 cluster resamples (seed 0): N1/N2 image-anchor groups, N3 complete reciprocal exchanges.

## By negative type

| neg_type | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| N1 | 132 | 99.24% | — | — | 99.24% | — |
| N2 | 130 | 86.92% | — | — | 86.92% | — |
| N3 | 22 | 50.00% | — | — | 50.00% | — |
| pos | 284 | 94.01% | — | 94.01% | — | — |

## By category

| Category | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| BOOT | 100 | 85.00% | 0.9548 | 86.00% | 84.00% | 85.00% |
| LAMP | 132 | 94.70% | 0.9924 | 98.48% | 90.91% | 94.70% |
| LIGHT_FIXTURE | 144 | 95.14% | 0.9767 | 100.00% | 90.28% | 95.14% |
| SANDAL | 96 | 89.58% | 0.9366 | 91.67% | 87.50% | 89.58% |
| SHOES | 96 | 92.71% | 0.9640 | 89.58% | 95.83% | 92.71% |

## By year

No non-empty values in the selected test split(s).

## Notes

- Metrics are pair-level. Positive recall is TPR; negative recall is TNR.
- AUC is undefined for single-class groups and is shown as —.
- R@1 was not computed (pass `--r-at-1` to enable it).
