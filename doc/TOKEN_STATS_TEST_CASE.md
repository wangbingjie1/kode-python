# Token 统计修复验证测试

## 测试场景

使用你提供的实际数据（第6次迭代）：

```javascript
input_tokens: 1
cache_creation_input_tokens: 34118
cache_read_input_tokens: 0
output_tokens: 1069
```

## 修复前的错误计算

```python
# ❌ 错误逻辑
total_input_tokens = 1  # 累加 input_tokens
regular_input_tokens = 1 - 34118 - 0 = -34117  # 负数！
total_cost = (-34117 * 3 + 34118 * 3.75 + 0 * 0.30 + 1069 * 15) / 1_000_000
           = (-102351 + 127942.5 + 0 + 16035) / 1_000_000
           = 41626.5 / 1_000_000
           = $0.0416265
```

**问题**：
- `regular_input_tokens` 为负数 `-34117`
- 成本计算公式虽然能得到正数，但概念完全错误
- 前端日志显示：`regular_input_tokens: -168980`（累加多次迭代后）

## 修复后的正确计算

```python
# ✅ 正确逻辑
regular_input_tokens = 1  # input_tokens 本身就是常规输入
true_total_input_tokens = 1 + 34118 + 0 = 34119
actual_tokens = 34119 + 1069 = 35188

# 成本计算
regular_input_cost = 1 * 3 / 1_000_000 = $0.000003
cache_creation_cost = 34118 * 3.75 / 1_000_000 = $0.1279425
cache_read_cost = 0 * 0.30 / 1_000_000 = $0
output_cost = 1069 * 15 / 1_000_000 = $0.016035

actual_cost = 0.000003 + 0.1279425 + 0 + 0.016035 = $0.1439805

# 无缓存成本对比
no_cache_input_cost = 34119 * 3 / 1_000_000 = $0.102357
no_cache_cost = 0.102357 + 0.016035 = $0.118392

# 缓存节省（这个会是负数，因为缓存创建比常规还贵）
cache_savings = 0.118392 - 0.1439805 = -$0.0255885
# 注意：缓存创建时成本会增加，读取时才节省
```

## 预期后端日志（修复后）

```
================================================================================
[SSE Usage Summary] Conversation xxx
================================================================================
📊 Token 统计:
  常规输入:          1 tokens × $3.00/MTok  = $0.000003
  缓存创建:     34,118 tokens × $3.75/MTok  = $0.127943
  缓存读取:          0 tokens × $0.30/MTok  = $0.000000
  输出生成:      1,069 tokens × $15.00/MTok = $0.016035
  ─────────────────────────────────────────────────────────────
  总输入:       34,119 tokens (常规 + 缓存创建 + 缓存读取)
  总输出:        1,069 tokens
  总计:         35,188 tokens

💰 成本分析:
  实际成本:   $0.143981
  无缓存成本: $0.118392
  节省:       $-0.025589 (-21.6%)

📦 用户配额扣除: 35,188 tokens (简化计费)
================================================================================
```

## 预期前端日志（修复后）

```javascript
[ChatStore] Final token stats received: {
  total_input_tokens: 34119,         // ✅ 正数
  total_output_tokens: 1069,
  total_tokens: 35188,
  cache_creation_tokens: 34118,
  cache_read_tokens: 0,
  regular_input_tokens: 1,           // ✅ 正数
  cost_breakdown: {
    regular_input_cost: 0.000003,
    cache_creation_cost: 0.1279425,
    cache_read_cost: 0,
    output_cost: 0.016035
  },
  total_cost: 0.1439805,             // ✅ 正数
  cache_savings: -0.0255885,         // 负数正常（缓存创建时）
  savings_percentage: -21.6,
  iteration_count: 6
}
```

## 验证步骤

### 1. 重启后端服务

```bash
python run.py
```

### 2. 重启前端服务

```bash
cd ../web-frontend
npm run dev
```

### 3. 发送测试消息

在前端发送任意消息，观察：
1. 浏览器控制台的日志
2. 后端控制台的 `[SSE Usage Summary]` 日志
3. 前端 UI 的 Token 统计卡片

### 4. 检查点

✅ **后端日志**：
- `regular_input_tokens` 应该是正数
- `总输入` 应该等于 `常规 + 缓存创建 + 缓存读取`
- `总计` 应该等于 `总输入 + 总输出`
- 所有成本应该是正数

✅ **前端日志**：
- 应该看到 `[ChatStore] Final token stats received: {...}`
- `total_input_tokens` 应该是正数
- `regular_input_tokens` 应该是正数
- `total_cost` 应该是正数

✅ **前端 UI**：
- "真实成本分析" 面板应该显示正常数值
- 各类 token 数量应该合理
- 成本应该是正数（美元和人民币）

## 常见问题

### Q: 为什么 `cache_savings` 是负数？

A: 在**缓存创建阶段**，成本会增加 25%（$3.75 vs $3.00），所以 savings 是负数。只有在**缓存读取阶段**，才能节省 90% 成本（$0.30 vs $3.00），savings 才会是正数。

### Q: 多次迭代后的累计统计？

A: 累计所有迭代后：
- 常规输入累计
- 缓存创建累计
- 缓存读取累计
- 输出累计

如果有多次迭代使用缓存读取（90% off），总体 savings 会变为正数。

### Q: 用户配额如何计费？

A: 简化计费策略：
```python
billable_tokens = true_total_input_tokens + total_output_tokens
```

包含所有 token（常规 + 缓存创建 + 缓存读取 + 输出），不区分缓存优惠。

## 参考链接

- Anthropic API 定价: https://www.anthropic.com/pricing
- Token 计算逻辑: `kode/web/api/sse.py:626-700`
- 前端处理逻辑: `web-frontend/src/stores/chat.ts:697-922`
