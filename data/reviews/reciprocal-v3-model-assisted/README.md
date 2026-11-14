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
