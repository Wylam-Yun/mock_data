# 1+1 Checker Pipeline 设计

## 背景

1+1 Checker 是一个面向 SRE 变更场景的**监督质量检查系统**。

核心问题：在"1+1 双人变更机制"中，执行人负责动手操作，配合人负责独立监督。但实际执行中，配合人往往只是"在旁边看着"或机械点击确认，没有真正独立核查。

Checker 的目标：以 SOP 为标准答案，以白屏/黑屏/平台日志为证据，自动判断**执行人是否合规操作**、**配合人是否真实监督**。

## 核心判断维度

1. **执行人合规性**：执行人有没有做 SOP 要求的操作？参数对不对？结果符不符合预期？
2. **配合人履职性**：配合人有没有做 SOP 要求的监督动作？有没有独立的查询/截图/回填证据？
3. **时序合理性**：配合人的确认是否在执行人操作之后合理时间内？确认太快可能是"陪跑"。
4. **独立性判定**：配合人有没有被被执行人带着走？有没有独立判断的证据？

## 为什么不是纯 RAG 场景

典型 RAG 场景是"用户问模糊问题，从大量文档里找相关片段回答"。但 1+1 Checker 的场景不同：

- SOP 是**结构化的**，有编号、有角色、有明确检查项，不是散文
- 日志也是**结构化的**，有时间戳、命令、回显、平台操作记录
- Checker 要做的不是"语义相似度检索"，而是**逐条 checklist 对账**

RAG 在这个系统中是**辅助检索工具**（用于 Stage 2 的模糊匹配），不是核心。核心是 SOP 解析 + 规则匹配 + LLM 推理。

## Pipeline 总览

```
输入层（SOP + 日志）
    │
    ▼
Stage 1：结构化预处理（确定性解析）
    │
    ▼
Stage 2：证据匹配（规则为主 + RAG 辅助）
    │
    ▼
Stage 3：合规判定（规则 + LLM 混合推理）
    │
    ▼
Stage 4：独立性分析（时序 + 关联推理）
    │
    ▼
Stage 5：报告生成（LLM 综合推理）
    │
    ▼
输出：结构化风险评估报告
```

---

## Stage 1：结构化预处理

**目标**：把非结构化的 SOP 和日志变成结构化数据，供后续 Stage 使用。

**不需要 LLM，不需要 RAG。** 纯确定性解析。

### 1a. SOP Parser

将 `sop.md` 解析为结构化步骤列表。

每个步骤输出：

```json
{
  "step_id": "SOP-EVT-073",
  "phase": "02-操作处理",
  "sub_phase": "1-创建增程商品",
  "role": "执行人",
  "action": "执行 grep -A 3 \"${DomainId}:${ProductName}\" /opt/.../bill_extend_product.json",
  "target": "bill_extend_product.json",
  "action_type": "shell_command",
  "expected": "回显包含增程商品信息",
  "evidence_source": "黑屏日志",
  "check_method": "精确命令匹配",
  "references": ["SOP-EVT-071"],
  "is_verification": true
}
```

关键标注字段说明：
- `evidence_source`：这个步骤的证据应该从哪里找（黑屏日志 / 白屏记录 / CAC 平台 / 时序推断 / 不可验证）
- `check_method`：用什么方式检查（精确命令匹配 / 关键词匹配 / 时序校验 / 人工确认 / 不可自动检查）
- `references`：前置依赖步骤的 ID
- `is_verification`：是否是验证类步骤（配合人需要独立确认的）

### 1b. Log Parser（多个 parser 并行）

不同日志源需要不同的解析器：

**黑屏日志 Parser**：
```json
{
  "timestamp": "2026-05-22T14:30:00+08:00",
  "user": "zhangsan",
  "role": "执行人",
  "command": "grep -A 3 \"Domain123:ProductA\" /opt/.../bill_extend_product.json",
  "args": ["-A", "3", "Domain123:ProductA"],
  "target_file": "/opt/.../bill_extend_product.json",
  "stdout": "...",
  "exit_code": 0,
  "source": "black_screen"
}
```

**白屏日志 Parser**：
```json
{
  "timestamp": "2026-05-22T14:35:00+08:00",
  "user": "lisi",
  "role": "配合人",
  "platform": "告警平台",
  "page": "告警列表",
  "query_params": {"cluster": "target_cluster", "status": "未处理"},
  "action_type": "查询",
  "result_summary": "查看了目标集群告警列表",
  "has_screenshot": true,
  "source": "white_screen"
}
```

**CAC 执行记录 Parser**：
```json
{
  "timestamp": "2026-05-22T14:25:00+08:00",
  "user": "zhangsan",
  "role": "执行人",
  "script": "cac_obs_oam_cli_execute",
  "params": {"action": "create", "target": "obsBillExtendProduct", ...},
  "result": "success",
  "source": "cac"
}
```

---

## Stage 2：证据匹配

**目标**：对每个 SOP 步骤，在预处理后的日志中找到对应的证据。

**规则匹配为主，RAG 辅助。**

### 2a. 精确匹配（规则引擎）

适用于 `check_method == "精确命令匹配"` 的步骤。

匹配逻辑：
- 从 SOP 步骤中提取关键特征（命令名、参数模式、目标文件）
- 在对应 `evidence_source` 的日志中用关键词/正则搜索
- 命中后校验参数（支持变量替换后的比对）

示例：SOP-EVT-073 要求执行 `grep -A 3 "${DomainId}:${ProductName}" ...`
- 在黑屏日志中搜索 `grep -A 3` + 包含变量值的参数
- 命中 `log_entry_20260522_143000`
- 校验目标文件路径一致

### 2b. 模糊匹配（RAG 辅助）

适用于 `check_method` 为关键词匹配或语义理解的步骤。

场景：SOP-EVT-001 "配合人分析目标集群未处理告警"
- 日志里不会有这么精确的描述
- RAG 从白屏日志中检索 "告警" "未处理" "目标集群" 相关片段
- 返回候选证据列表，交给 Stage 3 的 LLM 做最终判断

RAG 在此阶段的价值：
- 日志量大时，缩小后续规则匹配的范围
- 处理日志格式不统一、描述方式多样的情况
- 处理 SOP 中的引用跳转（如"按操作检测中的告警检测项执行"）

### 输出：Evidence Map

```json
{
  "SOP-EVT-073": {
    "status": "found",
    "evidence": ["log_entry_20260522_143000"],
    "match_type": "exact",
    "confidence": 1.0
  },
  "SOP-EVT-001": {
    "status": "found",
    "evidence": ["log_entry_yyy", "log_entry_zzz"],
    "match_type": "rag",
    "confidence": 0.7
  },
  "SOP-EVT-082": {
    "status": "not_applicable",
    "evidence": [],
    "match_type": "none",
    "confidence": null
  }
}
```

`status` 枚举值：
- `found`：找到明确证据
- `not_found`：未找到证据
- `partial`：找到部分证据（如只有命令没有回显）
- `not_applicable`：该步骤不需要日志证据（如"等待5分钟"）

---

## Stage 3：合规判定

**目标**：对每个 SOP 步骤，判断"做了没"和"做得对不对"。

**确定性判断用规则，模糊判断用 LLM。**

### 3a. 确定性判定（规则引擎）

适用于 Evidence Map 中 `match_type == "exact"` 且 `confidence == 1.0` 的步骤。

检查项：
- 该步骤有没有找到证据？ → found / not_found
- 命令参数是否匹配？ → 正则比对变量替换后的值
- 回显是否符合预期？ → 关键字段提取比对
- 执行时间是否在合理区间？ → 时序校验
- 角色是否正确？ → 执行人/配合人 vs 日志 user

输出：明确 pass / fail 的步骤

### 3b. 模糊判定（LLM 推理）

适用于 RAG 匹配的、confidence 低的、需要语义理解的步骤。

输入给 LLM 的 prompt 结构：

```
SOP 要求: {step.description}
日志证据: {step.evidence}
预期结果: {step.expected}

请判断:
1. 该步骤是否已完成？
2. 执行方式是否正确？
3. 结果是否符合预期？
```

输出：pass / fail / warning + 理由

### 输出：Compliance Results

```json
[
  {
    "step_id": "SOP-EVT-073",
    "verdict": "pass",
    "executor": "zhangsan",
    "detail": "黑屏日志找到 grep 命令，参数匹配，回显正常"
  },
  {
    "step_id": "SOP-EVT-075",
    "verdict": "fail",
    "executor": "lisi",
    "detail": "未找到配合人核对回显的证据"
  },
  {
    "step_id": "SOP-EVT-001",
    "verdict": "warning",
    "executor": "lisi",
    "detail": "找到告警查询记录但无法确认是否针对目标集群"
  }
]
```

`verdict` 枚举值：
- `pass`：步骤合规完成
- `fail`：步骤未完成或执行错误
- `warning`：有证据但不够明确，需要人工确认
- `skip`：步骤被跳过（有合理理由，如回退场景）
- `not_applicable`：步骤不适用于本次变更

---

## Stage 4：独立性分析

**目标**：判断配合人是否真实监督，还是"陪跑式监督"。

**这是 1+1 Checker 区别于普通合规检查的核心 Stage。**

### 4a. 时序分析

对每对"执行人动作 → 配合人验证"，分析时间间隔。

规则示例：
- 配合人确认时间 < 执行人操作时间 + 30秒 → 标记"确认过快，可能未实际核查"
- 配合人确认时间在合理窗口内 → 时序上合理，还需看独立证据
- 配合人确认时间远晚于执行人操作 → 可能遗漏或延迟监督

### 4b. 独立性判定

判断配合人的"确认"有没有独立证据支撑。

**有独立证据的情况**：
- 配合人白屏有独立的告警页面访问记录
- 配合人白屏有独立的查询操作（不同查询参数）
- 配合人有截图/回填记录，且截图内容与步骤相关
- 配合人执行了独立的验证命令（如白屏上的拨测检测）

→ 判定：**独立监督**

**无独立证据的情况**：
- 配合人只有"确认"/"正常"的文字回填
- 无白屏操作记录
- 无截图
- 确认时间紧跟执行人操作

→ 判定：**陪跑式监督**

### 输出：Independence Analysis

```json
[
  {
    "step_group": "SOP-EVT-073~075",
    "executor_action": "执行 grep 命令验证增程商品",
    "supervisor_action": "确认回显正常",
    "executor_time": "14:30:00",
    "supervisor_time": "14:30:05",
    "time_gap_seconds": 5,
    "independent_evidence": false,
    "verdict": "陪跑式监督",
    "detail": "配合人在执行人操作后5秒内确认，无独立白屏查询或截图证据"
  },
  {
    "step_group": "SOP-EVT-001~005",
    "executor_action": "无（配合人独立操作）",
    "supervisor_action": "分析目标集群告警",
    "supervisor_time": "14:00:30",
    "time_gap_seconds": null,
    "independent_evidence": true,
    "verdict": "独立监督",
    "detail": "配合人白屏有告警平台访问记录，查询了目标集群未处理告警列表"
  }
]
```

---

## Stage 5：报告生成

**目标**：综合所有判定结果，生成结构化风险评估报告。

**使用 LLM 做综合推理和自然语言生成。**

### 输入

- Compliance Results（Stage 3 输出）
- Independence Analysis（Stage 4 输出）
- SOP 基本信息（变更名称、变更对象等）

### 输出格式

```markdown
## 变更合规检查报告

**变更名称**：创建增程商品变更
**变更对象**：OBS bill 组件增程商品配置
**检查时间**：2026-05-22

### 检查总览

| 阶段 | 总步骤 | 通过 | 风险 | 跳过 |
|------|--------|------|------|------|
| 操作检测 | 64 | 58 | 6 | 0 |
| 操作处理 | 12 | 10 | 2 | 0 |
| 操作验证 | 14 | 12 | 2 | 0 |

### 高风险发现

#### 1. [SOP-EVT-075] 配合人未独立核对 grep 回显
- **风险类型**：陪跑式监督
- **详情**：执行人完成 grep 命令后配合人仅 5 秒内确认，无截图或独立查询记录
- **建议**：要求配合人补充独立验证证据

#### 2. [SOP-EVT-089~092] 变更后告警/拨测检测证据不足
- **风险类型**：一步一检缺失
- **详情**：白屏日志中未找到配合人针对目标集群的告警查询记录，仅有一条"检测完成"回填
- **建议**：要求配合人提供告警平台查询截图

### 总体结论

本次变更执行人操作基本合规，但配合人监督质量不足，存在 3 处"一步一检缺失"风险。
建议：要求配合人补充独立验证证据后方可关闭变更单。
```

---

## 技术选型总结

| Stage | 核心技术 | 需要 LLM？ | 需要 RAG？ |
|-------|---------|-----------|-----------|
| 1 - 结构化预处理 | 正则/解析器 | 不需要 | 不需要 |
| 2 - 证据匹配 | 关键词匹配为主，RAG 辅助 | 不需要 | **需要**（模糊匹配） |
| 3 - 合规判定 | 规则引擎 + LLM | 部分需要 | 不需要 |
| 4 - 独立性分析 | 时序分析 + LLM | 需要 | 不需要 |
| 5 - 报告生成 | LLM | 需要 | 不需要 |

### 关键结论

RAG 只在 Stage 2 的模糊匹配环节真正需要。其他四个 Stage 要么是确定性解析，要么是 LLM 推理，不需要检索增强。

## 建议实施顺序

1. **先做 Stage 1 + Stage 3a**：SOP 解析 + 规则匹配，能覆盖 60-70% 的检查项
2. **再做 Stage 4**：独立性分析，这是 1+1 Checker 的核心差异化能力
3. **然后做 Stage 5**：报告生成，用 LLM 综合输出
4. **最后做 Stage 2b + Stage 3b**：RAG 辅助匹配 + LLM 模糊判定，处理剩余的模糊场景

先用关键词匹配跑通主流程，等发现关键词匹配不够用的时候再加 RAG。
