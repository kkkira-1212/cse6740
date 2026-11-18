# Final v3 reporting protocol

Status: adopted reporting scope, 2026-11-18. The collaborator authorized merge
after reviewing the owner updates and Aaron's #19 implementation. Exact sources,
prior test exposure, adopted OOD hashes and remaining model-run prerequisites
are in [the final evaluation handoff](final_evaluation_handoff.md). This records
attributed owner statements, not formal approvals submitted on their behalf.
No new final model inference or result selection is performed by this document.
ID data is `abo-home-v3-20261115`; OOD uses PR #15's adopted 568-pair table.

## Questions and scope

1. Does adapting the SAME CLIP ViT-B/32 improve same-category (N2) and reciprocal
   color (N3) mismatch discrimination relative to its zero-shot checkpoint?
2. Does LoRA approach full-tuning performance with fewer trainable parameters?
3. Is any ID gain accompanied by loss of held-out-category performance on OOD?

BLIP/SigLIP (ALIGN in the appendix) are strong pretrained references,
not architecture-controlled measures of the benefit of CLIP fine-tuning. No
method is required to outperform these baselines for a valid conclusion. Report
no clear benefit or negative transfer when supported; do not manufacture harder
test data or expand tuning to force a win.

## Existing information and selection boundaries

The team has already examined historical v2 results, v3 shortcut-control test
results, and Jane's v3 baseline val diagnostics. This is therefore NOT a pristine
pre-registration or proof the test/source population was never explored. This
document fixes the proposed reporting scope, rather than claiming otherwise.
Each experiment owner must record whether final v3 model test scores had already
been inspected when accepting this protocol. If so, label these added analyses
as retrospective/exploratory rather than prospective confirmatory evidence.

Use already agreed configurations/seeds. Fit on ID train; choose checkpoints
and per-model/per-seed accuracy thresholds using ID val only. Freeze them before
final model test inference. No N2/N3-specific thresholds or selection on test.
Do not change prompts, hyperparameters, exclusions or metrics in response to
favorable/unfavorable test outcomes. Document deviations rather than rewriting
the plan after results. Test resampling analyses reuse saved scores, not tuning.

## Required metrics

All scores are higher-is-match, prediction rule `score >= ID-val threshold`.

| Scope | Required output | Interpretation |
|---|---|---|
| Overall ID test | AUC and accuracy | Broad score separation and operational classification |
| EACH N1/N2/N3 | Matched-anchor AUC | Pool the type's negative rows with only their own anchor positives; compute ordinary ROC AUC on this subset |
| EACH N1/N2/N3 | Negative recall AND corresponding-positive recall | Reject mismatches while retaining true matches at the SAME frozen threshold |
| EACH N1/N2/N3 | Balanced accuracy | Mean of those two recalls, on that matched subset |
| EACH N1/N2/N3 | Paired ranking accuracy and tie count | Fraction with positive score STRICTLY above its own negative; ties count as failures |
| Every reported scope | n_pos, n_neg, independent anchor/exchange count | Prevent percentages hiding small samples |

Matched-anchor AUC is NOT paired ranking accuracy: it pools all relevant
positive/negative scores before computing AUC, rather than comparing only each
pair. Paired ranking is threshold-free relative ordering; it does not establish
both rows were correctly classified. Always name these metrics separately.
Never call negative recall alone overall accuracy. Predicting every row as
mismatch produces 100% negative recall and 0% positive recall.

The overall dataset is balanced, so accuracy equals balanced accuracy there;
do not duplicate both in the main table. Type-specific positive populations
are disjoint by anchor and must not be replaced by all dataset positives.
Do not use donor `text_item_id` as the pairing key: use `anchor_item_id`.
No legacy three-way R@1 for this one-negative-per-image layout.

## Tables and uncertainty

Main ID table: method, seeds, test AUC, accuracy, N1 AUC, N2 AUC, N3 AUC.
Required hard-negative table: method/type, counts, matched AUC, negative recall,
corresponding-positive recall, balanced accuracy, paired ranking accuracy/ties.
Report N1 even if the narrative focuses on N2/N3; do not hide regressions.

For LoRA/full tuning, report all three seeds (0/1/2), mean and sample SD; do not
choose the best test seed. SD across seeds is not a test confidence interval.
Keep zero-shot CLIP results identical across comparisons, not repeated pseudo-seeds.

Report 95% test bootstrap intervals with fixed seed and 1,000 resamples.
Matched N1/N2 subsets resample image-anchor groups, retaining pos/neg together.
N3 resamples complete reciprocal exchanges, retaining both directions and all
their pos/neg rows. If estimating overall intervals, combine N3 exchange blocks
and N1/N2 anchor blocks. If retaining the shared evaluator's anchor-only overall
intervals, explicitly label that they omit reciprocal-exchange dependence.
For deltas, resample the SAME groups for both methods, then subtract metrics;
do not infer significance from comparing separate interval overlaps. Report
per-seed paired deltas without treating seeds and rows as independent samples.

Test N3 has only 30 negatives in 15 exchanges. One negative changes N3 recall
by 3.33 percentage points. Pair directions are dependent; a few corrected
samples are not proof of stable fine-grained color reasoning. Treat N2/N3
comparisons as planned secondary analyses, report all of them, and avoid a
collection of unadjusted significance claims across types/models/seeds.

## Paired error analysis

For each adapted CLIP seed versus zero-shot, join identical final v3 test rows
by `pair_id`. Each model uses its OWN frozen ID-val threshold. For N2/N3 and
their corresponding positives report counts:

- wrong -> correct (corrected errors);
- correct -> wrong (introduced errors);
- correct -> correct; wrong -> wrong.

Also compare pair-ranking wins/losses by `anchor_item_id`, including ties. These
counts describe where adaptation helps/hurts, not a new selection criterion.
Export all changed IDs with original/rewritten titles, scores, predictions,
category, negative type and exchange ID. Any illustrative figure must show both
improvements and failures; do not select only flattering cases. Preserve prior
model-assisted QC flags separately from fresh model errors. Test error analysis
does not justify relabeling the same scored benchmark after inspecting outcomes.

## OOD and ownership

Using the adopted PR #15 OOD table/hash, apply the SAME fixed ID
checkpoints/preprocessing and EACH model's ID-val threshold. Never train on OOD
or use it for checkpoint/prompt/model/threshold selection. Report lighting and
footwear separately, with the same metrics/counts. Negative-type/category mixes
differ from ID: pooled differences alone are not causal domain effects. OOD
means held out from this project's adaptation data, not necessarily unseen in
web-scale pretraining. Small OOD N3 exchange counts require explicit caveats.

- Aaron: shared metrics, matching/exchange resampling and score coverage checks.
- Jinlin: fixed CLIP zero-shot/LoRA/full-tuning scores, selected configurations,
  per-seed predictions, ID thresholds and paired comparisons.
- Jane: pretrained reference scores/metadata under the same ID/OOD protocol;
  Luna is deferred under the adopted scope.
- Yichi: N3/OOD construction, QC provenance/limitations and interpretation.
- Kira/team: preserve the adopted reporting plan and data snapshots. Adoption
  evidence and outstanding execution requirements are recorded in the handoff;
  adoption does not mean final analyses have already been run.
