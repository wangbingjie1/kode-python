# Stripe Webhook 本地测试指南

## 问题：支付成功但套餐未升级

**原因**：本地开发环境无法直接接收 Stripe 的 webhook 回调，因为 Stripe 服务器无法访问 localhost。

## 解决方案：使用 Stripe CLI 转发 Webhook

### 步骤 1：安装 Stripe CLI

Windows 下载：https://github.com/stripe/stripe-cli/releases/latest

或使用 Scoop：
```bash
scoop install stripe
```

### 步骤 2：登录 Stripe CLI

```bash
stripe login
```

这会打开浏览器让你授权 Stripe CLI 访问你的账户。

### 步骤 3：启动 Webhook 监听

**在新的终端窗口运行：**
```bash
stripe listen --forward-to http://localhost:8001/api/billing/stripe/webhook
```

你会看到类似输出：
```
> Ready! Your webhook signing secret is whsec_1234567890abcdef (^C to quit)
```

**复制这个 signing secret！**

### 步骤 4：配置 Webhook Secret

在 `.env` 文件中添加（或修改）：
```bash
STRIPE_WEBHOOK_SECRET=whsec_1234567890abcdef
```

**重要**：每次运行 `stripe listen` 都会生成新的 secret，需要更新 `.env`。

### 步骤 5：重启后端服务

```bash
# 停止当前后端（Ctrl+C）
# 重新启动
.venv/Scripts/python.exe run.py
```

### 步骤 6：测试完整支付流程

1. **保持 Stripe CLI 运行**（终端显示 "Ready!"）
2. **访问前端** - http://localhost:3000
3. **登录账户**
4. **进入个人中心 (Profile)**
5. **点击升级按钮**
6. **使用测试卡号**：`4242 4242 4242 4242`
   - 过期日期：任意未来日期（如 12/34）
   - CVC：任意 3 位数（如 123）
   - 邮编：任意（如 12345）
7. **完成支付**

### 步骤 7：观察结果

**Stripe CLI 终端会显示：**
```
2025-11-07 15:30:00 --> checkout.session.completed [evt_xxx]
2025-11-07 15:30:00 <-- [200] POST http://localhost:8001/api/billing/stripe/webhook
```

**后端日志会显示：**
```
INFO - Received Stripe webhook: checkout.session.completed
INFO - Checkout completed for user xxx, plan xxx
```

**前端页面会显示：**
- 套餐已升级到 Pro/Enterprise
- 配额已更新
- 使用量统计正确

## Webhook 事件流程

```
用户支付成功
    ↓
Stripe 触发 webhook: checkout.session.completed
    ↓
Stripe CLI 转发到本地: localhost:8001/api/billing/stripe/webhook
    ↓
后端验证签名（使用 STRIPE_WEBHOOK_SECRET）
    ↓
后端调用 StripeService.handle_webhook()
    ↓
创建/更新 Subscription 记录
    ↓
套餐升级完成
```

## 支持的 Webhook 事件

| 事件类型 | 处理逻辑 |
|---------|---------|
| `checkout.session.completed` | 创建订阅，绑定 Stripe Customer 和 Subscription ID |
| `invoice.payment_succeeded` | 续费成功，延长订阅周期 |
| `invoice.payment_failed` | 支付失败，标记订阅为 EXPIRED |
| `customer.subscription.deleted` | 取消订阅，设置结束日期 |

## 常见问题

### Q1: Stripe CLI 显示 "404 Not Found"
**A**: 检查 webhook 路径是否正确：
```bash
# 正确路径
stripe listen --forward-to http://localhost:8001/api/billing/stripe/webhook

# 错误路径（缺少 /api 前缀）
stripe listen --forward-to http://localhost:8001/billing/stripe/webhook
```

### Q2: 后端报错 "Invalid webhook signature"
**A**: `.env` 中的 `STRIPE_WEBHOOK_SECRET` 与 Stripe CLI 输出的不一致。重新复制粘贴。

### Q3: 支付成功但 Stripe CLI 没反应
**A**: 确保 Stripe CLI 在后台运行，终端显示 "Ready!"。

### Q4: 如何验证 webhook 是否生效？
**A**: 查看后端日志：
```bash
# 应该看到
INFO - Received Stripe webhook: checkout.session.completed
INFO - Checkout completed for user xxx, plan xxx
```

### Q5: 生产环境如何配置？
**A**: 在 Stripe Dashboard 配置真实的 webhook endpoint：
1. 登录 Stripe Dashboard
2. Developers → Webhooks → Add endpoint
3. Endpoint URL: `https://yourdomain.com/api/billing/stripe/webhook`
4. 选择事件：`checkout.session.completed`, `invoice.*`, `customer.subscription.*`
5. 复制 Signing Secret 到生产环境的 `.env`

## 测试命令速查

```bash
# 1. 启动 Stripe CLI 监听
stripe listen --forward-to http://localhost:8001/api/billing/stripe/webhook

# 2. 手动触发测试事件（可选）
stripe trigger checkout.session.completed

# 3. 查看 webhook 日志
stripe logs tail

# 4. 验证 webhook endpoint
curl -X POST http://localhost:8001/api/billing/stripe/webhook \
  -H "Content-Type: application/json" \
  -d '{}'
# 应该返回 400 (Missing Stripe signature)，说明端点正常运行
```

## 下一步

配置完成后，你的支付流程应该完整工作：
1. ✅ 创建 Checkout Session
2. ✅ 跳转到 Stripe 支付页面
3. ✅ 支付成功
4. ✅ **Webhook 回调升级套餐** ← 这是之前缺失的
5. ✅ 返回前端，显示新套餐

---

**需要帮助？** 查看完整文档：
- Stripe CLI: https://stripe.com/docs/stripe-cli
- Webhook 测试: https://stripe.com/docs/webhooks/test
