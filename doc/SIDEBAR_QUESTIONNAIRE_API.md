# 侧边栏问卷 API 文档

## 概述

本文档描述了侧边栏问卷功能的后端 API 接口。该功能允许用户在侧边栏中填写不确定性问题问卷，无需阻塞 AI 对话流程。

### 核心变更

**从阻塞式弹框改为侧边栏主动模式：**

| 旧流程（已废弃） | 新流程（推荐） |
|-----------------|---------------|
| Agent 触发 → 弹框阻塞 → 用户必须回答 | 用户点击上下文按钮 → 侧边栏显示问卷 → 随时填写 |
| 构建本体前：硬阻止 | 构建本体前：软提示，引导用户去侧边栏 |

---

## API 端点

### 基础路径

```
/api/uncertainty
```

---

### 1. 加载问卷 - `POST /sidebar/load`

前端侧边栏在用户选择数据库后调用此 API 加载问卷。

#### 请求

```typescript
interface SidebarLoadRequest {
  connection_name: string;           // 数据库连接名称（必填）
  priority_filter?: string[];        // 优先级过滤 ['high', 'medium', 'low']
  status_filter?: string[];          // 状态过滤 ['pending', 'resolved', 'skipped']，默认 ['pending']
  group_by?: 'domain' | 'priority' | 'none';  // 分组方式，默认 'domain'
  limit?: number;                    // 限制返回数量
}
```

#### 响应

```typescript
interface SidebarLoadResponse {
  status: 'success' | 'no_analysis';  // no_analysis 表示尚未进行分析
  connection_name: string;
  total_count: number;                // 总问题数
  filtered_count: number;             // 过滤后显示的问题数
  groups: UncertaintyGroup[];         // 分组后的问题列表
  summary: {                          // 各优先级统计
    high: { total: number; resolved: number; skipped: number; remaining: number };
    medium: { total: number; resolved: number; skipped: number; remaining: number };
    low: { total: number; resolved: number; skipped: number; remaining: number };
  };
  can_build_ontology: boolean;        // 是否可以构建本体（high.remaining === 0）
  message: string;
}

interface UncertaintyGroup {
  domain: string;                     // 业务域名称（或优先级，取决于 group_by）
  question_count: number;
  questions: UncertaintyItem[];
}

interface UncertaintyItem {
  id: string;                         // 问题唯一 ID（用于提交答案）
  domain: string;
  type: string;
  category: string;
  priority: 'high' | 'medium' | 'low';
  entity: string;                     // 关联的表名
  question: string;                   // 问题内容
  context?: string;                   // 上下文信息
  impact?: string;                    // 影响范围
  suggestions: string[];              // 建议选项
  status?: 'resolved' | 'skipped';    // 已回答/已跳过
  answer?: string;                    // 已有的回答
  answered_at?: string;               // 回答时间 ISO 格式
}
```

#### 示例

```bash
# 加载所有待处理的高优先级问题
curl -X POST http://localhost:8001/api/uncertainty/sidebar/load \
  -H "Content-Type: application/json" \
  -d '{
    "connection_name": "yanfa",
    "priority_filter": ["high"],
    "status_filter": ["pending"],
    "group_by": "domain"
  }'
```

---

### 2. 回答单个问题 - `POST /sidebar/answer`

用户在侧边栏中回答单个问题后立即调用，答案实时保存。

#### 请求

```typescript
interface SingleAnswerRequest {
  connection_name: string;
  uncertainty_id: string;             // 问题 ID（从 load 接口获取）
  answer: string;                     // 用户回答
}
```

#### 响应

```typescript
interface SingleAnswerResponse {
  status: 'success';
  uncertainty_id: string;
  message: string;
  remaining_high_priority: number;    // 剩余高优先级问题数
  can_build_ontology: boolean;        // 是否可以构建本体
}
```

#### 示例

```bash
curl -X POST http://localhost:8001/api/uncertainty/sidebar/answer \
  -H "Content-Type: application/json" \
  -d '{
    "connection_name": "yanfa",
    "uncertainty_id": "sales_order_abc123",
    "answer": "status 字段表示订单状态，取值：0=待付款，1=已付款，2=已发货，3=已完成"
  }'
```

---

### 3. 批量回答问题 - `POST /sidebar/batch-answer`

用户填写完多个问题后一次性提交。

#### 请求

```typescript
interface SidebarBatchAnswerRequest {
  connection_name: string;
  answers: Record<string, string>;    // { uncertainty_id: answer }
}
```

#### 响应

```typescript
interface SidebarBatchAnswerResponse {
  status: 'success';
  resolved_count: number;             // 本次解决的问题数
  not_found: string[];                // 未找到的问题 ID
  remaining_high_priority: number;
  can_build_ontology: boolean;
  summary: {                          // 更新后的统计
    high: { total: number; resolved: number; skipped: number; remaining: number };
    medium: { ... };
    low: { ... };
  };
  message: string;
}
```

#### 示例

```bash
curl -X POST http://localhost:8001/api/uncertainty/sidebar/batch-answer \
  -H "Content-Type: application/json" \
  -d '{
    "connection_name": "yanfa",
    "answers": {
      "sales_order_abc123": "status 表示订单状态",
      "inventory_stock_def456": "qty 是可用库存数量，不包含预留"
    }
  }'
```

---

### 4. 跳过问题 - `POST /sidebar/skip`

跳过非高优先级问题（高优先级问题不允许跳过）。

#### 请求

```typescript
interface SkipQuestionRequest {
  connection_name: string;
  uncertainty_id: string;
  reason?: string;                    // 跳过原因（可选）
}
```

#### 响应

```typescript
interface SkipQuestionResponse {
  status: 'success' | 'error';
  uncertainty_id: string;
  skipped_priority: string;           // 被跳过问题的优先级
  message: string;
  remaining_high_priority: number;
  can_build_ontology: boolean;
}
```

#### 错误情况

```json
// 尝试跳过高优先级问题
{
  "detail": "高优先级问题不允许跳过，必须回答！"
}
```

---

### 5. 获取状态 - `GET /status/{connection_name}`

获取当前问卷进度统计（已有接口，保持不变）。

#### 响应

```typescript
interface UncertaintyStatusResponse {
  status: 'success';
  connection_name: string;
  summary: {
    high: { total: number; resolved: number; skipped: number; remaining: number };
    medium: { ... };
    low: { ... };
  };
  can_build_ontology: boolean;
  message: string;
}
```

---

## 前端集成指南

### 1. 侧边栏触发时机

```typescript
// 当用户选择数据库时，加载问卷状态
async function onDatabaseSelected(connectionName: string) {
  const response = await api.post('/api/uncertainty/sidebar/load', {
    connection_name: connectionName,
    priority_filter: ['high', 'medium'],  // 只显示高、中优先级
    status_filter: ['pending'],
  });

  if (response.status === 'no_analysis') {
    // 显示"尚未分析"状态
    showNoAnalysisState();
  } else {
    // 渲染问卷
    renderQuestionnaire(response.groups);
    // 更新进度条
    updateProgress(response.summary);
  }
}
```

### 2. 问卷 UI 建议

```
┌─────────────────────────────────────┐
│ 上下文                         [X] │
├─────────────────────────────────────┤
│ 📊 数据库问卷                        │
│ ──────────────────────────────────  │
│ 进度: [████████░░░░] 8/12 已完成     │
│                                     │
│ 🔴 高优先级 (4 个待回答)              │
│ ├─ 销售域                            │
│ │  ├─ order 表的 status 字段含义？   │
│ │  │  [文本框输入答案...]            │
│ │  │              [提交]            │
│ │  └─ payment_status 与 status 区别？│
│ │     [文本框...]                   │
│ └─ 库存域                            │
│    └─ ...                           │
│                                     │
│ 🟡 中优先级 (3 个待回答)              │
│ └─ [展开/收起]                       │
└─────────────────────────────────────┘
```

### 3. 实时保存

```typescript
// 用户输入后自动保存（防抖）
const debouncedSave = debounce(async (id: string, answer: string) => {
  await api.post('/api/uncertainty/sidebar/answer', {
    connection_name: currentConnection,
    uncertainty_id: id,
    answer,
  });
  // 更新本地状态
  updateLocalProgress();
}, 1000);

// 输入框 onBlur 时也触发保存
```

### 4. 与 AI 对话集成

当 AI 返回 `sidebar_action` 字段时，前端应自动打开侧边栏：

```typescript
// SSE 消息处理
function handleToolResult(result: any) {
  if (result.sidebar_action?.type === 'open_questionnaire') {
    // 自动打开侧边栏并定位到问卷
    openSidebar('questionnaire');
    // 高亮提示
    showNotification(`发现 ${result.sidebar_action.unresolved_count} 个待回答问题`);
  }
}
```

---

## OntologyBuilder 行为变更

### 旧行为（硬阻止）

```json
{
  "status": "error",
  "gate_check_failed": true,
  "message": "❌ 不能构建本体！发现 N 个未解决的高优先级问题。"
}
```

### 新行为（软提示）

```json
{
  "status": "warning",
  "gate_check_failed": false,
  "message": "⚠️ 发现 N 个未解决的高优先级问题。",
  "suggestion": "建议先回答高优先级问题以提高本体质量。\n用户可以：\n1. 点击界面右上角的「上下文」按钮，在侧边栏中填写问卷\n2. 或者告诉我「跳过问卷，直接构建本体」（会影响本体质量）",
  "sidebar_action": {
    "type": "open_questionnaire",
    "connection_name": "yanfa",
    "unresolved_count": 5
  }
}
```

### 跳过检查

用户说"跳过问卷，直接构建"时，Agent 调用：

```python
OntologyBuilder(connection_name='yanfa', skip_uncertainty_check=True)
```

---

## 错误处理

| HTTP 状态码 | 场景 | 响应 |
|------------|------|------|
| 200 | 成功 | 正常响应 |
| 400 | 尝试跳过高优先级问题 | `{"detail": "高优先级问题不允许跳过，必须回答！"}` |
| 404 | 问题 ID 不存在 | `{"detail": "未找到问题 ID: xxx"}` |
| 404 | 领域目录不存在 | `{"detail": "未找到领域文件目录"}` |
| 500 | 服务器内部错误 | `{"detail": "加载问卷失败: ..."}` |

---

## 数据存储位置

问卷答案存储在 `schema_store/{connection_name}/domains/{domain}.json` 中：

```json
{
  "domain_name": "sales",
  "tables": {...},
  "uncertainties": [
    {
      "id": "sales_order_abc123",
      "status": "resolved",
      "answer": "用户的回答",
      "answered_at": "2025-11-26T10:30:00"
    }
  ],
  "business_rules": [
    {
      "entity": "order",
      "question": "status 字段含义？",
      "answer": "用户的回答",
      "added_at": "2025-11-26T10:30:00"
    }
  ]
}
```
