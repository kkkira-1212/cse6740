# WP5: zero-shot CLIP

This baseline uses OpenAI CLIP ViT-B/32 (`openai/clip-vit-base-patch32`),
revision `3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268`. It scores each
image/title pair by cosine similarity between normalized embeddings. There
is no training or label-based threshold selection in this script.

From the repository root, update the Conda environment and download the
furniture mini-version images:

```bash
conda env update -f environment.yml --prune
conda activate cse6740
python src/data/fetch_raw.py --out-dir data/raw
python src/data/build_items.py \
  --listings-dir data/raw/listings/metadata \
  --images-csv data/raw/images/metadata/images.csv.gz \
  --images-out data/images/small \
  --out-csv data/processed/items.csv \
  --out-counts-csv data/processed/items_counts.csv
```

Use the checked-in pair table to score all pairs:

```bash
python src/models/zero_shot_clip.py \
  --pairs-csv docs/mini_version/pairs.csv \
  --image-root data/images \
  --out-csv scores/clip_vit_b32_zero_shot.csv \
  --device auto --batch-size 32
```

The first run downloads public model weights. `auto` uses MPS if the current
process can access it, otherwise CPU. For a smoke run, add `--limit 30` and
write to `data/processed/clip_smoke.csv`. Images and titles are encoded once
per distinct value. The output has exactly `pair_id,score`, preserves input
order, and a larger score means a stronger match. CLIP text is truncated at
77 tokens; no `logit_scale` is applied.

On 2026-10-26, a full run used Python 3.11.17, torch 2.14.1,
transformers 5.21.0, and Apple M5 MPS. It produced 11,933 finite scores
for 11,933 pairs in matching ID order. Mean scores: positive 0.3213,
N1 0.2323, N2 0.3067. These are sanity checks, not evaluation metrics.
Select any classification threshold on val and report test results with
Aaron's evaluator. The mini version has two image paths across splits;
resolve or document that overlap before final test reporting.

## Validation threshold (provisional WP5 check)

```bash
python src/models/calibrate_clip.py
```

This selects the threshold maximizing accuracy on val only. Predictions use
`score >= threshold`; ties select the smallest threshold. It then evaluates
test with that fixed threshold. The JSON output records input hashes and
the exact selection rule. This small WP5 check does not replace Aaron's
shared WP4 evaluator.

For the current mini version the threshold is **0.30781579**. Validation
accuracy is 76.25%; test accuracy is 75.25%, AUC 0.8318, balanced accuracy
75.49%, and positive recall 76.19%. Test negative recall is 93.48% for N1
and 56.03% for N2. The test majority-class baseline is 66.64% because the
data contains about twice as many negatives as positives. Scores and model
weights are unchanged by calibration. These results remain provisional
because of cross-split image overlap and unresolved N2 label noise.
