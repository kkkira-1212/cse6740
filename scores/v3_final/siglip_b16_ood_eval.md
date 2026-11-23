# Evaluation report

- Pairs: `data/releases/abo-ood-v3-20261115-candidate/eval_pairs.csv`
- Scores: `scores/v3_final/siglip_b16_ood.csv`
- Selection: `fixed`
- Rule: `score >= threshold`
- Threshold: `0.04772732`
- Test splits: `ood_near`, `ood_far`
- Pairs: val 0, test 568
- Confidence intervals: 1000 cluster-bootstrap resamples by image_anchor_group (seed 0); shown for test overall and per-test-split rows.

## Main results

| Split | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | N1 recall | N2 recall | N3 recall |
|---|---|---|---|---|---|---|---|---|---|
| All selected | 568 | 91.02% [88.73%, 93.13%] | 0.9675 [0.9553, 0.9788] | 94.72% [91.90%, 97.18%] | 87.32% [83.45%, 91.20%] | 91.02% [88.73%, 93.13%] | 97.73% | 84.62% | 40.91% |
| ood_far | 292 | 89.04% [85.62%, 92.12%] | 0.9632 [0.9417, 0.9802] | 95.89% [92.47%, 98.63%] | 82.19% [75.34%, 88.36%] | 89.04% [85.62%, 92.12%] | 95.59% | 75.00% | 40.00% |
| ood_near | 276 | 93.12% [90.22%, 95.65%] | 0.9823 [0.9702, 0.9917] | 93.48% [89.13%, 97.10%] | 92.75% [88.41%, 96.38%] | 93.12% [90.22%, 95.65%] | 100.00% | 95.16% | 41.67% |

## Matched-anchor type metrics

| Split | Type | n_pos/n_neg | Clusters | AUC | Pos recall | Neg recall | Balanced | Paired rank | Ties |
|---|---|---|---|---|---|---|---|---|---|
| ood_near | N1 | 64/64 | 64 groups | 0.9998 [0.9985, 1.0000] | 93.75% [87.50%, 98.44%] | 100.00% [100.00%, 100.00%] | 96.88% [93.75%, 99.22%] | 100.00% [100.00%, 100.00%] | 0 |
| ood_near | N2 | 62/62 | 62 groups | 0.9891 [0.9755, 0.9974] | 91.94% [85.48%, 98.39%] | 95.16% [88.71%, 100.00%] | 93.55% [89.50%, 97.58%] | 100.00% [100.00%, 100.00%] | 0 |
| ood_near | N3 | 12/12 | 6 exchanges | 0.9236 [0.8681, 1.0000] | 100.00% [100.00%, 100.00%] | 41.67% [16.67%, 66.67%] | 70.83% [58.33%, 83.33%] | 100.00% [100.00%, 100.00%] | 0 |
| ood_far | N1 | 68/68 | 68 groups | 0.9981 [0.9939, 1.0000] | 95.59% [89.71%, 100.00%] | 95.59% [89.71%, 100.00%] | 95.59% [91.91%, 98.53%] | 100.00% [100.00%, 100.00%] | 0 |
| ood_far | N2 | 68/68 | 68 groups | 0.9394 [0.9046, 0.9736] | 95.59% [89.71%, 100.00%] | 75.00% [64.71%, 85.29%] | 85.29% [80.15%, 90.44%] | 97.06% [92.65%, 100.00%] | 0 |
| ood_far | N3 | 10/10 | 5 exchanges | 0.8300 [0.7600, 0.9200] | 100.00% [100.00%, 100.00%] | 40.00% [20.00%, 50.00%] | 70.00% [60.00%, 75.00%] | 100.00% [100.00%, 100.00%] | 0 |

- Each negative is compared with the positive of its own `anchor_item_id`.
- Paired ranking requires the positive score strictly above its negative; ties count as failures.
- Matched metrics are reported per test split and are not pooled across splits.
- Matched intervals use 1000 cluster resamples (seed 0): N1/N2 image-anchor groups, N3 complete reciprocal exchanges.

## By negative type

| neg_type | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| N1 | 132 | 97.73% | — | — | 97.73% | — |
| N2 | 130 | 84.62% | — | — | 84.62% | — |
| N3 | 22 | 40.91% | — | — | 40.91% | — |
| pos | 284 | 94.72% | — | 94.72% | — | — |

## By category

| Category | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| BOOT | 100 | 92.00% | 0.9768 | 98.00% | 86.00% | 92.00% |
| LAMP | 132 | 95.45% | 0.9922 | 95.45% | 95.45% | 95.45% |
| LIGHT_FIXTURE | 144 | 90.97% | 0.9732 | 91.67% | 90.28% | 90.97% |
| SANDAL | 96 | 84.38% | 0.9501 | 95.83% | 72.92% | 84.38% |
| SHOES | 96 | 90.62% | 0.9635 | 93.75% | 87.50% | 90.62% |

## By year

No non-empty values in the selected test split(s).

## Notes

- Metrics are pair-level. Positive recall is TPR; negative recall is TNR.
- AUC is undefined for single-class groups and is shown as —.
- R@1 was not computed (pass `--r-at-1` to enable it).
