# 小版本(家具,WP0–WP2)

给 Jack / Aaron / Jane 先跑通自己脚本用的小版本数据。类别选的是**家具**(product_type 白名单见
`src/data/build_items.py` 里的 `FURNITURE_TYPES`,排除了 `HOME_FURNITURE_AND_DECOR`、
`HOME_BED_AND_BATH`、`FURNITURE_COVER` 这几个混了非家具商品的大类,也过滤掉了布料色卡
"xxx Swatch" 这种误标成家具的条目)。

## 数据规模
- 3978 件商品(items.csv),3163 个近重复分组(group_id)
- train/val/test = 3186 / 393 / 399(按 group_id 划分,同组不跨 split)
- pairs.csv:3978 pos + 3978 N1(随机负例) + 3977 N2(同类难负例,1 条因同 split 同类别内找不到
  候选被跳过),共 11933 行

## 2026-10-21 更新:修了 Sean 在 PR #2 里报出的三个 N2 bug
Sean 审查时对我们的 pairs.csv 做了静态诊断,发现:1342/3978 条 N2 的负例图来自和文本不同的
split(训练集混进了 val/test 的图);47 条负例图其实就是文本自己那条正例用的图;69 条的
`(image_path, text)` 跟某条正例完全一样却被标成负例。我复现确认这三个数字完全对上,根因是:
- **跨 split**:原来的 N2/N1 候选池只按 product_type(和 group_id)过滤,没限制同 split。
- **同图/矛盾**:3 张 ABO 占位图("暂无图片")被几十个不相关商品共用,之前只在分组时排除了
  这条合并信号,选负例时却没排除"负例图=自己正例图"这种情况。
- **22 条额外矛盾**:标题逐字完全相同的重复上架商品(同一把椅子在 ABO 里被录入两次),但其中
  一条的 color/material 元数据跟标题对不上(标题写"Denim Blue",字段写"Beige"),导致我"去掉
  颜色词再比较标题"的归一化合并规则失效,两条没被合并进同一组。

修复:`build_items.py` 加了一条"标题逐字相同就合并"的分组规则(不依赖可能出错的 color/material
字段);`build_pairs.py` 的 N1/N2 候选现在强制同 split,并且在候选池和最终选择里都排除
"负例图 == 文本自己的正例图"和"(负例图, 文本) 已经是某条正例"这两种情况。改完三个 bug 计数都是 0
(自己写了脚本复查,不是只信 Sean 的报告)。`items.csv`/`pairs.csv` 已更新为修复后的版本。

## 怎么复现
```
python src/data/fetch_raw.py --out-dir data/raw

python src/data/count_categories.py --listings-dir data/raw/listings/metadata \
    --out-csv docs/category_counts.csv --out-md docs/category_counts.md

python src/data/build_items.py --listings-dir data/raw/listings/metadata \
    --images-csv data/raw/images/metadata/images.csv.gz \
    --images-out data/images/small \
    --out-csv data/processed/items.csv --out-counts-csv data/processed/items_counts.csv

python src/negatives/build_pairs.py --items-csv data/processed/items.csv \
    --out-csv data/processed/pairs.csv --spotcheck-csv docs/n1_n2_spotcheck_sample.csv
```
ABO listings/images 元数据从 `https://amazon-berkeley-objects.s3.amazonaws.com/` 按需下载(不是整个
tar,按分片/按需单张图拉取,几分钟内能跑完)。图片本身不进 git,`docs/mini_version/items.csv` 和
`pairs.csv` 是给大家对齐字段用的,要跑模型还是要自己跑一遍上面的脚本把图下下来。

## 做了哪些决定
1. **类别 = 家具**,对应 open-decisions.md 选项 B(只用家具)。还没做 OOD(家居装饰/服饰鞋靴),
   那是 Sean 的 WP10。
2. **N2 相似度**用 `sentence-transformers/all-MiniLM-L6-v2`(非 CLIP),同 product_type 内、排除同
   group_id,取 cosine 相似度最高的一个。
3. **N1/N2 比例**按 pos:N1:N2 = 1:1:1 处理(每条标题各出一次 pos、一次 N1、一次 N2),对应
   open-decisions.md 选项 3a 的思路,但那条是 N1:N2:N3 的比例,我这边先按这个套用,N3 出来后
   这个假设需要 Sean/组里确认一下。
4. **近重复分组**:共享 main_image_id,或去掉自己的 color/material 词 + 常见尺寸词后标题相同,
   或标题逐字完全相同(新加,见上面 10-21 更新),三者任一就归一组。发现 3 张 ABO 的占位图(没有
   真实图,各型号共用同一张"暂无图片"图)被几十个不相关商品共用,已经把"图片共享"这条规则限制
   在最多共享 4 次以内,超过的当占位图处理,不用来合并分组。
5. **抽检**:`docs/n1_n2_spotcheck_sample.csv` 放了 N1/N2 各 20 条(共 40,比文档建议的 50 对少一点,
   先凑够能跑通;真要定假负例比例还是需要大家手动过一遍填 `actually_a_match` 列)。我自己随机看了
   几张图,N1/N2 的负例构造逻辑是对的,但没有替代组内的正式人工审查。

## 已知局限 / 没做的事
- 只处理了 en_US 标题;同一商品的其它语言版本没有用上。
- WP1 文档要求的"颜色/材质标准化值出现在标题里"计数表做了,但只在全量 `docs/category_counts.csv`
  里(不分品类),家具专属的这张还没单独拆出来,需要的话我可以补。
- N2 候选目前允许跨「大类里不同小类」(比如 CHAIR 里躺椅和办公椅会互相当负例),没有按三级 node
  路径再细分,如果组里觉得太粗可以再收紧。
