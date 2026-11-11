# Shortcut controls (ABO home v2)

- Pairs: `data/releases/abo-home-v2-20261103/pairs.csv`
- Splits: train 5328, val 656, test 686
- Text model: TF-IDF word 1-2gram, min_df=2 + logistic regression (seed 0)
- Image model: clip / openai/clip-vit-base-patch32@3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268

| control | test n | Acc | AUC | Balanced | N1 AUC | N2 AUC | N3 AUC | N1 recall | N2 recall | N3 recall |
|---|---|---|---|---|---|---|---|---|---|---|
| text-only tf-idf | 686 | 61.22% | 0.6230 | 61.22% | 0.5302 | 0.4646 | 0.9928 | 3.91% | 2.34% | 91.95% |
| image-only CLIP | 686 | 50.00% | 0.5000 | 50.00% | 0.5000 | 0.5000 | 0.5000 | 0.00% | 0.00% | 0.00% |

Image-only scores are constant per anchor because v2 positive and negative pairs share the same image; its AUC is a structural 0.5, not a learned shortcut.
N1/N2/N3 AUC compares positives against that negative type only. Threshold-dependent recalls come from the shared evaluator's val-selected threshold.
