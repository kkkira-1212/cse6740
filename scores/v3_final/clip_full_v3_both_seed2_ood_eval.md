# Evaluation report

- Pairs: `data/releases/abo-ood-v3-20261115-candidate/eval_pairs.csv`
- Scores: `scores/v3_final/clip_full_v3_both_seed2_ood.csv`
- Selection: `fixed`
- Rule: `score >= threshold`
- Threshold: `0.47414356`
- Test splits: `ood_near`, `ood_far`
- Pairs: val 0, test 568
- Confidence intervals: 1000 cluster-bootstrap resamples by image_anchor_group (seed 0); shown for test overall and per-test-split rows.

## Main results

| Split | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | N1 recall | N2 recall | N3 recall |
|---|---|---|---|---|---|---|---|---|---|
| All selected | 568 | 67.78% [63.91%, 71.30%] | 0.7887 [0.7532, 0.8214] | 50.35% [44.37%, 55.99%] | 85.21% [80.99%, 89.08%] | 67.78% [63.91%, 71.30%] | 86.36% | 82.31% | 95.45% |
| ood_far | 292 | 65.41% [60.27%, 69.52%] | 0.8098 [0.7560, 0.8530] | 39.73% [30.82%, 47.26%] | 91.10% [86.30%, 95.21%] | 65.41% [60.27%, 69.52%] | 91.18% | 89.71% | 100.00% |
| ood_near | 276 | 70.29% [65.22%, 75.36%] | 0.7936 [0.7428, 0.8437] | 61.59% [53.62%, 69.57%] | 78.99% [71.74%, 85.53%] | 70.29% [65.22%, 75.36%] | 81.25% | 74.19% | 91.67% |

## Matched-anchor type metrics

| Split | Type | n_pos/n_neg | Clusters | AUC | Pos recall | Neg recall | Balanced | Paired rank | Ties |
|---|---|---|---|---|---|---|---|---|---|
| ood_near | N1 | 64/64 | 64 groups | 0.7754 [0.6995, 0.8494] | 54.69% [42.19%, 67.19%] | 81.25% [71.84%, 90.62%] | 67.97% [60.16%, 75.78%] | 79.69% [70.31%, 89.06%] | 0 |
| ood_near | N2 | 62/62 | 62 groups | 0.7781 [0.7032, 0.8507] | 62.90% [51.61%, 74.19%] | 74.19% [62.90%, 83.91%] | 68.55% [61.29%, 75.83%] | 80.65% [70.97%, 90.32%] | 0 |
| ood_near | N3 | 12/12 | 6 exchanges | 0.9722 [0.9302, 1.0000] | 91.67% [75.00%, 100.00%] | 91.67% [75.00%, 100.00%] | 91.67% [83.33%, 100.00%] | 100.00% [100.00%, 100.00%] | 0 |
| ood_far | N1 | 68/68 | 68 groups | 0.7868 [0.7076, 0.8573] | 33.82% [22.06%, 45.59%] | 91.18% [83.82%, 97.06%] | 62.50% [55.88%, 69.12%] | 80.88% [70.59%, 89.71%] | 0 |
| ood_far | N2 | 68/68 | 68 groups | 0.8129 [0.7402, 0.8785] | 41.18% [29.41%, 52.94%] | 89.71% [82.35%, 95.59%] | 65.44% [59.56%, 72.06%] | 79.41% [69.12%, 88.27%] | 0 |
| ood_far | N3 | 10/10 | 5 exchanges | 0.9200 [0.7600, 1.0000] | 70.00% [50.00%, 90.00%] | 100.00% [100.00%, 100.00%] | 85.00% [75.00%, 95.00%] | 100.00% [100.00%, 100.00%] | 0 |

- Each negative is compared with the positive of its own `anchor_item_id`.
- Paired ranking requires the positive score strictly above its negative; ties count as failures.
- Matched metrics are reported per test split and are not pooled across splits.
- Matched intervals use 1000 cluster resamples (seed 0): N1/N2 image-anchor groups, N3 complete reciprocal exchanges.

## By negative type

| neg_type | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| N1 | 132 | 86.36% | — | — | 86.36% | — |
| N2 | 130 | 82.31% | — | — | 82.31% | — |
| N3 | 22 | 95.45% | — | — | 95.45% | — |
| pos | 284 | 50.35% | — | 50.35% | — | — |

## By category

| Category | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| BOOT | 100 | 63.00% | 0.7800 | 42.00% | 84.00% | 63.00% |
| LAMP | 132 | 75.76% | 0.8526 | 74.24% | 77.27% | 75.76% |
| LIGHT_FIXTURE | 144 | 65.28% | 0.7535 | 50.00% | 80.56% | 65.28% |
| SANDAL | 96 | 63.54% | 0.7943 | 33.33% | 93.75% | 63.54% |
| SHOES | 96 | 69.79% | 0.8581 | 43.75% | 95.83% | 69.79% |

## By year

No non-empty values in the selected test split(s).

## Notes

- Metrics are pair-level. Positive recall is TPR; negative recall is TNR.
- AUC is undefined for single-class groups and is shown as —.
- R@1 was not computed (pass `--r-at-1` to enable it).
