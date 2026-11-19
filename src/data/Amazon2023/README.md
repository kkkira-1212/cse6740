# Amazon2023 source pipeline

Intermediate Amazon Reviews 2023 Home & Kitchen filter + one-MAIN-image
downloader. See [docs/amr_home.md](../../../docs/amr_home.md) for the full
contract, category mapping and limitations.

```bash
python src/data/Amazon2023/build_amr_items.py \
  --config configs/amr_home_v1.json \
  --meta-jsonl "data/raw/Amazon2023/meta_Home_and_Kitchen.jsonl" \
  --out-dir data/processed/amr-home-v1 \
  --max-per-type 200

python src/data/Amazon2023/download_amr_images.py \
  --out-dir data/processed/amr-home-v1 --resume-images

python src/data/Amazon2023/verify_amr.py \
  --out-dir data/processed/amr-home-v1 --images --allow-image-failures
```

Modules:

- `amr_io.py` — streaming JSONL/gzip reader, category token matching, MAIN
  image selection, date parsing, safe URL/path helpers.
- `build_amr_items.py` — deterministic hash top-K filter and source tables.
- `download_amr_images.py` — throttled, retrying, resumable image downloader.
- `verify_amr.py` — structural and hash verification.
