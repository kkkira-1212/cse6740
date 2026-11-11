# WP6: LoRA ablation and full fine-tuning on frozen ABO home v2

The first complete LoRA run increased validation AUC from 0.909448 to
0.973453; epoch 5 was selected. It trained 491,520 adapter parameters on MPS in
287.6 seconds including validation. The saved adapter reproduces its selected
scores exactly after reload. See the [validation report](../scores/clip_lora_v2_r8_both_seed0_val.md),
[scores](../scores/clip_lora_v2_r8_both_seed0_val.csv) and
[run metadata](../scores/clip_lora_v2_r8_both_seed0_meta.json).
All 51 tests passed. These results are a single-seed development run, not test
performance or a completed ablation study.

## Protocol fixed before training

Use the unchanged `abo-home-v2-20261103` release. Train has 2,664 image anchors
(5,328 labeled pairs); validation has 656 pairs; test has 686 pairs. No reciprocal
N3 supplement is appended. Generated N3 labels have a known text shortcut;
retain that limitation and report N1/N2/N3 separately in subsequent held-out
evaluation. This experiment does not repair or certify the dataset.

The first configuration is `configs/clip_lora_v2_r8_both_seed0.json`:

| Setting | Value |
|---|---|
| Base | CLIP ViT-B/32, revision `3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268` |
| LoRA | Both vision and text towers; attention Q and V projections |
| Rank / alpha / dropout | 8 / 16 / 0 |
| Optimizer | AdamW, learning rate 1e-4, weight decay 0.01 |
| Training | 5 epochs; 16 image anchors per batch; seed 0; float32 |
| Schedule | 10% linear warmup, cosine decay; gradient clipping norm 1 |
| Temperature | Fixed 0.07; pretrained logit scale is unused and frozen |
| Selection | Highest validation AUC, including the initial untrained adapter; earlier epoch wins ties |
| Scoring | Cosine similarity, higher means more consistent |

Each minibatch uses B images, B original positive titles and B explicit negative
titles. Image-to-text InfoNCE compares each image to all 2B titles. The reverse
loss compares only the B original positive titles to the B images. Average the
two losses. The negative title paired with an image is never a diagonal positive
target merely because it appeared as a row in the pair table.

Repeated tokenized titles are multiple known positives for their corresponding
original image. This handles donor titles repeated within a batch and collisions
after CLIP's 77-token truncation. Unknown semantic false negatives remain possible;
the training objective cannot correct noisy candidate labels.

Only LoRA weights receive gradients. Positive/negative pairs stay together as
one anchor, and every train anchor is used once per epoch. No negative-type
oversampling, validation augmentation or test-based configuration selection.
Data are preprocessed using the fixed pretrained processor without new random
image augmentations. Seeds are fixed; exact GPU bitwise reproducibility across
hardware/software versions is not promised.

## Run

From the repository root, using the documented `cse6740` environment:

```bash
python src/models/train_clip_lora.py \
  --config configs/clip_lora_v2_r8_both_seed0.json \
  --run-dir runs/clip_lora_v2_r8_both_seed0_smoke --device auto --smoke

python src/models/train_clip_lora.py \
  --config configs/clip_lora_v2_r8_both_seed0.json \
  --run-dir runs/clip_lora_v2_r8_both_seed0 --device auto
```

The smoke run uses 32 train anchors, 16 validation anchors and one epoch. It is
not an experiment result. Run directories must be new, preventing accidental
checkpoint overwrite. Model weights remain in ignored `runs/`; small metadata
and validation-score exports may be committed separately.

`training.json` records the exact configuration, input/code hashes, target
layers, trainable parameters, environment, epoch losses/AUCs, selection and
elapsed time. `best_adapter/` stores the selected adapter and `val_scores.csv`
stores its validation predictions. The final validation predictions are checked
against a freshly loaded adapter, with maximum tolerated score error 1e-5.

No test inference is performed by this trainer. Plan and freeze the comparison
matrix before scoring test: rank 4/8/16, text/vision/both towers, multiple seeds,
and a full-fine-tuning control using the same data and loss. Validation results
from the first run are development evidence, not final held-out performance.

## Fixed 15-run ablation matrix

The selected design has five configurations, each at seeds 0, 1 and 2:
both towers at ranks 4, 8 and 16, plus text-only and vision-only at rank 8.
This separates rank and tower ablations without running all nine combinations.
Alpha is twice rank, preserving the original alpha/rank scaling of 2. All other
training settings stay at the first run's values. Each run uses five epochs;
the original rank-8/both/seed-0 run is reused after hash/config validation.

```bash
python src/models/run_lora_ablation.py \
  --manifest configs/clip_lora_v2_ablation.json --device auto
```

The runner starts a separate process for each experiment, executes sequentially,
checks the selected adapter hash and reload validation, verifies exact validation
score coverage, and exports per-run CSV/JSON files to `scores/`. Partial and final
summaries are written as `clip_lora_v2_ablation_runs.csv`,
`clip_lora_v2_ablation_summary.csv` and `clip_lora_v2_ablation_summary.md`.
The aggregate reports arithmetic means and sample standard deviations across
seeds (ddof=1); these are validation-development statistics, not test confidence
intervals. The checkpoint selected for each seed may come from a different epoch.

## Full fine-tuning control

The full-parameter control uses the same fixed data, objective, optimizer
settings, five epochs, validation-only checkpoint selection and seeds 0, 1 and
2. Both CLIP towers are trainable (151,277,313 parameters), rather than only
the Q/V LoRA adapters. The smoke run completed successfully before the full
controls. Full runs are configured in
`configs/clip_full_v2_both_seed{0,1,2}_fair.json` and store complete checkpoints
under ignored `runs/`.

An initial control using the LoRA learning rate of 1e-4 was not a fair
optimization comparison: its three-seed mean was 0.963852 ± 0.003077. A
seed-0, three-epoch learning-rate pilot compared 1e-6, 3e-6, 1e-5 and 3e-5;
the best pilot used 3e-5 and reached validation AUC 0.982191. Using that
rate, the definitive five-epoch full-tuning runs reached 0.982981, 0.983027
and 0.982191 for seeds 0, 1 and 2: mean 0.982733 ± 0.000470 (sample SD).
This exceeds the rank-16 both-tower LoRA mean of 0.975545 ± 0.000187 on the
development validation split. These are validation-only comparisons; no
full-tuning test inference has been run.

Logs and live progress remain under ignored `runs/lora_ablation/`. Re-running
the command safely reuses completed runs only if configurations, trainer, dataset
and adapter hashes match. An incomplete or mismatching directory stops the batch
for investigation; it is not overwritten. This batch performs no test inference.

## Frozen held-out comparison

After all validation development was complete, the test manifest froze
rank-16 both-tower LoRA and the definitive LR=3e-5 full control, each at seeds
0, 1 and 2. The manifest and exact checkpoint hashes were committed before
test inference. Zero-shot CLIP is the unchanged WP5 baseline. Each checkpoint
uses a threshold selected on validation accuracy; the shared evaluator then
reports test metrics with 1,000 image-anchor-group bootstrap resamples.

Across seeds, LoRA reached test accuracy 0.937318 ± 0.001458 and AUC 0.979260 ±
0.000442. Full tuning reached accuracy 0.948008 ± 0.001683 and AUC 0.985267 ±
0.001034. Zero-shot accuracy/AUC were 0.793003/0.889400. These are the first
and only held-out test evaluations of the adapted checkpoints. See
`scores/clip_v2_selected_test_summary.md` for recalls and the individual
reports for per-seed 95% bootstrap intervals. N3 remains subject to the known
frozen text shortcut and must not be interpreted as clean visual color
reasoning.
