# Reciprocal color N3: development candidates and completed review

This is a separate WP3 development experiment based on ABO home v2 at commit
`32b552c0aa20bdf026403b8ebf29e277c3ca68c6`. It does not replace the frozen
release's pairs, labels, or N1/N2/N3 allocation. `N3R` identifies this
experimental layout; do not feed it to an existing experiment as a silent
replacement for the original N3.

## Completed human review

Yichi reviewed all 80 train candidates independently, including both directions
of each of 40 exchanges. Original judgments and comments are preserved in
`review_completed.csv`; `review_summary.json` is computed from that file.

| Decision | Rows |
|---|---:|
| Clear mismatch | 68 |
| Still matches (candidate false negative) | 2 |
| Uncertain | 10 |
| Pending | 0 |

`retained_complete_exchanges.csv` contains **60 candidates / 30 exchanges**.
Both directions must independently be marked mismatch for an exchange to be
retained. Eight individually accepted rows are held out because their reverse
direction was not accepted. No judgment is changed to keep an exchange intact.
These are one reviewer's judgments, not independently adjudicated ground truth.

Uncertain cases include gray versus ivory/cream/tan/white, white versus silver,
and a multicolor table. This version's metadata/color-family exclusions do not
resolve every visual ambiguity. Tightening those rules requires a new candidate
version and renewed review, rather than overwriting this batch.

## Construction and scope

- Use only the original v2 `n3_audit.csv` eligibility ledger with full raw-color
  checks, after verifying that its title and color span match the source item.
- Pair within split and product type, with matching recognized brand, title
  material keywords and color-phrase word count. Unknown brand values share an
  `other` bucket, so brand identity is not guaranteed in that bucket.
- Require different groups/images and a conservative color-family contrast.
  Skip unparsed commercial shade modifiers and known positive-input collisions.
- Select disjoint reciprocal exchanges by deterministic greedy matching of
  color-removed title TF-IDF similarity, with a fixed minimum of 0.45. This is
  a context-compatibility heuristic, not model-based negative certification.
- Swap the actual color phrases in both directions; preserve every character
  outside the color span. Source and target color phrase counts (case-insensitive)
  match exactly within each split/category, including the retained subset.

Of 663 eligible train/val sources, this rule produces 84 candidates: 80 train
and 4 val. All train candidates were reviewed; the 4 val candidates remain
unreviewed and are too few for meaningful validation estimates. No new test
candidates or test-model metrics were generated. Most eligible sources cannot
form a compatible reciprocal pair; count is not forced to match other negative
types. Original listing positives remain unverified.

`manifest.json` records generation status as unreviewed candidates; the separate
review summary records subsequent human decisions. `n3_with_positives.csv`
contains original positives plus all 84 generated candidates for diagnostics.
The retained CSV contains only the 60 reviewed negative rows, not a complete
training table. Designing a combined training set remains separate work.

## Text-only development diagnostic

On the exact same 80 train image anchors (160 positive/negative rows), use
5-fold GroupKFold over the 40 exchange IDs, keeping both directions and their
positives together. Fit TF-IDF within each training fold; Logistic Regression
uses a fixed 0.5 threshold. No val/test tuning. The comparison uses old N3
rewrites from the original ledger on those exact anchors.

| Text-only model | Old accuracy | Reciprocal accuracy | Old AUC | Reciprocal AUC |
|---|---:|---:|---:|---:|
| Word TF-IDF + LR | 89.375% | 50.0% | 0.9116 | 0.4929 |
| Character TF-IDF + LR | 90.0% | 47.5% | 0.9351 | 0.4845 |

These small development diagnostics concern all 80 reviewed candidates, not
only the retained 60. They support reduced obvious textual shortcuts, not
absence of every shortcut or final multimodal performance. The 60-row retained
set is not large enough to establish a complete N3 benchmark.

## Reproduce from the repository root

Use the shared environment (numpy, scikit-learn; Pillow for HTML rendering).

```bash
python src/negatives/reciprocal/build_balanced_n3.py --out /tmp/n3-reproduce
python src/negatives/reciprocal/check_text_only.py
python src/negatives/reciprocal/summarize_review.py \
  data/reviews/n3-reciprocal-dev-v1/review_completed.csv \
  --out /tmp/n3-reviewed
python src/negatives/reciprocal/render_review.py \
  --out /tmp/N3_Reciprocal_Review.html
```

The renderer uses the v2 image directory, downloads missing selected public ABO
images, checks their release hashes, and embeds them for offline use. Keep
generated HTML/images outside Git. It supports local progress, full-batch CSV
export and JSON backup/restore. The summarizer rejects changed source fields,
wrong batch IDs, duplicate or missing rows, and invalid decisions.

## Follow-up

The [expanded v2 batch](../n3-reciprocal-expanded-dev-v2/README.md) preserves
this batch, adds 208 non-overlapping train candidates, and records a 100-row
audit. Across both versions, the reviewed subset contains 158 negatives; a
separate 266-row training pool additionally allows 108 explicitly unreviewed
candidates after sample quality control. The known uncertain exchange is
excluded. This changes training inclusion policy, not the original judgments.
