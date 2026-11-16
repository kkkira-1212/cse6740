# V3 local pre-test handoff

Status: complete locally; not committed or pushed. No ID-test or OOD inference was run.

## Work completed

1. Froze seven ID-validation accuracy thresholds: one deterministic CLIP zero-shot baseline, rank-16 both-tower LoRA seeds 0/1/2, and full-tuning LR 3e-5 seeds 0/1/2.
2. Added and tested final-protocol metrics for matched N1/N2/N3 AUC and recalls, balanced accuracy, strict paired ranking and ties, zero-shot-to-adapted prediction/ranking transitions, and 1,000-resample complete-exchange N3 bootstrap intervals.
3. Froze a local selection manifest binding the V3 pairs, scores, configs, metadata, checkpoints and compute-cost artifacts by SHA-256.

Thresholds maximize ID-validation accuracy; ties select the smallest threshold and predictions use `score >= threshold`.

| Model | ID-val threshold | ID-val accuracy |
|---|---:|---:|
| zero-shot CLIP | 0.28604528 | 0.868902 |
| LoRA seed 0 | 0.36369967 | 0.928354 |
| LoRA seed 1 | 0.35778347 | 0.931402 |
| LoRA seed 2 | 0.37085807 | 0.929878 |
| full seed 0 | 0.41758221 | 0.934451 |
| full seed 1 | 0.42112321 | 0.935976 |
| full seed 2 | 0.47414356 | 0.942073 |

On the validation N2/N3 matched rows, adapted models corrected 49–56 zero-shot row-level errors while introducing 8–10 errors, depending on model/seed. This is implementation/development evidence only, not a held-out final claim.

Validation checks: 81 tests passed; deterministic re-export succeeded; checkpoint and score hashes match; V3 N3 validation bootstrap uses all 12 complete reciprocal exchanges.

## Next gated actions

- Wait for PR #15 to merge and publish the adopted OOD table/hash.
- Wait for PR #16 metric definitions to be accepted.
- Only then run the frozen checkpoints and thresholds once on final ID test and OOD.
