# Documentation

## Current data handoff

- [Furniture + Decor v2 guide](home_v2.md): scope, grouping, splits and negative-generation policy.
- [Release quickstart and contract](../data/releases/abo-home-v2-20261103/README.md): data tables, images, scoring and classification evaluation.
- [100-pair human-review batch](../data/reviews/abo-home-v2-20261103/README.md): review/download instructions and provenance.
- [Generation configuration](../configs/abo_home_v2.json): the exact parameters used by the release builder.
- [Environment setup](environment_setup.md): the shared project environment.

## Historical pilot and planning

The following records are preserved, but their scope, negative direction, balance and pair-ID assumptions may be superseded by the v2 guide:

- [Original furniture pilot](mini_version/README.md), product/pair tables and preliminary CLIP scores.
- [Sean's N3/OOD MVP](sean_mvp/README.md) and original human-review records.
- [Pilot schema](schema.md).
- [Original design](design.md), [planning decisions](open-decisions.md) and [work packages](work-packages.md).
- [Original category counts](category_counts.md).

Use one data version consistently. Do not combine historical thresholds, scores, review judgments or inferred source IDs with a new release.
