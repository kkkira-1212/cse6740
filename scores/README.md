# Model Scores

Each score CSV has exactly `pair_id,score`; IDs are unique and higher values mean stronger matches. Keep results tied to a specific data version, model/checkpoint, configuration and seed.

The checked-in `clip_vit_b32_zero_shot.csv` and calibration JSON belong to the original furniture pilot, not v2. No model inference or v2 performance results are included in the data release.

For new runs, use a distinct name such as `abo_home_v2_clip_b32.csv` and follow [the v2 scoring/evaluation instructions](../data/releases/abo-home-v2-20261103/README.md). Never apply an old score file or threshold to new pairs. Smoke-test/random-score outputs should stay outside published artifacts.
