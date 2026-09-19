# 招聘岗位公开 API 采集实验

这个实验验证一条可重复、低风险的最小链路：公开 JSON API → 字段校验 → 纯文本归一化 → 去重 → 内容哈希 → 小样本快照。

选择 Arbeitnow 是因为它提供无需登录和 API Key 的公开岗位 API，并公开说明使用边界。它只用于验证工程链路，不代表国内岗位覆盖方案。展示或复用数据时必须保留 `source_url` 和 Arbeitnow 来源归属；不得将结果提交给第三方招聘平台。

联网运行：

```powershell
python .\arbeitnow_experiment.py --keyword Python --limit 10 --output .\output\arbeitnow-python-sample.json
```

离线验收可直接运行测试：

```powershell
python -m pytest .\test_arbeitnow_experiment.py -q
```

实验不保存原始响应，只保留最长 1200 字的纯文本摘要。生产化前还需要接入来源台账、审核状态、调度锁、指标告警和下架流程；这些约束见项目的数据采集设计文档。
