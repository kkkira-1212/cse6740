# Experiment Entry Points and Status

## Current data

Use [the v2 quickstart](../data/releases/abo-home-v2-20261103/README.md) for paths, scoring and evaluation. v2 scores must be regenerated from exact new pairs; pilot score files and thresholds do not apply.

Each model writes unique `pair_id,score`, with higher values meaning stronger matches. Include dataset version, model/checkpoint, configuration and seed in result filenames and provenance. Keep random-score and smoke-test outputs outside published artifacts. No v2 model inference results are included in the data release.

## Classification evaluation

Aaron's shared evaluator was merged via [PR #4](https://github.com/kkkira-1212/cse6740/pull/4). Use `src/eval/eval.py` for the current shared entry point. The data ZIP also preserves a standalone classification-only snapshot, with matching classification metrics and the legacy three-way R@1 flag blocked. It selects thresholds on validation and evaluates test using fixed settings. Complete val+test scores suffice; train scores may be omitted.

Use identical versions, pairs and exclusions across compared models. One-negative-per-image v2 should not be described as the earlier three-candidate retrieval task. Semantic audit, text-only/image-only controls and final quality certification remain outstanding.

## Additional baselines

Jane's WP7/WP8 implementation was merged via [PR #5](https://github.com/kkkira-1212/cse6740/pull/5). It contains additional zero-shot encoders/ITM models and an experimental API judge. Availability of implementation does not imply completed API or v2 experiments. Do not reuse cached API judgments keyed only by stable pair IDs after inputs change.

Both implementations include fixed-image v2 compatibility. API resume fingerprints bind exact inputs/prompts/settings; subset sampling keeps explicit image-anchor groups together. Historical pilot examples remain in model-owner documentation, so provide the v2 pair and image paths explicitly as shown in the release contract.

## LoRA development

Jack's [first v2 LoRA protocol](jack_wp6_training.md) uses both CLIP towers' Q/V
projections, rank 8, seed 0 and explicit negative titles in InfoNCE. The trainer
uses train for gradients and val AUC for checkpoint selection, including the
initial adapter. It performs no test inference. The frozen N3 rules and their
known shortcut are retained; the reciprocal training pool is not appended.
Rank/tower/seed comparisons and the full-fine-tuning control remain subsequent
experiments. Development validation scores are not held-out test results.
