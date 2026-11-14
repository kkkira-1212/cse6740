# Shortcut controls: `abo-home-reciprocal-v3-candidate`

Status: **protocol frozen before test; single test run completed.**
This is a diagnostic run, not a final benchmark certification.
v2 pilot results are in [`controls.md`](controls.md).

## Data

- Pairs: `data/releases/abo-home-reciprocal-v3-candidate/pairs.csv`
- Pairs SHA-256: `14814aa6bba905c07377a929c44e7d28b76893497c9c59eb86b8b6a9da334003`
- Dataset version: `abo-home-reciprocal-v3-candidate`
- Candidate commit: `b1b0aaa7a6d2e999225f87e3b51af38df6252bb0`
  (follow-up `f3524aa` adds review metadata; data hash unchanged)
- Images: `data/releases/abo-home-v2-20261103/images` (3,335 verified images)
- Splits: train 5,328 / val 656 / test 686; 3,335 anchors; 6,670 pairs.
- Negative counts: train N1 1,199 / N2 1,199 / N3 266;
  val 152 / 152 / 24; test 156 / 157 / 30.
- Fixed-image layout: each anchor has one positive and one negative with the
  same `image_path`; `check_fixed_image_layout` enforces this.

## Frozen protocol

1. Fit on train only; no val/test rows in fitting.
2. Text-only:
   - word: TF-IDF `ngram_range=(1,2), min_df=2, sublinear_tf=True,
     strip_accents="unicode"`; logistic regression `max_iter=1000, random_state=0`.
   - char: TF-IDF `analyzer="char", ngram_range=(3,5), min_df=2`,
     same classifier.
3. Image-only: frozen CLIP ViT-B/32
   (`openai/clip-vit-base-patch32`,
   revision `3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268`), L2-normalized image
   embeddings, same logistic regression. New cache
   `data/processed/control_v3_clip_image_features.npz`, bound to the dataset
   version and pairs SHA-256; the v2 cache is not reused.
4. Threshold: select on val by accuracy, rule `score >= threshold`, smallest
   threshold on ties. Test is evaluated once after this protocol is frozen.
5. Metrics:
   - Overall: accuracy, AUC, balanced accuracy, positive/negative recall at the
     val-selected threshold (shared `eval.py`, image-anchor bootstrap).
   - N1/N2/N3: **matched-anchor AUC** — each negative is compared with the
     positive row having the same `anchor_item_id` (never the donor
     `text_item_id`). Report n_pos, n_neg, AUC, and threshold recall.
   - N3 CI: join `n3_provenance.csv` on `pair_id`; resample reciprocal
     exchanges (both directions together) 1000 times for the N3 AUC CI.
     N1/N2 intervals resample image-anchor groups.
   - Overall eval.py intervals use image-anchor clusters and do not capture
     reciprocal-exchange dependence; this is documented, not corrected.
6. Four remaining uncertainty flags are **train fallback N1/N2, not N3**:
   `B07Q88MYL4_N1`, `B07TTCHRB2_N2`, `B07JD7RFRN_N2`, `B075H8JNZT_N2`.
   They are `generated_unreviewed`, `applied_to_training_labels=false`, and are
   included in training. Their presence is reported with the results.
7. No v2 score files, CLIP feature caches or thresholds are reused. v3 pair IDs
   are partially reused from v2, so the run is bound to the dataset version and
   pairs SHA-256.

## Commands

Val-only protocol phase (no test scoring):

```bash
python src/eval/controls.py \
  --pairs-csv data/releases/abo-home-reciprocal-v3-candidate/pairs.csv \
  --image-root data/releases/abo-home-v2-20261103/images \
  --output-prefix control_v3 \
  --cache data/processed/control_v3_clip_image_features.npz \
  --image-mode clip --splits val --bootstrap 1000 --seed 0
```

Single test run after this file is frozen:

```bash
python src/eval/controls.py \
  --pairs-csv data/releases/abo-home-reciprocal-v3-candidate/pairs.csv \
  --image-root data/releases/abo-home-v2-20261103/images \
  --output-prefix control_v3 \
  --cache data/processed/control_v3_clip_image_features.npz \
  --image-mode clip --splits val test --bootstrap 1000 --seed 0 \
  --protocol-file docs/controls_v3.md
```

## Results

Test set: 686 pairs (343 positives + 343 negatives; N1 156 / N2 157 / N3 30).
Thresholds were selected on val only: word `0.5222853`, char `0.49939115`,
image `0.5`.

### Overall

| control | test Acc | test AUC | Balanced | Pos recall | Neg recall |
|---|---:|---:|---:|---:|---:|
| text-only word | 50.87% [47.52%, 54.52%] | 0.5160 [0.4757, 0.5574] | 50.87% | 36.44% | 65.31% |
| text-only char | 51.60% [48.10%, 54.96%] | 0.5204 [0.4803, 0.5600] | 51.60% | 62.39% | 40.82% |
| image-only CLIP | 50.00% [50.00%, 50.00%] | 0.5000 [0.5000, 0.5000] | 50.00% | 100.00% | 0.00% |

### Matched-anchor per-type AUC

Each negative is compared with the positive of its own `anchor_item_id`;
N3 intervals resample reciprocal exchanges, N1/N2 intervals resample
image-anchor groups.

| control | N1 | N2 | N3 |
|---|---|---|---|
| text-only word | 0.5698 [0.5066, 0.6384] (156/156, 156 groups) | 0.4687 [0.4086, 0.5302] (157/157, 157 groups) | 0.5189 [0.4611, 0.5600] (30/30, 15 exchanges) |
| text-only char | 0.5649 [0.5026, 0.6301] (156/156, 156 groups) | 0.4874 [0.4242, 0.5520] (157/157, 157 groups) | 0.5056 [0.4800, 0.5411] (30/30, 15 exchanges) |
| image-only CLIP | 0.5000 [0.5000, 0.5000] | 0.5000 [0.5000, 0.5000] | 0.5000 [0.5000, 0.5000] |

### Key findings

1. **The reciprocal N3 fix removed the v2 N3 text shortcut.**
   v2 N3 text AUC was 0.9928; v3 is 0.5189 (word) / 0.5056 (char), and both
   95% CIs include 0.5. The four target colors no longer dominate the text
   control: the word model's most negative features are `beige`, `navy`, `white`
   and size/color phrases, not `yellow`/`red`/`green`/`blue`. This is the main
   intended improvement of the candidate.
2. **A modest N1 text signal remains.**
   Matched-anchor N1 AUC is 0.5698 (word, CI [0.5066, 0.6384]) and
   0.5649 (char, CI [0.5026, 0.6301]). Both lower bounds are above 0.5, so
   this is a small but detectable text-side signal; it may be related to the 450
   new fallback N1 donor rows or to title-style differences between anchors and
   donors. It is much weaker than the old N3 shortcut but should be reviewed
   before freezing.
3. **N2 is at or below chance.**
   N2 AUC is 0.4687 (word) / 0.4874 (char); both CIs include 0.5. No strong
   N2 text shortcut is evident.
4. **Overall accuracy is near 50%, as expected after removing the N3 shortcut.**
   The v2 text-only overall 61.22% was driven by N3. v3 overall is 50.87%
   (word) / 51.60% (char), with CIs including 50%. Overall metrics are not
   directly comparable to v2 because the negative type mix changed.
5. **Image-only is a structural null.**
   All 1,342 val+test scores are 0.5 (`unique_scores=1`), test accuracy 50%,
   AUC 0.5000, and per-type AUC 0.5000. v3 remains fixed-image, so the
   positive and negative of each anchor share the same image; this control
   checks data/score alignment and finds no image-side shortcut by construction.
6. **Four uncertain cases are train fallback N1/N2, not N3.**
   `B07Q88MYL4_N1`, `B07TTCHRB2_N2`, `B07JD7RFRN_N2`, `B075H8JNZT_N2` are
   `generated_unreviewed`, `applied_to_training_labels=false`, and are included
   in training. They may add label noise; their presence is reported here and
   should be resolved or explicitly carried before final adoption.
7. **N3 test sample is small.**
   30 negatives across 15 reciprocal exchanges; the N3 CIs are correspondingly
   wide. Do not claim precise category/color generalization from this sample.

### Interpretation

- The candidate achieves its primary goal: replacing one-directional color
  swaps with reciprocal N3 removes the extreme N3 text shortcut.
- The remaining text-side risk is N1, at AUC ≈0.57. This is not a reason to
  reject the candidate, but it should be investigated before freezing:
  inspect fallback N1 donor titles for systematic length/brand/style cues, and
  decide whether the fallback selection rule needs a new candidate version.
- Do not tune on test. Any rule change requires a new candidate release and a
  fresh protocol/control run.
- The image-only null confirms the fixed-image layout; it is not evidence about
  image quality or model ability.

## Caveats

- Candidate is not frozen or human-certified; 450 fallback N1/N2 rows are
  generated/unreviewed; val/test N3 are small (24/30 = 12/15 reciprocal
  exchanges).
- 11 held-out reciprocal exchanges (22 negatives) were excluded; the retained
  54 val/test N3 are model-assisted mismatches, not human ground truth.
- Do not compare overall metrics directly with v2: the negative type mix changed
  (N3 770 -> 320; N1/N2 up by 225 each).
- Chance-like AUC alone does not certify labels.
