# Shortcut controls (abo-home-reciprocal-v3-candidate)

- Pairs: `data/releases/abo-home-reciprocal-v3-candidate/pairs.csv`
- Dataset version: `abo-home-reciprocal-v3-candidate`
- Pairs SHA-256: `14814aa6bba905c07377a929c44e7d28b76893497c9c59eb86b8b6a9da334003`
- Splits: train 5328, val 656, test 686
- Protocol: train fit; val accuracy threshold; rule `score >= threshold`; test once
- Text models: word, char TF-IDF + logistic regression (seed 0)
- Image model: clip / openai/clip-vit-base-patch32@3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268

| control | test n | Acc | AUC | Balanced | N1 AUC | N2 AUC | N3 AUC | N1 recall | N2 recall | N3 recall |
|---|---|---|---|---|---|---|---|---|---|---|
| text-only word | 686 | 50.87% | 0.5160 | 50.87% | 0.5698 | 0.4687 | 0.5189 | 65.38% | 61.78% | 83.33% |
| text-only char | 686 | 51.60% | 0.5204 | 51.60% | 0.5649 | 0.4874 | 0.5056 | 33.97% | 41.40% | 73.33% |
| image-only CLIP | 686 | 50.00% | 0.5000 | 50.00% | 0.5000 | 0.5000 | 0.5000 | 0.00% | 0.00% | 0.00% |

Matched-anchor detail (each negative compared with its own anchor's positive):

| control | N1 | N2 | N3 |
|---|---|---|---|
| text-only word | 0.5698 [0.5066, 0.6384] (156/156, 156 image_anchor_group) | 0.4687 [0.4086, 0.5302] (157/157, 157 image_anchor_group) | 0.5189 [0.4611, 0.5600] (30/30, 15 reciprocal_exchange) |
| text-only char | 0.5649 [0.5026, 0.6301] (156/156, 156 image_anchor_group) | 0.4874 [0.4242, 0.5520] (157/157, 157 image_anchor_group) | 0.5056 [0.4800, 0.5411] (30/30, 15 reciprocal_exchange) |
| image-only CLIP | 0.5000 [0.5000, 0.5000] (156/156, 156 image_anchor_group) | 0.5000 [0.5000, 0.5000] (157/157, 157 image_anchor_group) | 0.5000 [0.5000, 0.5000] (30/30, 15 reciprocal_exchange) |

Four remaining uncertainty flags are train fallback N1/N2, not N3: `B07Q88MYL4_N1`, `B07TTCHRB2_N2`, `B07JD7RFRN_N2`, `B075H8JNZT_N2`. They are generated/unreviewed and are included in training.

Image-only scores are constant per anchor because this fixed-image release's positive and negative pairs share the same image; its AUC is a structural 0.5.
N1/N2/N3 AUC uses matched-anchor positives. N3 intervals resample reciprocal exchanges; N1/N2 intervals resample image-anchor groups. Overall eval.py intervals use image-anchor groups and do not capture exchange dependence.
Overall metrics are not directly comparable across releases with different negative type mixes.
