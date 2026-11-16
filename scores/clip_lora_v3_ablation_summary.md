# LoRA validation ablation matrix

Completed: 15/15 runs.

Five configurations, seeds 0/1/2, five training epochs each. All hyperparameters except tower/rank/seed are shared; alpha/rank stays at 2. Each checkpoint is selected by validation AUC, including epoch 0. These are development validation results; test was not scored.

Reported deviations are sample standard deviations across seeds (ddof=1), not test confidence intervals. Each per-type AUC uses all validation positives and the specified negative type.

| Towers | Rank | Seeds | Trainable params | Val AUC mean ± SD | N1 AUC | N2 AUC | N3 AUC | Mean seconds |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| both | 8 | 3 | 491,520 | 0.969051 ± 0.000943 | 0.997299 | 0.941705 | 0.963330 | 270.3 |
| both | 4 | 3 | 245,760 | 0.964381 ± 0.000652 | 0.997199 | 0.931316 | 0.965955 | 263.1 |
| both | 16 | 3 | 983,040 | 0.972911 ± 0.000692 | 0.997720 | 0.950063 | 0.960493 | 296.5 |
| text | 8 | 3 | 196,608 | 0.939920 ± 0.001095 | 0.992900 | 0.904391 | 0.829395 | 187.2 |
| vision | 8 | 3 | 294,912 | 0.955130 ± 0.000787 | 0.997459 | 0.915109 | 0.940506 | 206.2 |

Timings include epoch training and validation, excluding initial model load and final adapter reload verification. Runs execute sequentially on the same device; this is not a hardware-controlled speed benchmark.

The initial zero-shot validation AUC is 0.924059. Frozen data, exact configs, per-run histories and checkpoint hashes are recorded in the adjacent metadata files. Adapter weights remain local under ignored runs/.
