# Text-only / Image-only 对照(ABO home v2)

WP4 的 shortcut 对照,用于在解读 v2 模型结果前检查数据里有没有单模态捷径。
统一评估口径见 [`src/eval/README.md`](../src/eval/README.md)。

## 数据

- `data/releases/abo-home-v2-20261103/pairs.csv`
- train 5,328 / val 656 / test 686 对。
- 正例 3,335,负例 3,335(N1 1,282 / N2 1,283 / N3 770);test 是 343 pos + 343 neg
  (N1 128 / N2 128 / N3 87),整体 **50/50 balanced**。
- v2 是 **fixed-image** 布局:每个 image anchor 的 pos 和 negative 使用同一个
  `image_path`。`validation.json` 确认 `cross_split_images: 0`、
  `one_positive_and_one_negative_per_anchor: true`。
- 两个对照都只在 **train** 上训练,val 选阈值,test 只评一次。
- 标签仍是 generated candidate,不是人工认证;原 positives 是 listing 关联。

## 方法

### Text-only

- 输入只有 `text` 一列。
- `TfidfVectorizer(ngram_range=(1,2), min_df=2, sublinear_tf=True,
  strip_accents="unicode")`,只在 train 上 fit。
- `LogisticRegression(max_iter=1000, random_state=0)`。
- 输出 val+test 的 `P(label=1)` 到 `scores/control_v2_text_tfidf.csv`。

### Image-only

- 冻结的 CLIP ViT-B/32 image tower:`openai/clip-vit-base-patch32`,
  revision `3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268`。
- L2-normalized 512-d image embedding;不训练 CLIP,只在 train 的 pair 上训练
  logistic regression。
- 图片特征缓存到 `data/processed/control_v2_clip_image_features.npz`。
- 输出 `scores/control_v2_image_clip.csv`。
- 如果图片还没下载,`--image-mode identity` 会用 per-image 常数分生成等价的 null 对照
  (不需要 CLIP);由于 v2 每个 anchor 的 pos/neg 共用图片,任何 image-only 模型都会得到常数分。

### 评估

`src/eval/controls.py` 默认自动调用 `src/eval/eval.py` 的 v2 模式:
image-anchor group bootstrap(1000 次),不使用 `--r-at-1`。

```bash
python src/eval/controls.py --image-mode clip --bootstrap 1000
```

## 结果

数据:val 656,test 686;text-only 阈值 `0.4087591`(val accuracy 选择)。

| control | test Acc | test AUC | Balanced | N1 AUC | N2 AUC | N3 AUC | N1 recall | N2 recall | N3 recall |
|---|---|---|---|---|---|---|---|---|---|
| text-only TF-IDF | 61.22% | 0.6230 | 61.22% | 0.5302 | 0.4646 | **0.9928** | 3.91% | 2.34% | 91.95% |
| image-only CLIP | 50.00% | 0.5000 | 50.00% | 0.5000 | 0.5000 | 0.5000 | 0.00% | 0.00% | 0.00% |

text-only 的 95% CI(test):Accuracy `[58.60%, 63.85%]`,AUC `[0.5816, 0.6622]`;
positive recall 96.79%,negative recall 25.66%。

### Text-only:N3 是强文本捷径

- **N3 AUC = 0.9928**;N1 0.5302、N2 0.4646,都在 0.5 附近。
- 阈值选在 val 上最大化 accuracy,所以模型倾向判正例:
  positive recall 96.79%,negative recall 25.66%;N1/N2 recall 只有 3.91%/2.34%,
  但 N3 recall 91.95%。
- TF-IDF 系数最负的词正好是 N3 的四个 target color:
  `yellow -5.46`、`red -4.78`、`green -4.66`、`blue -1.55`。
  最正的是 `brown 1.45`、`grey 1.31`、`black 1.23`、`beige 1.09`、
  `white 0.97`、`ivory 0.86`、`navy 0.85`。
- 也就是说,冻结版 v2 的 N3 只要把颜色词换成 yellow/red/green/blue,
  text-only 模型就能几乎完美地判成 negative。整体 61.22% accuracy 主要来自 N3,
  不代表图像-文本匹配能力。
- N1/N2 的 AUC 接近 0.5,说明当前 donor title 选择没有引入明显的文本捷径。

### Image-only:结构性 null

- train AUC 0.5000;val+test 1,342 个 score **全部等于 0.5**,unique scores = 1。
- test Accuracy 50.00%,AUC 0.5000,balanced accuracy 50.00%;
  N1/N2/N3 AUC 都是 0.5000。
- 原因:v2 的 pos 和 negative 共用同一张图,任何 image-only 模型看到相同特征,
  无法区分。logistic regression 收敛到常数 0.5。
- 这是 **数据完整性检查**,不是“图像没有信息”的结论;它确认 fixed-image 布局和
  score/pair 对齐是正确的。阈值相关的 N1/N2/N3 recall 在这个对照里是退化的
  (阈值 0.5 时全部判正),应看 AUC/accuracy。

## 与已有 N3 诊断的关系

仓库里已有 Sean 的 train-only 5-fold GroupKFold 小样本诊断:

| 诊断 | old N3 AUC(word/char) | reciprocal N3 AUC(word/char) |
|---|---|---|
| `data/reviews/n3-reciprocal-dev-v1/text_only_diagnostic.json` | 0.912 / 0.935 | 0.493 / 0.485 |
| `data/reviews/n3-reciprocal-expanded-dev-v2/text_only_diagnostic.json` | 0.955 / 0.950 | 0.540 / 0.531 |

这些是小样本开发诊断,不是冻结 release 的完整 train/val/test。本次对照是对
`abo-home-v2-20261103` 的完整评估,结果与旧 N3 诊断一致:原始 color swap 的文本
捷径极强。Sean 的 reciprocal N3 能把 shortcut 降到接近 0.5,但它是独立的开发 pool,
不是冻结 release;采用它需要新 release + 重新打分。

## 对解读 v2 结果的建议

1. **不要把 N3 上的高准确率当成图文匹配能力。** text-only 单独就能拿到 N3 AUC 0.993。
2. 主表至少按 N1/N2/N3 分开报告;N3 目前应视为 shortcut-prone subset。
3. 如果论文要声称 N3 的结果,先决定是否切换到 reciprocal N3(新 release)或在
   limitation 里明确 text shortcut。
4. N1/N2 的 text-only AUC 接近 0.5,说明 N1/N2 没有明显的文本捷径;这是好消息。
5. image-only 是结构性 null,说明 v2 fixed-image 设计确实切断了图像侧捷径;
   它不能用来评估图像质量,只能作为数据完整性检查。
6. 所有标签仍是 generated candidate;对照不解决 label noise 或假负例。

## 复现

- 图片:`python data/releases/abo-home-v2-20261103/tools/download_images.py`
  (3,335 张,已按 `image_manifest.csv` 做 SHA-256 校验)。
- 运行:

```bash
python src/eval/controls.py --image-mode clip --bootstrap 1000
```

- 产物:
  - `scores/control_v2_text_tfidf.csv`
  - `scores/control_v2_image_clip.csv`
  - `scores/control_v2_text_tfidf_eval.{csv,md,json}`
  - `scores/control_v2_image_clip_eval.{csv,md,json}`
  - `scores/control_v2_summary.md`
  - `scores/control_v2_meta.json`(环境、超参、top features、cache hash、score hash)
- 本次运行环境:Python 3.12.2、numpy 1.26.4、scikit-learn 1.7.2、
  torch 2.4.0+cu124、transformers 4.46.3、huggingface-hub 0.36.2。
  系统默认的 hub 1.10.2 与 transformers 4.46.3 不兼容,所以 CLIP 那次用了临时 venv;
  项目的 `environment.yml` 是目标环境。
- CLIP image cache 在 `data/processed/`,不进 git;重跑时用 `--recompute` 可强制重算。
