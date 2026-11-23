# Evaluation report

- Pairs: `data/releases/abo-ood-v3-20261115-candidate/eval_pairs.csv`
- Scores: `scores/v3_final/blip_itm_b_ood.csv`
- Selection: `fixed`
- Rule: `score >= threshold`
- Threshold: `0.26430228`
- Test splits: `ood_near`, `ood_far`
- Pairs: val 0, test 568
- Confidence intervals: 1000 cluster-bootstrap resamples by image_anchor_group (seed 0); shown for test overall and per-test-split rows.

## Main results

| Split | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | N1 recall | N2 recall | N3 recall |
|---|---|---|---|---|---|---|---|---|---|
| All selected | 568 | 91.20% [88.91%, 93.31%] | 0.9649 [0.9514, 0.9767] | 88.73% [84.86%, 92.25%] | 93.66% [90.49%, 96.48%] | 91.20% [88.91%, 93.31%] | 99.24% | 91.54% | 72.73% |
| ood_far | 292 | 88.70% [85.27%, 92.12%] | 0.9595 [0.9365, 0.9780] | 81.51% [74.66%, 87.67%] | 95.89% [92.47%, 98.63%] | 88.70% [85.27%, 92.12%] | 98.53% | 92.65% | 100.00% |
| ood_near | 276 | 93.84% [91.30%, 96.38%] | 0.9798 [0.9665, 0.9910] | 96.38% [92.75%, 99.28%] | 91.30% [86.23%, 95.65%] | 93.84% [91.30%, 96.38%] | 100.00% | 90.32% | 50.00% |

## Matched-anchor type metrics

| Split | Type | n_pos/n_neg | Clusters | AUC | Pos recall | Neg recall | Balanced | Paired rank | Ties |
|---|---|---|---|---|---|---|---|---|---|
| ood_near | N1 | 64/64 | 64 groups | 0.9978 [0.9912, 1.0000] | 93.75% [87.50%, 98.44%] | 100.00% [100.00%, 100.00%] | 96.88% [93.75%, 99.22%] | 98.44% [95.31%, 100.00%] | 0 |
| ood_near | N2 | 62/62 | 62 groups | 0.9878 [0.9711, 0.9984] | 98.39% [95.16%, 100.00%] | 90.32% [82.26%, 96.77%] | 94.35% [90.32%, 97.58%] | 100.00% [100.00%, 100.00%] | 0 |
| ood_near | N3 | 12/12 | 6 exchanges | 0.8403 [0.7639, 0.9236] | 100.00% [100.00%, 100.00%] | 50.00% [25.00%, 75.00%] | 75.00% [62.50%, 87.50%] | 100.00% [100.00%, 100.00%] | 0 |
| ood_far | N1 | 68/68 | 68 groups | 0.9883 [0.9745, 0.9987] | 85.29% [76.47%, 94.12%] | 98.53% [95.59%, 100.00%] | 91.91% [87.50%, 96.32%] | 100.00% [100.00%, 100.00%] | 0 |
| ood_far | N2 | 68/68 | 68 groups | 0.9234 [0.8817, 0.9639] | 77.94% [69.12%, 86.80%] | 92.65% [86.76%, 98.53%] | 85.29% [80.15%, 90.46%] | 91.18% [83.82%, 97.06%] | 0 |
| ood_far | N3 | 10/10 | 5 exchanges | 0.9800 [0.9400, 1.0000] | 80.00% [60.00%, 100.00%] | 100.00% [100.00%, 100.00%] | 90.00% [80.00%, 100.00%] | 100.00% [100.00%, 100.00%] | 0 |

- Each negative is compared with the positive of its own `anchor_item_id`.
- Paired ranking requires the positive score strictly above its negative; ties count as failures.
- Matched metrics are reported per test split and are not pooled across splits.
- Matched intervals use 1000 cluster resamples (seed 0): N1/N2 image-anchor groups, N3 complete reciprocal exchanges.

## By negative type

| neg_type | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| N1 | 132 | 99.24% | — | — | 99.24% | — |
| N2 | 130 | 91.54% | — | — | 91.54% | — |
| N3 | 22 | 72.73% | — | — | 72.73% | — |
| pos | 284 | 88.73% | — | 88.73% | — | — |

## By category

| Category | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| BOOT | 100 | 87.00% | 0.9648 | 76.00% | 98.00% | 87.00% |
| LAMP | 132 | 95.45% | 0.9865 | 96.97% | 93.94% | 95.45% |
| LIGHT_FIXTURE | 144 | 92.36% | 0.9732 | 95.83% | 88.89% | 92.36% |
| SANDAL | 96 | 88.54% | 0.9366 | 85.42% | 91.67% | 88.54% |
| SHOES | 96 | 90.62% | 0.9787 | 83.33% | 97.92% | 90.62% |

## By year

No non-empty values in the selected test split(s).

## Notes

- Metrics are pair-level. Positive recall is TPR; negative recall is TNR.
- AUC is undefined for single-class groups and is shown as —.
- R@1 was not computed (pass `--r-at-1` to enable it).
