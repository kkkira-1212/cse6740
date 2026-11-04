# Negative Construction and Review

## Current release

`src/data/build_home_release.py` is the canonical v2 orchestration entry point. It keeps images fixed, selects a different-type real title for N1 or same-type real title for N2, and reuses `build_n3.py` for conservative color substitutions. Pairing stays within splits and excludes the same near-duplicate group and existing positive-input conflicts.

`build_n2_audit.py` provides versioned review fields, validation, rendering and summary helpers used by the release builder. Its standalone CLI also supports the earlier furniture-only exploratory audit; use the release builder for the expanded furniture/decor batch.

## Preserved pilot/MVP utilities

- `build_pairs.py`: legacy pilot image-swapped N1/N2 construction, including title-nearest-neighbor N2. Do not use it to regenerate v2.
- `build_n3.py`: Sean's color-only candidate rules and audit trail.
- `build_ood.py`, `minilm_onnx.py`: Sean's provisional OOD MVP.
- `build_review.py`, `review_template.html`: original offline review tooling reused by v2.
- `finalize_review.py`: original MVP N3 finalizer; use the v2 review package's summarizer for its new batch schema.

See [current data rules](../../docs/home_v2.md), [v2 review instructions](../../data/reviews/abo-home-v2-20261103/README.md), and [original MVP records](../../docs/sean_mvp/README.md). Generated candidate labels are not automatically human-confirmed mismatches.

## Reciprocal N3 development experiment

`reciprocal/` provides deterministic paired color swapping, train-only text-only
diagnostics, an offline review renderer, and strict review summarization.
[Results and reproduction](../../data/reviews/n3-reciprocal-dev-v1/README.md):
80 train candidates reviewed, 60 retained in 30 fully accepted exchanges.
The original v2 release is preserved; this is not a replacement benchmark.
