# LoRA validation ablation matrix

Completed: 15/15 runs.

Five configurations, seeds 0/1/2, five training epochs each. All hyperparameters except tower/rank/seed are shared; alpha/rank stays at 2. Each checkpoint is selected by validation AUC, including epoch 0. These are development validation results; test was not scored.

Reported deviations are sample standard deviations across seeds (ddof=1), not test confidence intervals. Each per-type AUC uses all validation positives and the specified negative type. N3 retains its known text shortcut.

| Towers | Rank | Seeds | Trainable params | Val AUC mean ± SD | N1 AUC | N2 AUC | N3 AUC | Mean seconds |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| both | 8 | 3 | 491,520 | 0.972648 ± 0.001096 | 0.997213 | 0.951523 | 0.967315 | 278.8 |
| both | 4 | 3 | 245,760 | 0.968536 ± 0.000625 | 0.996927 | 0.941696 | 0.966133 | 267.6 |
| both | 16 | 3 | 983,040 | 0.975545 ± 0.000187 | 0.997541 | 0.958481 | 0.967899 | 268.4 |
| text | 8 | 3 | 196,608 | 0.945323 ± 0.000945 | 0.991231 | 0.907053 | 0.933486 | 191.6 |
| vision | 8 | 3 | 294,912 | 0.955867 ± 0.000387 | 0.997205 | 0.926878 | 0.936725 | 207.9 |

Timings include epoch training and validation, excluding initial model load and final adapter reload verification. Runs execute sequentially on the same device; this is not a hardware-controlled speed benchmark.

The initial zero-shot validation AUC is 0.909448. Frozen data, exact configs, per-run histories and checkpoint hashes are recorded in the adjacent metadata files. Adapter weights remain local under ignored runs/.
