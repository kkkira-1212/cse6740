# Final V3 evaluation handoff

Recorded 2026-11-18. This document adopts the reporting scope and OOD evaluation
population, preserves the evidence available at adoption, and separates code
integration from readiness to run each final model. It is not a claim that all
owners submitted formal GitHub approvals or that final inference is complete.

## Decisions and evidence

- ID: adopted `abo-home-v3-20261115`, with its existing reciprocal-candidate
  storage identity. Pairs SHA-256:
  `14814aa6bba905c07377a929c44e7d28b76893497c9c59eb86b8b6a9da334003`.
- OOD: adopt PR #15's screened 568-pair population without changing any table,
  label, exclusion or review decision. The full 600-pair construction remains.
  [Machine-readable freeze](../data/releases/abo-ood-v3-20261115-candidate/evaluation_freeze.json)
  binds the exact hashes, construction commit, adoption merge and counts.
- Reporting: adopt [the #16 protocol](v3_evaluation_protocol.md), using
  [Aaron's #19 shared evaluator](../src/eval/README.md) for final reporting.
  Jack's `final_protocol.py` validation utilities remain development evidence;
  do not silently mix output schemas or bootstrap conventions.
- Main pretrained references: BLIP and SigLIP; ALIGN in the appendix. Luna is
  deferred. These are cross-architecture references, not controlled estimates
  of CLIP adaptation benefit.

| Owner | Evidence available at adoption | Scope and limits |
|---|---|---|
| Kira | [PR15 review](https://github.com/kkkira-1212/cse6740/pull/15#pullrequestreview-5914444996), [PR16 review](https://github.com/kkkira-1212/cse6740/pull/16#pullrequestreview-5914445298) | Supports data/exclusions/reporting; did not independently repeat visual QC or image verification. |
| Aaron | [PR19](https://github.com/kkkira-1212/cse6740/pull/19), head `f01d9277ab62c00868b89e81d0b5f4d8bb1d525d`; screenshot of owner message supplied by collaborator | Implemented matched metrics, paired errors and ID-fitted OOD shortcut probe; owner said the corresponding eval was added and could merge if evaluation checks passed. This is implementation/interface evidence, not a new claim about unseen final model test scores. |
| Jinlin / Jack | [PR17](https://github.com/kkkira-1212/cse6740/pull/17), head `f950b01180f850a5fe048e9718ea134caa492636`; team update relayed by collaborator | Seven selected entries, own ID-val thresholds, checkpoint/config/score hashes and compute records. PR explicitly states no V3 ID-test/OOD inference. Relayed update says final runs await #15/#16. |
| Jane | [PR18](https://github.com/kkkira-1212/cse6740/pull/18), head `a3700f5cd1f80d111634d60f56da967ffc56af4e`; team update relayed by collaborator | Relayed update explicitly accepts #16, says results are val-only, selects BLIP/SigLIP main and ALIGN appendix, and defers Luna. Precise revisions and threshold records remain prerequisites below. |

The relayed team messages were provided in the collaborator's 2026-11-18 review
session; their original chat timestamps were not independently verified. They
are attributed statements, not formal approvals fabricated on owners' behalf.
The collaborator explicitly authorized merge/documentation on that date.
Historical v2 results and V3 shortcut-control test results were already viewed.
Do not describe the whole project as a pristine prospective preregistration.
Owners must record any subsequent final-model test/OOD exposure or deviations.

## OOD counts and limitations retained in the report

| Split | Pairs | Positive | N1 | N2 | N3 negative | N3 exchanges |
|---|---:|---:|---:|---:|---:|---:|
| `ood_near` lighting | 276 | 138 | 64 | 62 | 12 | 6 |
| `ood_far` footwear | 292 | 146 | 68 | 68 | 10 | 5 |

Only 74 original candidate negatives received model-assisted visual QC (64
proposed mismatch, 10 uncertain). This is not independent human certification
of the 568 retained rows. Unsampled N1/N2 remain generated candidates and
original listing positives are unverified. Sixteen anchors were excluded with
their positives and complete affected N3 exchanges, without replacements;
screening therefore changes the evaluation population. Keep the original
candidate, review ledger and exclusion history. The very small N3 exchange
counts preclude precise color-generalization claims. Global grouping is
heuristic and prior pilot source exposure remains disclosed. This is category
shift within ABO, not cross-source/time evidence or proof of unseen pretraining
categories.

## Final scoring prerequisites

1. Every owner pulls the merged code, verifies `evaluation_freeze.json` and the
   ID manifest, and records the code commit actually used. Verify downloaded
   images with each release's verifier before inference.
2. Jack uses `configs/clip_v3_final_selection.json`: one deterministic zero-shot
   CLIP, rank-16 both-tower LoRA seeds 0/1/2, full tuning LR 3e-5 seeds 0/1/2,
   each with its own frozen ID-val threshold. Weights remain local and must
   match their recorded hashes. The existing `score_selected_checkpoints.py`
   is a historical V2 val/test runner; it does not accept the V3 final-selection
   schema or arbitrary OOD splits. Jack must supply/verify that entry point
   before final scoring, preserving the frozen model/preprocessing/thresholds.
3. Jane records the exact model and processor revisions actually used for the
   saved val predictions, plus preprocessing/environment, score hashes and
   maximum-ID-val-accuracy thresholds (ties: smallest threshold). Current
   `*_val_meta.json` files have `revision: main`, `resolved_commit: null`.
   Recover the actual cached revisions or weight hashes; a newly resolved
   current `main` is not proof of the prior val checkpoint. If recovery is
   impossible, rerun ID val with a pinned revision and freeze it before test.
4. Jane's `run_wp8.sh` final mode currently reloads default `main`, updates its
   environment and omits matched-metric flags. Use verified explicit scoring
   commands with `--revision <frozen-commit>`, or fix that runner before final
   inference. Reuse the same model/processor for ID and OOD. Do not rerun the
   default command as evidence of a pre-frozen final run.
5. Produce complete `pair_id,score` files (higher is match); no duplicate,
   missing, unknown or nonfinite scores. Apply each model/seed's own ID-val
   threshold (`score >= threshold`), never a threshold selected on OOD/test.
   Retain all seeds; report mean and sample SD separately from test intervals.

These are execution requirements, not permission for further model selection.
No OOD training, prompt tuning, threshold fitting, outcome-driven exclusions,
or best-test-seed selection is permitted.

## Shared final evaluation commands

Run ID and OOD separately so provenance files and split scopes are explicit.
Replace filenames and threshold placeholders with the frozen values for each
model/seed. These commands evaluate saved scores; they do not run a model.

```sh
python src/eval/eval.py \
  --pairs-csv data/releases/abo-home-reciprocal-v3-candidate/pairs.csv \
  --scores-csv scores/MODEL_id.csv \
  --test-splits test --fixed-threshold ID_VAL_THRESHOLD \
  --matched-type-metrics \
  --n3-provenance data/releases/abo-home-reciprocal-v3-candidate/n3_provenance.csv \
  --bootstrap 1000 --seed 0

python src/eval/eval.py \
  --pairs-csv data/releases/abo-ood-v3-20261115-candidate/eval_pairs.csv \
  --scores-csv scores/MODEL_ood.csv \
  --test-splits ood_near ood_far --fixed-threshold ID_VAL_THRESHOLD \
  --matched-type-metrics \
  --n3-provenance data/releases/abo-ood-v3-20261115-candidate/eval_n3_provenance.csv \
  --bootstrap 1000 --seed 0
```

OOD N3 provenance uses an internal pair suffix; the shared code maps by
`anchor_item_id`. It retains 22 negatives in 11 complete exchanges. Do not use
donor `text_item_id` as the pairing key. No legacy three-way R@1.

Report overall AUC/accuracy and matched N1/N2/N3 AUC, negative and corresponding
positive recall, balanced accuracy, strict paired-ranking accuracy/ties and
counts. N3 matched intervals resample complete exchanges; N1/N2 resample anchor
groups. Existing overall intervals remain anchor-only: explicitly state that
they omit reciprocal-exchange dependence. `paired_errors.py` exports descriptive
corrected/introduced counts and ranking changes; it does not implement paired
confidence intervals for model deltas. If reporting delta intervals or
significance, implement/verify same-block paired resampling first; do not infer
significance from separate CI overlap. Keep ID, near OOD and far OOD separate.

## Amazon Reviews 2023 remains a separate work item

WP9 originally assigns Amazon Reviews 2023 field/time research and a compatible
test table to Aaron. No corresponding pushed dataset, builder or delivery PR
was found during the 2026-11-18 repository check. This is not proof that no
local work exists. Aaron should report progress, field/time feasibility, scope
and delivery path. PR #19's OOD shortcut tool operates on ABO and does not
complete WP9. Do not delay the already adopted ABO benchmark to silently add a
new source, and do not label ABO category-shift results cross-source/time.

## Integration verification

The combined #15/#17/#18/#19 checkout passed 96 data/evaluation tests, including
the real OOD-table integration checks. No new final V3 model ID-test/OOD scores
were generated by that review; tests use fixtures, synthetic scores and saved
control scores, including a lightweight ID-fitted shortcut smoke run.
The complete suite subsequently passed **109 tests** using Python 3.11.16,
CPU torch 2.15.0+cpu, transformers 5.21.0, peft 0.21.2, numpy 2.4.6 and
scikit-learn 1.9.1. Windows test invocation uses `python -X utf8 -m unittest
discover -s tests`. These fixture tests do not independently reproduce the
locally held selected checkpoints or the original MPS environment.
Windows CRLF checkout can break the frozen trainer's byte hash; `.gitattributes`
now pins that trainer and the CLIP config/score files to LF, preserving their
Git blob contents and existing hashes. Dataset/review hash verifiers pass.
