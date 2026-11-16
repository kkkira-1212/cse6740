# OOD v3 model-assisted QC

`decisions.csv` contains exact negative title/image inputs and initial image
SHA-256 for 74 rows. Reviewer is Codex visual inspection; none are human labels.
The sample uses deterministic SHA-256 ordering from the generator: 10 N1 and 10
N2 per tier, plus every selected N3 direction (34). No model scores were used.

64 proposed mismatch; 10 uncertain. Examples of uncertainty: a lamp's shade and
base have different colors, reflective mesh could be black or silver, the
original Blue lamp appears green/teal, generic sneaker/footwear donor titles lack
clearly contradictory visible attributes. Do not use different listing IDs or
category alone to certify mismatch. Source positives are not fully certified.

`finalize_ood_v3.py` verifies exact reviewed fields and image hashes against the
captured manifest. It excludes whole anchors for uncertain cases and whole
reciprocal exchanges when either direction is flagged, keeping positive/negative
counts balanced in each tier. The retained table still contains unreviewed N1/N2.
Original 600-pair candidates and all judgments are retained. No replacement rows
are sampled after QC. Screening is semantic QC prior to model inference, not
tuning on OOD performance. Team review is still required for final adoption.
