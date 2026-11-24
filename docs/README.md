# Documentation

## Current data handoff

- [Final evaluation handoff](final_evaluation_handoff.md): adoption evidence,
  frozen OOD hashes, model-run prerequisites and Amazon Reviews WP9 status.

- [Adopted OOD v3 population](../data/releases/abo-ood-v3-20261115-candidate/README.md):
  lighting/footwear held-out category tests, ID-global grouping checks, explicit
  model-assisted QC and fixed-ID-threshold handoff; 568-pair table hash-pinned.
- [Adopted v3 reporting protocol](v3_evaluation_protocol.md): overall and
  matched N2/N3 metrics, paired error analysis, uncertainty and ID/OOD selection
  boundaries; adoption evidence and execution requirements in the handoff.

- [Furniture + Decor v2 guide](home_v2.md): scope, grouping, splits and negative-generation policy.
- [Release quickstart and contract](../data/releases/abo-home-v2-20261103/README.md): data tables, images, scoring and classification evaluation.
- [100-pair human-review batch](../data/reviews/abo-home-v2-20261103/README.md): review/download instructions and provenance.
- [Generation configuration](../configs/abo_home_v2.json): the exact parameters used by the release builder.
- [Experiment entry points and status](experiments.md): current scoring and evaluation interfaces, plus pending model PRs.
- [Amazon Reviews 2023 Home & Kitchen source items](amr_home.md): intermediate cross-source pilot, category mapping and image downloader.
- [Environment setup](environment_setup.md): the shared project environment.

## Historical pilot and planning

The following records are preserved, but their scope, negative direction, balance and pair-ID assumptions may be superseded by the v2 guide:

- [Original furniture pilot](mini_version/README.md), product/pair tables and preliminary CLIP scores.
- [Sean's N3/OOD MVP](sean_mvp/README.md) and original human-review records.
- [Pilot schema](schema.md).
- [Original design](design.md), [planning decisions](open-decisions.md) and [work packages](work-packages.md).
- [Original category counts](category_counts.md).

Use one data version consistently. Do not combine historical thresholds, scores, review judgments or inferred source IDs with a new release.
