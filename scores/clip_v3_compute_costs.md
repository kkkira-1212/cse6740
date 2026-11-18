# V3 validation compute cost

Measured wall-clock time on local Apple MPS. These are device-time proxies, not cloud billing costs; monetary cost is not applicable. Model loading, validation, checkpoint saving and reload verification are included in each recorded run where performed.

| Family | Runs | Seconds | Device-hours |
|---|---:|---:|---:|
| zero_shot | 3 | 17.3 | 0.0048 |
| lora | 15 | 3670.2 | 1.0195 |
| full | 3 | 1882.1 | 0.5228 |
| **total** | **21** | **5569.6** | **1.5471** |

The detailed CSV contains every run, seed, parameter count and elapsed time. Test inference is not included because test was not scored.
