# 电商图文匹配(Multimodal Image-Text Matching)

课程项目(Prof. Tuo Zhao):判断电商商品的**主图**与**英文标题**是否匹配(二分类,可选 R@1 检索)。
主线:零样本 CLIP → LoRA 微调(参考 e-CLIP / EI-CLIP)→ 全量微调对照,并加入 OOD、跨时间测试和 GPT-6 Luna 等更多基线。

## 老师的四条建议 → 对应工作包
1. 更多数据集(不同时间)→ WP9(Amazon Reviews 2023)
2. 更多基线模型 → WP5、WP8
3. OOD 测试 → WP10
4. GPT-6 Luna 作为另一个基线 → WP7

## 分工
| 成员 | 工作包 | 目录 |
|---|---|---|
| Kira | WP0 schema、WP1 ABO 数据底座、WP2 N1/N2 负例 | `src/data/`、`src/negatives/` |
| Jack | WP5 零样本 CLIP + 全量微调对照、WP6 LoRA | `src/models/` |
| Aaron | WP4 评估脚本 + 对照、WP9 时间维度数据 | `src/eval/`、`src/data/` |
| Jane | WP7 Luna、WP8 更多基线 | `src/baselines/` |
| Sean | WP3 N3 属性替换 + 假负例审查、WP10 OOD 测试集 | `src/negatives/` |

详见 [docs/work-packages.md](docs/work-packages.md)。

## 文档
- [docs/design.md](docs/design.md) 主线设计(任务、数据、负例、模型、评估、风险)
- [docs/schema.md](docs/schema.md) 统一数据字段和分数文件格式(**WP0 已冻结**)
- [docs/work-packages.md](docs/work-packages.md) 每人工作包详解
- [docs/open-decisions.md](docs/open-decisions.md) 待组内拍板的事项与备选方案
- [CONTRIBUTING.md](CONTRIBUTING.md) 协作约定

## 目录
```
docs/      设计与分工文档
src/       各人代码(按模块分目录,目前只有说明,尚未写流水线)
data/      数据放这里,不进 git(见 data/README.md)
scores/    各模型的分数文件(pair_id,score)
paper/     LaTeX 论文模板(可传 Overleaf)
```

## 数据与许可
ABO 官网标 CC BY 4.0,论文标 CC BY-NC 4.0,**按非商业课程项目使用**。原始数据和图片不要提交到仓库。
