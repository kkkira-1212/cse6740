# 统一数据格式(WP0 已冻结 —— 字段名不再改,如需改动请先在组里提出)

## pairs 表字段
| 字段 | 含义 |
|---|---|
| pair_id | 每个图文对的唯一 id,格式 `<text来源item_id>_<neg_type>`,如 `B072ZLCB3M_N2` |
| item_id | 图所属商品的 id(注意:负例行里这是**图**的来源商品,不是 text 的来源商品) |
| image_path | 主图相对路径,相对 `data/images/` 根目录,如 `small/14/14fe8812.jpg` |
| text | 英文标题(N3 为改写后的标题) |
| label | 1 = 匹配,0 = 不匹配 |
| neg_type | pos / N1 / N2 / N3 |
| category | 类别(text 来源商品的 product_type) |
| year | 年份(跨时间测试用;ABO 数据本身没有上架时间,此字段留空,Aaron 的 WP9 时间维度数据会填上) |
| split | train / val / test(当前已有);OOD 和跨时间测试集名字留给 WP10/WP9 定,格式约定为 `ood_near` / `ood_far` / `crosstime_<year>` |

## items 表(WP1 产出)
item_id, title, image_path, product_type, node, color, material, group_id, split

- `image_path` 的根目录是 `data/images/`(本地小分辨率 ABO 图片存放处,不进 git)。
- `group_id` 是近重复分组:同一商品的不同尺寸/颜色版本共享一个 group_id,同一 group_id 不会跨 split。

## 分数文件
`pair_id,score`,分数越高越匹配。

## 「匹配」的定义(建议,待组内确认)
标题里说的每一句图里都不矛盾即算匹配;标题漏说一部分(如黑背白垫的椅子只写「黑色椅子」)不算错。Luna 的 prompt 也按此写。
