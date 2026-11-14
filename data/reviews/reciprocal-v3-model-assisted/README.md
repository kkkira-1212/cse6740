# Model-assisted held-out color review

`decisions.csv` records Codex visual inspection of all 76 generated val/test
reciprocal negatives and their original titles. This is **not human review**.
Image hashes bind the exact v2 release images, and `pair_sha256` binds each
pre-review generated candidate. No previous human-review file is modified.

Protocol: inspect each product image against the original title color and the
proposed replacement. Mark a negative mismatch only when its changed color
clearly conflicts with the principal product surface. Use uncertain for
multicolor/partially descriptive colors, obscured products, or ambiguous shades.
Original-color ambiguity is recorded separately. Do not infer non-visible
properties or certify the full listing title. Whole-exchange exclusion follows
if either direction is uncertain/matching or its original-color check is uncertain.

The ledger has 67 mismatch and 9 uncertain negative decisions. Three additional
original-color checks are uncertain (and one obscured rug is uncertain in both
fields). Eleven complete exchanges are excluded. The remaining 54 negatives
are model-assisted candidates, not human-certified ground truth.

Reviewers can revise this ledger with provenance in a follow-up commit and
rebuild the candidate. No model scores were viewed or used for these decisions.

## Fallback train N1/N2 spot check

`fallback_train_spotcheck.csv` records model-assisted visual checks of 20 new
train fallback rows (10 N1, 10 N2). Sample selection sorts each train/type stratum
by SHA-256 of `fallback-qc-20261114:` + pair ID and takes 10. All images were
verified against the v2 image hashes. Results: 16 mismatch, 4 uncertain, no
confident match. Ambiguity includes lifestyle images showing a secondary object,
nearby rug/chair colors, and similar gray sofas. This small targeted train sample
is not a population error-rate estimate or human certification. No candidates
were resampled or dropped after this check, and all 450 fallback rows retain
generated/unreviewed status. Kira should review these flagged rows before final
adoption; any resulting change must be explicit and versioned.

## Follow-up after Kira's technical review

The original spot-check CSV above is preserved verbatim. The 2026-11-14
`fallback_train_adjudications.csv` appends six model-assisted follow-up proposals
after [Kira's review](https://github.com/kkkira-1212/cse6740/pull/12#issuecomment-6881272896).
Each row binds the original ledger, exact candidate commit/pairs hash, image
hash, previous decision and new reasoning. The companion
`fallback_adjudication_manifest.json` binds these records. None are human
judgments, and none change candidate rows, training labels or sampling.

| Pair ID | Follow-up proposal | Reason |
|---|---|---|
| B07Q88MYL4_N1 | uncertain | Rug scene contains an armchair that could fit the substituted title. |
| B07TTCHRB2_N2 | uncertain | Actual rug dimensions/material cannot be confirmed from the image. |
| B07DBLN3V2_N2 | mismatch, model-assisted proposal | Visible closed tufted back contradicts the explicit Open Back title. |
| B07JD7RFRN_N2 | uncertain | Gray sofa may fit the loveseat title; width/model is unverified. |
| B075H8JNZT_N2 | uncertain; original reason invalid | Title includes both a rod AND rings; off-frame accessories do not prove mismatch. Finial detail is insufficient for a confident conclusion. |
| B082VFPPJM_N1 | mismatch; explanation corrected | Padded ottoman/stool image contradicts framed abstract wall art, not a supposed white-wood ottoman. |

For reporting, overlay the six proposals by `pair_id` on the 20-row original
spot check, while retaining both histories: still 16 proposed mismatches and
4 uncertain cases, but the uncertain set has changed. Current uncertainties are
`B07Q88MYL4_N1`, `B07TTCHRB2_N2`, `B07JD7RFRN_N2`, `B075H8JNZT_N2`.
The closed-back chair proposal is not silently promoted to human verification.
All fallback training labels remain generated/unreviewed, including flagged rows.

Aaron may run diagnostic controls on Kira-reviewed commit
`b1b0aaa7a6d2e999225f87e3b51af38df6252bb0`, with pairs SHA-256
`14814aa6bba905c07377a929c44e7d28b76893497c9c59eb86b8b6a9da334003`,
carrying this follow-up ledger alongside results. The candidate data/hash is
unchanged by this follow-up; the PR head advances for metadata/tests only.
This is not final benchmark approval. Resolve or explicitly document remaining
QC uncertainty and agree control criteria before final adoption.
