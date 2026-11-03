# Evaluation report

- Pairs: `docs/mini_version/pairs.csv`
- Scores: `scores/siglip_b16_zero_shot.csv`
- Selection: `val` / `accuracy`
- Rule: `score >= threshold`
- Threshold: `0.05825306`
- Test splits: `test`
- Pairs: val 1161, test 1188
- Excluded pairs: cross-split image: 145 (test 8, train 119, val 18)
- Confidence intervals: 1000 cluster-bootstrap resamples by text-source item (seed 0); shown for test overall and per-test-split rows.

## Validation

| Split | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | N1 recall | N2 recall | N3 recall | R@1 |
|---|---|---|---|---|---|---|---|---|---|---|
| val | 1161 | 83.81% | 0.9193 | 88.31% | 81.57% | 84.94% | 98.72% | 64.25% | — | 84.42% |

## Main results

| Split | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | N1 recall | N2 recall | N3 recall | R@1 |
|---|---|---|---|---|---|---|---|---|---|---|
| All selected | 1188 | 83.42% [81.56%, 85.14%] | 0.9149 [0.9013, 0.9282] | 88.61% [85.64%, 91.67%] | 80.83% [78.44%, 83.23%] | 84.72% [82.83%, 86.42%] | 98.99% | 62.72% | — | 86.08% [83.60%, 88.58%] |

## By negative type

| neg_type | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | R@1 |
|---|---|---|---|---|---|---|---|
| N1 | 396 | 98.99% | — | — | 98.99% | — | — |
| N2 | 397 | 62.72% | — | — | 62.72% | — | — |
| pos | 395 | 88.61% | — | 88.61% | — | — | — |

## By category

| Category | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | R@1 |
|---|---|---|---|---|---|---|---|
| AV_FURNITURE | 2 | 100.00% | 1.0000 | 100.00% | 100.00% | 100.00% | 100.00% |
| BED | 60 | 80.00% | 0.9463 | 80.00% | 80.00% | 80.00% | 100.00% |
| BED_FRAME | 4 | 75.00% | 1.0000 | 100.00% | 66.67% | 83.33% | 100.00% |
| BENCH | 24 | 66.67% | 0.8203 | 62.50% | 68.75% | 65.62% | 50.00% |
| CABINET | 15 | 100.00% | 1.0000 | 100.00% | 100.00% | 100.00% | 100.00% |
| CHAIR | 401 | 85.04% | 0.9174 | 91.04% | 82.02% | 86.53% | 88.06% |
| DESK | 18 | 88.89% | 0.9167 | 66.67% | 100.00% | 83.33% | 100.00% |
| DRESSER | 6 | 100.00% | 1.0000 | 100.00% | 100.00% | 100.00% | 100.00% |
| HEADBOARD | 57 | 82.46% | 0.9529 | 100.00% | 73.68% | 86.84% | 94.74% |
| OTTOMAN | 86 | 83.72% | 0.9298 | 89.29% | 81.03% | 85.16% | 85.71% |
| SHELF | 39 | 87.18% | 0.9763 | 84.62% | 88.46% | 86.54% | 92.31% |
| SOFA | 252 | 78.57% | 0.8762 | 88.10% | 73.81% | 80.95% | 77.38% |
| STOOL_SEATING | 65 | 81.54% | 0.9113 | 90.48% | 77.27% | 83.87% | 80.95% |
| TABLE | 159 | 88.05% | 0.9300 | 86.79% | 88.68% | 87.74% | 88.68% |

## By year

No non-empty values in the selected test split(s).

## Notes

- Metrics are pair-level. Positive recall is TPR; negative recall is TNR.
- AUC is undefined for single-class groups and is shown as —.
- R@1 is within-title 3-way ranking: the positive image must outrank the title's own
  N1/N2 images. It is not global image retrieval; ties count as failures.
