# Evaluation

Aaron's shared evaluator is in [PR #4](https://github.com/kkkira-1212/cse6740/pull/4), still separate from this data release.

For immediate v2 classification experiments, use the [bundled classification entry point](../../data/releases/abo-home-v2-20261103/tools/evaluate.py) and [release instructions](../../data/releases/abo-home-v2-20261103/README.md). It selects thresholds on val and evaluates test with fixed settings. The old three-way R@1 flag is disabled for v2's one-negative-per-image layout.

Do not reuse pilot thresholds or scores. All compared models must use the same version, pairs and exclusions. Single-modality controls and final semantic quality review remain outstanding.
