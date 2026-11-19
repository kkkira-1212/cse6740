# Amazon Reviews 2023 Home & Kitchen source items

Version: `amr-home-v1-20261118` (intermediate pilot; not a frozen release).

This pipeline reads the UCSD Amazon Reviews 2023 `Home_and_Kitchen` metadata
dump and selects the project's 10 ABO product types. It is a source-items
builder only: it does not create near-duplicate groups, splits, negative pairs,
or model scores.

## Source

- Dataset: [Amazon Reviews 2023](https://amazon-reviews-2023.github.io/)
  (McAuley Lab, UCSD).
- Local metadata: `data/raw/Amazon2023/meta_Home_and_Kitchen.jsonl`
  (untracked; 11.8 GB, 3,735,584 records).
- Images are Amazon CDN URLs from the metadata `images` list. The metadata has
  `thumb` (~75px), `large` (~500px) and `hi_res` (~1500px), not medium/small;
  the downloader uses `large` first, then `hi_res`, then `thumb`. Images are not
  redistributed. `data/raw/` and `data/processed/` are git-ignored.
- Use for research/coursework only; consult the dataset terms before other
  reuse.

## Commands

```bash
python -m unittest discover -s tests -p "test_amr_*.py" -v

python src/data/Amazon2023/build_amr_items.py \
  --config configs/amr_home_v1.json \
  --meta-jsonl "data/raw/Amazon2023/meta_Home_and_Kitchen.jsonl" \
  --out-dir data/processed/amr-home-v1 \
  --max-per-type 200

python src/data/Amazon2023/download_amr_images.py \
  --out-dir data/processed/amr-home-v1 \
  --requests-per-second 2

python src/data/Amazon2023/verify_amr.py \
  --out-dir data/processed/amr-home-v1 \
  --images --allow-image-failures \
  --abo-listings-dir data/raw/listings/metadata
```

`--resume-images` on either command skips images whose file SHA-256 matches the
manifest. `--allow-image-failures` makes `verify --images` report unrecoverable
items (for example a thumb-only 40x40 URL) without failing the whole pilot; the
strict default still rejects any image error.

## ABO overlap exclusion

Before top-K selection, the builder loads all 16 official ABO listing shards
(`data/raw/listings/metadata`, 147,702 records) and excludes AMR items that
match any of:

- ABO `item_id` == AMR `parent_asin`;
- any ABO `main_image_id` or `other_image_id` == any AMR MAIN-image variant id;
- exact normalized en_US title (length >= 12) — a conservative relisting check.

Excluded rows go to `abo_overlap.csv` with `signals`/`details`; the top-K then
fills from the remaining eligible items, so the per-type cap still holds. Use
`--skip-abo-overlap` only for domains where ABO overlap is not relevant. The
ABO directory can be overridden with `--abo-listings-dir`. `--skip-source-hash` avoids hashing the 11.8 GB metadata for smoke
runs. `--max-per-type 0` keeps every eligible item and is memory-heavy.

## Category mapping

Rules are ordered and token/phrase-based (not raw substrings). The config is
`configs/amr_home_v1.json`.

| Type | Rule |
|---|---|
| `CHAIR` | leaf `Chairs` / `Armchairs`, excluding slipcovers/pads/mats |
| `TABLE` | leaf `Tables` / `Table Sets`; `Table & Chair Sets` goes to the catch-all |
| `SOFA` | leaf `Sofas & Couches` |
| `OTTOMAN` | leaf `Ottomans` |
| `STOOL_SEATING` | leaf `Barstools` / `Stools` |
| `RUG` | Home Décor Products → `Area Rugs` |
| `WALL_ART` | any canonical `Wall Art` path |
| `PILLOW` | Bedding → decorative pillows; or `Pillows, Throws & Poufs` pillow/cushion leaves |
| `HOME_FURNITURE_AND_DECOR` | fallback for remaining `Furniture` (beds, dressers, bar carts, TV stands, accent furniture, etc.) |
| `HOME` | fallback for remaining `Home Décor Products` (frames, mirrors, shelves, curtains, candles, clocks, etc.) |

Broad fallbacks follow the ABO catch-all types, not the literal type names.
As a result, `HOME_FURNITURE_AND_DECOR` can include media storage/accessory
leaves and `HOME` can include candles, clocks and figurines; filter on
`category_leaf` later if a narrower benchmark is wanted. Global excludes remove
replacement parts, slipcovers, lighting/lamp paths, pillowcases/shams, rug pads,
chair pads and similar non-target leaves. Bedding leftovers (sheets, blankets)
are `type_unmapped`.

Current full-scan estimate: about 1.29M eligible source items before the
per-type cap. The pilot keeps 200 per type, so it is type-balanced and not a
natural category-prevalence sample. `HOME` and `HOME_FURNITURE_AND_DECOR` are
large catch-alls.

## Outputs

`data/processed/amr-home-v1/`:

- `items.csv` — project items fields plus AMR provenance (`image_url_*`,
  `year`, `date_first_available`, `rating_number`, `category_l2`,
  `category_leaf`, `classification_rule`, `source_line`, ...).
- `image_manifest.csv` — one row per item with accepted variant/URL, SHA-256,
  bytes, format, dimensions and error class.
- `filter_summary.csv`, `sampling_summary.csv`, `dfa_summary.csv`,
  `second_level_counts.csv`, `exclusion_summary.csv`.
- `no_main_images.csv` when any mapped item has no MAIN image.
- `abo_overlap.csv` when any candidate matches ABO by item id, image id or exact title.
- `config.json`, `manifest.json`, `validation.json`, `checksums.json`.
- `images/<type>/<sha256-prefix>/<parent_asin>.jpg` (untracked).

`year` is populated only from `details["Date First Available"]`; review
timestamps are a later fallback. DFA coverage is much lower for PILLOW, WALL_ART
and HOME than for the furniture types, so those types need the review-time
fallback before a balanced cross-time split. The pilot is also type-balanced,
not time-balanced (only a small pre-2015 subset); the cross-time phase should
resample deliberately by year from the eligible pool rather than reuse this
pilot as-is. `split` is `unassigned` and
`group_id` is a per-item placeholder until the grouping/split phase. Positives
are listing title + MAIN image and are not human-certified.

## Next phase

Near-duplicate grouping, `crosstime_<year>` splits, N1/N2/N3 construction,
review-timestamp fallback, and human QC.

ABO overlap exclusion is applied before top-K and recorded in
`abo_overlap.csv`. The full eligible pool excludes 2,825 candidates on at least
one signal (2,442 item-id, 2,678 image-id, 1,955 exact-title matches). The
previous 2,000-item pilot contained 12 of them, so the rebuilt selection changes
by 12 replacements and still holds 200 items/type with zero remaining ABO
item/image/title overlap.
