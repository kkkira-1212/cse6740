# Full fine-tuning validation summary

The definitive control trains both CLIP towers for five epochs at learning rate 3e-5. Checkpoints are selected by validation AUC, including epoch 0. Test was not scored.

Across seeds 0/1/2, validation AUC is 0.982733 ± 0.000470 (sample SD). Per-type means are N1 0.997386, N2 0.974036, and N3 0.973501.

The learning rate was chosen using seed-0 three-epoch development pilots (1e-6, 3e-6, 1e-5, 3e-5). An earlier three-seed run at the LoRA learning rate 1e-4 is retained as development evidence, not pooled with the definitive control. N3 retains its known text shortcut.

Exact histories, hashes, reload checks and validation predictions are in the adjacent per-run files. Full checkpoints remain under ignored `runs/`.
