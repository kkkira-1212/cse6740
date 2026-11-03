# Experiment Entry Points and Status

## Current data

Use [the v2 quickstart](../data/releases/abo-home-v2-20261103/README.md) for paths, scoring and evaluation. v2 scores must be regenerated from exact new pairs; pilot score files and thresholds do not apply.

Each model writes unique `pair_id,score`, with higher values meaning stronger matches. Include dataset version, model/checkpoint, configuration and seed in result filenames and provenance. Keep random-score and smoke-test outputs outside published artifacts. No v2 model inference results are included in the data release.

## Classification evaluation

Aaron's shared evaluator is in [PR #4](https://github.com/kkkira-1212/cse6740/pull/4). The data release bundles a classification-only copy for immediate use, with the legacy three-way R@1 flag blocked. It selects thresholds on validation and evaluates test using fixed settings. Complete val+test scores suffice; train scores may be omitted.

Use identical versions, pairs and exclusions across compared models. One-negative-per-image v2 should not be described as the earlier three-candidate retrieval task. Semantic audit, text-only/image-only controls and final quality certification remain outstanding.

## Additional baselines

Jane's WP7/WP8 implementation is in [PR #5](https://github.com/kkkira-1212/cse6740/pull/5). It contains additional zero-shot encoders/ITM models and an experimental API judge. Availability of implementation does not imply completed API or v2 experiments. Do not reuse cached API judgments keyed only by stable pair IDs after inputs change.

The files edited by those pending PRs are preserved by the data-publication change so it does not add documentation merge conflicts. Model-owner instructions in those branches may still describe the old pilot; use explicit v2 input and image paths from the current release contract.
