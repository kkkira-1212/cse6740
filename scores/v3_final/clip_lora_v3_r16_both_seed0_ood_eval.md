# Evaluation report

- Pairs: `data/releases/abo-ood-v3-20261115-candidate/eval_pairs.csv`
- Scores: `scores/v3_final/clip_lora_v3_r16_both_seed0_ood.csv`
- Selection: `fixed`
- Rule: `score >= threshold`
- Threshold: `0.36369967`
- Test splits: `ood_near`, `ood_far`
- Pairs: val 0, test 568
- Confidence intervals: 1000 cluster-bootstrap resamples by image_anchor_group (seed 0); shown for test overall and per-test-split rows.

## Main results

| Split | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | N1 recall | N2 recall | N3 recall |
|---|---|---|---|---|---|---|---|---|---|
| All selected | 568 | 83.27% [80.11%, 85.92%] | 0.8995 [0.8753, 0.9210] | 81.69% [77.11%, 85.92%] | 84.86% [80.63%, 88.73%] | 83.27% [80.11%, 85.92%] | 90.91% | 76.15% | 100.00% |
| ood_far | 292 | 82.19% [77.74%, 86.30%] | 0.8970 [0.8573, 0.9279] | 76.71% [69.86%, 82.88%] | 87.67% [82.19%, 92.47%] | 82.19% [77.74%, 86.30%] | 89.71% | 83.82% | 100.00% |
| ood_near | 276 | 84.42% [80.43%, 88.41%] | 0.9112 [0.8805, 0.9425] | 86.96% [81.16%, 92.05%] | 81.88% [75.36%, 87.68%] | 84.42% [80.43%, 88.41%] | 92.19% | 67.74% | 100.00% |

## Matched-anchor type metrics

| Split | Type | n_pos/n_neg | Clusters | AUC | Pos recall | Neg recall | Balanced | Paired rank | Ties |
|---|---|---|---|---|---|---|---|---|---|
| ood_near | N1 | 64/64 | 64 groups | 0.9480 [0.9121, 0.9761] | 85.94% [76.56%, 93.75%] | 92.19% [84.38%, 98.44%] | 89.06% [83.59%, 93.75%] | 96.88% [92.19%, 100.00%] | 0 |
| ood_near | N2 | 62/62 | 62 groups | 0.8652 [0.8067, 0.9251] | 85.48% [75.81%, 93.55%] | 67.74% [56.45%, 79.03%] | 76.61% [70.16%, 83.06%] | 95.16% [88.71%, 100.00%] | 0 |
| ood_near | N3 | 12/12 | 6 exchanges | 1.0000 [1.0000, 1.0000] | 100.00% [100.00%, 100.00%] | 100.00% [100.00%, 100.00%] | 100.00% [100.00%, 100.00%] | 100.00% [100.00%, 100.00%] | 0 |
| ood_far | N1 | 68/68 | 68 groups | 0.9176 [0.8659, 0.9581] | 75.00% [64.71%, 85.29%] | 89.71% [80.88%, 95.59%] | 82.35% [76.47%, 88.24%] | 92.65% [85.29%, 98.53%] | 0 |
| ood_far | N2 | 68/68 | 68 groups | 0.8722 [0.8131, 0.9291] | 79.41% [69.12%, 88.24%] | 83.82% [73.53%, 92.65%] | 81.62% [75.00%, 87.50%] | 86.76% [79.41%, 94.12%] | 0 |
| ood_far | N3 | 10/10 | 5 exchanges | 0.9100 [0.7900, 1.0000] | 70.00% [50.00%, 90.00%] | 100.00% [100.00%, 100.00%] | 85.00% [75.00%, 95.00%] | 100.00% [100.00%, 100.00%] | 0 |

- Each negative is compared with the positive of its own `anchor_item_id`.
- Paired ranking requires the positive score strictly above its negative; ties count as failures.
- Matched metrics are reported per test split and are not pooled across splits.
- Matched intervals use 1000 cluster resamples (seed 0): N1/N2 image-anchor groups, N3 complete reciprocal exchanges.

## By negative type

| neg_type | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| N1 | 132 | 90.91% | — | — | 90.91% | — |
| N2 | 130 | 76.15% | — | — | 76.15% | — |
| N3 | 22 | 100.00% | — | — | 100.00% | — |
| pos | 284 | 81.69% | — | 81.69% | — | — |

## By category

| Category | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| BOOT | 100 | 84.00% | 0.9068 | 84.00% | 84.00% | 84.00% |
| LAMP | 132 | 87.88% | 0.9513 | 93.94% | 81.82% | 87.88% |
| LIGHT_FIXTURE | 144 | 81.25% | 0.8785 | 80.56% | 81.94% | 81.25% |
| SANDAL | 96 | 76.04% | 0.8655 | 66.67% | 85.42% | 76.04% |
| SHOES | 96 | 86.46% | 0.9245 | 79.17% | 93.75% | 86.46% |

## By year

No non-empty values in the selected test split(s).

## Notes

- Metrics are pair-level. Positive recall is TPR; negative recall is TNR.
- AUC is undefined for single-class groups and is shown as —.
- R@1 was not computed (pass `--r-at-1` to enable it).
