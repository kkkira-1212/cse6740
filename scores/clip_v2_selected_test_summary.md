# Frozen held-out CLIP comparison

Model/configuration selection was frozen from validation before test inference. Thresholds are selected independently per checkpoint on validation accuracy and then fixed on test. Each seed's 95% interval uses 1,000 image-anchor-group bootstrap resamples (seed 6740). Across-seed deviations below are sample SDs, not confidence intervals.

| Method | Seeds | Test accuracy mean ± SD | Test AUC mean ± SD | Positive recall | N1 recall | N2 recall | N3 recall |
|---|---:|---:|---:|---:|---:|---:|---:|
| Zero-shot CLIP | 1 | 0.793003 | 0.889400 | 0.874636 | 0.945312 | 0.679688 | 0.413793 |
| LoRA r16 both | 3 | 0.937318 ± 0.001458 | 0.979260 ± 0.000442 | 0.933916 | 0.976562 | 0.888021 | 0.965517 |
| Full both lr3e-5 | 3 | 0.948008 ± 0.001683 | 0.985267 ± 0.001034 | 0.932945 | 0.992188 | 0.921875 | 0.980843 |

Per-seed results and bootstrap intervals are recorded in `clip_v2_selected_test_runs.csv` and the individual evaluator reports. N3 retains the frozen dataset's known text shortcut, so its strong recall is not clean evidence of visual color reasoning.
