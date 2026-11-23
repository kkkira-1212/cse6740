# Evaluation report

- Pairs: `data/releases/abo-ood-v3-20261115-candidate/eval_pairs.csv`
- Scores: `scores/v3_final/clip_lora_v3_r16_both_seed1_ood.csv`
- Selection: `fixed`
- Rule: `score >= threshold`
- Threshold: `0.35778347`
- Test splits: `ood_near`, `ood_far`
- Pairs: val 0, test 568
- Confidence intervals: 1000 cluster-bootstrap resamples by image_anchor_group (seed 0); shown for test overall and per-test-split rows.

## Main results

| Split | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | N1 recall | N2 recall | N3 recall |
|---|---|---|---|---|---|---|---|---|---|
| All selected | 568 | 83.45% [80.46%, 86.44%] | 0.9017 [0.8776, 0.9241] | 82.75% [78.52%, 86.97%] | 84.15% [79.93%, 88.38%] | 83.45% [80.46%, 86.44%] | 90.15% | 76.15% | 95.45% |
| ood_far | 292 | 83.56% [79.45%, 87.67%] | 0.9026 [0.8652, 0.9325] | 78.77% [71.92%, 84.93%] | 88.36% [82.88%, 93.15%] | 83.56% [79.45%, 87.67%] | 91.18% | 83.82% | 100.00% |
| ood_near | 276 | 83.33% [79.35%, 87.33%] | 0.9043 [0.8719, 0.9374] | 86.96% [81.16%, 92.05%] | 79.71% [72.46%, 86.23%] | 83.33% [79.35%, 87.33%] | 89.06% | 67.74% | 91.67% |

## Matched-anchor type metrics

| Split | Type | n_pos/n_neg | Clusters | AUC | Pos recall | Neg recall | Balanced | Paired rank | Ties |
|---|---|---|---|---|---|---|---|---|---|
| ood_near | N1 | 64/64 | 64 groups | 0.9341 [0.8918, 0.9702] | 84.38% [75.00%, 92.19%] | 89.06% [81.25%, 96.88%] | 86.72% [81.25%, 92.19%] | 95.31% [90.59%, 100.00%] | 0 |
| ood_near | N2 | 62/62 | 62 groups | 0.8626 [0.7984, 0.9254] | 87.10% [77.42%, 95.16%] | 67.74% [56.41%, 79.03%] | 77.42% [70.97%, 83.87%] | 93.55% [87.10%, 98.39%] | 0 |
| ood_near | N3 | 12/12 | 6 exchanges | 1.0000 [1.0000, 1.0000] | 100.00% [100.00%, 100.00%] | 91.67% [75.00%, 100.00%] | 95.83% [87.50%, 100.00%] | 100.00% [100.00%, 100.00%] | 0 |
| ood_far | N1 | 68/68 | 68 groups | 0.9254 [0.8791, 0.9643] | 77.94% [67.65%, 88.24%] | 91.18% [83.82%, 97.06%] | 84.56% [78.68%, 89.71%] | 94.12% [88.24%, 98.53%] | 0 |
| ood_far | N2 | 68/68 | 68 groups | 0.8793 [0.8194, 0.9360] | 79.41% [69.12%, 88.27%] | 83.82% [74.96%, 92.65%] | 81.62% [74.98%, 88.24%] | 86.76% [79.41%, 94.12%] | 0 |
| ood_far | N3 | 10/10 | 5 exchanges | 0.9000 [0.7800, 1.0000] | 80.00% [60.00%, 100.00%] | 100.00% [100.00%, 100.00%] | 90.00% [80.00%, 100.00%] | 100.00% [100.00%, 100.00%] | 0 |

- Each negative is compared with the positive of its own `anchor_item_id`.
- Paired ranking requires the positive score strictly above its negative; ties count as failures.
- Matched metrics are reported per test split and are not pooled across splits.
- Matched intervals use 1000 cluster resamples (seed 0): N1/N2 image-anchor groups, N3 complete reciprocal exchanges.

## By negative type

| neg_type | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| N1 | 132 | 90.15% | — | — | 90.15% | — |
| N2 | 130 | 76.15% | — | — | 76.15% | — |
| N3 | 22 | 95.45% | — | — | 95.45% | — |
| pos | 284 | 82.75% | — | 82.75% | — | — |

## By category

| Category | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| BOOT | 100 | 85.00% | 0.9176 | 86.00% | 84.00% | 85.00% |
| LAMP | 132 | 87.12% | 0.9603 | 95.45% | 78.79% | 87.12% |
| LIGHT_FIXTURE | 144 | 79.86% | 0.8592 | 79.17% | 80.56% | 79.86% |
| SANDAL | 96 | 81.25% | 0.8759 | 72.92% | 89.58% | 81.25% |
| SHOES | 96 | 84.38% | 0.9219 | 77.08% | 91.67% | 84.38% |

## By year

No non-empty values in the selected test split(s).

## Notes

- Metrics are pair-level. Positive recall is TPR; negative recall is TNR.
- AUC is undefined for single-class groups and is shown as —.
- R@1 was not computed (pass `--r-at-1` to enable it).
