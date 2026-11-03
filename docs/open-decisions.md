> **Historical pilot/planning document.** For current furniture/decor data, use the [v2 guide](home_v2.md) and [version-specific contract](../data/releases/abo-home-v2-20261103/README.md). Negative direction, allocation and pair-ID semantics differ.

# 待组内拍板的事项与备选方案
建议讨论顺序:先定 1(类别)和 2(N2),它们影响 WP1/WP2。

## 0. 先说明
ABO 各类别真实条数暂未取得(下载地址在我这边被网络策略拦截)。Kira(WP1)第一步:下载 listings → 保留有 en_US 标题和 main_image_id 的条目 → 按 product_type 和一级类目路径计数 → 统计 color/material 标准化值出现在标题里的条数 → 把表发给大家。

## 1. 类别
- A(推荐,计数后确认):家具 + 家居装饰训练;OOD 用服饰/鞋靴。跨度大;服饰鞋靴近重复多,假负例风险高。
- B:只用家具,OOD 用家居装饰。简单,但 OOD 跨度小。
- C:随机留出一个一级类目做 OOD。数据驱动,但可能抽到噪声大的类别。
- 建议排除手机壳/配件(标题多为「兼容某型号」,判断待数据验证)。
- 补充建议:OOD 分两档——近 OOD(如家具→灯具/家居装饰)和远 OOD(如→服饰/鞋靴),都与零样本 CLIP 比较。

## 2. N2 怎么挑
a) 同 product_type 随机;**b) 同 product_type 内取标题相似度最高(推荐,用非 CLIP 的句向量,再去重)**;c) 同品牌不同型号(最难,可作更难档);d) 用 CLIP 挑(对 CLIP 基线不公平,只作消融)。必须剔除近重复。

## 3. 负例比例
**a) N1:N2:N3 = 1:1:1(推荐主设置)**;b) 训练 1:2:2、测试 1:1:1(消融);c) 主测试不含 N1,仅作 sanity check。

## 4. 训练目标
**A) InfoNCE + batch 内难负例(推荐主线)**;B) 二分类头(时间够再做消融);C) 两者都做(会让 Jack 超载)。

## 5. 测试集大小与 Luna 预算
标准误:N=2000 → 每种负例约 333 对 → ±2.5 个点;N=6000 → 约 1000 对 → ±1.5。选项:A) 2k 全模型;**B) 6k,Luna 只跑分层 2k(推荐起步)**;C) 6k 全模型。费用示意(假设每次 1500 入/500 出 token):约 $0.40/千次,12,000 次约 $4.8;图片计费和推理 token 未核实,以 20 对小测试为准。

## 6. 全量微调对照
a) 不做;**b) 同数据同 epoch 做一次(推荐;ViT-B/32 约 1.5 亿参数,估计单卡可放下)**;c) 额外做部分冻结。
