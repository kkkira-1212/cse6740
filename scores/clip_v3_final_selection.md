# Frozen V3 ID-validation selection

Seven evaluation entries are frozen locally before ID-test or OOD inference: one deterministic zero-shot baseline, three rank-16 both-tower LoRA seeds, and three full-tuning seeds at LR 3e-5.

Thresholds maximize ID-validation accuracy; ties select the smallest threshold. Prediction uses `score >= threshold`. The protocol smoke output verifies matched N1/N2/N3 metrics, strict paired ranking, zero-shot-to-adapted error transitions, and 1,000-resample reciprocal-exchange N3 intervals on validation only.

| Model | Threshold | Val accuracy |
|---|---:|---:|
| clip_zero_shot_v3 | 0.2860452800 | 0.868902 |
| clip_lora_v3_r16_both_seed0 | 0.3636996700 | 0.928354 |
| clip_lora_v3_r16_both_seed1 | 0.3577834700 | 0.931402 |
| clip_lora_v3_r16_both_seed2 | 0.3708580700 | 0.929878 |
| clip_full_v3_both_seed0 | 0.4175822100 | 0.934451 |
| clip_full_v3_both_seed1 | 0.4211232100 | 0.935976 |
| clip_full_v3_both_seed2 | 0.4741435600 | 0.942073 |

No ID-test or OOD scores were read or generated.
