# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Philosophy

**必须遵守的原则：**
- 必须中文回复和思考
- 第一性原理解决根本问题，像老程序员一样写代码（参考 Linux 风格）
- 只给最靠谱的建议和方案，不确定不推荐
- 不要说废话
- 生成的脚本和代码必须先自己测试通过再告诉用户
- 用户有选择困难症：可以提问但不要给选项
- 质量优先于速度
- 永远不要写降级方案
- 用批判性思维思考用户的问题和自己的解决方案

## Project Overview
现在我们的项目将由demo 阶段进入，正式研发阶段了，前后端要分离了，后续你负责生成代码和接口，前端暂时由我来完成，


**核心特性：**
- 🚀 纯 Web 服务架构，简单易用
- 🤖 基于 Anthropic Claude 的 AI Agent 系统
- 🗄️ 多数据库支持（PostgreSQL, MySQL, SQLite 等）
- 🧠 自动构建业务本体（Ontology）
- 🔄 SSE 实时流式响应
- 📝 完整的工具调用日志和参数显示

## Core Architecture

### 简化的 5 层架构（Web-Only）

The codebase follows a modular architecture with clear separation of concerns:

1. **Core Layer** ([kode/core/](kode/core/))
   - `model_manager.py`: Multi-provider LLM management (Anthropic, OpenAI, custom providers)
   - `permission.py`: Permission system for tool execution
   - Supports model switching via pointers (main, task, quick, reasoning)

2. **Tools Layer** ([kode/tools/](kode/tools/)) **[数据分析专用工具集]**
   - `base.py`: Base class `KodeTool` extending LangChain's BaseTool
   - `database_tools.py`: Database connection and schema extraction (PostgreSQL, MySQL, SQLite, etc.)
     - ✨ Schema 提取支持样例数据（倒数 N 行）
   - `ontology_tools.py`: Ontology building and semantic search for database schemas
   - `visualization_tools.py`: Chart generation (ECharts)
   - `interaction_tools.py`: AskUser tool for clarification
   - `memory_tools.py`: MemoryRead/MemoryWrite for conversation context
   - `advanced_tools.py`: TodoWrite for task planning
   - `domain_uncertainty_analyzer.py`: Domain-level uncertainty analysis
   - `uncertainty_qa_tool.py`: Uncertainty Q&A management
   - **移除**: FileRead, FileWrite, FileEdit, Bash, Grep, Glob（数据分析不需要，节省 ~30% tool token）
   - All tools inherit from KodeTool with permission management

3. **Agents Layer** ([kode/agents/](kode/agents/))
   - `base.py`: AgentConfig (loaded from markdown) and KodeAgent classes
   - `loader.py`: 5-tier priority agent loading system:
     1. Built-in agents (code-embedded)
     2. `~/.claude/agents/` (Claude Code compatibility)
     3. `~/.kode/agents/` (Kode user directory)
     4. `./.claude/agents/` (Claude Code project directory)
     5. `./.kode/agents/` (Kode project directory)
   - Agents defined in markdown with YAML frontmatter (see [examples/agents/](examples/agents/))

4. **Context Layer** ([kode/context/](kode/context/))
   - `manager.py`: Conversation history, file caching, project structure tracking
   - Token limit management and context trimming

5. **Services Layer** ([kode/services/](kode/services/))
   - `conversation.py`: Async conversation service with streaming support
   - `database_manager.py`: Database connection pool management and multi-database support
   - Provides business logic for web API

6. **Web Layer** ([kode/web/](kode/web/)) **[主入口]**
   - `main.py`: FastAPI application entry point (port 8001)
   - `api/`: REST API endpoints
     - `chat.py`: Conversation and message endpoints
     - `project.py`: Project management endpoints
     - `database.py`: Database connection management endpoints
     - `auth.py`: OAuth authentication (Google login)
     - `billing.py`: Stripe billing and subscription management
     - `sse.py`: Server-Sent Events streaming endpoints
   - `middleware/`: Middleware components
     - `quota_check.py`: Token/message quota enforcement
     - `locale.py`: i18n locale detection
   - Database: SQLite (default) with SQLAlchemy ORM + Alembic migrations
   - Models: User, Project, Conversation, Message, DatabaseConnection, Plan, Subscription, Usage

**Frontend Layer** (位于 `./web-frontend/`, 同级目录)
   - Vue 3 + TypeScript + Vite
   - `src/components/`: Reusable UI components
     - `NotificationContainer.vue`: Toast notification system
     - `MessageItem.vue`: Chat message display with markdown rendering
   - `src/views/`: Page views
     - `ChatView.vue`: Main chat interface
   - `src/stores/`: Pinia state management
     - `chat.ts`: Chat state, SSE integration, message handling
   - `src/services/`:
     - `api.ts`: REST API client (Axios)
     - `sse.ts`: SSE (Server-Sent Events) service with auto-reconnect
   - `src/composables/`: Vue composables
     - `useNotification.ts`: Global notification system
   - `src/config/`: Configuration constants

### Configuration System

Hierarchical configuration with 4-tier priority ([kode/utils/config.py](kode/utils/config.py)):

1. Environment variables (highest priority)
2. Project config (`./.kode.json`)
3. User config (`~/.kode.json`)
4. Default values (lowest priority)

Configuration includes:
- Model definitions and pointers
- API keys (supports `ANTHROPIC_API_KEY`, `OPENAI_API_KEY` env vars)
- Execution parameters (temperature, maxTokens, verbose)

### Web API Architecture

**REST Endpoints:**

*Core:*
- `GET /health` - Health check (no auth)
- `GET /api/config` - Get current configuration

*Chat:*
- `POST /api/chat/conversations` - Create conversation
- `GET /api/chat/conversations/{id}` - Get conversation details
- `GET /api/chat/conversations/{id}/messages` - Get message history
- `DELETE /api/chat/conversations/{id}` - Delete conversation

*Database Management:*
- `POST /api/database/connections` - Create database connection
- `GET /api/database/connections` - List all connections
- `DELETE /api/database/connections/{id}` - Delete connection

*Authentication:*
- `GET /api/auth/google` - Google OAuth login
- `GET /api/auth/google/callback` - OAuth callback

*Billing (Stripe):*
- `GET /api/billing/plans` - List subscription plans
- `POST /api/billing/checkout` - Create Stripe checkout session
- `POST /api/billing/webhook` - Stripe webhook endpoint

**SSE (Server-Sent Events):**
- `GET /api/sse/chat/{conversation_id}/stream?task=xxx` - Real-time streaming chat via SSE
- `POST /api/sse/chat/{conversation_id}/message` - POST version for sending messages
- Message types: `thinking`, `chunk`, `complete`, `error`, `tool_call`, `done`
- Server streams: `data: {"type": "chunk", "content": "...", "metadata": {}}`
- Uses text/event-stream with automatic reconnection support

**Database Models:**
- `User`: User accounts with OAuth support (Google)
- `Project`: Project grouping for conversations
- `Conversation`: Chat sessions with title and timestamps
- `Message`: Individual messages (role: user/assistant, content, metadata)
- `DatabaseConnection`: Persisted database connections (PostgreSQL, MySQL, etc.)
- `Plan`: Subscription plans (Free, Pro, Enterprise) with quotas
- `Subscription`: User subscriptions linked to Stripe
- `Usage`: Token and message usage tracking for billing

### Agent Definition Format

Agents are markdown files with YAML frontmatter:

```markdown
---
name: agent-name
description: "When to use this agent"
tools: ["FileRead", "Bash"]  # or "*" for all tools
model: claude-sonnet-4-5  # optional, defaults to main model
max_iterations: 15
---

System prompt content here...
```

## Development Commands

### Setup

```bash
# Install dependencies with Poetry
poetry install
```

### Running Kode (简化启动)

**方式一：使用启动脚本（推荐）**

```bash
# 后端服务 (自动清理端口、启动在 http://localhost:8001)
python run.py

# 前端服务 (在另一个终端运行)
cd web-frontend
npm run dev
```

**方式二：手动启动**

```bash
# 后端 (port 8001)
python -m kode.web.main

# 前端 (port 3000)
cd web-frontend
npm run dev
```

**run.py 启动脚本特性：**
- ✓ 自动清理占用 8001 端口的旧进程 (Windows)
- ✓ 多进程兼容 (Windows multiprocessing.freeze_support)
- ✓ 简化配置，直接启动

### Configuration Management

**配置文件位置：**
- 项目配置：`./.kode.json` (API keys, model settings)
- 用户配置：`~/.kode.json` (用户级默认配置)
- 环境变量：`.env` (OAuth, Stripe, database credentials)

**必需的环境变量** (`.env`):
```bash
# AI Model API Keys
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...  # Optional

# OAuth (Google Login)
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=http://localhost:8001/api/auth/google/callback

# Stripe Billing
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Security
SECRET_KEY=your-secret-key-here  # For JWT tokens

# Database (optional, defaults to SQLite)
DATABASE_URL=sqlite+aiosqlite:///./kode.db
```

参考 `.env.example` 获取完整模板。

### Database Migrations (Alembic)

```bash
# 创建新的迁移文件
alembic revision --autogenerate -m "描述变更内容"

# 应用迁移到数据库
alembic upgrade head

# 回滚到上一个版本
alembic downgrade -1

# 查看当前版本
alembic current

# 查看迁移历史
alembic history
```

**注意**: 数据库 schema 变更后必须生成迁移文件。

### Testing

```bash
# Run pytest tests
poetry run pytest

# Run quick component test
python test_run.py

# Run real API test (requires API key)
python test_real_api.py

# Test database connections
pytest tests/test_database_tools.py -v
```

### Code Quality

```bash
# Format code with Black
poetry run black kode/ tests/

# Lint with Ruff
poetry run ruff check kode/ tests/

# Type check with mypy
poetry run mypy kode/
```

Configuration in [pyproject.toml](pyproject.toml):
- Black: line-length 100, Python 3.10+
- Ruff: E, F, I, N, W rules, ignoring E501
- Mypy: strict typing enabled

## Key Implementation Patterns

### Tool Creation

Extend `KodeTool` base class:

```python
from kode.tools.base import KodeTool
from pydantic import BaseModel, Field

class MyToolInput(BaseModel):
    param: str = Field(description="Parameter description")

class MyTool(KodeTool):
    name: str = "MyTool"
    description: str = "Tool description"
    args_schema: Type[BaseModel] = MyToolInput
    requires_permission: bool = True

    def _run(self, param: str) -> str:
        # Implementation
        return result
```

### Agent Creation

1. Create markdown file in one of the agent directories
2. Use YAML frontmatter for configuration
3. Write system prompt as markdown content
4. Agent auto-discovered by loader

### Model Switching

Models are accessed via pointers for flexibility:

```python
# In code
model = model_manager.get_model("main")  # Uses main pointer
model = model_manager.get_model("task")  # Uses task pointer

# Pointers can be reconfigured in .kode.json without code changes
```

### Frontend Development Patterns

**SSE Communication:**
```typescript
// services/sse.ts
// Handles streaming responses with EventSource API
sseService.connect(conversationId)
sseService.sendMessage(content) // Creates SSE connection and streams response
sseService.onMessage((chunk) => handleStreamingChunk(chunk))
```

**State Management (Pinia):**
```typescript
// stores/chat.ts
const chatStore = useChatStore()
await chatStore.connectToConversation(conversationId)
await chatStore.sendMessage(content)
```

**Notification System:**
```typescript
// composables/useNotification.ts
import { notification } from '@/composables/useNotification'
notification.success('Title', 'Message')
notification.error('Error', 'Details', 5000) // 5s duration
```

**Important Frontend Notes:**
- Use `Read` tool before `Edit` or `Write` for Vue/TS files
- All constants should go in `src/config/constants.ts`
- SSE (Server-Sent Events) used for real-time streaming (replaces WebSocket)
- EventSource API provides automatic reconnection
- Vite proxy forwards `/api` to backend (port 8000)

## Key Architecture Decisions

### Single Agent System (重要变更)

项目采用 **单 Agent 架构**，移除了原有的多 Agent 加载系统：

- **唯一 Agent**: `data-analyst` 内置在 `conversation.py:_create_data_analyst_agent()`
- **专注领域**: ERP 数据分析和业务洞察
- **缓存优先**: Agent 自动检测并使用已缓存的 schema/ontology
- **工具集**: 拥有所有工具的访问权限 (`tools: "*"`)
- **系统感知**: 自动注入宿主机系统信息（OS、Python 版本、路径等）
- **代码位置**: `kode/services/conversation.py:133-211`

这个设计简化了系统复杂度，专注于数据分析场景。

**新增：系统信息注入**

Agent 启动时会自动获取并注入宿主机系统信息到提示词中：
- 操作系统类型和版本（Windows/Linux/macOS）
- Python 版本和实现
- 当前工作目录和用户主目录
- Shell/终端类型
- 路径分隔符和命名约定

这使得 AI 能够：
- 生成符合当前操作系统的命令
- 正确处理文件路径
- 理解平台特定的限制

详细实现见 [kode/services/conversation.py:163-211](kode/services/conversation.py)

### Subscription & Billing System

**三层计费体系**（类似 Cursor）:

1. **Free Plan (免费版)**
   - 10万 tokens/月
   - 50 条消息/月
   - 3 个对话
   - 无数据库连接

2. **Pro Plan (专业版 - ¥99/月)**
   - 200万 tokens/月
   - 1000 条消息/月
   - 50 个对话
   - 5 个数据库连接
   - 支持本体构建

3. **Enterprise Plan (企业版 - ¥499/月)**
   - 1000万 tokens/月
   - 无限消息
   - 500 个对话
   - 50 个数据库连接
   - 定制模型、API 访问、专属支持

**配额执行**:
- `QuotaCheckMiddleware` 在每次 API 调用前检查配额
- `Usage` 模型跟踪实际使用量
- 超额后阻止请求并返回 403 错误

**Stripe 集成**:
- Checkout Sessions 用于订阅
- Webhook 处理支付事件
- 自动创建/更新/取消订阅

详见 [kode/web/api/billing.py](kode/web/api/billing.py) 和 [kode/services/stripe_service.py](kode/services/stripe_service.py)。

## Important Notes

**环境和运行：**
- **Virtual Environment**: 优先使用 `.venv`，启动脚本会自动检测环境
- **启动方式**: 推荐使用 `python run.py`，会自动清理端口和处理编码问题
- **Port Configuration**: 后端 8001，前端开发服务器 3000 (通过 Vite proxy 转发到后端)

**架构和兼容性：**
- **Single Agent**: 只使用内置的 `data-analyst` agent，移除了多 Agent 加载系统
- **LangChain**: 使用 LangChain 1.0+，简化的 agent 实现（无 AgentExecutor）
- **Claude Code Compatibility**: 目录结构同时支持 `.claude/` 和 `.kode/`

**配置和安全：**
- **API Keys**: 存储在 `.kode.json` (git-ignored) 或使用环境变量 `ANTHROPIC_API_KEY`/`OPENAI_API_KEY`
- **Environment Variables**: 必需配置在 `.env` 中（OAuth、Stripe、数据库）
- **Authentication**: OAuth 2.0 Google 登录
- **Billing**: Stripe 集成，三层订阅计划（Free/Pro/Enterprise）
- **Quota Enforcement**: QuotaCheckMiddleware 强制执行 token/消息配额

**数据库和缓存：**
- **Database Migrations**: 使用 Alembic 进行 schema 版本管理（migrations/ 目录）
- **Schema Cache**: 数据库 schema 自动缓存到 `schema_store/`
- **Ontology Cache**: 业务本体缓存到 `ontology_store/`
- **Connection Pool**: DatabaseManager 自动管理连接池

**通信协议：**
- **SSE (Server-Sent Events)**: 前端使用 SSE 实现流式响应，支持自动重连
- **Message Types**: `thinking`, `chunk`, `complete`, `error`, `tool_call`, `done`
- **Permission System**: 工具可以要求用户授权后执行

**中文支持：**
- 必须使用中文回复和思考
- 示例 agents 提供中文版本
- i18n 支持通过 LocaleMiddleware

## File Structure Overview

```
kode-python/
├── kode/                      # 主后端代码
│   ├── agents/                # Agent 系统 (base.py, anthropic_streaming.py)
│   ├── context/               # 对话上下文管理
│   ├── core/                  # 核心系统
│   │   ├── model_manager.py   # LLM 多模型管理
│   │   ├── permission.py      # 权限系统
│   │   ├── oauth.py           # OAuth 认证
│   │   └── security.py        # 安全工具
│   ├── tools/                 # 工具实现
│   │   ├── database_tools.py  # 数据库连接/查询工具
│   │   ├── ontology_tools.py  # 本体构建工具
│   │   └── [其他工具]
│   ├── services/              # 业务服务层
│   │   ├── conversation.py    # 对话服务 (核心)
│   │   ├── database_manager.py
│   │   ├── billing_service.py
│   │   └── stripe_service.py
│   ├── web/                   # FastAPI Web 层
│   │   ├── main.py            # 入口 (port 8001)
│   │   ├── api/               # REST 端点
│   │   │   ├── chat.py
│   │   │   ├── sse.py         # SSE 流式响应
│   │   │   ├── database.py
│   │   │   ├── auth.py        # OAuth 登录
│   │   │   └── billing.py     # Stripe 计费
│   │   └── middleware/
│   │       ├── quota_check.py # 配额检查
│   │       └── locale.py      # i18n
│   ├── models/                # SQLAlchemy ORM
│   │   ├── user.py
│   │   ├── subscription.py
│   │   ├── usage.py
│   │   └── [其他模型]
│   ├── schemas/               # Pydantic schemas
│   ├── database/              # 数据库配置
│   │   └── session.py
│   ├── utils/                 # 工具类
│   │   ├── config.py          # 配置管理
│   │   ├── logger.py
│   │   └── i18n.py            # 国际化
│   └── locales/               # i18n 翻译文件
├── web-frontend/              # Vue 前端 (同级目录)
│   ├── src/
│   │   ├── components/
│   │   ├── views/
│   │   ├── stores/            # Pinia 状态
│   │   ├── services/          # API/SSE 客户端
│   │   └── config/
│   ├── package.json
│   └── vite.config.ts
├── migrations/                # Alembic 数据库迁移
├── schema_store/              # 数据库 schema 缓存
├── ontology_store/            # 本体缓存
├── scripts/                   # 辅助脚本
├── .env                       # 环境变量 (git-ignored)
├── .env.example               # 环境变量模板
├── .kode.json                 # Kode 配置 (git-ignored)
├── .kode.json.example         # 配置模板
├── pyproject.toml             # Poetry 依赖
├── requirements.txt           # pip 依赖 (备用)
├── run.py                     # 启动脚本
├── CLAUDE.md                  # 本文档
├── BILLING_MODULE_README.md   # 计费模块文档
└── STRIPE_SETUP_COMPLETE.md   # Stripe 设置指南
```

## Database & Ontology Tools **[NEW]**

Kode now supports connecting to databases and building business ontologies for intelligent data analysis.

### Supported Databases
- **PostgreSQL** (asyncpg driver) - ✅ 完整支持（异步）
- **MySQL** (aiomysql driver) - ✅ 完整支持（异步）
- **SQL Server** (pyodbc driver) - ✅ 完整支持（同步）**[2025-11-21 新增]**
- **SQLite** (aiosqlite driver) - ✅ 基础支持（异步）
- **Oracle** (cx_oracle driver) - ⚠️ 部分支持（驱动未安装）

### Available Tools

**Database Tools** ([kode/tools/database_tools.py](kode/tools/database_tools.py)):
- `DatabaseConnectTool`: Connect to databases with connection pooling
- `DatabaseTestConnectionTool`: Verify connection health
- `DatabaseSchemaExtractorTool`: Extract complete schema metadata (tables, columns, constraints, relationships)
  - **✨ NEW**: Extracts table and column COMMENT/备注 information (critical for ontology building)
  - **✨ NEW**: 支持样例数据提取（倒数 N 行），帮助 AI 理解数据结构
    - 默认提取每个表倒数 5 行
    - 可通过 `include_sample_data` 和 `sample_row_limit` 参数控制
    - 自动处理多种数据库类型（PostgreSQL/MySQL/SQLite/SQL Server/Oracle）
    - 智能排序（按主键倒序）
  - Supports PostgreSQL, MySQL, Oracle, SQL Server (not SQLite)
- `DatabaseExecuteQueryTool`: **✨ NEW** Execute SQL queries on connected databases
  - SELECT queries: Read-only, returns results with configurable row limit
  - INSERT/UPDATE/DELETE: Write operations with affected row count
  - Supports parameterized queries (`:param_name` syntax) to prevent SQL injection
  - Automatic query type detection and error handling
  - Example: `SELECT * FROM users WHERE age > :min_age` with `params={"min_age": 25}`
- `DatabaseListConnectionsTool`: List all configured connections
- `DatabaseDisconnectTool`: Safely disconnect from databases

**Ontology Tools** ([kode/tools/ontology_tools.py](kode/tools/ontology_tools.py)):
- `OntologyBuilderTool`: Convert database schema to business ontology
  - Transforms technical table/column names to business terms
  - Infers implicit relationships beyond FK constraints
  - Extracts hierarchical structures
- `OntologyStorageTool`: Persist ontology with versioning
- `OntologySearchTool`: Semantic search in ontologies

### Quick Start

```bash
# Install database dependencies
poetry install

# Use the ontology-builder agent
poetry run kode
> 使用 ontology-builder 智能体连接我的数据库并构建本体
```

### Example Agent

The `ontology-builder` agent ([examples/agents/ontology-builder.md](examples/agents/ontology-builder.md)) automates:
1. Database connection and validation
2. Schema extraction (tables, columns, constraints, relationships)
3. Business ontology construction
4. Ontology persistence for future queries

### Configuration

Add to `.kode.json`:
```json
{
  "databases": {
    "connections": [
      {
        "name": "erp_production",
        "type": "postgresql",
        "host": "localhost",
        "port": 5432,
        "database": "erp_db",
        "username": "user",
        "password": "${DB_PASSWORD}",
        "ssl": true
      }
    ]
  },
  "ontology": {
    "storage_path": "./ontology_store",
    "enrichment": {
      "use_llm": true,
      "llm_model": "quick"
    }
  }
}
```

### Key Implementation Files

- **Database Tools**: [kode/tools/database_tools.py](kode/tools/database_tools.py) - 完整的数据库连接、Schema 提取、查询执行工具
- **Ontology Tools**: [kode/tools/ontology_tools.py](kode/tools/ontology_tools.py) - 本体构建、存储和搜索
- **Database Manager**: [kode/services/database_manager.py](kode/services/database_manager.py) - 数据库连接池管理
- **Test Suite**: [tests/test_database_tools.py](tests/test_database_tools.py) - 数据库工具综合测试

### Use Cases

1. **Data Discovery**: Quickly understand customer database structures
2. **Intelligent Q&A**: Natural language queries based on ontology
3. **Impact Analysis**: Understand dependencies and relationships
4. **Documentation**: Auto-generate data dictionaries and ER diagrams
5. **Data Governance**: Identify quality issues and normalization opportunities

## Common Development Workflows

### 添加新的 API 端点

1. 在 `kode/web/api/` 创建或编辑路由文件
2. 在 `kode/schemas/` 添加 Pydantic request/response schemas
3. 在 `kode/services/` 实现业务逻辑
4. 在 `kode/web/main.py` 注册路由 (参考已有的 `app.include_router()` 调用)
5. 重启服务测试端点 (`python run.py`)

### 添加新的数据库模型

1. 在 `kode/models/` 创建 SQLAlchemy 模型
2. 运行 `alembic revision --autogenerate -m "Add XXX model"`
3. 检查生成的迁移文件，确保正确
4. 运行 `alembic upgrade head` 应用迁移
5. 在相关 service 中使用新模型

### 添加新的 Tool

1. 在 `kode/tools/` 创建工具文件，继承 `KodeTool`
2. 定义 Pydantic input schema (继承自 `BaseModel`)
3. 实现 `_run()` 方法 (核心逻辑)
4. 在 `kode/services/conversation.py` 的 `__init__` 中注册工具到 `self.tools` 列表
5. 重启服务并通过对话测试工具执行

### 调试 SSE 流式响应

1. 检查 `kode/services/conversation.py:execute_task_streaming()`
2. 查看 `kode/agents/anthropic_streaming.py` 的流式实现
3. 使用 `logger.info/warning` 添加日志（会输出到控制台）
4. 前端使用浏览器 DevTools 查看 EventSource 消息

### Stripe 测试

使用 Stripe CLI 监听 webhook:
```bash
stripe listen --forward-to localhost:8001/api/billing/webhook
```

使用测试卡号: `4242 4242 4242 4242`

## Test Files & Scripts

**启动脚本：**
- `run.py`: 主启动脚本（推荐使用，自动处理端口清理和环境设置）

**测试文件：**
- `test_run.py`: 快速组件验证（无 API 调用）
- `test_real_api.py`: 完整集成测试（需要 API key）
- `tests/`: pytest 测试目录
  - `test_database_tools.py`: 数据库和本体工具测试

**辅助脚本：**
- `scripts/`: 数据初始化、迁移等辅助脚本

## SQL Server Support Details **[2025-11-21 新增]**

### 完整支持清单

✅ **驱动和连接**
- 已安装 `pyodbc 5.3.0`
- 检测到 `ODBC Driver 17 for SQL Server`
- 支持同步连接池

✅ **Schema 批量提取**
- 表结构（sys.tables）
- 列信息（sys.columns + sys.types）
- 列注释（sys.extended_properties / MS_Description）
- 主键（sys.indexes）
- 外键（sys.foreign_keys）

✅ **数据提取**
- 使用 SQL Server 特有的 TOP 语法
- 支持样例数据提取（倒数 N 行）

✅ **本体构建**
- 完整的 schema 到本体映射
- 自动解析列注释中的枚举映射
- 支持中文字段名和注释

### 关键实现位置

- 连接管理: [kode/services/database_manager.py:94-101](kode/services/database_manager.py)
- Schema 提取: [kode/tools/database_tools.py:851-1039](kode/tools/database_tools.py)
- 样例数据: [kode/tools/database_tools.py:491-494](kode/tools/database_tools.py)

### 使用要求

**Windows 系统**：
1. 安装 [ODBC Driver 17 for SQL Server](https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server)
2. 确保 SQL Server 允许远程连接（TCP/IP 协议）
3. 开放防火墙端口 1433

**连接字符串格式**：
```
mssql+pyodbc://username:password@host:port/database?driver=ODBC+Driver+17+for+SQL+Server
```

### 测试方法

```bash
# 1. 检查驱动和基本连接（推荐先运行）
python test/test_sqlserver_simple.py

# 2. 完整功能测试（需要实际数据库）
python test/test_sqlserver_connection.py
```

### 功能对比

| 功能            | PostgreSQL | MySQL | SQL Server |
| --------------- | ---------- | ----- | ---------- |
| Schema 批量提取 | ✅          | ✅     | ✅          |
| 列注释提取      | ✅          | ✅     | ✅          |
| 样例数据        | ✅          | ✅     | ✅          |
| 异步支持        | ✅          | ✅     | ❌          |
| 本体构建        | ✅          | ✅     | ✅          |

详细实现见 [kode/tools/database_tools.py:851-1039](kode/tools/database_tools.py) (SQL Server Schema 提取)