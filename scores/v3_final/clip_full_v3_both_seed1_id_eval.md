# Evaluation report

- Pairs: `data/releases/abo-home-reciprocal-v3-candidate/pairs.csv`
- Scores: `scores/v3_final/clip_full_v3_both_seed1_id.csv`
- Selection: `fixed`
- Rule: `score >= threshold`
- Threshold: `0.42112321`
- Test splits: `test`
- Pairs: val 656, test 686
- Validation metrics omitted: not all validation pairs have scores.
- Confidence intervals: 1000 cluster-bootstrap resamples by image_anchor_group (seed 0); shown for test overall and per-test-split rows.

## Main results

| Split | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | N1 recall | N2 recall | N3 recall |
|---|---|---|---|---|---|---|---|---|---|
| All selected | 686 | 94.61% [93.00%, 96.21%] | 0.9869 [0.9805, 0.9927] | 95.63% [93.29%, 97.67%] | 93.59% [90.96%, 96.21%] | 94.61% [93.00%, 96.21%] | 99.36% | 89.81% | 83.33% |

## Matched-anchor type metrics

| Split | Type | n_pos/n_neg | Clusters | AUC | Pos recall | Neg recall | Balanced | Paired rank | Ties |
|---|---|---|---|---|---|---|---|---|---|
| test | N1 | 156/156 | 156 groups | 0.9986 [0.9953, 1.0000] | 96.15% [92.95%, 98.72%] | 99.36% [98.08%, 100.00%] | 97.76% [95.83%, 99.04%] | 100.00% [100.00%, 100.00%] | 0 |
| test | N2 | 157/157 | 157 groups | 0.9737 [0.9569, 0.9874] | 94.27% [90.45%, 97.45%] | 89.81% [85.33%, 94.27%] | 92.04% [89.17%, 94.90%] | 98.73% [96.82%, 100.00%] | 0 |
| test | N3 | 30/30 | 15 exchanges | 1.0000 [1.0000, 1.0000] | 100.00% [100.00%, 100.00%] | 83.33% [70.00%, 93.33%] | 91.67% [85.00%, 96.67%] | 100.00% [100.00%, 100.00%] | 0 |

- Each negative is compared with the positive of its own `anchor_item_id`.
- Paired ranking requires the positive score strictly above its negative; ties count as failures.
- Matched metrics are reported per test split and are not pooled across splits.
- Matched intervals use 1000 cluster resamples (seed 0): N1/N2 image-anchor groups, N3 complete reciprocal exchanges.

## By negative type

| neg_type | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| N1 | 156 | 99.36% | — | — | 99.36% | — |
| N2 | 157 | 89.81% | — | — | 89.81% | — |
| N3 | 30 | 83.33% | — | — | 83.33% | — |
| pos | 343 | 95.63% | — | 95.63% | — | — |

## By category

| Category | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| CHAIR | 162 | 94.44% | 0.9849 | 96.30% | 92.59% | 94.44% |
| HOME | 22 | 90.91% | 0.9835 | 90.91% | 90.91% | 90.91% |
| HOME_FURNITURE_AND_DECOR | 46 | 91.30% | 0.9868 | 86.96% | 95.65% | 91.30% |
| OTTOMAN | 38 | 94.74% | 0.9861 | 100.00% | 89.47% | 94.74% |
| PILLOW | 30 | 96.67% | 1.0000 | 100.00% | 93.33% | 96.67% |
| RUG | 116 | 93.97% | 0.9887 | 91.38% | 96.55% | 93.97% |
| SOFA | 70 | 94.29% | 0.9943 | 100.00% | 88.57% | 94.29% |
| STOOL_SEATING | 44 | 93.18% | 0.9876 | 95.45% | 90.91% | 93.18% |
| TABLE | 86 | 94.19% | 0.9876 | 95.35% | 93.02% | 94.19% |
| WALL_ART | 72 | 100.00% | 1.0000 | 100.00% | 100.00% | 100.00% |

## By year

No non-empty values in the selected test split(s).

## Notes

- Metrics are pair-level. Positive recall is TPR; negative recall is TNR.
- AUC is undefined for single-class groups and is shown as —.
- R@1 was not computed (pass `--r-at-1` to enable it).
