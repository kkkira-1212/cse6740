# LoRA development validation results

Dataset: frozen ABO home v2. These are 656 validation pairs used for checkpoint selection, not held-out test results. No test inference was performed.

| Subset | Pairs | Zero-shot AUC | Selected LoRA AUC |
|---|---:|---:|---:|
| all | 656 | 0.909448 | 0.973453 |
| N1 | 452 | 0.986649 | 0.997295 |
| N2 | 452 | 0.882794 | 0.952105 |
| N3 | 408 | 0.831098 | 0.969588 |

Each negative-type AUC compares all validation positives against only that negative type. Frozen N3 has a known text shortcut; improved N3 AUC does not establish visual color reasoning.

| Epoch | Train loss | Validation AUC | Seconds |
|---|---:|---:|---:|
| 0 | — | 0.909448 | 3.3 |
| 1 | 1.151115 | 0.954408 | 59.2 |
| 2 | 0.531867 | 0.967114 | 58.1 |
| 3 | 0.429035 | 0.971102 | 55.4 |
| 4 | 0.374934 | 0.973174 | 55.9 |
| 5 | 0.343008 | 0.973453 | 55.7 |

Selected epoch: 5. Trainable parameters: 491,520 / 151,768,833 total including adapters (0.324%).

Training/validation loop: 287.6 seconds on MPS; this excludes initial model loading and the final adapter reload check. Reload max score error: 0.0.

The zero-shot validation predictions are from Jack WP5 commit 268a5c5. The initial adapter reproduces its overall validation AUC. The training input and script hashes, exact config and library versions are in the adjacent metadata JSON.

This is one seed and one configuration. Multi-seed variability, rank/tower ablations and full fine-tuning are not completed by this run.
