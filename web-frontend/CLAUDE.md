# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

Kode Web Frontend 是一个基于 Vue 3 + TypeScript + Vite 的现代化 Web 应用，为 Kode AI 编码助手提供前端界面。该应用采用 SSE (Server-Sent Events) 实现实时流式通信，集成了认证、计费、数据库管理等功能模块。

## 开发命令

### 安装依赖
```bash
npm install
```

### 开发环境
```bash
npm run dev        # 启动开发服务器 (http://localhost:3000)
```

### 生产构建
```bash
npm run build      # 类型检查 + 构建
npm run preview    # 预览生产构建
```

### 代码质量
```bash
npm run lint       # ESLint 检查和自动修复
```

## 核心架构

### 技术栈
- **框架**: Vue 3 (Composition API)
- **语言**: TypeScript
- **构建工具**: Vite 5
- **状态管理**: Pinia
- **路由**: Vue Router 4
- **HTTP 客户端**: Axios
- **样式**: Tailwind CSS 3 + PostCSS
- **国际化**: Vue I18n
- **Markdown 渲染**: markdown-it + highlight.js
- **代码编辑器**: Monaco Editor

### 项目结构

```
src/
├── components/          # 可复用组件
│   ├── MessageItem.vue         # 消息项（支持 Markdown 渲染）
│   ├── ToolCallItem.vue        # 工具调用显示组件
│   ├── ToolCallIndicator.vue   # 工具调用状态指示器
│   ├── NotificationContainer.vue # 通知容器
│   ├── NotificationToast.vue    # Toast 通知
│   ├── ChatInput.vue           # 聊天输入框
│   ├── ContextPanel.vue        # 上下文面板
│   ├── AppSidebar.vue          # 应用侧边栏
│   ├── OntologyViewer.vue      # 本体查看器
│   ├── QueryTester.vue         # SQL 查询测试器
│   ├── QueryResultTable.vue    # 查询结果表格
│   ├── PricingPlans.vue        # 套餐定价
│   ├── UsageQuota.vue          # 使用配额显示
│   └── LanguageSwitcher.vue    # 语言切换器
├── views/              # 页面视图
│   ├── ChatView.vue            # 主聊天界面
│   ├── LoginView.vue           # 登录页
│   ├── ProfileView.vue         # 用户资料页
│   ├── BillingView.vue         # 计费/订阅页
│   └── DatabaseView.vue        # 数据库管理页
├── stores/             # Pinia 状态管理
│   ├── chat.ts                 # 聊天状态（消息、SSE 连接）
│   ├── auth.ts                 # 认证状态（登录、Token 管理）
│   ├── billing.ts              # 计费状态（订阅、配额）
│   └── locale.ts               # 国际化状态
├── services/           # 服务层
│   ├── api.ts                  # REST API 客户端（Axios）
│   ├── sse.ts                  # SSE 服务（流式通信）
│   └── websocket.ts            # WebSocket 服务（已废弃，保留兼容）
├── composables/        # Vue Composables
│   └── useNotification.ts      # 全局通知系统
├── router/             # 路由配置
│   └── index.ts                # 路由定义和路由守卫
├── i18n/               # 国际化配置
│   └── index.ts                # Vue I18n 配置（中英文）
├── config/             # 配置常量
│   └── constants.ts            # 全局常量（API、SSE、UI 配置）
└── assets/             # 静态资源
    └── main.css                # Tailwind CSS 入口
```

## 核心设计模式

### 1. SSE 流式通信架构

应用使用 SSE (Server-Sent Events) 实现实时流式响应，取代了传统的 WebSocket。

**SSE 服务核心流程** (services/sse.ts):
1. 调用 `connect(conversationId)` 设置会话 ID（不立即建立连接）
2. 调用 `sendMessage(content)` 时建立 SSE 连接并发送消息
3. 服务器通过 SSE 流式返回多种类型的事件
4. 收到 `done` 事件后自动断开连接（单次请求-响应模式）
5. 下次发送消息时重新建立连接

**SSE 消息类型** (在 ChatStore 中处理):
- `thinking`: AI 思考过程（内部推理，可选显示）
- `chunk`: 实际 LLM 输出内容（流式追加）
- `text_complete`: 文本部分完成（在工具调用前）
- `tool_call`: 工具调用开始/执行中（显示工具名称和参数）
- `tool_result`: 工具执行结果/错误
- `complete`: 消息完成
- `error`: 错误信息
- `done`: 流结束信号（断开 SSE）

**认证方式**:
- SSE 不支持自定义 HTTP 头
- Token 通过 URL 参数传递: `/api/sse/chat/{id}/stream?task={content}&token={token}`

### 2. Pinia 状态管理模式

**Chat Store** (stores/chat.ts):
- 管理消息列表和流式消息状态
- SSE 事件处理器集中在 `handleStreamingChunk()`
- 工具调用消息的创建和更新逻辑：
  - `tool_call` 事件：创建或更新工具消息（显示执行状态）
  - `tool_result` 事件：更新工具消息（添加结果或错误）
  - 通过 `findLatestToolMessage()` 避免重复创建工具消息
- 消息类型：
  - `user`: 用户消息
  - `assistant`: AI 响应（含 `isStreaming` 标记）
  - `tool`: 工具调用（含 `toolCall` 元数据）
  - `system`: 系统消息（错误等）

**Auth Store** (stores/auth.ts):
- JWT Token 管理（access_token + refresh_token）
- Token 存储在 localStorage
- 自动 Token 刷新机制（在 API 拦截器中）
- 支持用户名密码登录和 Google OAuth

**Billing Store** (stores/billing.ts):
- 订阅状态和套餐管理
- 配额使用情况跟踪
- Stripe 支付集成

### 3. API 客户端设计 (services/api.ts)

**请求拦截器**:
- 自动添加 `Authorization: Bearer {token}` 头
- 自动添加 `Accept-Language: {locale}` 头（国际化）

**响应拦截器**:
- 401 错误自动触发 Token 刷新
- 刷新成功后自动重试原请求
- 刷新失败后跳转登录页
- 使用 `_retry` 标记避免无限重试

**API 函数分类**:
- 聊天相关: `createConversation()`, `getConversationMessages()`, etc.
- 数据库相关: `createDatabaseConnection()`, `getDatabaseSchema()`, etc.
- 本体相关: `listOntologies()`, `searchOntology()`, etc.
- 计费相关: `listPlans()`, `createSubscription()`, `createStripeCheckout()`, etc.

### 4. 路由守卫 (router/index.ts)

**认证守卫逻辑**:
1. 所有路由默认需要认证（`meta.requiresAuth !== false`）
2. 未登录用户重定向到 `/login?redirect={原路径}`
3. 已登录用户访问 `/login` 重定向到首页
4. 登录成功后根据 `redirect` 参数跳转

**路由结构**:
- `/login` - 登录页（公开）
- `/` → `/chat` - 主聊天页
- `/chat/:conversationId` - 特定会话
- `/database` - 数据库管理
- `/billing` - 计费/订阅管理
- `/profile` - 用户资料

### 5. 通知系统 (composables/useNotification.ts)

**全局单例模式**:
```typescript
import { notification } from '@/composables/useNotification'

notification.success('标题', '消息内容')
notification.error('错误', '详细信息', 5000) // 自定义持续时间
notification.info('提示', '信息')
notification.warning('警告', '注意事项')
```

**特性**:
- 自动管理通知列表
- 支持自定义持续时间
- Toast 动画（Tailwind CSS transitions）
- 显示在 `NotificationContainer.vue` 中

## 关键实现细节

### Markdown 渲染 (MessageItem.vue)

- 使用 `markdown-it` + `highlight.js` 渲染消息
- 代码块自动语法高亮
- 支持 Tailwind Typography 样式
- 安全的 HTML 渲染（XSS 防护）

### 工具调用显示 (ToolCallItem.vue)

- 显示工具名称、参数、结果
- 状态指示器：`started`, `executing`, `completed`, `error`
- 可展开/折叠详细参数和结果
- JSON 格式化显示

### 数据库管理 (DatabaseView.vue)

- 连接池管理（增删改查连接配置）
- 连接测试功能
- Schema 提取（表结构、列信息、外键、索引）
- 本体构建和查看
- SQL 查询测试器（带结果表格）

### 计费集成 (BillingView.vue)

- 套餐展示（免费/专业/企业）
- Stripe Checkout 集成
- 配额使用可视化（进度条）
- 订阅状态管理（激活/过期/试用）

## 开发规范

### 代码风格

1. **文件读写前必须先 Read**
   - 修改现有文件前必须使用 Read 工具查看内容
   - 新建文件需确认目录结构和命名规范

2. **常量集中管理**
   - 所有配置常量放在 `src/config/constants.ts`
   - 不要在组件中硬编码配置值

3. **类型安全**
   - 所有 API 函数必须定义 TypeScript 类型
   - 使用 `interface` 定义数据结构
   - 避免使用 `any`，优先使用 `unknown` 或具体类型

4. **Composables 使用**
   - 可复用逻辑提取为 Composables（`use*` 命名）
   - 全局功能使用单例模式（如 `notification`）

5. **组件拆分原则**
   - 单一职责：一个组件只负责一个功能
   - 可复用性：通用组件放在 `components/`
   - Props 验证：使用 TypeScript 定义 Props 类型

### SSE 调试

1. **浏览器 DevTools**
   - Network 标签查看 `eventsource` 类型请求
   - EventStream 面板查看实时消息

2. **Console 日志**
   - Chat Store 中有详细的 `console.log` 输出
   - 搜索 `[ChatStore]` 前缀定位相关日志

3. **常见问题**
   - Token 认证失败：检查 localStorage 中的 `access_token`
   - 连接断开：检查后端 SSE 端点是否正确返回 `text/event-stream`
   - 消息重复：检查是否多次调用 `sendMessage()`

### API 代理配置

开发环境中，Vite 代理 `/api` 请求到后端：

```typescript
// vite.config.ts
proxy: {
  '/api': {
    target: 'http://localhost:8001',  // 后端地址
    changeOrigin: true,
    rewrite: (path) => path  // 不重写路径
  }
}
```

生产环境需配置 Nginx 或其他反向代理。

### 国际化

- 语言文件在 `src/i18n/` 目录
- 支持中文（zh-CN）和英文（en-US）
- 使用 `$t('key')` 获取翻译文本
- locale 存储在 localStorage

### 样式系统

- **Tailwind CSS** 为主要样式方案
- 避免大量内联样式（超过 3-4 个类时考虑提取）
- 全局样式在 `src/assets/main.css`
- 自定义颜色定义在 `tailwind.config.js`

## 后端集成

### 后端服务启动

前端依赖后端 API，启动前确保后端运行：

```bash
# 在项目根目录（kode-python/）
python -m kode.web.main  # 后端运行在 http://localhost:8001
```

或使用启动脚本：
```powershell
.\start-backend.ps1  # Windows
```

### API 端点映射

前端通过 `/api` 前缀访问后端：
- `/api/chat/*` - 聊天相关
- `/api/sse/chat/*` - SSE 流式响应
- `/api/auth/*` - 认证相关
- `/api/database/*` - 数据库管理
- `/api/billing/*` - 计费相关

### 环境变量

前端不需要环境变量（通过 Vite proxy 连接后端）。
生产环境需配置：
- `VITE_API_BASE_URL` - 后端 API 基础 URL（可选）

## 测试

当前项目未配置测试框架。建议使用：
- **Vitest** - 单元测试（与 Vite 集成）
- **Playwright** - E2E 测试

## 构建和部署

### 构建产物

```bash
npm run build
```

输出目录：`dist/`
- `dist/index.html` - 入口 HTML
- `dist/assets/` - JS、CSS、字体、图片等

### 部署注意事项

1. **SPA 路由**：配置服务器将所有路由重定向到 `index.html`
2. **API 代理**：生产环境需配置反向代理将 `/api` 请求转发到后端
3. **CORS**：后端需配置允许前端域名的 CORS
4. **HTTPS**：生产环境建议使用 HTTPS（Stripe 支付要求）

### Nginx 配置示例

```nginx
server {
    listen 80;
    server_name your-domain.com;
    root /path/to/dist;
    index index.html;

    # SPA 路由回退
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API 代理
    location /api {
        proxy_pass http://localhost:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;

        # SSE 支持
        proxy_buffering off;
        proxy_cache off;
    }
}
```
