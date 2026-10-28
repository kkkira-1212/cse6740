# WP4 评估脚本

负责人:Aaron。脚本:[`src/eval/eval.py`](eval.py)。

输入 pairs 表(见 [`docs/schema.md`](../../docs/schema.md))和任意模型的分数文件
(`pair_id,score`,分数越高越匹配),在 val 上选一个阈值,在 test 上统一出指标。
所有模型必须用同一份 pairs、同一个阈值选择规则、同一个 test 子集。

## 基本用法

```bash
conda activate cse6740

python src/eval/eval.py \
  --pairs-csv docs/mini_version/pairs.csv \
  --scores-csv scores/clip_vit_b32_zero_shot.csv
```

默认在分数文件同目录输出三个文件:

- `<model>_eval.csv`:长表,一行一个分组(overall / split / neg_type / category / year)。
  列包括 `dimension/value`(分组)、`n/n_pos/n_neg`、`accuracy/auc/positive_recall/
  negative_recall/balanced_accuracy`、`recall_N1/N2/N3`(分负例类型 recall)、`r_at_1`,
  以及 `*_ci_low/high`(仅在 `--bootstrap` 时对 overall / split 行填充)。
- `<model>_eval.md`:可直接贴到组内或论文草稿的 Markdown 报告
- `<model>_eval.json`:阈值、指标、输入 hash、排除项等 provenance

最终评估建议固定用:

```bash
python src/eval/eval.py \
  --pairs-csv docs/mini_version/pairs.csv \
  --scores-csv scores/<model>.csv \
  --drop-cross-split-images --r-at-1 --bootstrap 1000 \
  --out-csv scores/<model>_eval.csv \
  --out-md scores/<model>_eval.md \
  --out-json scores/<model>_eval.json
```

## 阈值协议

- 默认 `--val-split val`,在 val 上选使 `--objective accuracy` 最大的阈值;
  规则是 `score >= threshold`,并列最优时取最小阈值。
  这组成了 `calibrate_clip.py` 的规则,便于和已有的 WP5 结果对齐。
- `--objective balanced_accuracy` 可改用 balanced accuracy 选阈值;但**所有模型必须
  在看 test 之前定好同一个 objective**,不能每个模型挑一个好看的。
- `--fixed-threshold` 只用于事先固定阈值的模型(例如 Luna 的 0.5)。它会跳过 val 选阈值,
  并在 JSON 里记录 `selection_split: "fixed"`;不要用它看着 test 调阈值。
- test 只评一次。`--test-splits` 支持 `test`、`ood_near`、`ood_far`、`crosstime_<year>`
  等 schema 约定的名字;需要多个时用空格分隔。
- OOD / 跨时间评估时,pairs 里要同时有 in-distribution 的 `val` 和目标 test split,
  这样阈值仍来自 in-distribution val;否则用 `--fixed-threshold` 固定事先定好的阈值。

## 指标

- 总体:Accuracy、AUC、positive recall(TPR)、negative recall(TNR)、balanced accuracy
- 按 `split / neg_type / category / year` 分组汇报
- 分负例类型 recall:`N1 / N2 / N3`
- `--r-at-1`:标题内 3-way R@1——正例图分数必须高于该标题自己的 N1/N2 图。
  这是当前 1:1:1 pairs 设计下的检索指标,不是全局图片库检索;平局算错。
- `--bootstrap N`:按 text-source item(`pair_id` 前缀)聚类的 percentile bootstrap
  95% 置信区间,默认 0(关闭)。同一标题的 pos/N1/N2 三条 pair 不独立,所以不能按
  pair 直接算二项置信区间。注意:图会在不同标题之间复用,当前 bootstrap 只按文本侧
  聚类,没有建模图像侧复用。

## 数据检查与排除

写文件前会严格校验:

- scores 里不能出现 pairs 中不存在的 `pair_id`;`pair_id` 不能重复
- 实际用到的 split 必须有分数:非 `--fixed-threshold` 时 val 要完整,
  每个 test split 要完整;train 的分数可以缺省
- `score` 有限;`label` 为 0/1;`label=1` 必须是 `neg_type=pos`,
  `label=0` 不能是 `pos`
- val 必须同时含正负例;每个 test split 也必须同时含正负例

另外:

- 自动检测跨 split 的 `image_path`。当前 mini version 有 2 张 ABO 占位图
  (`small/87/874f86c4.jpg`、`small/35/3595924e.jpg`)跨 train/val/test;
  `--drop-cross-split-images` 会在选阈值和评估前删除所有使用这些图的 pair。
  **最终 test 数字建议加上这个 flag。**
- `--exclude-pair-list FILE`:每行一个 `pair_id`,空行和 `#` 开头的行忽略。
  用于排除人工审查确认的假负例等。排除发生在阈值选择之前。
- 分数文件可以只覆盖 val+test(不跑 train),也可以用 `--fixed-threshold` 只交 test。
  但如果某个模型只评了 test 的子集,要跨模型比较时必须让所有模型都评同一份子集
  (或各自用同一份子集 pairs 表),不能拿 subset 的数和全量的数直接比。

## 当前 baseline 的复现结果

不排除占位图时,`eval.py` 与 `src/models/calibrate_clip.py` 完全一致:

| 指标 | val | test |
|---|---|---|
| threshold | 0.30781579 | 0.30781579 |
| Accuracy | 76.25% | 75.25% |
| AUC | 0.8356 | 0.8318 |
| Balanced accuracy | 75.76% | 75.49% |
| N1 recall | 95.17% | 93.48% |
| N2 recall | 59.29% | 56.03% |

加上 `--drop-cross-split-images` 后(最终 test 建议口径):

| 指标 | val | test |
|---|---|---|
| threshold | 0.30781579 | 0.30781579 |
| Accuracy | 76.57% | 75.51% |
| AUC | 0.8423 | 0.8352 |
| Balanced accuracy | 76.39% | 75.87% |
| N1 recall | 95.13% | 93.43% |
| N2 recall | 58.55% | 56.17% |
| R@1(标题内 3-way) | 72.47% | 75.95% |

`src/models/calibrate_clip.py` 保留为 WP5 的临时检查;跨模型对比以本脚本为准。
