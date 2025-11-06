# 商业化模块文档

## 概述

本模块为 Kode AI ERP 平台添加了完整的订阅计费系统，支持按月订阅的套餐模式，并集成了 Stripe 支付。

## 功能特性

### 1. 订阅套餐管理

提供三个套餐等级（类似 Cursor）：

| 套餐 | 价格 | Token 配额 | 消息配额 | 对话数 | 数据库连接 | 高级功能 |
|------|------|-----------|---------|--------|-----------|---------|
| 免费版 | ¥0 | 10万/月 | 50条/月 | 3个 | - | - |
| 专业版 | ¥99/月 | 200万/月 | 1000条/月 | 50个 | 5个 | ✓ |
| 企业版 | ¥499/月 | 1000万/月 | 10000条/月 | 500个 | 50个 | ✓✓ |

**高级功能包括**：
- 数据库连接和查询
- 业务本体（Ontology）构建
- 高级数据分析
- 优先技术支持（企业版）

### 2. 使用量追踪

自动追踪并记录：
- ✅ Token 使用量（基于字符数估算，约 1 token = 4 字符）
- ✅ 消息条数
- ✅ 对话数量
- ✅ 数据库查询次数

### 3. 配额限制

- 在 SSE 聊天端点自动检查配额
- 超额时返回 429 状态码，提示升级套餐
- 每个计费周期重置使用量

### 4. Stripe 支付集成

- ✅ 创建 Checkout Session
- ✅ 处理支付成功回调
- ✅ 处理订阅续费
- ✅ 处理支付失败和订阅取消
- ✅ Webhook 事件处理

## 数据库架构

### 新增表

#### `plans` - 订阅套餐表
```sql
- id: 套餐ID
- name: 套餐名称（free, pro, enterprise）
- display_name: 显示名称
- price: 价格
- token_quota: Token 配额
- message_quota: 消息配额
- conversation_quota: 对话配额
- database_connection_quota: 数据库连接配额
- database_access: 是否支持数据库功能
- advanced_analysis: 是否支持高级分析
- ontology_building: 是否支持本体构建
- priority_support: 是否享受优先支持
```

#### `subscriptions` - 用户订阅表
```sql
- id: 订阅ID
- user_id: 用户ID（外键）
- plan_id: 套餐ID（外键）
- status: 订阅状态（active, expired, cancelled, trial）
- start_date: 开始时间
- end_date: 结束时间
- auto_renew: 是否自动续费
- stripe_customer_id: Stripe 客户ID
- stripe_subscription_id: Stripe 订阅ID
```

#### `usage` - 使用量记录表
```sql
- id: 记录ID
- user_id: 用户ID（外键）
- subscription_id: 订阅ID（外键）
- period_start: 计费周期开始
- period_end: 计费周期结束
- token_count: Token 使用量
- message_count: 消息数
- conversation_count: 对话数
- database_query_count: 数据库查询次数
```

## API 端点

### 套餐管理

```bash
GET  /api/billing/plans              # 列出所有套餐
GET  /api/billing/plans/{plan_id}    # 获取套餐详情
POST /api/billing/plans              # 创建套餐（管理员）
PATCH /api/billing/plans/{plan_id}   # 更新套餐（管理员）
```

### 订阅管理

```bash
GET  /api/billing/subscriptions/me                    # 获取当前用户订阅
POST /api/billing/subscriptions                       # 创建订阅
POST /api/billing/subscriptions/{id}/cancel          # 取消订阅
```

### 使用量查询

```bash
GET /api/billing/usage/me           # 获取当前用户使用量
GET /api/billing/usage/me/summary   # 获取使用量摘要
```

### Stripe 支付

```bash
POST /api/billing/stripe/checkout    # 创建 Stripe Checkout Session
POST /api/billing/stripe/webhook     # Stripe Webhook 回调
```

## 配置说明

在 `.kode.json` 或环境变量中配置：

```json
{
  "stripe": {
    "secret_key": "sk_test_...",
    "webhook_secret": "whsec_..."
  }
}
```

或使用环境变量：

```bash
export STRIPE_SECRET_KEY="sk_test_..."
export STRIPE_WEBHOOK_SECRET="whsec_..."
```

## 安装和迁移

### 1. 安装依赖

```bash
poetry install
```

如需 Stripe 集成，安装：

```bash
poetry add stripe
```

### 2. 运行数据库迁移

```bash
python scripts/migrate_billing.py
```

迁移脚本会：
1. 创建 `plans`, `subscriptions`, `usage` 表
2. 创建三个默认套餐（免费版、专业版、企业版）
3. 为现有用户分配免费订阅

### 3. 启动服务

```bash
python run.py
# 或
python -m kode.web.main
```

## 使用示例

### 1. 查看可用套餐

```bash
curl http://localhost:8001/api/billing/plans
```

### 2. 查看当前订阅

```bash
curl http://localhost:8001/api/billing/subscriptions/me \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 3. 查看使用量摘要

```bash
curl http://localhost:8001/api/billing/usage/me/summary \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 4. 创建 Stripe 支付会话

```bash
curl -X POST http://localhost:8001/api/billing/stripe/checkout \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "plan_id": "pro-plan-id",
    "success_url": "https://yourapp.com/success",
    "cancel_url": "https://yourapp.com/cancel"
  }'
```

返回：
```json
{
  "session_id": "cs_test_...",
  "checkout_url": "https://checkout.stripe.com/..."
}
```

## 核心服务

### BillingService

主要方法：
- `get_user_active_subscription()` - 获取用户有效订阅
- `create_subscription()` - 创建订阅
- `cancel_subscription()` - 取消订阅
- `increment_usage()` - 增加使用量
- `get_usage_summary()` - 获取使用量摘要
- `check_quota()` - 检查配额

### StripeService

主要方法：
- `create_customer()` - 创建 Stripe 客户
- `create_checkout_session()` - 创建支付会话
- `handle_webhook()` - 处理 Webhook 事件
- `cancel_subscription()` - 取消 Stripe 订阅

## 配额检查流程

1. 用户发送消息到 `/api/sse/chat/{conversation_id}/stream`
2. 系统调用 `check_user_quota()` 检查配额
3. 如果配额充足，继续处理请求
4. 如果配额不足，返回 429 错误：

```json
{
  "detail": "配额已用尽，请升级套餐或等待下个计费周期",
  "error_code": "QUOTA_EXCEEDED"
}
```

5. 消息处理完成后，自动调用 `increment_usage()` 更新使用量

## 文件清单

### 数据库模型
- `kode/models/plan.py` - 套餐模型
- `kode/models/subscription.py` - 订阅模型
- `kode/models/usage.py` - 使用量模型

### Pydantic Schemas
- `kode/schemas/billing.py` - 所有计费相关的请求/响应 Schema

### 服务层
- `kode/services/billing_service.py` - 计费业务逻辑
- `kode/services/stripe_service.py` - Stripe 集成

### API 端点
- `kode/web/api/billing.py` - 计费相关 REST API

### 中间件
- `kode/web/middleware/quota_check.py` - 配额检查中间件

### 数据库迁移
- `scripts/migrate_billing.py` - 迁移脚本

## 注意事项

1. **Token 计算**：当前使用字符数估算（1 token ≈ 4 字符），未来可集成 `tiktoken` 库精确计算

2. **Stripe 测试**：开发环境使用 Stripe 测试密钥，生产环境替换为正式密钥

3. **Webhook 安全**：确保配置 `STRIPE_WEBHOOK_SECRET`，验证 Webhook 签名

4. **配额重置**：每个计费周期自动重置使用量（基于订阅的 `start_date` 和 `end_date`）

5. **默认订阅**：新用户自动分配免费订阅，有效期 10 年

## 未来优化

- [ ] 集成 tiktoken 库精确计算 Token 数量
- [ ] 添加使用量预警通知（邮件/站内信）
- [ ] 支持套餐升级/降级
- [ ] 添加发票生成功能
- [ ] 支持团队协作和席位管理
- [ ] 添加使用量分析仪表板
- [ ] 支持优惠码和促销活动
- [ ] 集成其他支付方式（支付宝、微信支付）

## 问题排查

### 1. 配额检查失败

检查用户是否有有效订阅：
```sql
SELECT * FROM subscriptions WHERE user_id = 'xxx' AND status = 'active';
```

### 2. 使用量未更新

检查 SSE 端点日志，确认 `increment_usage()` 被调用。

### 3. Stripe Webhook 失败

- 验证 `STRIPE_WEBHOOK_SECRET` 配置正确
- 检查 Stripe Dashboard 的 Webhook 日志
- 确保服务器可公网访问（本地测试可用 ngrok）

## 联系支持

如有问题，请提交 Issue 或联系技术支持。
