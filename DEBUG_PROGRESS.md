# 进度消息调试指南

## 问题：前端没有显示进度消息

### 快速排查清单

#### 1. 检查后端日志（最重要！）

启动后端后，触发本体构建，检查控制台是否有以下日志：

```bash
# 期望看到的日志：
[ConversationService] Set execution_context for 17 tools
📋 开始并行构建本体：共 6 个业务域，67 个表
🚀 开始构建 user_management（11 个表）
...
[SSE] Forwarding progress: 📋 开始并行构建本体：共 6 个业务域，67 个表
```

**如果没有看到这些日志**，说明问题在后端。

#### 2. 检查前端控制台（浏览器 DevTools）

打开浏览器开发者工具 (F12)，在 Console 中查找：

```javascript
// 期望看到的日志：
[ChatStore] SSE message received: progress
[ChatStore] Received chunk: progress {type: "progress", content: "..."}
[ChatStore] Adding/updating progress message: {...}
```

**如果没有看到这些日志**，说明前端没有收到 SSE 消息。

#### 3. 检查 SSE 连接状态

在浏览器 DevTools 的 Network 标签页：

1. 筛选 `EventStream` 类型
2. 找到 `/api/sse/chat/...` 请求
3. 点击查看响应内容，应该能看到实时流式数据

**如果看不到或连接断开**，说明 SSE 连接有问题。

---

## 常见问题与解决方案

### 问题 1: 后端没有发送 progress 消息

**症状**: 控制台没有 "📋 开始并行构建本体" 等日志

**可能原因**:
- 没有触发 `_build_all_domains_parallel` 方法
- `execution_context` 没有正确设置
- `message_queue` 为 None

**检查方法**:
```python
# 在 ontology_tools.py:989 添加临时日志
print(f"DEBUG: execution_context = {self._execution_context}")
print(f"DEBUG: message_queue = {self._execution_context.get('message_queue') if self._execution_context else None}")
```

**解决方案**:
- 确保使用的是 `OntologyBuilderTool._run()` 而不是直接调用 `_build_ontology()`
- 检查 `conversation.py:847-856` 是否正确设置了 `execution_context`

---

### 问题 2: 前端没有收到 SSE 消息

**症状**: 后端有日志，但前端控制台没有 `[ChatStore] SSE message received: progress`

**可能原因**:
- SSE 连接断开或未建立
- 前端 SSE 服务没有正确监听
- 消息在传输过程中丢失

**检查方法**:
1. 打开浏览器 DevTools → Network → EventStream
2. 确认有 SSE 连接且状态为 `pending`（持续连接）
3. 查看响应内容，应该能看到 `data: {"type": "progress", ...}`

**解决方案**:
- 刷新页面重新建立 SSE 连接
- 检查 `web-frontend/src/services/sse.ts` 的实现
- 确认 `sseService.onMessage()` 回调已注册

---

### 问题 3: 前端收到消息但没有渲染

**症状**: 前端控制台有 `[ChatStore] Adding/updating progress message`，但界面没有显示

**可能原因**:
- TypeScript 类型错误（已修复）
- Vue 组件没有正确处理 `isProgress` 条件
- CSS 样式问题导致不可见

**检查方法**:
1. 打开 Vue DevTools
2. 查看 `messages` 数组，确认有 `role: 'progress'` 的消息
3. 检查 DOM 树中是否有对应的进度消息元素

**解决方案**:
- 已修复 `ChatMessage` 接口，添加 `'progress'` 类型
- 已在 `MessageItem.vue` 添加 progress 渲染逻辑
- 重新编译前端：`cd web-frontend && npm run dev`

---

## 调试技巧

### 1. 添加临时日志

在关键位置添加 `console.log` 或 `logger.info`：

**后端**:
```python
# kode/tools/ontology_tools.py:993
logger.info(f"🔍 [DEBUG] Sending progress: {progress_msg}")
```

**前端**:
```typescript
// web-frontend/src/stores/chat.ts:907
console.log('🔍 [DEBUG] Progress message added to messages:', progressMessage)
```

### 2. 手动触发测试消息

在后端临时添加一个简单的测试工具：

```python
# test_send_progress.py
import asyncio
from kode.tools.base import KodeTool

class TestProgressTool(KodeTool):
    name = "TestProgress"
    description = "测试进度消息"

    async def _arun(self):
        for i in range(5):
            await self.send_progress(
                content=f"测试进度 {i+1}/5",
                stage="test",
                current=i+1,
                total=5
            )
            await asyncio.sleep(1)
        return "完成"
```

### 3. 使用浏览器 Network 监控

1. 打开 DevTools → Network
2. 勾选 "Preserve log"
3. 触发本体构建
4. 筛选 `sse` 查看所有 SSE 消息
5. 点击消息查看详细内容

---

## 最可能的原因

根据你的描述 "前端没有任何反应"，最可能的原因是：

### ❌ TypeScript 类型错误（已修复）

之前 `ChatMessage` 接口的 `role` 没有包含 `'progress'`，导致 TypeScript 编译错误。

**解决方案**: 已在 [web-frontend/src/stores/chat.ts](web-frontend/src/stores/chat.ts#L76) 添加 `'progress'` 类型。

**验证方法**:
```bash
cd web-frontend
npm run build  # 检查是否有编译错误
```

### 需要做的事情

1. **重新编译前端**（最重要！）:
   ```bash
   cd web-frontend
   # 停止当前的 dev 服务器 (Ctrl+C)
   npm run dev  # 重新启动，TypeScript 会重新编译
   ```

2. **刷新浏览器页面**（清除缓存）:
   - Windows/Linux: `Ctrl + Shift + R`
   - Mac: `Cmd + Shift + R`

3. **重新触发本体构建**:
   - 发送消息: "帮我构建 yanfa 数据库的本体"
   - 观察进度条是否显示

---

## 验证成功的标志

如果一切正常，你应该看到：

### 后端日志:
```
[ConversationService] Set execution_context for 17 tools
📋 开始并行构建本体：共 6 个业务域，67 个表
🚀 开始构建 user_management（11 个表）
[SSE] Forwarding progress: 📋 开始并行构建本体...
✅ user_management 完成（11 个表，AI耗时 5.23s，总耗时 5.45s）
🎉 本体构建完成！6 个域全部完成，总耗时 45.67s
```

### 前端控制台:
```
[ChatStore] SSE message received: progress
[ChatStore] Received chunk: progress {...}
[ChatStore] Adding/updating progress message: {...}
```

### 浏览器界面:
- 蓝紫色 (Indigo) 背景的进度卡片
- 带闪电图标的 Avatar
- 显示进度条和百分比
- "1 / 6" 等计数显示

---

## 如果还是不行

请提供以下信息：

1. **后端日志截图**（包含启动时的日志）
2. **前端控制台截图**（Console 和 Network 标签）
3. **浏览器版本**
4. **是否有 TypeScript/JavaScript 错误**

我会根据具体情况进一步诊断！
