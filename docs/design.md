> **Historical pilot/planning document.** For current furniture/decor data, use the [v2 guide](home_v2.md) and [version-specific contract](../data/releases/abo-home-v2-20261103/README.md). Negative direction, allocation and pair-ID semantics differ.

# 主线设计

## 任务
输入(商品主图,英文标题),输出匹配/不匹配;可选 R@1 检索。所有模型用同一测试集、同一评估口径。

## 数据
- **ABO**:147,702 条商品、398,212 张图、576 个 product_type;字段含 item_name(多语言,用 en_US)、main_image_id、color/material/pattern/style、product_type、node(层级类目)。color 字段的值不一定出现在标题或图里(例:象牙色沙发 color 值为 Neutral,标题写 Linen)。近重复条目(如不同尺码)按 group 分组,同组不跨 split。
- **Amazon Reviews 2023**:作为跨时间测试集,只测不训。商品时间信息需核实(评论有时间戳,商品可能无上架日期)。
- 各类别真实条数待 Kira(WP1)统计后补充。

## 负例
- N1 随机负例:最容易。
- N2 同类难负例:同 product_type,存在假负例风险。
- N3 属性替换:颜色/材质等;风险是文本侧捷径,且多色商品会产生假负例,需过滤。
- 正负 1:1;每条标题各出现一次正例、一次负例;按负例类型分别报告。

## 模型与对照
零样本 CLIP(ViT-B/32 起步,余弦相似度 + val 阈值)→ LoRA(Q/V 投影,rank 4/8/16,文本/图像/两边消融,多种子)→ 全量微调对照;text-only / image-only 对照用来发现数据捷径;更多基线(WP8);GPT-6 Luna(WP7)。

## Luna baseline
输出 0–100 匹配概率(阈值 50,AUC 用同一个数),统计解析失败;两版 prompt(P1 直接判断,P2 先检查类别/颜色/材质/形状);固定推理强度;先 20 对小测试估成本。已确认:支持文本+图像输入、文本输出、有推理强度设置;未确认:图像输入格式、限速、图片计费。

## 评估
Accuracy、AUC、正/负例准确率、分负例类型准确率、可训练参数量、训练时间、R@1(可选);固定随机种子,LoRA 多种子。

## 经验教训(NewsCLIPpings, arXiv 2104.05893)
随机负例太容易;文本改写会引入语言偏差;用 CLIP 过滤数据会对 CLIP 基线不公平;RN50 上小数据集冻结部分层更好、大数据集全量微调更好。

## 风险
假负例(N2/N3、近重复)、标题漏说、多色商品、Luna 成本与图片计费未核实、ABO 许可按非商业处理。
