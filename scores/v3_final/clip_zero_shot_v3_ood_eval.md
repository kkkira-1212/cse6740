# Evaluation report

- Pairs: `data/releases/abo-ood-v3-20261115-candidate/eval_pairs.csv`
- Scores: `scores/v3_final/clip_zero_shot_v3_ood.csv`
- Selection: `fixed`
- Rule: `score >= threshold`
- Threshold: `0.28604528`
- Test splits: `ood_near`, `ood_far`
- Pairs: val 0, test 568
- Confidence intervals: 1000 cluster-bootstrap resamples by image_anchor_group (seed 0); shown for test overall and per-test-split rows.

## Main results

| Split | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | N1 recall | N2 recall | N3 recall |
|---|---|---|---|---|---|---|---|---|---|
| All selected | 568 | 82.57% [79.75%, 85.39%] | 0.9012 [0.8802, 0.9230] | 91.20% [87.68%, 94.37%] | 73.94% [68.66%, 78.87%] | 82.57% [79.75%, 85.39%] | 88.64% | 63.08% | 50.00% |
| ood_far | 292 | 87.67% [84.25%, 91.10%] | 0.9282 [0.8979, 0.9560] | 90.41% [85.62%, 94.54%] | 84.93% [78.77%, 90.41%] | 87.67% [84.25%, 91.10%] | 94.12% | 77.94% | 70.00% |
| ood_near | 276 | 77.17% [73.19%, 81.16%] | 0.8817 [0.8503, 0.9118] | 92.03% [87.68%, 96.38%] | 62.32% [54.35%, 70.29%] | 77.17% [73.19%, 81.16%] | 82.81% | 46.77% | 33.33% |

## Matched-anchor type metrics

| Split | Type | n_pos/n_neg | Clusters | AUC | Pos recall | Neg recall | Balanced | Paired rank | Ties |
|---|---|---|---|---|---|---|---|---|---|
| ood_near | N1 | 64/64 | 64 groups | 0.9519 [0.9192, 0.9766] | 92.19% [85.94%, 98.44%] | 82.81% [71.88%, 92.19%] | 87.50% [81.25%, 92.97%] | 98.44% [95.31%, 100.00%] | 0 |
| ood_near | N2 | 62/62 | 62 groups | 0.8491 [0.7864, 0.9139] | 93.55% [87.10%, 98.39%] | 46.77% [33.87%, 58.06%] | 70.16% [63.71%, 75.83%] | 91.94% [85.48%, 98.39%] | 0 |
| ood_near | N3 | 12/12 | 6 exchanges | 0.8264 [0.7568, 0.9444] | 83.33% [66.67%, 100.00%] | 33.33% [16.67%, 50.00%] | 58.33% [50.00%, 66.67%] | 100.00% [100.00%, 100.00%] | 0 |
| ood_far | N1 | 68/68 | 68 groups | 0.9717 [0.9403, 0.9948] | 91.18% [83.82%, 97.06%] | 94.12% [86.76%, 98.53%] | 92.65% [88.24%, 96.32%] | 98.53% [95.59%, 100.00%] | 0 |
| ood_far | N2 | 68/68 | 68 groups | 0.8875 [0.8313, 0.9414] | 88.24% [80.88%, 95.59%] | 77.94% [67.65%, 86.80%] | 83.09% [76.47%, 88.97%] | 88.24% [80.88%, 95.59%] | 0 |
| ood_far | N3 | 10/10 | 5 exchanges | 0.9600 [0.8800, 1.0000] | 100.00% [100.00%, 100.00%] | 70.00% [50.00%, 90.00%] | 85.00% [75.00%, 95.00%] | 100.00% [100.00%, 100.00%] | 0 |

- Each negative is compared with the positive of its own `anchor_item_id`.
- Paired ranking requires the positive score strictly above its negative; ties count as failures.
- Matched metrics are reported per test split and are not pooled across splits.
- Matched intervals use 1000 cluster resamples (seed 0): N1/N2 image-anchor groups, N3 complete reciprocal exchanges.

## By negative type

| neg_type | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| N1 | 132 | 88.64% | — | — | 88.64% | — |
| N2 | 130 | 63.08% | — | — | 63.08% | — |
| N3 | 22 | 50.00% | — | — | 50.00% | — |
| pos | 284 | 91.20% | — | 91.20% | — | — |

## By category

| Category | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| BOOT | 100 | 91.00% | 0.9340 | 94.00% | 88.00% | 91.00% |
| LAMP | 132 | 75.76% | 0.9157 | 95.45% | 56.06% | 75.76% |
| LIGHT_FIXTURE | 144 | 78.47% | 0.8592 | 88.89% | 68.06% | 78.47% |
| SANDAL | 96 | 86.46% | 0.8928 | 93.75% | 79.17% | 86.46% |
| SHOES | 96 | 85.42% | 0.9514 | 83.33% | 87.50% | 85.42% |

## By year

No non-empty values in the selected test split(s).

## Notes

- Metrics are pair-level. Positive recall is TPR; negative recall is TNR.
- AUC is undefined for single-class groups and is shown as —.
- R@1 was not computed (pass `--r-at-1` to enable it).
