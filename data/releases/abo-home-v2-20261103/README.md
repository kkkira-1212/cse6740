# ABO Furniture + Decor v2 — Candidate Release

Version: **abo-home-v2-20261103**. **Not a human-certified benchmark.** All N1/N2/N3 labels are generated candidate labels. The original positives are listing-provided associations, also not manually certified.

## Contents and split sizes

| Split | Image anchors / positives | N1 | N2 | N3 | Total pairs |
|---|---:|---:|---:|---:|---:|
| train | 2,664 | 1,030 | 1,031 | 603 | 5,328 |
| val | 328 | 124 | 124 | 80 | 656 |
| test | 343 | 128 | 128 | 87 | 686 |
| total | 3,335 | 1,282 | 1,283 | 770 | 6,670 |

Ten retained types: CHAIR, RUG, TABLE, WALL_ART, SOFA, HOME_FURNITURE_AND_DECOR, STOOL_SEATING, OTTOMAN, PILLOW, HOME. Mixed HOME types require an explicit Furniture/Home Decor path; their labels are coarse and may still be noisy.

All official listing shards were scanned. Explicit scope, frequent-image, global-group and category-size filters were applied. 6,479 in-scope usable product records yielded 3,969 representative groups before category-size selection; 3,335 groups remain in the main release. This is not every furniture/decor record in ABO. See `category_ranking.csv`, `scope_exclusions.csv`, `group_members.csv` and `config.json` for exact boundaries and exclusions.

Lighting types LAMP/LIGHT_FIXTURE/HOME_LIGHTING_AND_LAMPS and footwear types SHOES/SANDAL/BOOT are held out; globally connected groups are excluded from main data. They are not included as N1 donors. OOD data itself is not rebuilt in this delivery.

## Start here

With the full ZIP, unzip it and run from the extracted release directory:

```bash
python tools/verify.py --images
```

If you received tables without images:

```bash
python tools/download_images.py
python tools/verify.py --images
```

The downloader fetches only the selected public ABO images and checks exact SHA-256 values. Images are at `images/small/...`. Every `image_path` in the tables is relative to **this release's `images/` directory**, not the repository's old pilot image directory.

## Score the new pairs

From the repository root, using Jack's existing CLIP scorer:

```bash
conda activate cse6740
python src/models/zero_shot_clip.py \
  --pairs-csv data/releases/abo-home-v2-20261103/pairs.csv \
  --image-root data/releases/abo-home-v2-20261103/images \
  --out-csv scores/abo_home_v2_clip_b32.csv \
  --device auto --batch-size 32
```

This invokes model inference and may download weights; it was not run as part of constructing this data release. Existing environment/model-code compatibility still applies. The scorer currently supports CPU/MPS, not an explicit CUDA option.

Jane's baseline code, available on her PR #5 branch, accepts the same pair/image interface and can score only val+test. Use a new output filename per dataset/model/configuration. Never reuse pilot scores, cached API judgments or pilot thresholds for these new pairs.

## Evaluate classification

The bundled evaluator is copied from Aaron PR #4 (`4e3d9f7`), with the legacy `--r-at-1` flag blocked. This release has only one negative per image, not the old three-way ranking task. No pending PR is silently merged by bundling this tool.

From the repository root:

```bash
python data/releases/abo-home-v2-20261103/tools/evaluate.py \
  --pairs-csv data/releases/abo-home-v2-20261103/pairs.csv \
  --scores-csv scores/abo_home_v2_clip_b32.csv \
  --bootstrap 1000
```

The tool selects an Accuracy-maximizing threshold on val and applies it to test. It accepts complete val+test scores without train scores. It reports Accuracy, AUC, balanced accuracy and recalls by negative type/category, with CSV/Markdown/JSON outputs. Pair-ID prefixes identify image anchors in v2; therefore the bundled evaluator's internally named source-item bootstrap clusters represent image anchors here. Title reuse can introduce additional dependence; no confidence interval corrects label noise.

## Data contract

Core columns are unchanged: `pair_id,item_id,image_path,text,label,neg_type,category,year,split`. Additional columns explicitly record `anchor_item_id,image_item_id,text_item_id,anchor_group_id,text_group_id,dataset_version,label_status`.

**Important version change:** pair IDs are `<image_anchor_item_id>_<neg_type>` in v2; the old pilot used a text-source prefix. Do not infer title-source IDs from v2 pair IDs. Use explicit source columns. For N3, `text_item_id` refers to the original title's product before rewriting. `item_id` always owns the image. This release has a single representative per near-duplicate group.

Each anchor has its original title as a positive and exactly one N1/N2/N3 negative candidate:

- N1: real title from a different product type, different group, same split.
- N2: real title from the same product type, different group, same split. No similarity model is used.
- N3: Sean's color-only substitution with full raw color checks, preserving the image. Material swaps are not implemented.

N3 is limited by eligible anchors and at most one third of each split's negatives. N1/N2 divide the remainder approximately equally. N3 coverage differs by type; those differences may themselves create shortcuts. Text-only/image-only controls remain required.

Title donors are chosen from the least-used legal groups, randomizing ties. Three uses per split across N1/N2 is a soft limit, not a hard one-use rule. This run has max use 1 and zero relaxations. Original positives and N3 rewritten titles are not counted as N1/N2 donor uses. Full distributions are in `title_source_reuse.csv` and `reuse_relaxations.csv`.

## Quality and provenance

`validation.json` confirms structural checks, not semantic mismatch correctness. `image_manifest.csv` records every image hash; `checksums.json` records packaged non-image file hashes. `manifest.json` records metadata/code hashes and candidate status. `n3_audit.csv` and `n3_skipped.csv` preserve color substitution/skip reasons.

The associated 100-pair human audit is sampled from the exact train N2 rows across all retained types. It does not certify every negative or measure N1/N3 quality. Do not selectively alter test labels to improve a model. If the audit changes the construction rule, publish a new version and rescore models.

Grouping uses image sharing, exact titles and normalized-title heuristics, including global checks against held-out lighting/footwear. It does not establish true product identity or guarantee absence of visual near-duplicate leakage. Earlier project work inspected parts of the original pilot; this resplit is not claimed as a completely pristine source-level holdout.

## Source and distribution

Images and metadata: [Amazon Berkeley Objects](https://amazon-berkeley-objects.s3.amazonaws.com/index.html), credited to Amazon.com and the ABO authors. Use for this noncommercial coursework; review original terms before other reuse. Generated tables/groupings/negative pairs are project-derived modifications. Images, raw metadata, model weights and API logs should not be committed to Git. The full image ZIP is a separate teammate handoff artifact.
