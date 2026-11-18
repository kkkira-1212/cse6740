# V3 fixed-config LoRA validation summary

Rank 16 on both CLIP towers was selected by the historical V2 validation ablation before V3 model runs. These three V3 runs use the frozen `abo-home-v3-20261115` snapshot and perform no held-out test inference.

Across seeds 0/1/2, validation AUC is 0.972911 ± 0.000692 (sample SD). Matched-anchor per-type validation AUC means are N1 0.998355, N2 0.945031, and N3 0.999421.

Exact configs, histories, data/trainer/checkpoint hashes, reload checks and validation predictions are stored in the adjacent files. Test evaluation remains deferred pending the team meeting.
