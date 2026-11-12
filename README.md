# Product Image–Title Consistency

A Georgia Tech CSE 6740 project studying whether an e-commerce product's main image agrees with its English title. The experimental plan compares pretrained vision–language baselines, CLIP adaptation with LoRA, and full fine-tuning, with held-out category and cross-source/time tests.

## Current data release

A proposed [reciprocal N3 full-split candidate](data/releases/abo-home-reciprocal-v3-candidate/README.md)
is available for data-owner review and new shortcut controls. It preserves existing
train QC and adds explicitly model-assisted held-out color judgments. It is not
frozen or human-certified, and changes the evaluated population. The v2 release
and historical results remain separate.

**[ABO Furniture + Decor v2 — 2026-11-03](https://github.com/kkkira-1212/cse6740/releases/tag/abo-home-v2-20261103)** is available for preliminary experiments and human N2 review. It contains **3,335 image anchors and 6,670 image–title pairs** across 10 retained furniture/decor types.

**Generated negative labels are candidates, not human-certified ground truth.** A 100-pair train N2 audit is complete (94 mismatch, 1 match, 5 uncertain). The reciprocal-color N3 audits now retain 158 individually reviewed negatives. An expanded training pool contains 266 N3 negatives: those 158 plus 108 unreviewed generated candidates, after excluding a known uncertain exchange. See the [expanded N3 training guide](data/reviews/n3-reciprocal-expanded-dev-v2/README.md). See the [N2 review](data/reviews/abo-home-v2-20261103/README.md) and [N3 development results](data/reviews/n3-reciprocal-dev-v1/README.md). These sample reviews do not certify all release or training-pool labels. No multimodal model performance on v2 is reported yet.

| Deliverable | Download | Start here |
|---|---|---|
| Main experiment data, including all 3,335 images | [Full data ZIP · approximately 30 MiB](https://github.com/kkkira-1212/cse6740/releases/download/abo-home-v2-20261103/abo-home-v2-20261103-full.zip) | Release `README.md`, then `python tools/verify.py --images` |
| 100-pair N2 human-review batch | [Offline review ZIP · approximately 0.93 MiB](https://github.com/kkkira-1212/cse6740/releases/download/abo-home-v2-20261103/n2-home-v2-100-review.zip) | Open `N2_v2_review.html`; images are embedded |

The N2 review batch is sampled from the exact **train N2** pairs in the main release, covering every retained type. It is not a separately generated set. Export completed judgments as CSV and back up progress as JSON.

| Split | Anchors / positives | N1 | N2 | N3 | Total pairs |
|---|---:|---:|---:|---:|---:|
| train | 2,664 | 1,030 | 1,031 | 603 | 5,328 |
| val | 328 | 124 | 124 | 80 | 656 |
| test | 343 | 128 | 128 | 87 | 686 |

Retained types: CHAIR, RUG, TABLE, WALL_ART, SOFA, HOME_FURNITURE_AND_DECOR, STOOL_SEATING, OTTOMAN, PILLOW, and HOME. All 16 official ABO metadata shards were scanned; explicit scope, grouping and size filters were applied. This is not every furniture/decor record in ABO. Lighting and footwear are held out; OOD sets themselves are not rebuilt in this release.

## Setup and run

Run from the repository root with Python 3.11:

```bash
conda env create -f environment.yml
conda activate cse6740
```

Download and extract the full data ZIP. Place its top-level directory under `data/releases/`, or adjust the paths below. If using the tracked tables without the image ZIP, fetch and verify only the release images:

```bash
python data/releases/abo-home-v2-20261103/tools/download_images.py
python data/releases/abo-home-v2-20261103/tools/verify.py --images
```

Score the new pairs with the existing CLIP baseline:

```bash
python src/models/zero_shot_clip.py \
  --pairs-csv data/releases/abo-home-v2-20261103/pairs.csv \
  --image-root data/releases/abo-home-v2-20261103/images \
  --out-csv scores/abo_home_v2_clip_b32.csv \
  --device auto --batch-size 32
```

Evaluate classification using a threshold selected on validation data:

```bash
python src/eval/eval.py \
  --pairs-csv data/releases/abo-home-v2-20261103/pairs.csv \
  --scores-csv scores/abo_home_v2_clip_b32.csv \
  --bootstrap 1000
```

The shared evaluator accepts complete val+test scores without train scores and clusters v2 bootstrap intervals by explicit image-anchor group. The ZIP also contains a frozen standalone classification evaluator with matching classification metrics. It reports Accuracy, AUC, balanced accuracy and per-negative-type/category recalls. The legacy three-way R@1 flag is disabled because v2 has one negative per anchor. Model inference requires checkpoint downloads and the documented environment; it was not rerun during dataset construction.

## Negative construction

All v2 negatives **keep the image fixed and change the title**:

- **N1:** a real title from a different product type and different group, within the same split.
- **N2:** a real title from the same product type and a different group, within the same split. No nearest-title or model-score mining is used.
- **N3:** a conservative color-word substitution, using Sean's full raw-metadata checks. Material swaps are not implemented.

Products are globally grouped before splitting, and one deterministic representative is retained per group. Each anchor has one positive and one candidate negative. N3 is limited by eligible anchors and at most one third of each split's negatives; N1/N2 share the remainder approximately equally.

N1/N2 title donors are selected from the least-used legal groups, randomizing ties. Three uses per split is a soft limit; any relaxation is logged. This run required no relaxation and achieved a maximum donor use count of one. Structural constraints do not prove semantic mismatch.

## Reproduce the data

The new generator, configuration, tests and release tables are tracked:

```bash
python src/data/fetch_raw.py --out-dir data/raw
python src/data/build_home_release.py \
  --config configs/abo_home_v2.json \
  --out-dir data/releases/abo-home-v2-20261103 \
  --audit-dir ../output/n2_home_v2_20261103 \
  --download-images
python -m unittest discover -s tests -v
```

The generator refuses to overwrite an existing release. Use `--resume-images` to finish/retry image verification without regenerating pairs. Use a new version/path when changing construction rules. See the [data guide](docs/home_v2.md), [release contract](data/releases/abo-home-v2-20261103/README.md), [configuration](configs/abo_home_v2.json) and [review batch metadata](data/reviews/abo-home-v2-20261103/README.md).

## Versions and experiment status

The old [furniture pilot](docs/mini_version/README.md) contains 3,978 product records and uses image-swapped N1/N2 negatives. Its source tables, scores and human-review records are preserved. **Do not mix pilot scores, thresholds, pair-ID interpretations or API caches with v2.** In v2, the pair-ID prefix identifies the image anchor; title provenance is explicit in `text_item_id`.

[Aaron's shared evaluator PR #4](https://github.com/kkkira-1212/cse6740/pull/4) and [Jane's additional baseline PR #5](https://github.com/kkkira-1212/cse6740/pull/5) are merged with fixed-image v2 compatibility. Five models have historical pilot scores; there are no new v2 model-performance results. API resume keys bind exact inputs and prompts, and subset sampling preserves explicit image-anchor pairs. LoRA, full fine-tuning, API-judge results, full-dataset shortcut controls and cross-time experiments remain outstanding. Train-only text-only diagnostics for the separate reciprocal N3 development batch are recorded with its review results.

## Repository guide

| Path | Purpose |
|---|---|
| `configs/` | Versioned data-generation settings |
| `src/data/` | Official metadata download, product selection, grouping and splits |
| `src/negatives/` | Negative-generation and human-review utilities |
| `src/models/`, `src/baselines/` | Model scoring and adaptation work |
| `src/eval/` | Shared evaluation work |
| `data/releases/` | Versioned small tables, manifests and handoff tools; images distributed separately |
| `data/reviews/` | Audit inputs, completed judgments, summaries and reviewed development candidates; no embedded images |
| `docs/` | Current guides and clearly identified historical planning |
| `scores/` | Model scores and evaluation artifacts, labeled by data version |
| `tests/` | Data/review/evaluation safeguards |
| `paper/` | Manuscript scaffold |

Team responsibilities: Kira—data and N1/N2; Jack—CLIP/LoRA/full fine-tuning; Aaron—evaluation and cross-time data; Jane—API/additional baselines; Sean—N3, review and OOD. See the [documentation index](docs/README.md) and [contribution guidelines](CONTRIBUTING.md).

## Data source

Images and metadata: [Amazon Berkeley Objects](https://amazon-berkeley-objects.s3.amazonaws.com/index.html), credited to Amazon.com and the ABO authors. Generated tables, groupings and negative pairs are project-derived modifications. This project uses ABO for noncommercial coursework; consult the original dataset terms before other reuse. Raw images, metadata archives, weights, API logs and credentials are excluded from Git history; data ZIPs are distributed as release assets.
