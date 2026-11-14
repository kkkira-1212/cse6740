# Reciprocal N3 full-split benchmark candidate

**Candidate, not frozen. No human certification or shortcut-control pass is claimed.**
This is a proposed successor to `abo-home-v2-20261103`, not a replacement of
that release or PR #10's historical results. Kira/data-owner review and Aaron's
controls remain necessary before selecting this as the final benchmark.

## Construction and population change

Keep ALL original image anchors, positives, product groups and split assignments.
Keep original N1/N2 negatives unchanged. Replace old N3 with accepted reciprocal
N3 where available; otherwise generate a legal N1/N2 title replacement. No
anchor is removed. Compared with v2, the image/positive population is identical,
but negative titles and type proportions change. Overall metrics still mix that
change with model behavior; do not attribute differences solely to training.

Fallback seed is 20261114. Final non-N3 negatives are split approximately equally
between N1/N2 in each split; remaining N2 assignments are proportional to category
using largest remainders. Donors stay within split, differ in group AND image,
and have a different original title from the anchor (case-insensitive). N1 donors
have a different product type; N2 donors have the same type. Among legal donors,
choose least-used title groups (counting preserved N1/N2), with deterministic
SHA-256 tie breaks. No similarity/model mining is used. All 450 fallback rows
remain generated/unreviewed. `fallback_provenance.csv` records each old N3 ID and
new donor; `title_donor_reuse.csv` records final counts (maximum 2, no soft-limit
exceedances). `excluded_anchors.csv` is now header-only, superseding the earlier
draft deletion policy. Structural legality does not establish semantic mismatch.
A model-assisted train spot check of 10 new N1 and 10 new N2 rows found 16 clear
mismatches and 4 uncertain cases; the ledger is under
`data/reviews/reciprocal-v3-model-assisted/fallback_train_spotcheck.csv`. It does
not certify the fallback pool. No rows were resampled based on this check.
Follow-up proposals after Kira's technical review are appended in
`data/reviews/reciprocal-v3-model-assisted/fallback_train_adjudications.csv`:
the chair's closed-back contradiction supports a proposed mismatch; the rod/rings
case is now uncertain, and the framed-wall-art explanation is corrected. Original
review records and all data rows/labels are unchanged. Carry the current four
uncertainty flags with diagnostic controls; see the review README for exact IDs.

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
| train | 2664 | 1199 | 1199 | 266 | 5328 |
| val | 328 | 152 | 152 | 24 | 656 |
| test | 343 | 156 | 157 | 30 | 686 |

Val/test N3 are small (12/15 reciprocal exchanges). Do not claim precise
category/color generalization from these sample sizes. Each included anchor
has one positive and one negative with identical images. No old-rule N3 remains.
Review exclusions apply to N3 proposals only: their anchors remain with fallback
N1/N2. Original-color ambiguity flags remain in the review ledger; keeping all
original positives does not certify those titles. Review decisions use no model
performance metrics. All 3,335 original image anchors and 6,670 pairs are retained.

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

1. Data owners review the fallback policy, generated N1/N2 quality and model-assisted ledger.
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
