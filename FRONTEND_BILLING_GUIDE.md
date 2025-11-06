# 前端商业化模块使用指南

## 概述

前端已完成商业化订阅系统的界面实现，用户可以通过 Web 界面管理订阅、查看使用量并升级套餐。

## 功能列表

### 1. 订阅管理页面 (`/billing`)

访问路径：导航栏 → "订阅" 或直接访问 `/billing`

**功能包括：**
- 📊 **当前订阅状态**：显示套餐名称、有效期、续费状态
- 📈 **使用量统计**：Token、消息、对话数使用情况（带进度条）
- 💳 **套餐选择**：查看三个套餐的对比和价格
- ⬆️ **一键升级**：点击"立即升级"跳转到 Stripe 支付页面
- ❌ **取消订阅**：可选立即取消或计费周期结束后取消

### 2. 套餐展示组件 (`PricingPlans.vue`)

**设计特点：**
- 三栏卡片布局（免费版、专业版、企业版）
- "最受欢迎"标签（专业版）
- 当前套餐绿色高亮
- 悬停动画效果
- 响应式设计

**套餐信息：**
| 功能 | 免费版 | 专业版 | 企业版 |
|------|-------|-------|-------|
| 价格 | ¥0 | ¥99/月 | ¥499/月 |
| Token | 10万/月 | 200万/月 | 1000万/月 |
| 消息 | 50条/月 | 1000条/月 | 10000条/月 |
| 对话 | 3个 | 50个 | 500个 |
| 数据库 | - | 5个连接 | 50个连接 |
| 高级功能 | - | ✓ | ✓✓ |

### 3. 使用量显示组件 (`UsageQuota.vue`)

**显示内容：**
- Token 使用量（进度条）
- 消息数量（进度条）
- 当前套餐徽章
- 配额超限警告（红色提示）

**颜色警告系统：**
- 绿色：< 70% 使用
- 黄色：70% - 90% 使用
- 红色：> 90% 使用

### 4. Billing Store (Pinia)

**状态管理：**
```typescript
// 使用示例
import { useBillingStore } from '@/stores/billing'

const billingStore = useBillingStore()

// 获取数据
await billingStore.refreshAll()

// 升级套餐
await billingStore.upgradeToPlan(planId)

// 取消订阅
await billingStore.cancelSubscription(immediate)

// 访问状态
const currentPlan = billingStore.currentPlan
const usage = billingStore.usageSummary
const isQuotaExceeded = billingStore.isQuotaExceeded
```

## 页面预览

### 订阅管理页面结构

```
┌─────────────────────────────────────────┐
│  导航栏  [对话] [数据库] [订阅] [用户]   │
├─────────────────────────────────────────┤
│                                         │
│  订阅管理                                │
│                                         │
│  ┌─────────────────────────────────┐  │
│  │ 当前订阅                         │  │
│  │ 专业版 [激活]                    │  │
│  │ 有效期：2025-01-01 - 2025-02-01  │  │
│  │                     [取消订阅]   │  │
│  └─────────────────────────────────┘  │
│                                         │
│  ┌─────────────────────────────────┐  │
│  │ 使用量统计                       │  │
│  │ [Token] ████░░ 60万/200万       │  │
│  │ [消息]  ███░░░ 300/1000         │  │
│  │ [对话]  5/50                     │  │
│  └─────────────────────────────────┘  │
│                                         │
│  升级套餐                                │
│  ┌────┐  ┌────┐  ┌────┐             │
│  │免费│  │专业│  │企业│             │
│  │版  │  │版  │  │版  │             │
│  │¥0  │  │¥99 │  │¥499│             │
│  └────┘  └────┘  └────┘             │
└─────────────────────────────────────────┘
```

## 集成到主界面

### 在聊天界面显示使用量（可选）

在 `ChatView.vue` 中添加使用量组件：

```vue
<template>
  <div class="chat-view">
    <!-- 在侧边栏或顶部添加 -->
    <UsageQuota />

    <!-- 其他聊天界面内容 -->
  </div>
</template>

<script setup>
import UsageQuota from '@/components/UsageQuota.vue'
import { useBillingStore } from '@/stores/billing'
import { onMounted } from 'vue'

const billingStore = useBillingStore()

onMounted(async () => {
  // 加载使用量数据
  await billingStore.fetchUsageSummary()
})
</script>
```

## 支付流程

### Stripe Checkout 集成

1. **用户点击"立即升级"**
   - 前端调用 `/api/billing/stripe/checkout`
   - 传入套餐ID、成功/取消跳转URL

2. **后端创建 Checkout Session**
   - 返回 Stripe Checkout URL

3. **跳转到 Stripe 支付页面**
   - `window.location.href = checkoutUrl`

4. **支付完成后跳转**
   - 成功：`/billing/success`
   - 取消：`/billing`

5. **Webhook 更新订阅状态**
   - Stripe 回调后端 `/api/billing/stripe/webhook`
   - 后端自动更新订阅状态

## API 错误处理

### 配额超限（429 错误）

当用户配额用尽时，后端返回 `429 Too Many Requests`：

```typescript
// 在 SSE 或 API 调用中捕获
try {
  await sendMessage(content)
} catch (error) {
  if (error.response?.status === 429) {
    // 显示升级提示
    notification.error(
      '配额已用尽',
      '请升级套餐以继续使用',
      {
        action: () => router.push('/billing')
      }
    )
  }
}
```

### 订阅过期

```typescript
// 检查订阅状态
if (subscription.status !== 'active') {
  notification.warning(
    '订阅已过期',
    '请续费以继续使用高级功能'
  )
}
```

## 样式定制

### 主题色

商业化模块使用了以下色彩方案：

```css
/* 主色调 */
--primary-blue: #3b82f6;
--primary-blue-dark: #2563eb;

/* 成功色 */
--success-green: #10b981;

/* 警告色 */
--warning-yellow: #f59e0b;
--error-red: #ef4444;

/* 渐变 */
background: linear-gradient(135deg, #3b82f6, #2563eb);
```

### 自定义样式

在组件中覆盖默认样式：

```vue
<style scoped>
/* 修改卡片圆角 */
.plan-card {
  border-radius: 1.5rem; /* 默认是 1rem */
}

/* 修改按钮颜色 */
.plan-button {
  background: linear-gradient(135deg, #your-color, #your-color-dark);
}
</style>
```

## 启动和测试

### 1. 启动后端

```bash
python run.py
# 或
python -m kode.web.main
```

### 2. 运行数据库迁移

```bash
python scripts/migrate_billing.py
```

### 3. 启动前端

```bash
cd web-frontend
npm run dev
```

### 4. 访问订阅页面

打开浏览器访问：`http://localhost:3000/billing`

## 常见问题

### Q: 为什么看不到套餐？

A: 确保后端已运行数据库迁移脚本，创建了默认套餐。

### Q: 点击升级后没有跳转？

A: 检查：
1. 后端是否配置了 `STRIPE_SECRET_KEY`
2. 浏览器控制台是否有错误
3. 后端日志是否显示 Stripe API 调用失败

### Q: 使用量不更新？

A: 使用量在每次对话后自动更新，刷新页面可以看到最新数据。

### Q: 如何自定义套餐？

A: 通过后端 API 创建/更新套餐：
```bash
curl -X POST http://localhost:8001/api/billing/plans \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "custom",
    "display_name": "定制版",
    "price": 199,
    "token_quota": 5000000,
    ...
  }'
```

## 下一步优化

- [ ] 在聊天界面集成使用量提示
- [ ] 添加支付成功后的庆祝动画
- [ ] 实现套餐对比表格视图
- [ ] 添加历史账单查看功能
- [ ] 支持团队席位管理
- [ ] 添加优惠码输入框
- [ ] 实现套餐升级/降级预览

## 相关文档

- [后端商业化模块文档](BILLING_MODULE_README.md)
- [API 文档](http://localhost:8001/docs) - FastAPI 自动生成
- [Stripe 文档](https://stripe.com/docs/api)
