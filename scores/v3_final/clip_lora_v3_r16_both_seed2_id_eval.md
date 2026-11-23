# Evaluation report

- Pairs: `data/releases/abo-home-reciprocal-v3-candidate/pairs.csv`
- Scores: `scores/v3_final/clip_lora_v3_r16_both_seed2_id.csv`
- Selection: `fixed`
- Rule: `score >= threshold`
- Threshold: `0.37085807`
- Test splits: `test`
- Pairs: val 656, test 686
- Validation metrics omitted: not all validation pairs have scores.
- Confidence intervals: 1000 cluster-bootstrap resamples by image_anchor_group (seed 0); shown for test overall and per-test-split rows.

## Main results

| Split | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | N1 recall | N2 recall | N3 recall |
|---|---|---|---|---|---|---|---|---|---|
| All selected | 686 | 93.15% [91.25%, 94.90%] | 0.9799 [0.9720, 0.9876] | 91.25% [88.05%, 94.46%] | 95.04% [92.71%, 97.38%] | 93.15% [91.25%, 94.90%] | 98.08% | 91.08% | 100.00% |

## Matched-anchor type metrics

| Split | Type | n_pos/n_neg | Clusters | AUC | Pos recall | Neg recall | Balanced | Paired rank | Ties |
|---|---|---|---|---|---|---|---|---|---|
| test | N1 | 156/156 | 156 groups | 0.9953 [0.9885, 0.9997] | 89.74% [84.62%, 94.23%] | 98.08% [95.51%, 100.00%] | 93.91% [91.03%, 96.47%] | 99.36% [98.08%, 100.00%] | 0 |
| test | N2 | 157/157 | 157 groups | 0.9601 [0.9408, 0.9770] | 91.72% [87.26%, 95.54%] | 91.08% [86.62%, 95.54%] | 91.40% [88.54%, 94.27%] | 99.36% [98.09%, 100.00%] | 0 |
| test | N3 | 30/30 | 15 exchanges | 0.9989 [0.9956, 1.0000] | 96.67% [90.00%, 100.00%] | 100.00% [100.00%, 100.00%] | 98.33% [95.00%, 100.00%] | 100.00% [100.00%, 100.00%] | 0 |

- Each negative is compared with the positive of its own `anchor_item_id`.
- Paired ranking requires the positive score strictly above its negative; ties count as failures.
- Matched metrics are reported per test split and are not pooled across splits.
- Matched intervals use 1000 cluster resamples (seed 0): N1/N2 image-anchor groups, N3 complete reciprocal exchanges.

## By negative type

| neg_type | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| N1 | 156 | 98.08% | — | — | 98.08% | — |
| N2 | 157 | 91.08% | — | — | 91.08% | — |
| N3 | 30 | 100.00% | — | — | 100.00% | — |
| pos | 343 | 91.25% | — | 91.25% | — | — |

## By category

| Category | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| CHAIR | 162 | 95.06% | 0.9849 | 92.59% | 97.53% | 95.06% |
| HOME | 22 | 95.45% | 0.9917 | 90.91% | 100.00% | 95.45% |
| HOME_FURNITURE_AND_DECOR | 46 | 86.96% | 0.9887 | 73.91% | 100.00% | 86.96% |
| OTTOMAN | 38 | 94.74% | 0.9972 | 94.74% | 94.74% | 94.74% |
| PILLOW | 30 | 93.33% | 0.9822 | 100.00% | 86.67% | 93.33% |
| RUG | 116 | 90.52% | 0.9798 | 82.76% | 98.28% | 90.52% |
| SOFA | 70 | 90.00% | 0.9820 | 97.14% | 82.86% | 90.00% |
| STOOL_SEATING | 44 | 95.45% | 0.9876 | 95.45% | 95.45% | 95.45% |
| TABLE | 86 | 91.86% | 0.9632 | 90.70% | 93.02% | 91.86% |
| WALL_ART | 72 | 98.61% | 0.9961 | 100.00% | 97.22% | 98.61% |

## By year

No non-empty values in the selected test split(s).

## Notes

- Metrics are pair-level. Positive recall is TPR; negative recall is TNR.
- AUC is undefined for single-class groups and is shown as —.
- R@1 was not computed (pass `--r-at-1` to enable it).
