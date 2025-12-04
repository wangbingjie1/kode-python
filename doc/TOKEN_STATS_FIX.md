# Token 统计修复文档

## 问题描述

前端显示的 token 统计数据不准确，出现负数和异常值。

## 根本原因

### 0. **最严重问题：对 Anthropic API 返回的 token 字段理解错误** ⚠️

**错误假设**（修复前）：
```python
# ❌ 错误：以为 input_tokens 包含所有输入
total_input_tokens = regular + cache_creation + cache_read
regular_input_tokens = total_input_tokens - cache_creation - cache_read  # 计算出负数！
```

**实际情况**（Anthropic API 文档）：
```python
# ✅ 正确：input_tokens 只是常规输入，不包含缓存
usage = {
    "input_tokens": 1,          # 常规输入（非缓存）
    "output_tokens": 1069,      # 输出
    "cache_creation_input_tokens": 34118,  # 缓存创建
    "cache_read_input_tokens": 0          # 缓存读取
}

# 真实总输入 = 1 + 34118 + 0 = 34119
```

这导致了：
- `regular_input_tokens` 计算为负数（1 - 34118 - 0 = -34117）
- `total_cost` 为负数
- 前端显示完全错误的数据

### 1. 缺少 `final_token_stats` 事件处理

**后端发送**（`kode/web/api/sse.py:732-765`）：
```python
final_token_stats = {
    "type": "final_token_stats",
    "metadata": {
        "total_input_tokens": ...,      # 完整输入 token 数
        "total_output_tokens": ...,     # 完整输出 token 数
        "cache_creation_tokens": ...,   # 缓存创建 token 数
        "cache_read_tokens": ...,       # 缓存读取 token 数
        "cost_breakdown": {...},        # 详细成本分析
        "iteration_count": ...          # 迭代次数
    }
}
```

**前端缺失**：
- `web-frontend/src/stores/chat.ts` 的 `handleStreamingChunk()` 函数中没有处理此事件
- 导致前端只能依赖增量累加的 `token_usage` 事件，无法获得后端计算的准确总计

### 2. `token_usage` 增量累加逻辑错误

**问题代码**（修复前）：
```typescript
case 'token_usage': {
  // 累加到会话总计
  conversationTokenUsage.value.total_input_tokens += usage.input_tokens
  conversationTokenUsage.value.total_output_tokens += usage.output_tokens
  conversationTokenUsage.value.total_tokens += usage.total_tokens  // ❌ 重复累加
  conversationTokenUsage.value.iterations = usage.iteration       // ❌ 应该取最大值
}
```

**问题分析**：
- `total_tokens` 已经等于 `input_tokens + output_tokens`，再累加会重复计算
- `iterations` 直接赋值会丢失历史最大值

## 修复方案

### 修复 0: 修正后端 token 计算逻辑（最关键）⚠️

**位置**: `kode/web/api/sse.py`

**修复前**（第626-656行）：
```python
# ❌ 错误假设
actual_tokens = total_input_tokens + total_output_tokens
regular_input_tokens = total_input_tokens - total_cache_creation_tokens - total_cache_read_tokens  # 负数！
```

**修复后**：
```python
# ✅ 正确理解 Anthropic API
regular_input_tokens = total_input_tokens  # input_tokens 本身就是常规输入
true_total_input_tokens = total_input_tokens + total_cache_creation_tokens + total_cache_read_tokens
actual_tokens = true_total_input_tokens + total_output_tokens

# 成本计算（正确）
regular_input_cost = regular_input_tokens * 3 / 1_000_000
cache_creation_cost = total_cache_creation_tokens * 3.75 / 1_000_000
cache_read_cost = total_cache_read_tokens * 0.30 / 1_000_000
output_cost = total_output_tokens * 15 / 1_000_000
```

**影响范围**：
1. `sse.py:626-648` - 计费逻辑
2. `sse.py:732-775` - `final_token_stats` 事件
3. 后端日志输出

### 修复 1: 添加 `final_token_stats` 事件处理

**位置**: `web-frontend/src/stores/chat.ts:904-922`

```typescript
case 'final_token_stats': {
  // ✅ 处理最终的 token 统计和成本分析
  const finalStats = chunk.metadata
  console.log('[ChatStore] Final token stats received:', finalStats)

  // 更新会话级别的 token 统计（使用后端计算的准确数据）
  conversationTokenUsage.value = {
    total_input_tokens: finalStats.total_input_tokens || 0,
    total_output_tokens: finalStats.total_output_tokens || 0,
    total_tokens: finalStats.total_tokens || 0,
    cache_creation_input_tokens: finalStats.cache_creation_tokens || 0,
    cache_read_input_tokens: finalStats.cache_read_tokens || 0,
    iterations: finalStats.iteration_count || 0,
    tool_calls_count: conversationTokenUsage.value.tool_calls_count
  }

  console.log('[ChatStore] Updated conversation token usage:', conversationTokenUsage.value)
  break
}
```

### 修复 2: 修正 `token_usage` 增量累加逻辑

**位置**: `web-frontend/src/stores/chat.ts:697-726`

```typescript
case 'token_usage': {
  // 处理每次 API 调用的 token 统计（增量累加，最终会被 final_token_stats 覆盖）
  const usage: TokenUsage = {
    input_tokens: chunk.metadata?.input_tokens || 0,
    output_tokens: chunk.metadata?.output_tokens || 0,
    total_tokens: chunk.metadata?.total_tokens || 0,
    cache_creation_input_tokens: chunk.metadata?.cache_creation_input_tokens,
    cache_read_input_tokens: chunk.metadata?.cache_read_input_tokens,
    iteration: chunk.metadata?.iteration
  }

  // 累加到会话总计
  conversationTokenUsage.value.total_input_tokens += usage.input_tokens
  conversationTokenUsage.value.total_output_tokens += usage.output_tokens
  // ✅ total_tokens 不需要累加，直接计算（避免重复）
  conversationTokenUsage.value.total_tokens =
    conversationTokenUsage.value.total_input_tokens +
    conversationTokenUsage.value.total_output_tokens
  conversationTokenUsage.value.cache_creation_input_tokens += usage.cache_creation_input_tokens || 0
  conversationTokenUsage.value.cache_read_input_tokens += usage.cache_read_input_tokens || 0
  // ✅ iterations 使用最大值（而非赋值）
  conversationTokenUsage.value.iterations = Math.max(
    conversationTokenUsage.value.iterations || 0,
    usage.iteration || 0
  )

  console.log('[ChatStore] Token usage:', usage)
  console.log('[ChatStore] Conversation total:', conversationTokenUsage.value)
  break
}
```

## 数据流向

```
后端 SSE 流
    ↓
1. [token_usage 事件] → 增量统计（实时显示，用户体验好）
    ↓
2. [final_token_stats 事件] → 准确总计（覆盖增量结果）
    ↓
前端 conversationTokenUsage → TokenUsageCard/TokenCostCard 组件 → 显示统计
```

## 验证方法

### 1. 控制台日志验证

发送消息后，在浏览器控制台查看：
```
[ChatStore] Token usage: {...}           # 每次迭代的增量
[ChatStore] Conversation total: {...}    # 累计统计
[ChatStore] Final token stats received: {...}  # ✅ 最终准确统计
[ChatStore] Updated conversation token usage: {...}
```

### 2. 对比后端日志

后端日志（`kode/web/api/sse.py`）：
```
[SSE Token] Iteration 1: input=..., output=..., cache_creation=..., cache_read=...
[SSE Usage Summary] Conversation xxx
  常规输入:   xxx tokens × $3.00/MTok  = $...
  缓存创建:   xxx tokens × $3.75/MTok  = $...
  缓存读取:   xxx tokens × $0.30/MTok  = $...
  输出生成:   xxx tokens × $15.00/MTok = $...
  总计:       xxx tokens
```

前端应该显示相同的 token 数值。

### 3. UI 验证

打开 "真实成本分析" 面板（`RealTokenCostCard.vue`）：
- API 调用次数应该等于迭代次数
- 总 Tokens 应该等于后端日志的总计
- 成本计算应该精确到小数点后 6 位

## 预期效果

修复后，前端显示的 token 统计应该：
1. ✅ 与后端日志完全一致
2. ✅ 实时显示增量统计（用户体验好）
3. ✅ 最终准确统计（数据准确）
4. ✅ 包含完整的缓存优化信息

## 相关文件

- **后端**: `kode/web/api/sse.py` (SSE 事件生成器)
- **前端**: `web-frontend/src/stores/chat.ts` (事件处理逻辑)
- **组件**:
  - `web-frontend/src/components/TokenUsageCard.vue` (用户统计卡片)
  - `web-frontend/src/components/TokenCostCard.vue` (开发者成本卡片)
  - `web-frontend/src/components/RealTokenCostCard.vue` (实时成本追踪)

## 修复时间

2025-12-04
