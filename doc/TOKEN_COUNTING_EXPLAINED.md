# Anthropic API Token 计数详解

## 官方文档来源

根据 [Anthropic Prompt Caching 官方文档](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)

## Token 字段定义

### 1. `input_tokens`
**定义**：未被缓存的输入 tokens（即 cache breakpoint 之后的部分）

**官方原文**：
> Number of input tokens which were **not** read from or used to create a cache (i.e., tokens after the last cache breakpoint).

### 2. `cache_creation_input_tokens`
**定义**：本次创建缓存时写入的 tokens 数量

**官方原文**：
> Number of tokens written to the cache when creating a new entry.

### 3. `cache_read_input_tokens`
**定义**：本次从缓存读取的 tokens 数量

**官方原文**：
> Number of tokens retrieved from the cache for this request.

## 关键公式

```
total_input_tokens = cache_read_input_tokens + cache_creation_input_tokens + input_tokens
```

**重要**：`input_tokens` 字段**不包含**缓存相关的 tokens，它只代表 cache breakpoint 之后的新输入。

## 具体例子（来自官方文档）

假设有一个 200,000 tokens 的缓存文档和 50 tokens 的用户问题：

```
cache_read_input_tokens: 100,000
cache_creation_input_tokens: 0
input_tokens: 50
──────────────────────────────────
总计: 100,050 tokens
```

## 实际项目中的验证

根据项目日志：

```
常规输入:         33 tokens       ← 这是 input_tokens（未被缓存的部分）
缓存创建:     34,613 tokens       ← cache_creation_input_tokens
缓存读取:    213,406 tokens       ← cache_read_input_tokens
────────────────────────────────────
总输入:      248,052 tokens       ← 33 + 34,613 + 213,406 ✅
输出:          2,858 tokens
────────────────────────────────────
总计:        250,910 tokens       ← 248,052 + 2,858 ✅
```

**验证**：33 + 34,613 + 213,406 = 248,052 ✅ 正确！

## 为什么总 tokens 是 25万但不超过 20万上下文限制？

这是 **Prompt Caching 的关键优势**：

### 计费 tokens vs 上下文占用

1. **计费 tokens = 250,910**（包含所有类型，用于成本计算）
   - 常规输入: 33 × $3.00/MTok
   - 缓存创建: 34,613 × $3.75/MTok（1.25× 价格）
   - 缓存读取: 213,406 × $0.30/MTok（节省 90%！）
   - 输出: 2,858 × $15.00/MTok

2. **上下文窗口占用**：根据 2025 更新，**缓存读取不计入 ITPM 限制**
   - 实际占用可能只包含：常规输入 + 缓存创建 + 输出
   - 这远低于 200K 限制

## 定价（< 200K tokens）

| Token 类型 | 价格（/MTok） | 说明 |
|-----------|-------------|------|
| 常规输入 | $3.00 | 基准价格 |
| 缓存创建 | $3.75 | 1.25× 基准（多 25%）|
| 缓存读取 | $0.30 | 0.1× 基准（节省 90%）|
| 输出 | $15.00 | 5× 基准 |

## 2025 年更新

根据官方公告：
- **缓存读取不再计入 ITPM (Input Tokens Per Minute) 限制**
- 自动读取最长的缓存前缀
- 缓存默认 TTL 为 5 分钟（每次使用刷新）
- 可选 1 小时 TTL

## 代码实现

### ✅ 正确的计算方式

```python
# 这是 Anthropic API 返回的值（每次迭代）
input_tokens = 33              # 常规输入（未缓存）
cache_creation = 34_613        # 缓存创建
cache_read = 213_406           # 缓存读取
output_tokens = 2_858          # 输出

# 计算总输入
total_input = input_tokens + cache_creation + cache_read  # = 248,052

# 计算总 tokens
total_tokens = total_input + output_tokens  # = 250,910

# 成本计算
regular_cost = input_tokens * 3.00 / 1_000_000
cache_creation_cost = cache_creation * 3.75 / 1_000_000
cache_read_cost = cache_read * 0.30 / 1_000_000
output_cost = output_tokens * 15.00 / 1_000_000

total_cost = regular_cost + cache_creation_cost + cache_read_cost + output_cost
```

### ❌ 常见错误

```python
# 错误 1: 认为 input_tokens 已包含缓存
total_input = input_tokens  # ❌ 缺少缓存 tokens

# 错误 2: 试图从 input_tokens 中减去缓存
regular_input = input_tokens - cache_creation - cache_read  # ❌ 会得到负数或 0

# 正确：input_tokens 本身就是未被缓存的部分，不需要减
regular_input = input_tokens  # ✅
```

## 总结

- ✅ `input_tokens` = 未被缓存的常规输入（cache breakpoint 之后）
- ✅ 总输入 = `input_tokens` + `cache_creation` + `cache_read`
- ✅ 25万 tokens 是正确的计费数字
- ✅ 不冲突 20万上下文限制（缓存读取不占用 ITPM）
- ✅ Prompt Caching 能节省高达 90% 成本

## 参考资料

- [Anthropic Prompt Caching Documentation](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)
- [Token-saving updates on the Anthropic API](https://www.anthropic.com/news/token-saving-updates)
- [Prompt caching with Claude](https://www.anthropic.com/news/prompt-caching)
