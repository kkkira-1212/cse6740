# Expanded reciprocal N3: audited subset and training pool

This follow-up to the v1 development batch adds **208 new train candidates**,
using images that were not in the previous 80-row review. It preserves every
previous judgment and all 60 previously retained candidates. Frozen ABO home
v2 release tables, splits and scores are unchanged.

## Completed sample audit

100 of the 208 candidates (50 complete exchanges, allocated approximately by
category) were reviewed: **99 mismatch, 1 uncertain, 0 match, 0 pending**.
The uncertain case is a rug with Light Blue changed to Beige. Both directions
of its exchange are excluded, including the individually accepted reverse row.
The sample yields **98 individually reviewed candidates in 49 complete exchanges**.
This is one reviewer's sample, not certification of the unsampled population.

| Output | Negatives | Status |
|---|---:|---|
| `retained_complete_exchanges.csv` | 98 | Accepted complete exchanges from this audit only; original provenance schema |
| `reviewed_negatives.csv` | 158 | Previous 60 plus new 98; each negative individually reviewed |
| `training_negatives.csv` | 266 | Reviewed 158 plus unsampled 108; known uncertain exchange excluded |
| `paired_train.csv` | 266 negatives + 266 positives | Supplemental train-only table for the same 266 images |

**Sampling quality control does not mean every training row is human-approved.**
The 108 unsampled rows keep `review_status=unreviewed`, blank review decisions
and `label_status=generated_unreviewed`. The 158 accepted negatives have
`review_status=reviewed_mismatch`. The original 100-row export is preserved in
`review_completed.csv`, including the uncertain decision. A completed audit is
required before the builder enables unsampled candidates.

Original positives in `paired_train.csv` use listing titles and are labeled
`original_listing_unverified`; reviewing a rewritten negative did not certify
its original positive. The pool is allowed as generated training data with
sample quality control, not as an entirely human-verified benchmark.

## Relaxed construction

The base remains the v2 raw-color-checked eligibility ledger. Retain same split
and product type, different images/groups, one recognizable color span,
commercial-shade prefix exclusions, reciprocal swapping, positive-input
collision checks and one use per new image. Exclude all 80 previously reviewed
image anchors, including prior rejected/uncertain examples.

Brand, material-keyword and color-phrase word-count equality are no longer hard
requirements because only the color phrase is transferred. Color-removed
TF-IDF similarity ranks partners without a minimum threshold. Keep the old
conservative color-family exclusions, and add gray versus white/beige/silver,
gray versus green, and white versus silver based on the earlier train audit.
White-family aliases include ivory/cream and beige-family aliases include tan.
These are imperfect rules; multicolor products, lighting and metadata errors
can still produce false negatives.

There are 587 eligible train sources after color/modifier checks; excluding the
previous 80 leaves 507. Deterministic matching uses 208 and leaves 299 unmatched.
The source/target color phrase counts match within each category. Rejecting
whole known-bad exchanges preserves this balance in the final 266-row pool.
No validation/test candidates are generated or inspected in this version.

## Text-only diagnostic

Use the 208 new anchors and their original positives (416 rows); compare
original old-rule rewrites and expanded rewrites on the exact same anchors.
Five-fold GroupKFold keeps reciprocal directions and positives together;
TF-IDF is fitted per training fold, with fixed Logistic Regression threshold
0.5. No validation/test selection.

| Text-only model | Old accuracy | Expanded accuracy | Old AUC | Expanded AUC |
|---|---:|---:|---:|---:|
| Word TF-IDF + LR | 93.03% | 52.88% | 0.9553 | 0.5405 |
| Character TF-IDF + LR | 88.22% | 50.96% | 0.9496 | 0.5312 |

These diagnostics concern all 208 new candidates before audit exclusions, not
only the 98 reviewed rows or the combined 266-row pool. They support reduced
obvious textual shortcuts, not semantic correctness or multimodal test accuracy.

## Reproduction from the repository root

Use the shared environment: numpy, scikit-learn, and Pillow for rendering.

```bash
python src/negatives/reciprocal/build_expanded_n3.py --out /tmp/n3-expanded
python src/negatives/reciprocal/check_text_only.py \
  --data-dir data/reviews/n3-reciprocal-expanded-dev-v2 \
  --out-json /tmp/n3-expanded-text-only.json
python src/negatives/reciprocal/summarize_review.py \
  data/reviews/n3-reciprocal-expanded-dev-v2/review_completed.csv \
  --sample-csv data/reviews/n3-reciprocal-expanded-dev-v2/review_sample.csv \
  --out /tmp/n3-expanded-reviewed
python src/negatives/reciprocal/build_training_pool.py --out /tmp/n3-train-pool
python src/negatives/reciprocal/render_review.py \
  --sample-csv data/reviews/n3-reciprocal-expanded-dev-v2/review_sample.csv \
  --out /tmp/N3_Expanded_Review.html
```

`manifest.json` describes the original candidate-generation status;
`review_summary.json` describes subsequent human judgments;
`training_manifest.json` records training inclusion, review-status counts and
source hashes. Regeneration refuses to overwrite a different review sample.
The renderer downloads missing selected public ABO images and verifies source
release hashes. Embedded HTML/images are not committed.

## Integrating with a main experiment

`paired_train.csv` is a standalone N3 training supplement, not a complete
train/val/test dataset. Canonical negative type is `N3`; `source_pair_id`,
`source_dataset_id` and `source_neg_type` preserve v1/v2 experimental provenance.
Its pair IDs reuse `<anchor>_pos` and `<anchor>_N3`, so **do not blindly append it
to original v2 pairs**: deduplicate original positives and explicitly remove or
replace overlapping old N3 first under a new combined dataset version.

All rows remain train. Keep validation/test thresholds and evaluation separate;
these training rows cannot establish held-out color generalization. Relative
N1/N2/N3 sampling weights are a training choice, not a required 1:1:1 constraint.
