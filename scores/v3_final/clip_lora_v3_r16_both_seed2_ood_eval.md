# Evaluation report

- Pairs: `data/releases/abo-ood-v3-20261115-candidate/eval_pairs.csv`
- Scores: `scores/v3_final/clip_lora_v3_r16_both_seed2_ood.csv`
- Selection: `fixed`
- Rule: `score >= threshold`
- Threshold: `0.37085807`
- Test splits: `ood_near`, `ood_far`
- Pairs: val 0, test 568
- Confidence intervals: 1000 cluster-bootstrap resamples by image_anchor_group (seed 0); shown for test overall and per-test-split rows.

## Main results

| Split | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | N1 recall | N2 recall | N3 recall |
|---|---|---|---|---|---|---|---|---|---|
| All selected | 568 | 83.27% [80.28%, 86.27%] | 0.9025 [0.8791, 0.9245] | 77.11% [72.54%, 82.39%] | 89.44% [85.92%, 92.96%] | 83.27% [80.28%, 86.27%] | 94.70% | 82.31% | 100.00% |
| ood_far | 292 | 82.19% [78.07%, 86.30%] | 0.9050 [0.8691, 0.9337] | 72.60% [65.07%, 79.45%] | 91.78% [86.99%, 95.89%] | 82.19% [78.07%, 86.30%] | 95.59% | 86.76% | 100.00% |
| ood_near | 276 | 84.42% [80.43%, 88.41%] | 0.9059 [0.8753, 0.9373] | 81.88% [75.36%, 88.41%] | 86.96% [81.16%, 92.75%] | 84.42% [80.43%, 88.41%] | 93.75% | 77.42% | 100.00% |

## Matched-anchor type metrics

| Split | Type | n_pos/n_neg | Clusters | AUC | Pos recall | Neg recall | Balanced | Paired rank | Ties |
|---|---|---|---|---|---|---|---|---|---|
| ood_near | N1 | 64/64 | 64 groups | 0.9456 [0.9060, 0.9751] | 75.00% [64.06%, 85.94%] | 93.75% [85.94%, 98.44%] | 84.38% [78.91%, 89.84%] | 93.75% [87.50%, 98.44%] | 0 |
| ood_near | N2 | 62/62 | 62 groups | 0.8535 [0.7937, 0.9129] | 85.48% [75.81%, 93.55%] | 77.42% [66.13%, 87.10%] | 81.45% [75.00%, 87.90%] | 93.55% [87.10%, 98.39%] | 0 |
| ood_near | N3 | 12/12 | 6 exchanges | 1.0000 [1.0000, 1.0000] | 100.00% [100.00%, 100.00%] | 100.00% [100.00%, 100.00%] | 100.00% [100.00%, 100.00%] | 100.00% [100.00%, 100.00%] | 0 |
| ood_far | N1 | 68/68 | 68 groups | 0.9299 [0.8852, 0.9658] | 72.06% [61.76%, 82.35%] | 95.59% [89.71%, 100.00%] | 83.82% [77.94%, 89.71%] | 94.12% [88.24%, 98.53%] | 0 |
| ood_far | N2 | 68/68 | 68 groups | 0.8787 [0.8235, 0.9310] | 73.53% [63.24%, 83.82%] | 86.76% [77.94%, 94.12%] | 80.15% [73.53%, 86.76%] | 88.24% [80.88%, 95.59%] | 0 |
| ood_far | N3 | 10/10 | 5 exchanges | 0.9000 [0.7800, 1.0000] | 70.00% [50.00%, 90.00%] | 100.00% [100.00%, 100.00%] | 85.00% [75.00%, 95.00%] | 100.00% [100.00%, 100.00%] | 0 |

- Each negative is compared with the positive of its own `anchor_item_id`.
- Paired ranking requires the positive score strictly above its negative; ties count as failures.
- Matched metrics are reported per test split and are not pooled across splits.
- Matched intervals use 1000 cluster resamples (seed 0): N1/N2 image-anchor groups, N3 complete reciprocal exchanges.

## By negative type

| neg_type | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| N1 | 132 | 94.70% | — | — | 94.70% | — |
| N2 | 130 | 82.31% | — | — | 82.31% | — |
| N3 | 22 | 100.00% | — | — | 100.00% | — |
| pos | 284 | 77.11% | — | 77.11% | — | — |

## By category

| Category | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| BOOT | 100 | 85.00% | 0.9196 | 82.00% | 88.00% | 85.00% |
| LAMP | 132 | 87.12% | 0.9541 | 87.88% | 86.36% | 87.12% |
| LIGHT_FIXTURE | 144 | 81.94% | 0.8655 | 76.39% | 87.50% | 81.94% |
| SANDAL | 96 | 76.04% | 0.8750 | 62.50% | 89.58% | 76.04% |
| SHOES | 96 | 85.42% | 0.9266 | 72.92% | 97.92% | 85.42% |

## By year

No non-empty values in the selected test split(s).

## Notes

- Metrics are pair-level. Positive recall is TPR; negative recall is TNR.
- AUC is undefined for single-class groups and is shown as —.
- R@1 was not computed (pass `--r-at-1` to enable it).
