# Evaluation report

- Pairs: `data/releases/abo-ood-v3-20261115-candidate/eval_pairs.csv`
- Scores: `scores/v3_final/clip_full_v3_both_seed0_ood.csv`
- Selection: `fixed`
- Rule: `score >= threshold`
- Threshold: `0.41758221`
- Test splits: `ood_near`, `ood_far`
- Pairs: val 0, test 568
- Confidence intervals: 1000 cluster-bootstrap resamples by image_anchor_group (seed 0); shown for test overall and per-test-split rows.

## Main results

| Split | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | N1 recall | N2 recall | N3 recall |
|---|---|---|---|---|---|---|---|---|---|
| All selected | 568 | 71.13% [67.61%, 74.47%] | 0.7930 [0.7594, 0.8252] | 58.45% [53.17%, 64.08%] | 83.80% [79.23%, 88.03%] | 71.13% [67.61%, 74.47%] | 84.85% | 81.54% | 90.91% |
| ood_far | 292 | 70.55% [65.75%, 74.66%] | 0.8056 [0.7555, 0.8480] | 54.11% [45.89%, 61.64%] | 86.99% [80.82%, 91.78%] | 70.55% [65.75%, 74.66%] | 86.76% | 85.29% | 100.00% |
| ood_near | 276 | 71.74% [67.03%, 76.81%] | 0.7850 [0.7377, 0.8355] | 63.04% [55.07%, 71.74%] | 80.43% [74.64%, 86.96%] | 71.74% [67.03%, 76.81%] | 82.81% | 77.42% | 83.33% |

## Matched-anchor type metrics

| Split | Type | n_pos/n_neg | Clusters | AUC | Pos recall | Neg recall | Balanced | Paired rank | Ties |
|---|---|---|---|---|---|---|---|---|---|
| ood_near | N1 | 64/64 | 64 groups | 0.7734 [0.7016, 0.8457] | 57.81% [45.31%, 70.31%] | 82.81% [73.40%, 90.62%] | 70.31% [61.72%, 78.12%] | 85.94% [76.56%, 93.75%] | 0 |
| ood_near | N2 | 62/62 | 62 groups | 0.7828 [0.7050, 0.8595] | 66.13% [53.23%, 77.42%] | 77.42% [66.13%, 87.10%] | 71.77% [64.52%, 78.23%] | 79.03% [67.74%, 88.71%] | 0 |
| ood_near | N3 | 12/12 | 6 exchanges | 0.8403 [0.6875, 0.9861] | 75.00% [58.33%, 91.67%] | 83.33% [66.67%, 100.00%] | 79.17% [66.67%, 91.67%] | 75.00% [58.33%, 91.67%] | 0 |
| ood_far | N1 | 68/68 | 68 groups | 0.7794 [0.7100, 0.8447] | 50.00% [38.24%, 61.76%] | 86.76% [77.94%, 94.12%] | 68.38% [62.50%, 74.26%] | 80.88% [72.06%, 89.71%] | 0 |
| ood_far | N2 | 68/68 | 68 groups | 0.8099 [0.7415, 0.8757] | 57.35% [45.59%, 69.12%] | 85.29% [76.47%, 92.65%] | 71.32% [64.71%, 78.69%] | 83.82% [75.00%, 92.65%] | 0 |
| ood_far | N3 | 10/10 | 5 exchanges | 0.9200 [0.8100, 1.0000] | 60.00% [50.00%, 80.00%] | 100.00% [100.00%, 100.00%] | 80.00% [75.00%, 90.00%] | 100.00% [100.00%, 100.00%] | 0 |

- Each negative is compared with the positive of its own `anchor_item_id`.
- Paired ranking requires the positive score strictly above its negative; ties count as failures.
- Matched metrics are reported per test split and are not pooled across splits.
- Matched intervals use 1000 cluster resamples (seed 0): N1/N2 image-anchor groups, N3 complete reciprocal exchanges.

## By negative type

| neg_type | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| N1 | 132 | 84.85% | — | — | 84.85% | — |
| N2 | 130 | 81.54% | — | — | 81.54% | — |
| N3 | 22 | 90.91% | — | — | 90.91% | — |
| pos | 284 | 58.45% | — | 58.45% | — | — |

## By category

| Category | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| BOOT | 100 | 72.00% | 0.7624 | 64.00% | 80.00% | 72.00% |
| LAMP | 132 | 79.55% | 0.8666 | 77.27% | 81.82% | 79.55% |
| LIGHT_FIXTURE | 144 | 64.58% | 0.7216 | 50.00% | 79.17% | 64.58% |
| SANDAL | 96 | 65.62% | 0.8030 | 39.58% | 91.67% | 65.62% |
| SHOES | 96 | 73.96% | 0.8507 | 58.33% | 89.58% | 73.96% |

## By year

No non-empty values in the selected test split(s).

## Notes

- Metrics are pair-level. Positive recall is TPR; negative recall is TNR.
- AUC is undefined for single-class groups and is shown as —.
- R@1 was not computed (pass `--r-at-1` to enable it).
