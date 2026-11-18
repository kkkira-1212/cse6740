# OOD v3 candidate: lighting and footwear

Status: **candidate for team review, not frozen or human-certified**. This is
Sean/Yichi's WP10 handoff aligned to ID release `abo-home-v3-20261115`. It does
not change the frozen ID dataset. No model inference, OOD-based checkpoint/prompt
selection or threshold fitting has been run here.

## Scope and construction

- Near category shift: LAMP / LIGHT_FIXTURE (lighting), 150 image anchors.
- Far category shift: SHOES / SANDAL / BOOT (footwear), 150 image anchors.
- Both are from ABO; these are **held-out category shifts relative to the
  project's ID adaptation data**, not new-source, temporal, or proof of unseen
  categories during large-scale pretraining. Near/far are descriptive labels.
- Scan all 16 listing shards (147,702 source records), using the exact ID global
  grouping signals: low-frequency shared main images, exact normalized titles,
  and category-specific titles with color/material/size removed. Recomputed group
  IDs must match every frozen ID item. Exclude any candidate component, image or
  exact title connected to ALL ID splits. One representative per global group;
  near and far share no groups/images/items. Grouping remains heuristic, not
  exhaustive perceptual duplicate detection.
- Deterministic seed 20261115; choose 150 per tier by round-robin product types.
  This provides cross-type N1 donors, but is not natural ABO category prevalence.
- Fixed image, changed title. N1 uses a different product type in the same tier;
  N2 a different product from the same type. Donors differ in group/image and
  title. Allocate remaining negatives approximately equally to N1/N2; use
  least-used donor groups and deterministic hash tie breaks, no nearest-title
  mining. Maximum N1/N2 title donor use is one in this run.
- N3 reuses raw-metadata color safety checks and the existing reciprocal N3
  generator independently within each tier/type. Cap complete exchanges at
  one-third of negatives. No one-directional red/blue/green/yellow substitutions
  are used as evaluation N3. Whole exchanges preserve color phrase counts.

The old `docs/sean_mvp/ood_*` data and human review are historical. Their
image-swapped/nearest-neighbor construction and labels are **not transferred**
to these new inputs. Some items may have been explored in the pilot; this is not
a pristine source holdout and that history must be disclosed.

## Tables and review

Full unreviewed candidate (`pairs.csv`):

| Tier | Pos | N1 | N2 | N3 | Total |
|---|---:|---:|---:|---:|---:|
| near lighting | 150 | 64 | 64 | 22 | 300 |
| far footwear | 150 | 69 | 69 | 12 | 300 |

Codex visually inspected 74 exact candidate negatives: 10 N1 + 10 N2 per tier,
plus ALL 34 reciprocal N3. The ledger contains 64 proposed mismatch and 10
uncertain judgments, explicitly **model-assisted**, with image hashes and exact
title inputs. This is a limited semantic QC sample, not human ground truth or
a population false-negative-rate estimate. Title claims such as sizes/materials
cannot generally be verified from a small image. Original positives remain
listing-unverified. All 300 images are valid readable files; captured SHA-256
hashes bind future downloads to the initial source image bytes.

`eval_pairs.csv` is the **proposed primary scoring table**, produced by explicit
QC exclusions before any model scoring. Remove uncertain anchors together with
their positives; if either reciprocal direction is flagged, remove the complete
exchange. Do not resample replacements. Keep all original candidates/decisions.
Sixteen anchors are excluded, leaving:

| Tier | Pos | N1 | N2 | N3 | Total |
|---|---:|---:|---:|---:|---:|
| near lighting | 138 | 64 | 62 | 12 | 276 |
| far footwear | 146 | 68 | 68 | 10 | 292 |

Only 6/5 reciprocal exchanges remain in near/far N3: report counts and broad
uncertainty, not precise color-generalization claims. The unsampled N1/N2 labels
remain generated candidates. Review exclusions change the evaluated population;
do not hide the filtering or claim all 568 rows were reviewed.

| File | Purpose |
|---|---|
| items.csv / pairs.csv | Full 300-anchor/600-pair candidate and provenance |
| n3_candidates.csv / n3_provenance.csv | Generated reciprocal candidates and full selected exchanges |
| review_sample.csv | Exact 74-row visual QC batch |
| eval_pairs.csv | Proposed scoring subset, 568 rows |
| eval_n3_provenance.csv | Retained exchange IDs for N3 bootstrap |
| eval_excluded_anchors.csv | Explicit whole-anchor/exchange exclusions |
| manifest.json / screening_manifest.json | Independent construction and QC hashes/counts |
| image_manifest.csv | 300 captured image hashes; images excluded from Git |

Decision ledger: `data/reviews/ood-v3-model-assisted/decisions.csv`.

## Download, verify, reproduce

```sh
python data/releases/abo-ood-v3-20261115-candidate/download_images.py
python data/releases/abo-ood-v3-20261115-candidate/verify.py --images
```

Image root is `data/releases/abo-ood-v3-20261115-candidate/images`.
To reconstruct from official metadata using the project's numpy/sklearn/Pillow
environment (all raw shards/images remain untracked):

```sh
python src/data/fetch_raw.py --out-dir data/raw
python src/negatives/build_ood_v3.py --download-images
python src/negatives/finalize_ood_v3.py
python -m unittest discover -s tests -v
```

Metadata/source hashes and construction inputs are in `manifest.json`. Review
input text hashes normalize CRLF to LF; output CSVs use LF.

## Model handoff (after team adopts a pinned table/hash)

Jane and Jinlin score `eval_pairs.csv` using the EXACT same model revisions,
selected ID checkpoints, preprocessing and higher-is-match score convention as
their final ID runs. Do not train on these rows. No OOD val split exists. Each
model's threshold comes from **that model's ID v3 validation run**, not another
model's threshold and never OOD accuracy. Score rows with `ood_near`/`ood_far`
split names; baseline runners with default val/test filters need explicit
`--splits ood_near ood_far`. Checkpoint scorers may need split parameterization.

The shared evaluator already accepts these split names and a fixed threshold:

```sh
python src/eval/eval.py \
  --pairs-csv data/releases/abo-ood-v3-20261115-candidate/eval_pairs.csv \
  --scores-csv scores/YOUR_MODEL_ood_v3.csv \
  --test-splits ood_near ood_far \
  --fixed-threshold YOUR_ID_VAL_THRESHOLD --bootstrap 1000
```

Replace the filename/threshold placeholders with the model's fixed values. Main
results: per-tier AUC + accuracy at the ID threshold, positive/negative recalls,
and matched-anchor N1/N2/N3 AUC. Keep pairing rank accuracy separate. Shared
evaluator intervals use anchor groups; N3 needs exchange-level resampling with
`eval_n3_provenance.csv`, as in Aaron's v3 controls. Do not present pooled
near/far or pooled-ID-vs-OOD numbers as controlled causal domain-shift effects:
category and negative-type mixtures differ. No legacy three-way R@1.

Before freeze: Kira reviews scope/grouping/exclusions; Aaron checks evaluation
and shortcut diagnostics using frozen ID-fitted probes (no fitting on OOD);
team agrees the evaluation population and limitations. Then pin hashes and run
selected models once. If adding further semantic adjudication, preserve history
and issue a new table/hash before inference.
