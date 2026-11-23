# Evaluation report

- Pairs: `data/releases/abo-home-reciprocal-v3-candidate/pairs.csv`
- Scores: `scores/v3_final/clip_lora_v3_r16_both_seed0_id.csv`
- Selection: `fixed`
- Rule: `score >= threshold`
- Threshold: `0.36369967`
- Test splits: `test`
- Pairs: val 656, test 686
- Validation metrics omitted: not all validation pairs have scores.
- Confidence intervals: 1000 cluster-bootstrap resamples by image_anchor_group (seed 0); shown for test overall and per-test-split rows.

## Main results

| Split | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | N1 recall | N2 recall | N3 recall |
|---|---|---|---|---|---|---|---|---|---|
| All selected | 686 | 92.71% [90.82%, 94.46%] | 0.9789 [0.9707, 0.9865] | 91.84% [88.63%, 94.75%] | 93.59% [90.96%, 95.92%] | 92.71% [90.82%, 94.46%] | 98.08% | 89.17% | 93.33% |

## Matched-anchor type metrics

| Split | Type | n_pos/n_neg | Clusters | AUC | Pos recall | Neg recall | Balanced | Paired rank | Ties |
|---|---|---|---|---|---|---|---|---|---|
| test | N1 | 156/156 | 156 groups | 0.9938 [0.9852, 0.9996] | 90.38% [85.26%, 94.87%] | 98.08% [95.51%, 100.00%] | 94.23% [91.67%, 96.47%] | 99.36% [98.08%, 100.00%] | 0 |
| test | N2 | 157/157 | 157 groups | 0.9586 [0.9394, 0.9766] | 91.72% [87.26%, 95.54%] | 89.17% [84.08%, 94.27%] | 90.45% [87.26%, 93.63%] | 99.36% [98.09%, 100.00%] | 0 |
| test | N3 | 30/30 | 15 exchanges | 1.0000 [1.0000, 1.0000] | 100.00% [100.00%, 100.00%] | 93.33% [83.33%, 100.00%] | 96.67% [91.67%, 100.00%] | 100.00% [100.00%, 100.00%] | 0 |

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
| pos | 343 | 91.84% | — | 91.84% | — | — |

## By category

| Category | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| CHAIR | 162 | 94.44% | 0.9854 | 95.06% | 93.83% | 94.44% |
| HOME | 22 | 95.45% | 0.9917 | 90.91% | 100.00% | 95.45% |
| HOME_FURNITURE_AND_DECOR | 46 | 89.13% | 0.9849 | 78.26% | 100.00% | 89.13% |
| OTTOMAN | 38 | 94.74% | 0.9972 | 94.74% | 94.74% | 94.74% |
| PILLOW | 30 | 93.33% | 0.9867 | 100.00% | 86.67% | 93.33% |
| RUG | 116 | 88.79% | 0.9753 | 81.03% | 96.55% | 88.79% |
| SOFA | 70 | 90.00% | 0.9780 | 97.14% | 82.86% | 90.00% |
| STOOL_SEATING | 44 | 93.18% | 0.9917 | 95.45% | 90.91% | 93.18% |
| TABLE | 86 | 93.02% | 0.9616 | 93.02% | 93.02% | 93.02% |
| WALL_ART | 72 | 97.22% | 0.9961 | 97.22% | 97.22% | 97.22% |

## By year

No non-empty values in the selected test split(s).

## Notes

- Metrics are pair-level. Positive recall is TPR; negative recall is TNR.
- AUC is undefined for single-class groups and is shown as —.
- R@1 was not computed (pass `--r-at-1` to enable it).
