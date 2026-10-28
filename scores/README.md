# scores/
每个模型/配置一个 CSV,两列:`pair_id,score`。分数越高越匹配。
评估脚本([`src/eval/eval.py`](../src/eval/eval.py),Aaron)统一读取本目录,按
`neg_type / category / year / split` 分组出表,并输出 `<model>_eval.csv` /
`<model>_eval.md` / `<model>_eval.json`。用法见 [`src/eval/README.md`](../src/eval/README.md)。
