# Evaluation report

- Pairs: `docs/mini_version/pairs.csv`
- Scores: `scores/align_b_zero_shot.csv`
- Selection: `val` / `accuracy`
- Rule: `score >= threshold`
- Threshold: `0.18577546`
- Test splits: `test`
- Pairs: val 1161, test 1188
- Excluded pairs: cross-split image: 145 (test 8, train 119, val 18)
- Confidence intervals: 1000 cluster-bootstrap resamples by text_source_item (seed 0); shown for test overall and per-test-split rows.

## Validation

| Split | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | N1 recall | N2 recall | N3 recall | R@1 |
|---|---|---|---|---|---|---|---|---|---|---|
| val | 1161 | 84.32% | 0.9233 | 86.49% | 83.25% | 84.87% | 98.97% | 67.36% | — | 86.13% |

## Main results

| Split | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | N1 recall | N2 recall | N3 recall | R@1 |
|---|---|---|---|---|---|---|---|---|---|---|
| All selected | 1188 | 81.82% [79.83%, 83.70%] | 0.9062 [0.8922, 0.9198] | 85.82% [82.28%, 89.17%] | 79.82% [77.45%, 82.38%] | 82.82% [80.74%, 84.71%] | 98.99% | 60.71% | — | 83.85% [80.25%, 87.40%] |

## By negative type

| neg_type | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | R@1 |
|---|---|---|---|---|---|---|---|
| N1 | 396 | 98.99% | — | — | 98.99% | — | — |
| N2 | 397 | 60.71% | — | — | 60.71% | — | — |
| pos | 395 | 85.82% | — | 85.82% | — | — | — |

## By category

| Category | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | R@1 |
|---|---|---|---|---|---|---|---|
| AV_FURNITURE | 2 | 100.00% | 1.0000 | 100.00% | 100.00% | 100.00% | — |
| BED | 60 | 81.67% | 0.9388 | 85.00% | 80.00% | 82.50% | 95.00% |
| BED_FRAME | 4 | 75.00% | 1.0000 | 100.00% | 66.67% | 83.33% | — |
| BENCH | 24 | 70.83% | 0.8750 | 75.00% | 68.75% | 71.88% | 75.00% |
| CABINET | 15 | 100.00% | 1.0000 | 100.00% | 100.00% | 100.00% | 100.00% |
| CHAIR | 401 | 85.54% | 0.9265 | 91.04% | 82.77% | 86.91% | 87.02% |
| DESK | 18 | 77.78% | 1.0000 | 33.33% | 100.00% | 66.67% | 100.00% |
| DRESSER | 6 | 100.00% | 1.0000 | 100.00% | 100.00% | 100.00% | 100.00% |
| HEADBOARD | 57 | 70.18% | 0.8213 | 84.21% | 63.16% | 73.68% | 73.68% |
| OTTOMAN | 86 | 82.56% | 0.9409 | 96.43% | 75.86% | 86.15% | 92.86% |
| SHELF | 39 | 84.62% | 0.8994 | 84.62% | 84.62% | 84.62% | 76.92% |
| SOFA | 252 | 74.60% | 0.8530 | 84.52% | 69.64% | 77.08% | 72.62% |
| STOOL_SEATING | 65 | 78.46% | 0.8820 | 85.71% | 75.00% | 80.36% | 85.71% |
| TABLE | 159 | 88.05% | 0.9521 | 75.47% | 94.34% | 84.91% | 86.79% |

## By year

No non-empty values in the selected test split(s).

## Notes

- Metrics are pair-level. Positive recall is TPR; negative recall is TNR.
- AUC is undefined for single-class groups and is shown as —.
- R@1 is within-title 3-way ranking: the positive image must outrank the title's own
  N1/N2 images, using complete triplets only and excluding N3 title rewrites.
  It is not global image retrieval; ties count as failures.
