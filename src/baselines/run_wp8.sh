#!/usr/bin/env bash
# WP8 end-to-end run on a local machine (macOS MPS, CUDA, or CPU).
# Run from the repository root:  bash src/baselines/run_wp8.sh
# Optional: MODELS="siglip-b16 clip-l14" bash src/baselines/run_wp8.sh
set -euo pipefail

MODELS="${MODELS:-siglip-b16 clip-l14 blip-itm-b align-b}"
PAIRS="docs/mini_version/pairs.csv"

# 1) Conda environment (shared team environment.yml).
eval "$(conda shell.bash hook)"
if conda env list | grep -qE '^cse6740 '; then
  conda env update -n cse6740 -f environment.yml --prune
else
  conda env create -f environment.yml
fi
conda activate cse6740
python -c "import torch, transformers; print('torch', torch.__version__, 'transformers', transformers.__version__, 'mps', torch.backends.mps.is_available())"

# 2) ABO metadata + furniture mini-version images (skipped when already present).
if [ ! -d data/images/small ]; then
  python src/data/fetch_raw.py --out-dir data/raw
  python src/data/build_items.py \
    --listings-dir data/raw/listings/metadata \
    --images-csv data/raw/images/metadata/images.csv.gz \
    --images-out data/images/small \
    --out-csv data/processed/items.csv \
    --out-counts-csv data/processed/items_counts.csv
fi

# 3) Smoke test: 30 pairs, one model, scores written outside scores/.
python src/baselines/zero_shot_baselines.py --model siglip-b16 --limit 30 \
  --out-csv data/processed/siglip_smoke.csv

# 4) Score val + test for each model, then evaluate with the shared WP4 evaluator.
for model in $MODELS; do
  name="${model//-/_}_zero_shot"
  python src/baselines/zero_shot_baselines.py --model "$model" --pairs-csv "$PAIRS" --batch-size 16
  python src/eval/eval.py --pairs-csv "$PAIRS" --scores-csv "scores/${name}.csv" \
    --drop-cross-split-images --r-at-1 --bootstrap 1000 \
    --out-csv "scores/${name}_eval.csv" --out-md "scores/${name}_eval.md" --out-json "scores/${name}_eval.json"
done

echo "Done. Reports: scores/*_zero_shot_eval.md"
