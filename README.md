# mock_data — OBS 增程商品变更 SOP 模拟数据集

## 文件清单

| 文件 | 条数 | 说明 |
|---|---|---|
| `sop.md` | 115 步骤 | SOP 定义 |
| `event_clean.json` | 52 条 | 纯净版，仅 SOP 对应的有效日志 |
| `event_with_noise.json` | 5200 条 | 52 有效 + 5148 噪声，有效日志措辞与 SOP 一致 |
| `event_noise_paraphrased.json` | 5200 条 | 同上，有效日志的 event_name / detection_log 做了语义改写 |
| `event_paraphrase_mapping.json` | 52 条 | 语义改写前后对照表（含 SOP 步骤对应关系），用作 ground truth |

## 用法

- `event_clean.json` → 基线，验证模型能否识别全部 SOP 步骤
- `event_with_noise.json` → 测试噪声过滤 + SOP 匹配能力（有效日志措辞与 SOP 一致）
- `event_noise_paraphrased.json` → 测试纯语义理解能力（有效日志措辞与 SOP 不同）
- `event_paraphrase_mapping.json` → 评估语义匹配的 precision / recall（ground truth）

## 数据结构

日志条目：`log_id`（EVT-xxxxx，连续编号，无有效/噪声区分）、`event_time`（严格升序）、`actor`（lisi/zhangsan）、`role`、`platform`、`event_type`、`event_name`、`params`、`detection_log`、`seq_id`

注意：事件日志中**不包含**任何能区分有效/噪声日志的字段。`log_id` 为连续编号（EVT-00001 ~ EVT-05200），无前缀区分；`related_sop_ref` 已移除；元数据中无有效/噪声计数。Agent 需要通过 event_name、detection_log、params 等内容与 SOP 步骤描述进行语义匹配，自行判断每条日志对应哪个 SOP 步骤。SOP 步骤对应关系仅记录在 `event_paraphrase_mapping.json` 中，用作评估 ground truth。

噪声特征：仅 lisi/zhangsan 两人，按 SOP 阶段生成上下文相关噪声，覆盖 17 个平台，操作其他集群/组件/变更单。
