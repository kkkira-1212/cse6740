#!/usr/bin/env bash
# WP8 zero-shot baselines on a fixed-image release (v2 / v3), run from the repository root.
#
# Default MODE=val scores the val split only and prints threshold-free diagnostics;
# it never touches test, so it is safe before the benchmark is frozen.
#   bash src/baselines/run_wp8.sh
#
# MODE=final scores val + test and runs the shared evaluator. Use it only after the
# team has frozen the data version:
#   MODE=final CONFIRM_FROZEN=yes DATA_DIR=data/releases/<frozen-version> bash src/baselines/run_wp8.sh
#
# Add OOD once the OOD release is adopted (scored with the same models, judged with each
# model's ID-val threshold, never tuned on):
#   MODE=final CONFIRM_FROZEN=yes OOD_DIR=data/releases/<adopted-ood-release> bash src/baselines/run_wp8.sh
#
# Optional: MODELS="siglip-b16 blip-itm-b" to choose models.
set -euo pipefail

MODE="${MODE:-val}"
MODELS="${MODELS:-siglip-b16 blip-itm-b align-b}"
DATA_DIR="${DATA_DIR:-data/releases/abo-home-reciprocal-v3-candidate}"
IMAGE_ROOT="${IMAGE_ROOT:-data/releases/abo-home-v2-20261103/images}"
PAIRS="$DATA_DIR/pairs.csv"
OOD_DIR="${OOD_DIR:-}"
OOD_PAIRS="${OOD_PAIRS:-$OOD_DIR/eval_pairs.csv}"
VERSION="$(basename "$DATA_DIR")"

if [ "$MODE" = "final" ] && [ "${CONFIRM_FROZEN:-}" != "yes" ]; then
  echo "MODE=final reads test. Set CONFIRM_FROZEN=yes only after the data version is frozen." >&2
  exit 2
fi
[ -f "$PAIRS" ] || { echo "missing $PAIRS (pull the latest main first)" >&2; exit 1; }

# 1) Conda environment (shared team environment.yml).
eval "$(conda shell.bash hook)"
if conda env list | grep -qE '^cse6740 '; then
  conda env update -n cse6740 -f environment.yml --prune
else
  conda env create -f environment.yml
fi
conda activate cse6740
python -c "import torch, transformers; print('torch', torch.__version__, 'transformers', transformers.__version__, 'mps', torch.backends.mps.is_available())"

# 2) Release images (v3 reuses the v2 images). The downloader skips files whose hash already matches.
python data/releases/abo-home-v2-20261103/tools/download_images.py

# Optional OOD (final mode only): the adopted OOD release directory and its scoring table.
if [ "$MODE" = "final" ] && [ -n "$OOD_DIR" ]; then
  [ -f "$OOD_PAIRS" ] || { echo "missing $OOD_PAIRS (merge the OOD release first)" >&2; exit 1; }
  python "$OOD_DIR/download_images.py"
  ID_OOD_PAIRS="data/processed/${VERSION}_plus_$(basename "$OOD_DIR")_pairs.csv"
  python src/baselines/concat_csv.py --out "$ID_OOD_PAIRS" "$PAIRS" "$OOD_PAIRS"
fi

# 3) Score each model.
for model in $MODELS; do
  name="${VERSION}_${model//-/_}"
  if [ "$MODE" = "final" ]; then
    python src/baselines/zero_shot_baselines.py --model "$model" --pairs-csv "$PAIRS" \
      --image-root "$IMAGE_ROOT" --splits val test --batch-size 16 --out-csv "scores/${name}.csv"
    eval_pairs="$PAIRS"; eval_scores="scores/${name}.csv"; test_splits="test"
    if [ -n "$OOD_DIR" ]; then
      # OOD is scored with the same model and judged with the ID-val threshold; never tuned on.
      ood_name="$(basename "$OOD_DIR")_${model//-/_}"
      python src/baselines/zero_shot_baselines.py --model "$model" --pairs-csv "$OOD_PAIRS" \
        --image-root "$OOD_DIR/images" --splits ood_near ood_far --batch-size 16 --out-csv "scores/${ood_name}.csv"
      eval_scores="data/processed/${name}_id_ood_scores.csv"
      python src/baselines/concat_csv.py --out "$eval_scores" "scores/${name}.csv" "scores/${ood_name}.csv"
      eval_pairs="$ID_OOD_PAIRS"; test_splits="test ood_near ood_far"; name="${name}_with_ood"
    fi
    python src/eval/eval.py --pairs-csv "$eval_pairs" --scores-csv "$eval_scores" --bootstrap 1000 \
      --test-splits $test_splits \
      --out-csv "scores/${name}_eval.csv" --out-md "scores/${name}_eval.md" --out-json "scores/${name}_eval.json"
  else
    python src/baselines/zero_shot_baselines.py --model "$model" --pairs-csv "$PAIRS" \
      --image-root "$IMAGE_ROOT" --splits val --batch-size 16 --out-csv "scores/${name}_val.csv"
    python src/baselines/val_diagnostics.py --pairs-csv "$PAIRS" --scores-csv "scores/${name}_val.csv"
  fi
done

echo "Done (MODE=$MODE, data=$VERSION)."
