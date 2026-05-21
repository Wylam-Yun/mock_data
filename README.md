# mock_data — OBS 增程商品变更 SOP 模拟数据集

## 文件清单

| 文件 | 条数 | 说明 |
|---|---|---|
| `sop.md` | 115 步骤 | SOP 定义 |
| `event_clean.json` | 52 条 | 纯净版，仅 SOP 对应的有效日志 |
| `event_with_noise.json` | 5200 条 | 52 有效 + 5148 噪声，有效日志措辞与 SOP 一致 |
| `event_noise_paraphrased.json` | 5200 条 | 同上，有效日志的 event_name / detection_log / related_sop_ref 全部语义改写 |
| `event_paraphrase_mapping.json` | 52 条 | 语义改写前后对照表，用作 ground truth |

## 用法

- `event_clean.json` → 基线，验证模型能否识别全部 SOP 步骤
- `event_with_noise.json` → 测试精确匹配下的噪声过滤能力
- `event_noise_paraphrased.json` → 测试纯语义理解能力（所有字段均改写，无法靠精确匹配）
- `event_paraphrase_mapping.json` → 评估语义匹配的 precision / recall

## 数据结构

日志条目：`log_id`（LOG-xxx=有效, NOISE-xxxxx=噪声）、`related_sop_ref`（噪声为 null）、`event_time`（严格升序）、`actor`（lisi/zhangsan）、`role`、`platform`、`event_type`、`event_name`、`params`、`detection_log`、`seq_id`

噪声特征：仅 lisi/zhangsan 两人，按 SOP 阶段生成上下文相关噪声，覆盖 17 个平台，操作其他集群/组件/变更单。
