# WP7 Luna + WP8 更多基线

负责人:Jane。所有脚本都输出统一的分数文件 `pair_id,score`(分数越高越匹配),指标一律用
Aaron 的 `src/eval/eval.py` 算。从仓库根目录运行。

| 文件 | 作用 |
|---|---|
| `common.py` | 读 pairs、写分数文件、选设备 |
| `sample_subset.py` | 分层抽样子集(Luna 预算用),同一标题的 pos/N1/N2 保持在一起 |
| `luna_baseline.py` | WP7:GPT-6 Luna 判断图文是否匹配,P1/P2 两版 prompt |
| `zero_shot_baselines.py` | WP8:CLIP ViT-L/14、SigLIP、SigLIP2、ALIGN、BLIP ITM、BLIP-2 ITM 零样本 |

## 0. 准备

WP8 一条命令跑完(建环境 → 下数据和图片 → 冒烟测试 → 4 个模型打分 → 评估):

```bash
bash src/baselines/run_wp8.sh
```

按 `src/models/README.md` 先下好家具小版本的图片(`data/images/small/...`)。

## WP7:GPT-6 Luna

已核实(2026-10-28,[官方模型页](https://developers.openai.com/api/docs/models/gpt-6-luna)):
模型 id `gpt-6-luna`;输入文本+图像,输出文本;推理强度 none/low/medium(默认)/high/xhigh/max;
价格每百万 token 输入 $0.10、缓存输入 $0.01、输出 $0.50;支持 Responses API、Batch、结构化输出;
Build 档限速 5,000 RPM。图像按 patch 计 token,官方页面没给 Luna 的具体换算,所以**以小测试的
`usage` 实测为准**,脚本会把每次调用的 token 和费用写进 summary。

设计(对应 `docs/design.md`):
- 图片用 base64 data URL 传(ABO 小图 ≤256px),标题作为文本。
- 用结构化输出(JSON schema, strict)要求返回 `match_probability`(0–100 整数);score = 概率/100,
  评估时用固定阈值 0.5。
- P1 直接判断;P2 先对类别/颜色/材质/形状各给出 consistent / contradicted / not_checkable,再给概率。
- 两版 prompt 都写明「只有明显矛盾才判不匹配,标题漏说不算;品牌、尺寸、型号无法从图片核实,不算矛盾」。
- 推理强度整轮固定(默认 `low`,用 `--reasoning-effort` 改,写进文件名)。
- 解析失败不赋默认值:单独写进 `*_parse_failures.txt` 并在 summary 里计数;重跑时默认**不重试**
  解析失败(否则会掩盖失败率),只重试网络/API 错误。
- 原始响应逐条追加到 `data/luna_logs/*.jsonl`(不进 git),中断后用同一条命令即可续跑。

```bash
export OPENAI_API_KEY=...            # 不要提交到仓库

# 1) 先看请求长什么样(不调用 API)
python src/baselines/luna_baseline.py --prompt P1 --limit 1 --dry-run

# 2) 小测 20 对,两版各一次,看 summary 里的 cost_usd_per_1k_pairs 和 median_seconds_per_call
python src/baselines/luna_baseline.py --prompt P1 --limit 20 --tag pilot
python src/baselines/luna_baseline.py --prompt P2 --limit 20 --tag pilot

# 3) 正式跑。家具小版本的 test 只有约 1.2k 对,可以直接全跑;全量数据再用分层 2k 子集:
python src/baselines/sample_subset.py --splits test --target-pairs 2000 --seed 0 \
  --out-csv data/processed/luna_subset_test.csv
python src/baselines/luna_baseline.py --prompt P1   # 默认 docs/mini_version/pairs.csv 的 test
python src/baselines/luna_baseline.py --prompt P2

# 4) 评估:固定阈值 0.5,排除解析失败
python src/eval/eval.py --pairs-csv docs/mini_version/pairs.csv \
  --scores-csv scores/luna_p1_effort-low.csv --fixed-threshold 0.5 \
  --exclude-pair-list scores/luna_p1_effort-low_parse_failures.txt \
  --drop-cross-split-images --r-at-1 --bootstrap 1000
```

输出(在 `scores/`):`luna_<prompt>_effort-<e>.csv`(分数)、`*_parse_failures.txt`、
`*_summary.json`(调用数、失败率和原因、token、费用、耗时、P2 各属性判断的分布)。

**公平比较的注意点**:Luna 只跑 test(或子集),阈值固定 0.5;其他模型在 val 上选阈值。和 Luna
对比时,其他模型要在**同一份子集、排除同样的解析失败 pair** 上重新评一次,不能拿全量数和子集数比。

## WP8:更多零样本基线

| `--model` | Hugging Face id | 打分方式 |
|---|---|---|
| `clip-l14` | `openai/clip-vit-large-patch14` | 图/文向量余弦相似度(与 WP5 同法,更大的模型) |
| `siglip-b16` | `google/siglip-base-patch16-224` | 余弦相似度(sigmoid 训练的双塔;文本按训练时 pad 到 64) |
| `siglip2-b16` | `google/siglip2-base-patch16-224` | 同上,SigLIP2 |
| `align-b` | `kakaobrain/align-base` | 余弦相似度(ALIGN:EfficientNet + BERT 双塔,噪声网页图文训练) |
| `blip-itm-b` | `Salesforce/blip-itm-base-coco` | 融合模型的图文匹配(ITM)头,score = P(匹配) |
| `blip2-itm-g` | `Salesforce/blip2-itm-vit-g` | BLIP-2 Q-Former 的 ITM 头(大,Mac 上慢,可选) |

建议先跑 `siglip-b16`、`clip-l14`、`blip-itm-b` 三个:分别回答「换训练目标」「加大模型」
「双塔 vs 融合」三个问题。

```bash
# 冒烟测试
python src/baselines/zero_shot_baselines.py --model siglip-b16 --limit 30 \
  --out-csv data/processed/siglip_smoke.csv

# 正式:默认只算 val + test(评估器只需要这两个)
python src/baselines/zero_shot_baselines.py --model siglip-b16
python src/baselines/zero_shot_baselines.py --model clip-l14 --batch-size 16
python src/baselines/zero_shot_baselines.py --model blip-itm-b --batch-size 16

python src/eval/eval.py --pairs-csv docs/mini_version/pairs.csv \
  --scores-csv scores/siglip_b16_zero_shot.csv --drop-cross-split-images --r-at-1 --bootstrap 1000
```

每个模型同时写一个 `*_meta.json`(Hugging Face id、revision、参数量、设备、耗时、库版本),
就是工作包要求的「一行说明」的来源。结果定稿时用 `--revision <commit hash>` 固定权重版本。
`--device auto` 依次选 CUDA / MPS / CPU。

### 候选模型对比(调研结论)

| 模型 | 开源权重 | 类型 | 适用于本任务 | 结论 |
|---|---|---|---|---|
| CLIP ViT-L/14 | 是(HF) | 双塔 | 是 | 已接入,看「加大模型」能提升多少 |
| SigLIP / SigLIP2 | 是(HF) | 双塔 | 是 | 已接入,看「换训练目标」的效果 |
| ALIGN | 是(HF,kakaobrain 复现版) | 双塔 | 是 | 已接入;注意不是 Google 原版权重 |
| BLIP ITM | 是(HF) | 融合 | 是 | 已接入,看「双塔 vs 融合」 |
| BLIP-2 ITM | 是(HF) | 融合 | 是 | 已接入,较大,算力允许再跑 |
| Chinese-CLIP | 是(HF) | 双塔 | 否 | 只支持中文文本;本项目 pairs 是英文标题,不接入 |
| GPT-6 Luna | 否(API) | 生成式 | 是 | WP7 |

参数量不在这里手填,以每次运行写出的 `*_meta.json` 里的 `n_params` 为准。

## 已知局限

- Luna 的图片 token 数没有官方换算,费用以小测实测为准。
- SigLIP 用余弦相似度而不是 sigmoid 概率;两者只差一个单调变换,AUC 和 val 选阈值的结果相同。
- ITM 类模型要逐对前向,比双塔慢很多。
