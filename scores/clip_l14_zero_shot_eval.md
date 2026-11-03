# Evaluation report

- Pairs: `docs/mini_version/pairs.csv`
- Scores: `scores/clip_l14_zero_shot.csv`
- Selection: `val` / `accuracy`
- Rule: `score >= threshold`
- Threshold: `0.26010886`
- Test splits: `test`
- Pairs: val 1161, test 1188
- Excluded pairs: cross-split image: 145 (test 8, train 119, val 18)
- Confidence intervals: 1000 cluster-bootstrap resamples by text_source_item (seed 0); shown for test overall and per-test-split rows.

## Validation

| Split | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | N1 recall | N2 recall | N3 recall | R@1 |
|---|---|---|---|---|---|---|---|---|---|---|
| val | 1161 | 79.76% | 0.8703 | 81.04% | 79.12% | 80.08% | 96.92% | 61.14% | — | 77.33% |

## Main results

| Split | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | N1 recall | N2 recall | N3 recall | R@1 |
|---|---|---|---|---|---|---|---|---|---|---|
| All selected | 1188 | 76.85% [74.77%, 79.04%] | 0.8572 [0.8406, 0.8740] | 75.95% [71.79%, 80.15%] | 77.30% [74.69%, 79.97%] | 76.63% [74.35%, 79.01%] | 95.96% | 58.69% | — | 74.36% [70.15%, 78.32%] |

## By negative type

| neg_type | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | R@1 |
|---|---|---|---|---|---|---|---|
| N1 | 396 | 95.96% | — | — | 95.96% | — | — |
| N2 | 397 | 58.69% | — | — | 58.69% | — | — |
| pos | 395 | 75.95% | — | 75.95% | — | — | — |

## By category

| Category | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | R@1 |
|---|---|---|---|---|---|---|---|
| AV_FURNITURE | 2 | 100.00% | 1.0000 | 100.00% | 100.00% | 100.00% | — |
| BED | 60 | 80.00% | 0.8413 | 80.00% | 80.00% | 80.00% | 65.00% |
| BED_FRAME | 4 | 75.00% | 1.0000 | 0.00% | 100.00% | 50.00% | — |
| BENCH | 24 | 66.67% | 0.7969 | 87.50% | 56.25% | 71.88% | 62.50% |
| CABINET | 15 | 100.00% | 1.0000 | 100.00% | 100.00% | 100.00% | 100.00% |
| CHAIR | 401 | 79.30% | 0.8866 | 77.61% | 80.15% | 78.88% | 80.92% |
| DESK | 18 | 88.89% | 0.9583 | 66.67% | 100.00% | 83.33% | 83.33% |
| DRESSER | 6 | 66.67% | 1.0000 | 0.00% | 100.00% | 50.00% | 100.00% |
| HEADBOARD | 57 | 75.44% | 0.7950 | 73.68% | 76.32% | 75.00% | 68.42% |
| OTTOMAN | 86 | 79.07% | 0.8842 | 82.14% | 77.59% | 79.86% | 78.57% |
| SHELF | 39 | 82.05% | 0.8432 | 61.54% | 92.31% | 76.92% | 69.23% |
| SOFA | 252 | 68.25% | 0.8014 | 77.38% | 63.69% | 70.54% | 64.29% |
| STOOL_SEATING | 65 | 75.38% | 0.8431 | 85.71% | 70.45% | 78.08% | 76.19% |
| TABLE | 159 | 79.87% | 0.8820 | 66.04% | 86.79% | 76.42% | 75.47% |

## By year

No non-empty values in the selected test split(s).

## Notes

- Metrics are pair-level. Positive recall is TPR; negative recall is TNR.
- AUC is undefined for single-class groups and is shown as —.
- R@1 is within-title 3-way ranking: the positive image must outrank the title's own
  N1/N2 images, using complete triplets only and excluding N3 title rewrites.
  It is not global image retrieval; ties count as failures.
