# WP6: first LoRA experiment on frozen ABO home v2

The first full run is complete. Validation AUC increased from 0.909448 to
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
