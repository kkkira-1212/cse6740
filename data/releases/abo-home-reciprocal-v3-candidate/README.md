# Reciprocal N3 full-split benchmark candidate

**Candidate, not frozen. No human certification or shortcut-control pass is claimed.**
This is a proposed successor to `abo-home-v2-20261103`, not a replacement of
that release or PR #10's historical results. Kira/data-owner review and Aaron's
controls remain necessary before selecting this as the final benchmark.

## Construction and population change

Keep the original product groups and split assignments. Keep original N1/N2
negatives where an anchor has no reciprocal replacement. Replace a selected
anchor's negative with reciprocal N3. Remove old-rule N3 anchors lacking an
accepted reciprocal replacement, including their positives. This explicit
reduced-population policy avoids filling missing N3 with new, unreviewed N1/N2.
It changes negative proportions and the evaluated population; v2 and this
candidate's headline metrics are **not a controlled apples-to-apples comparison**.

Train uses the exact previous 266-negative supplemental pool (158 human-reviewed,
108 generated/unreviewed); previous human judgments are unchanged. Held-out
candidates use `build_expanded_n3.generate` independently in val and test with
the pre-existing color rules and same-split/category matching. No model scores,
performance thresholds, or test metrics were used to construct/select rows.

76 held-out candidate negatives were visually inspected by Codex using the
release images, verified against v2 SHA-256 hashes. The decision ledger is
`data/reviews/reciprocal-v3-model-assisted/decisions.csv`. Exclude a complete
exchange when either negative is not clearly a mismatch or the original color
is uncertain. Eleven exchanges (22 negatives) are excluded, leaving 54 negatives.
The generated, pre-review table is retained for audit. Model-assisted decisions
are not human judgments; these inspections check visible color consistency,
not every dimension/material/count claim in the positive title. N1/N2 and their
positives are not re-audited by this work.

| Split | Positives | N1 | N2 | N3 | Total rows |
|---|---:|---:|---:|---:|---:|
| train | 2327 | 1030 | 1031 | 266 | 4654 |
| val | 272 | 124 | 124 | 24 | 544 |
| test | 286 | 128 | 128 | 30 | 572 |

Val/test N3 are small (12/15 reciprocal exchanges). Do not claim precise
category/color generalization from these sample sizes. Each included anchor
has one positive and one negative with identical images. No old-rule N3 remains.
Review exclusions are semantic QC, not selection on held-out model performance.

## Reproduce and use

From repository root, in the shared numpy/scikit-learn environment:

```sh
python src/negatives/reciprocal/build_benchmark_candidate.py
python -m unittest discover -s tests -v
```

`manifest.json` binds source/review and output tables by SHA-256. Input text hashes
normalize CRLF to LF; output tables are written with LF. CSV schema
matches v2, with explicit `dataset_version` and label status. Pair IDs retain
anchor semantics but are reused across releases: always bind caches/results to
the dataset version AND input hash. Never append this table to v2.

Images and item metadata are reused from v2, unchanged. Run its image downloader:

```sh
python data/releases/abo-home-v2-20261103/tools/download_images.py
```

Use this directory's `pairs.csv` with image root
`data/releases/abo-home-v2-20261103/images`. Do not use v2's standalone verifier
on this candidate's table; the new builder runs candidate structural checks.
Use the shared evaluator with this pairs table and fresh scores, recalibrating
thresholds on val only. Do not reuse v2 thresholds or score caches.

## Before final adoption

1. Data owners review the population/coverage policy and model-assisted ledger.
2. Agree on shortcut-control criteria before running controls; report overall
   and per-negative-type results, including N3 versus its corresponding positives.
3. Aaron runs text-only/image-only controls with train fitting and val thresholds.
   Word/character controls are useful; chance-like AUC alone does not certify labels.
4. Keep reciprocal exchanges together in resampling/diagnostics because the two
   directions share construction. Existing image-anchor intervals do not account
   for all exchange dependence; document or update that analysis.
5. Freeze the adopted version/hash and fixed model settings, then rerun zero-shot,
   LoRA r16 both (seeds 0/1/2), and full tuning (seeds 0/1/2). If controls reveal a
   problem, keep this candidate diagnostic; do not repeatedly tune rules on test.

No training, held-out model scoring, or release publication was performed here.
