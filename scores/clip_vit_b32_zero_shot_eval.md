# Evaluation report

- Pairs: `docs/mini_version/pairs.csv`
- Scores: `scores/clip_vit_b32_zero_shot.csv`
- Selection: `val` / `accuracy`
- Rule: `score >= threshold`
- Threshold: `0.30781579`
- Test splits: `test`
- Pairs: val 1161, test 1188
- Excluded pairs: cross-split image: 145 (test 8, train 119, val 18)
- Confidence intervals: 1000 cluster-bootstrap resamples by text-source item (seed 0); shown for test overall and per-test-split rows.

## Validation

| Split | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | N1 recall | N2 recall | N3 recall | R@1 |
|---|---|---|---|---|---|---|---|---|---|---|
| val | 1161 | 76.57% | 0.8423 | 75.84% | 76.93% | 76.39% | 95.13% | 58.55% | — | 72.47% |

## Main results

| Split | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | N1 recall | N2 recall | N3 recall | R@1 |
|---|---|---|---|---|---|---|---|---|---|---|
| All selected | 1188 | 75.51% [73.45%, 77.68%] | 0.8352 [0.8191, 0.8531] | 76.96% [72.89%, 81.22%] | 74.78% [71.86%, 77.58%] | 75.87% [73.73%, 78.13%] | 93.43% | 56.17% | — | 75.95% [72.93%, 79.27%] |

## By negative type

| neg_type | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | R@1 |
|---|---|---|---|---|---|---|---|
| N1 | 396 | 93.43% | — | — | 93.43% | — | — |
| N2 | 397 | 56.17% | — | — | 56.17% | — | — |
| pos | 395 | 76.96% | — | 76.96% | — | — | — |

## By category

| Category | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | R@1 |
|---|---|---|---|---|---|---|---|
| AV_FURNITURE | 2 | 100.00% | 1.0000 | 100.00% | 100.00% | 100.00% | 100.00% |
| BED | 60 | 68.33% | 0.8713 | 30.00% | 87.50% | 58.75% | 85.00% |
| BED_FRAME | 4 | 75.00% | 0.6667 | 0.00% | 100.00% | 50.00% | 100.00% |
| BENCH | 24 | 70.83% | 0.8359 | 75.00% | 68.75% | 71.88% | 75.00% |
| CABINET | 15 | 86.67% | 1.0000 | 60.00% | 100.00% | 80.00% | 100.00% |
| CHAIR | 401 | 79.55% | 0.8734 | 73.13% | 82.77% | 77.95% | 81.34% |
| DESK | 18 | 83.33% | 0.9722 | 83.33% | 83.33% | 83.33% | 100.00% |
| DRESSER | 6 | 83.33% | 1.0000 | 50.00% | 100.00% | 75.00% | 100.00% |
| HEADBOARD | 57 | 80.70% | 0.8490 | 63.16% | 89.47% | 76.32% | 84.21% |
| OTTOMAN | 86 | 77.91% | 0.8836 | 96.43% | 68.97% | 82.70% | 71.43% |
| SHELF | 39 | 76.92% | 0.8432 | 69.23% | 80.77% | 75.00% | 76.92% |
| SOFA | 252 | 66.67% | 0.7702 | 90.48% | 54.76% | 72.62% | 63.10% |
| STOOL_SEATING | 65 | 70.77% | 0.8442 | 90.48% | 61.36% | 75.92% | 71.43% |
| TABLE | 159 | 78.62% | 0.8551 | 77.36% | 79.25% | 78.30% | 73.58% |

## By year

No non-empty values in the selected test split(s).

## Notes

- Metrics are pair-level. Positive recall is TPR; negative recall is TNR.
- AUC is undefined for single-class groups and is shown as —.
- R@1 is within-title 3-way ranking: the positive image must outrank the title's own
  N1/N2 images. It is not global image retrieval; ties count as failures.
