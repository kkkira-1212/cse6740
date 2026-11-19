# Evaluation report

- Pairs: `data/releases/abo-ood-v3-20261115-candidate/eval_pairs.csv`
- Scores: `scores/v3_final/clip_full_v3_both_seed1_ood.csv`
- Selection: `fixed`
- Rule: `score >= threshold`
- Threshold: `0.42112321`
- Test splits: `ood_near`, `ood_far`
- Pairs: val 0, test 568
- Confidence intervals: 1000 cluster-bootstrap resamples by image_anchor_group (seed 0); shown for test overall and per-test-split rows.

## Main results

| Split | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | N1 recall | N2 recall | N3 recall |
|---|---|---|---|---|---|---|---|---|---|
| All selected | 568 | 69.54% [65.67%, 73.24%] | 0.7825 [0.7472, 0.8163] | 55.28% [49.30%, 60.92%] | 83.80% [79.58%, 88.03%] | 69.54% [65.67%, 73.24%] | 82.58% | 84.62% | 86.36% |
| ood_far | 292 | 67.12% [61.99%, 71.92%] | 0.8017 [0.7498, 0.8478] | 44.52% [36.28%, 52.74%] | 89.73% [84.25%, 93.84%] | 67.12% [61.99%, 71.92%] | 85.29% | 92.65% | 100.00% |
| ood_near | 276 | 72.10% [66.67%, 77.17%] | 0.7838 [0.7289, 0.8331] | 66.67% [59.42%, 74.64%] | 77.54% [70.29%, 84.06%] | 72.10% [66.67%, 77.17%] | 79.69% | 75.81% | 75.00% |

## Matched-anchor type metrics

| Split | Type | n_pos/n_neg | Clusters | AUC | Pos recall | Neg recall | Balanced | Paired rank | Ties |
|---|---|---|---|---|---|---|---|---|---|
| ood_near | N1 | 64/64 | 64 groups | 0.7812 [0.6953, 0.8555] | 62.50% [50.00%, 75.00%] | 79.69% [68.75%, 89.06%] | 71.09% [63.28%, 78.91%] | 84.38% [75.00%, 92.19%] | 0 |
| ood_near | N2 | 62/62 | 62 groups | 0.7685 [0.6943, 0.8408] | 66.13% [54.84%, 77.42%] | 75.81% [64.52%, 85.48%] | 70.97% [62.90%, 77.44%] | 77.42% [66.13%, 87.10%] | 0 |
| ood_near | N3 | 12/12 | 6 exchanges | 0.8611 [0.7083, 1.0000] | 91.67% [75.00%, 100.00%] | 75.00% [58.33%, 91.67%] | 83.33% [66.67%, 95.83%] | 83.33% [66.67%, 100.00%] | 0 |
| ood_far | N1 | 68/68 | 68 groups | 0.7790 [0.7093, 0.8449] | 42.65% [30.88%, 54.41%] | 85.29% [76.47%, 92.65%] | 63.97% [56.62%, 70.59%] | 75.00% [64.71%, 85.29%] | 0 |
| ood_far | N2 | 68/68 | 68 groups | 0.7978 [0.7256, 0.8653] | 44.12% [32.35%, 57.35%] | 92.65% [85.29%, 98.53%] | 68.38% [61.76%, 75.74%] | 79.41% [70.59%, 88.24%] | 0 |
| ood_far | N3 | 10/10 | 5 exchanges | 0.9000 [0.8000, 1.0000] | 60.00% [50.00%, 80.00%] | 100.00% [100.00%, 100.00%] | 80.00% [75.00%, 90.00%] | 100.00% [100.00%, 100.00%] | 0 |

- Each negative is compared with the positive of its own `anchor_item_id`.
- Paired ranking requires the positive score strictly above its negative; ties count as failures.
- Matched metrics are reported per test split and are not pooled across splits.
- Matched intervals use 1000 cluster resamples (seed 0): N1/N2 image-anchor groups, N3 complete reciprocal exchanges.

## By negative type

| neg_type | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| N1 | 132 | 82.58% | — | — | 82.58% | — |
| N2 | 130 | 84.62% | — | — | 84.62% | — |
| N3 | 22 | 86.36% | — | — | 86.36% | — |
| pos | 284 | 55.28% | — | 55.28% | — | — |

## By category

| Category | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| BOOT | 100 | 62.00% | 0.7588 | 40.00% | 84.00% | 62.00% |
| LAMP | 132 | 79.55% | 0.8671 | 81.82% | 77.27% | 79.55% |
| LIGHT_FIXTURE | 144 | 65.28% | 0.7242 | 52.78% | 77.78% | 65.28% |
| SANDAL | 96 | 66.67% | 0.8043 | 41.67% | 91.67% | 66.67% |
| SHOES | 96 | 72.92% | 0.8346 | 52.08% | 93.75% | 72.92% |

## By year

No non-empty values in the selected test split(s).

## Notes

- Metrics are pair-level. Positive recall is TPR; negative recall is TNR.
- AUC is undefined for single-class groups and is shown as —.
- R@1 was not computed (pass `--r-at-1` to enable it).
