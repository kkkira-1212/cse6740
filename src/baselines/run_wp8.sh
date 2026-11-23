#!/usr/bin/env bash
# WP8 pretrained reference models (BLIP, SigLIP, ALIGN) on the V3 benchmark, run from the repository root.
#
# MODE=val (default) scores the ID val split only and prints threshold-free diagnostics.
#   bash src/baselines/run_wp8.sh
#
# MODE=final scores the ID test split and the adopted OOD table with the frozen setup in
# configs/wp8_v3_reference_freeze.json (exact HF revision + ID-val threshold per model), then
# evaluates ID and OOD separately with the shared evaluator (--fixed-threshold, matched metrics,
# N3 exchange provenance). It never selects a threshold, never updates the environment, and
# refuses to run without the freeze record:
#   MODE=final CONFIRM_FROZEN=yes bash src/baselines/run_wp8.sh
#
# Optional: MODELS="siglip-b16 blip-itm-b". Final mode defaults to every model in the freeze record.
set -euo pipefail

MODE="${MODE:-val}"
MODELS="${MODELS:-}"
DATA_DIR="data/releases/abo-home-reciprocal-v3-candidate"
IMAGE_ROOT="data/releases/abo-home-v2-20261103/images"
PAIRS="$DATA_DIR/pairs.csv"
ID_N3="$DATA_DIR/n3_provenance.csv"
OOD_DIR="data/releases/abo-ood-v3-20261115-candidate"
OOD_PAIRS="$OOD_DIR/eval_pairs.csv"
OOD_N3="$OOD_DIR/eval_n3_provenance.csv"
FREEZE="configs/wp8_v3_reference_freeze.json"
VERSION="$(basename "$DATA_DIR")"
OUT="scores/v3_final"

[ -f "$PAIRS" ] || { echo "missing $PAIRS (pull the latest main first)" >&2; exit 1; }

eval "$(conda shell.bash hook)"
if [ "$MODE" = "final" ]; then
  [ "${CONFIRM_FROZEN:-}" = "yes" ] || { echo "MODE=final reads test/OOD. Set CONFIRM_FROZEN=yes." >&2; exit 2; }
  [ -f "$FREEZE" ] || { echo "missing $FREEZE: run record_hf_revisions.py and freeze_references.py first" >&2; exit 1; }
  if [ -n "$(git status --porcelain -- src configs data)" ]; then
    echo "uncommitted changes under src/configs/data; commit first so the run binds to a code commit" >&2; exit 1
  fi
  conda activate cse6740   # no environment update in final mode
  # The final run must use the same library versions that produced the frozen val scores.
  python - "$FREEZE" <<'PY'
import json, sys, torch, transformers
for key, m in json.load(open(sys.argv[1]))["models"].items():
    env = m["val_environment"]
    if (env["torch"], env["transformers"]) != (torch.__version__, transformers.__version__):
        sys.exit(f"{key}: environment differs from frozen val run {env} vs {torch.__version__}/{transformers.__version__}")
print("environment matches the frozen val run")
PY
  # Verify the adopted OOD table and the downloaded images before any inference.
  python data/releases/abo-home-v2-20261103/tools/download_images.py
  python "$OOD_DIR/download_images.py"
  python "$OOD_DIR/verify.py" --images
  mkdir -p "$OUT"
  RUN_RECORD="$OUT/run_record.json"
  python - "$RUN_RECORD" <<'PY'
import datetime, json, platform, subprocess, sys, torch, transformers
commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
json.dump({"code_commit": commit, "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "torch": torch.__version__, "transformers": transformers.__version__,
           "mps": torch.backends.mps.is_available(), "platform": platform.platform()},
          open(sys.argv[1], "w"), indent=2)
print("code commit", commit)
PY
else
  if conda env list | grep -qE '^cse6740 '; then
    conda env update -n cse6740 -f environment.yml --prune
  else
    conda env create -f environment.yml
  fi
  conda activate cse6740
  python data/releases/abo-home-v2-20261103/tools/download_images.py
fi

if [ -z "$MODELS" ]; then
  if [ "$MODE" = "final" ]; then
    MODELS="$(python -c "import json; print(' '.join(json.load(open('$FREEZE'))['models']))")"
  else
    MODELS="siglip-b16 blip-itm-b align-b"
  fi
fi

frozen() {  # frozen <model> <field>
  python -c "import json,sys; print(json.load(open('$FREEZE'))['models'][sys.argv[1]][sys.argv[2]])" "$1" "$2"
}

for model in $MODELS; do
  key="${model//-/_}"
  if [ "$MODE" = "final" ]; then
    revision="$(frozen "$model" revision)"
    threshold="$(frozen "$model" id_val_threshold)"
    echo "== $model revision=$revision threshold=$threshold"
    python src/baselines/zero_shot_baselines.py --model "$model" --revision "$revision" \
      --pairs-csv "$PAIRS" --image-root "$IMAGE_ROOT" --splits test --batch-size 16 \
      --out-csv "$OUT/${key}_id_test.csv"
    python src/baselines/zero_shot_baselines.py --model "$model" --revision "$revision" \
      --pairs-csv "$OOD_PAIRS" --image-root "$OOD_DIR/images" --splits ood_near ood_far --batch-size 16 \
      --out-csv "$OUT/${key}_ood.csv"
    python src/eval/eval.py --pairs-csv "$PAIRS" --scores-csv "$OUT/${key}_id_test.csv" \
      --test-splits test --fixed-threshold "$threshold" \
      --matched-type-metrics --n3-provenance "$ID_N3" --bootstrap 1000 --seed 0 \
      --out-csv "$OUT/${key}_id_test_eval.csv" --out-md "$OUT/${key}_id_test_eval.md" \
      --out-json "$OUT/${key}_id_test_eval.json"
    python src/eval/eval.py --pairs-csv "$OOD_PAIRS" --scores-csv "$OUT/${key}_ood.csv" \
      --test-splits ood_near ood_far --fixed-threshold "$threshold" \
      --matched-type-metrics --n3-provenance "$OOD_N3" --bootstrap 1000 --seed 0 \
      --out-csv "$OUT/${key}_ood_eval.csv" --out-md "$OUT/${key}_ood_eval.md" \
      --out-json "$OUT/${key}_ood_eval.json"
  else
    python src/baselines/zero_shot_baselines.py --model "$model" --pairs-csv "$PAIRS" \
      --image-root "$IMAGE_ROOT" --splits val --batch-size 16 --out-csv "scores/${VERSION}_${key}_val.csv"
    python src/baselines/val_diagnostics.py --pairs-csv "$PAIRS" --scores-csv "scores/${VERSION}_${key}_val.csv"
  fi
done

echo "Done (MODE=$MODE)."
