# Evaluation report

- Pairs: `docs/mini_version/pairs.csv`
- Scores: `scores/blip_itm_b_zero_shot.csv`
- Selection: `val` / `accuracy`
- Rule: `score >= threshold`
- Threshold: `0.75372261`
- Test splits: `test`
- Pairs: val 1161, test 1188
- Excluded pairs: cross-split image: 145 (test 8, train 119, val 18)
- Confidence intervals: 1000 cluster-bootstrap resamples by text_source_item (seed 0); shown for test overall and per-test-split rows.

## Validation

| Split | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | N1 recall | N2 recall | N3 recall | R@1 |
|---|---|---|---|---|---|---|---|---|---|---|
| val | 1161 | 86.56% | 0.9310 | 86.23% | 86.73% | 86.48% | 99.23% | 74.09% | — | 88.00% |

## Main results

| Split | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | N1 recall | N2 recall | N3 recall | R@1 |
|---|---|---|---|---|---|---|---|---|---|---|
| All selected | 1188 | 84.34% [82.55%, 86.23%] | 0.9184 [0.9061, 0.9310] | 83.80% [80.20%, 87.37%] | 84.62% [82.37%, 87.00%] | 84.21% [82.12%, 86.21%] | 99.49% | 69.77% | — | 85.38% [82.08%, 88.78%] |

## By negative type

| neg_type | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | R@1 |
|---|---|---|---|---|---|---|---|
| N1 | 396 | 99.49% | — | — | 99.49% | — | — |
| N2 | 397 | 69.77% | — | — | 69.77% | — | — |
| pos | 395 | 83.80% | — | 83.80% | — | — | — |

## By category

| Category | n | Accuracy | AUC | Pos recall | Neg recall | Balanced | R@1 |
|---|---|---|---|---|---|---|---|
| AV_FURNITURE | 2 | 100.00% | 1.0000 | 100.00% | 100.00% | 100.00% | — |
| BED | 60 | 86.67% | 0.9263 | 70.00% | 95.00% | 82.50% | 80.00% |
| BED_FRAME | 4 | 75.00% | 1.0000 | 100.00% | 66.67% | 83.33% | — |
| BENCH | 24 | 75.00% | 0.8906 | 75.00% | 75.00% | 75.00% | 75.00% |
| CABINET | 15 | 100.00% | 1.0000 | 100.00% | 100.00% | 100.00% | 100.00% |
| CHAIR | 401 | 86.53% | 0.9276 | 91.04% | 84.27% | 87.66% | 87.02% |
| DESK | 18 | 94.44% | 1.0000 | 83.33% | 100.00% | 91.67% | 100.00% |
| DRESSER | 6 | 100.00% | 1.0000 | 100.00% | 100.00% | 100.00% | 100.00% |
| HEADBOARD | 57 | 78.95% | 0.9127 | 68.42% | 84.21% | 76.32% | 100.00% |
| OTTOMAN | 86 | 84.88% | 0.9433 | 89.29% | 82.76% | 86.02% | 85.71% |
| SHELF | 39 | 87.18% | 0.9053 | 76.92% | 92.31% | 84.62% | 76.92% |
| SOFA | 252 | 77.78% | 0.8671 | 76.19% | 78.57% | 77.38% | 76.19% |
| STOOL_SEATING | 65 | 86.15% | 0.9340 | 90.48% | 84.09% | 87.28% | 95.24% |
| TABLE | 159 | 86.79% | 0.9231 | 83.02% | 88.68% | 85.85% | 88.68% |

## By year

No non-empty values in the selected test split(s).

## Notes

- Metrics are pair-level. Positive recall is TPR; negative recall is TNR.
- AUC is undefined for single-class groups and is shown as —.
- R@1 is within-title 3-way ranking: the positive image must outrank the title's own
  N1/N2 images, using complete triplets only and excluding N3 title rewrites.
  It is not global image retrieval; ties count as failures.
