# Additional Baselines

Jane's WP7/WP8 implementation is in [PR #5](https://github.com/kkkira-1212/cse6740/pull/5), still under review. It contains additional zero-shot encoders/ITM models and an experimental API judge. This data release does not imply those experiments are complete or merge that PR.

Use [the v2 data contract](../../data/releases/abo-home-v2-20261103/README.md) for current pair paths and explicit title/image source IDs. Pilot scores and cached API judgments must not be reused for regenerated pairs. Every model outputs unique `pair_id,score`, with larger scores indicating stronger matches.
