# Data Preparation

Current entry point: `build_home_release.py`, configured by `configs/abo_home_v2.json`. It reads all official ABO metadata shards, applies explicit furniture/decor scope, builds global near-duplicate groups, selects representatives, filters small types, splits by group and generates fixed-image candidate pairs. With `--download-images`, it verifies all selected images and creates the matching 100-pair train N2 audit.

Use `fetch_raw.py` to obtain raw metadata and `abo_io.py` for shared readers. `build_items.py` and `count_categories.py` are the original furniture-pilot pipeline. Sean's `download_abo_metadata.py` and `download_pair_images.py` remain for existing callers; they are not additional steps required by the new release builder.

[`Amazon2023/`](Amazon2023/README.md) is the intermediate Amazon Reviews 2023
Home & Kitchen source-items filter and one-image downloader. It is test-only
data preparation, not a frozen release and not part of the ABO v2/v3 inputs.
See [the AMR guide](../../docs/amr_home.md).

See [the current guide](../../docs/home_v2.md) and [release quickstart](../../data/releases/abo-home-v2-20261103/README.md). The legacy pilot is not overwritten. Cross-time grouping/splits remain future work.
