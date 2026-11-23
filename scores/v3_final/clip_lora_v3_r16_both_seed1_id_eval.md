# Evaluation report

- Pairs: `data/releases/abo-home-reciprocal-v3-candidate/pairs.csv`
- Scores: `scores/v3_final/clip_lora_v3_r16_both_seed1_id.csv`
- Selection: `fixed`
- Rule: `score >= threshold`
- Threshold: `0.35778347`
- Test splits: `test`
- Pairs: val 656, test 686
- Validation metrics omitted: not all validation pairs have scores.
- Confidence intervals: 1000 cluster-bootstrap resamples by image_anchor_group (seed 0); shown for test overall and per-test-split rows.

## Main results

| Split | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | N1 recall | N2 recall | N3 recall |
|---|---|---|---|---|---|---|---|---|---|
| All selected | 686 | 93.73% [91.98%, 95.48%] | 0.9798 [0.9722, 0.9873] | 93.88% [91.25%, 96.21%] | 93.59% [90.96%, 96.21%] | 93.73% [91.98%, 95.48%] | 98.08% | 89.17% | 93.33% |

## Matched-anchor type metrics

| Split | Type | n_pos/n_neg | Clusters | AUC | Pos recall | Neg recall | Balanced | Paired rank | Ties |
|---|---|---|---|---|---|---|---|---|---|
| test | N1 | 156/156 | 156 groups | 0.9945 [0.9868, 0.9997] | 93.59% [89.73%, 96.79%] | 98.08% [95.51%, 100.00%] | 95.83% [93.59%, 97.76%] | 99.36% [98.08%, 100.00%] | 0 |
| test | N2 | 157/157 | 157 groups | 0.9612 [0.9429, 0.9778] | 92.99% [88.54%, 96.82%] | 89.17% [84.08%, 93.63%] | 91.08% [87.90%, 93.95%] | 98.73% [96.82%, 100.00%] | 0 |
| test | N3 | 30/30 | 15 exchanges | 0.9967 [0.9889, 1.0000] | 100.00% [100.00%, 100.00%] | 93.33% [83.33%, 100.00%] | 96.67% [91.67%, 100.00%] | 100.00% [100.00%, 100.00%] | 0 |

- Each negative is compared with the positive of its own `anchor_item_id`.
- Paired ranking requires the positive score strictly above its negative; ties count as failures.
- Matched metrics are reported per test split and are not pooled across splits.
- Matched intervals use 1000 cluster resamples (seed 0): N1/N2 image-anchor groups, N3 complete reciprocal exchanges.

## By negative type

| neg_type | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| N1 | 156 | 98.08% | — | — | 98.08% | — |
| N2 | 157 | 89.17% | — | — | 89.17% | — |
| N3 | 30 | 93.33% | — | — | 93.33% | — |
| pos | 343 | 93.88% | — | 93.88% | — | — |

## By category

| Category | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| CHAIR | 162 | 95.68% | 0.9854 | 97.53% | 93.83% | 95.68% |
| HOME | 22 | 90.91% | 0.9917 | 90.91% | 90.91% | 90.91% |
| HOME_FURNITURE_AND_DECOR | 46 | 89.13% | 0.9905 | 78.26% | 100.00% | 89.13% |
| OTTOMAN | 38 | 97.37% | 0.9972 | 100.00% | 94.74% | 97.37% |
| PILLOW | 30 | 93.33% | 0.9733 | 100.00% | 86.67% | 93.33% |
| RUG | 116 | 92.24% | 0.9750 | 87.93% | 96.55% | 92.24% |
| SOFA | 70 | 91.43% | 0.9763 | 97.14% | 85.71% | 91.43% |
| STOOL_SEATING | 44 | 93.18% | 0.9897 | 95.45% | 90.91% | 93.18% |
| TABLE | 86 | 93.02% | 0.9627 | 93.02% | 93.02% | 93.02% |
| WALL_ART | 72 | 97.22% | 0.9969 | 97.22% | 97.22% | 97.22% |

## By year

No non-empty values in the selected test split(s).

## Notes

- Metrics are pair-level. Positive recall is TPR; negative recall is TNR.
- AUC is undefined for single-class groups and is shown as —.
- R@1 was not computed (pass `--r-at-1` to enable it).
