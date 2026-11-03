# Data

## Current version

Use [ABO Furniture + Decor v2](releases/abo-home-v2-20261103/README.md) for the new candidate-data experiments. Download the [complete data/image package](https://github.com/kkkira-1212/cse6740/releases/download/abo-home-v2-20261103/abo-home-v2-20261103-full.zip) or run its image downloader against the tracked tables.

The matching [100-pair N2 audit](reviews/abo-home-v2-20261103/README.md) is available as an [offline review package](https://github.com/kkkira-1212/cse6740/releases/download/abo-home-v2-20261103/n2-home-v2-100-review.zip). Do not mix this batch with the earlier furniture-only audit.

## Layout and tracking policy

```text
data/raw/                      # official metadata; ignored
data/images/                   # legacy pilot images; ignored
data/processed/                # local intermediate/smoke outputs; ignored
data/releases/<version>/       # tracked CSVs, configuration, manifests and tools
  images/                      # selected images; ignored, supplied by ZIP/downloader
data/reviews/<version>/         # tracked blank review samples and provenance
```

Small versioned tables are tracked. Raw metadata, images, model weights and image-embedded review HTML are not committed. Package URLs, sizes and SHA-256 values are in [packages.json](packages.json).

## Compatibility

The [current data guide](../docs/home_v2.md) and version-specific release README define v2. `docs/mini_version/` and the original schema describe the older pilot, which is preserved for provenance. Old model scores and thresholds do not apply to new pair inputs.
