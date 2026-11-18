# WP5: zero-shot CLIP on ABO home v2

Scored all 6,670 pairs with the existing frozen CLIP ViT-B/32 scorer on MPS, batch size 32. The release verifier checked all 3,335 images. Model revision and environment versions are recorded in `scores/abo_home_v2_clip_b32_meta.json`.

```bash
python src/models/zero_shot_clip.py --pairs-csv data/releases/abo-home-v2-20261103/pairs.csv --image-root data/releases/abo-home-v2-20261103/images --out-csv scores/abo_home_v2_clip_b32.csv --device auto --batch-size 32
python src/eval/eval.py --pairs-csv data/releases/abo-home-v2-20261103/pairs.csv --scores-csv scores/abo_home_v2_clip_b32.csv --bootstrap 1000
```

Validation-selected threshold: 0.28664815. Test: 686 pairs, accuracy 79.30%, AUC 0.8894; N1/N2/N3 negative recall 94.53%/67.97%/41.38%. See the score evaluation report for confidence intervals and category breakdowns. All 44 existing tests passed.

Labels remain generated candidates. Frozen v2 N3 has a documented text shortcut (Aaron PR #9); these results do not certify semantic label quality. Pilot scores are a different dataset and cannot be directly interpreted as improvement or regression. LoRA and full fine-tuning are subsequent experiments.
