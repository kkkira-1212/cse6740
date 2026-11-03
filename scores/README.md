# scores/
每个模型/配置一个 CSV,两列:`pair_id,score`。分数越高越匹配。
评估脚本(`src/eval/`,Aaron)统一读取本目录并按 `neg_type / category / year / split` 分组出表。
