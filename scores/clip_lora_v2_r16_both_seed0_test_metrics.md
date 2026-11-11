# Evaluation report

- Pairs: `data/releases/abo-home-v2-20261103/pairs.csv`
- Scores: `scores/clip_lora_v2_r16_both_seed0_selected_eval.csv`
- Selection: `val` / `accuracy`
- Rule: `score >= threshold`
- Threshold: `0.35701188`
- Test splits: `test`
- Pairs: val 656, test 686
- Confidence intervals: 1000 cluster-bootstrap resamples by image_anchor_group (seed 6740); shown for test overall and per-test-split rows.

## Validation

| Split | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | N1 recall | N2 recall | N3 recall |
|---|---|---|---|---|---|---|---|---|---|
| val | 656 | 94.21% | 0.9757 | 92.99% | 95.43% | 94.21% | 100.00% | 89.52% | 97.50% |

## Main results

| Split | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | N1 recall | N2 recall | N3 recall |
|---|---|---|---|---|---|---|---|---|---|
| All selected | 686 | 93.73% [91.98%, 95.34%] | 0.9788 [0.9703, 0.9873] | 93.59% [91.25%, 95.92%] | 93.88% [91.55%, 96.50%] | 93.73% [91.98%, 95.34%] | 97.66% | 88.28% | 96.55% |

## By negative type

| neg_type | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| N1 | 128 | 97.66% | — | — | 97.66% | — |
| N2 | 128 | 88.28% | — | — | 88.28% | — |
| N3 | 87 | 96.55% | — | — | 96.55% | — |
| pos | 343 | 93.59% | — | 93.59% | — | — |

## By category

| Category | n | Accuracy | AUC | Pos recall | Neg recall | Balanced |
|---|---|---|---|---|---|---|
| CHAIR | 162 | 96.91% | 0.9883 | 96.30% | 97.53% | 96.91% |
| HOME | 22 | 95.45% | 0.9917 | 90.91% | 100.00% | 95.45% |
| HOME_FURNITURE_AND_DECOR | 46 | 91.30% | 0.9811 | 82.61% | 100.00% | 91.30% |
| OTTOMAN | 38 | 92.11% | 0.9945 | 94.74% | 89.47% | 92.11% |
| PILLOW | 30 | 96.67% | 0.9911 | 100.00% | 93.33% | 96.67% |
| RUG | 116 | 91.38% | 0.9738 | 86.21% | 96.55% | 91.38% |
| SOFA | 70 | 90.00% | 0.9722 | 97.14% | 82.86% | 90.00% |
| STOOL_SEATING | 44 | 90.91% | 0.9897 | 95.45% | 86.36% | 90.91% |
| TABLE | 86 | 91.86% | 0.9621 | 93.02% | 90.70% | 91.86% |
| WALL_ART | 72 | 98.61% | 0.9961 | 100.00% | 97.22% | 98.61% |

## By year

No non-empty values in the selected test split(s).

## Notes

- Metrics are pair-level. Positive recall is TPR; negative recall is TNR.
- AUC is undefined for single-class groups and is shown as —.
- R@1 was not computed (pass `--r-at-1` to enable it).
