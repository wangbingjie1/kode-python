# CLAUDE.md
必须中文回复和思考，第一性原理解决根本问题，像一个老程序员一样写代码，比如Linux，只给最靠谱的建议和方案，不确定不推荐，不要说废话，尽量不要生成说明文件，生成脚本和代码，要自己先测试通过，再告诉用户，用户有选择困难症，你可以向他提问，但不要给他选项，我不要你的速度，我要你的质量
This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Kode 是一个基于 AI 的原生 ERP 开发平台，采用 LangChain 构建。项目已简化为 **Web-Only** 架构，移除了 CLI/REPL 模式，专注于提供 Web API 服务和前端界面。

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

2. **Tools Layer** ([kode/tools/](kode/tools/))
   - `base.py`: Base class `KodeTool` extending LangChain's BaseTool
   - `file_tools.py`: FileRead, FileWrite, FileEdit tools
   - `bash_tool.py`: Shell command execution
   - `grep_tool.py`: Code search functionality
   - `glob_tool.py`: File pattern matching
   - `database_tools.py`: **[NEW]** Database connection and schema extraction (PostgreSQL, MySQL, SQLite, etc.)
   - `ontology_tools.py`: **[NEW]** Ontology building and semantic search for database schemas
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
   - `main.py`: FastAPI application entry point (port 8000)
   - `api/`: REST API endpoints
     - `chat.py`: Conversation and message endpoints
     - `project.py`: Project management endpoints
   - `websocket/`: WebSocket handlers for real-time streaming chat
     - `connection.py`: WebSocket connection manager and message routing
   - Database: SQLite (default) with SQLAlchemy ORM
   - Models: User, Conversation, Message, Project

**Frontend Layer** ([web-frontend/](web-frontend/))
   - Vue 3 + TypeScript + Vite
   - `src/components/`: Reusable UI components
     - `NotificationContainer.vue`: Toast notification system
     - `MessageItem.vue`: Chat message display with markdown rendering
   - `src/views/`: Page views
     - `ChatView.vue`: Main chat interface
   - `src/stores/`: Pinia state management
     - `chat.ts`: Chat state, WebSocket integration, message handling
   - `src/services/`:
     - `api.ts`: REST API client (Axios)
     - `websocket.ts`: WebSocket service with auto-reconnect
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
- `GET /health` - Health check (no auth)
- `GET /api/config` - Get current configuration
- `POST /api/chat/conversations` - Create conversation
- `GET /api/chat/conversations/{id}` - Get conversation details
- `GET /api/chat/conversations/{id}/messages` - Get message history
- `DELETE /api/chat/conversations/{id}` - Delete conversation

**SSE (Server-Sent Events):**
- `GET /api/sse/chat/{conversation_id}/stream?task=xxx` - Real-time streaming chat via SSE
- `POST /api/sse/chat/{conversation_id}/message` - POST version for sending messages
- Message types: `thinking`, `chunk`, `complete`, `error`, `tool_call`, `done`
- Server streams: `data: {"type": "chunk", "content": "...", "metadata": {}}`
- Uses text/event-stream with automatic reconnection support

**Database Models:**
- `User`: Basic user information (default user created on startup)
- `Project`: Project grouping for conversations (default project: "default")
- `Conversation`: Chat sessions with title and timestamps
- `Message`: Individual messages (role: user/assistant, content, metadata)

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

**方式一：使用简化启动脚本（推荐）**

```bash
# 后端服务
python run.py           # 直接运行，自动启动在 http://localhost:8001

# 或使用 PowerShell 脚本
.\start-backend.ps1     # Windows（自动清理旧进程、检查端口）
.\stop-backend.ps1      # 停止后端
```

**方式二：手动启动**

```bash
# 后端 (port 8001)
python -m kode.web.main

# 前端 (port 3000, 在另一个终端)
cd web-frontend
npm run dev
```

**后端启动脚本特性：**
- ✓ 自动停止占用端口的旧进程
- ✓ 清除 Python 缓存（__pycache__, *.pyc）
- ✓ 验证虚拟环境和 API Key
- ✓ 确保单例运行（端口占用检查）
- ✓ Uvicorn 自动重载（修改代码自动重启）

### Configuration Management

配置文件位置：
- 项目配置：`./.kode.json`
- 用户配置：`~/.kode.json`
- 环境变量：`ANTHROPIC_API_KEY`

### Testing

```bash
# Run pytest tests
poetry run pytest

# Run quick component test
python test_run.py

# Run real API test (requires API key)
python test_real_api.py
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

## Important Notes

- **Virtual Environment**: Prefer using `.venv` directly over Poetry for running services. Startup scripts auto-detect the environment.
- **LangChain Compatibility**: Project uses LangChain 1.0+ with simplified agent implementation (no AgentExecutor)
- **Claude Code Compatibility**: Directory structure supports both `.claude/` and `.kode/` for interoperability
- **API Keys**: Store in `.kode.json` (git-ignored) or `ANTHROPIC_API_KEY`/`OPENAI_API_KEY` environment variables
- **Chinese Support**: Example agents provided in Chinese ([examples/agents/](examples/agents/))
- **Permission System**: Tools can require user permission before execution
- **SSE Communication**: Frontend uses SSE (Server-Sent Events) for streaming responses with automatic reconnection
- **Port Configuration**: Backend uses 8000, frontend development server uses 3000 (proxied to backend)

## File Structure Overview

```
kode-python/
├── kode/
│   ├── agents/          # Agent system with loader
│   ├── cli/             # CLI interface and REPL
│   ├── context/         # Conversation and project context
│   ├── core/            # Core systems (models, permissions)
│   ├── tools/           # Tool implementations
│   ├── services/        # Business services
│   ├── web/             # Web layer
│   │   ├── api/         # REST API endpoints (chat, project, sse)
│   │   └── main.py      # FastAPI app
│   ├── models/          # SQLAlchemy ORM models (NEW)
│   ├── schemas/         # Pydantic schemas (NEW)
│   ├── database/        # Database config (NEW)
│   └── utils/           # Config, logging utilities
├── web-frontend/        # Vue 3 + TypeScript frontend
│   ├── src/
│   │   ├── components/  # NotificationContainer, MessageItem
│   │   ├── views/       # ChatView (main interface)
│   │   ├── stores/      # Pinia state (chat store)
│   │   ├── services/    # API client, SSE service
│   │   ├── composables/ # useNotification
│   │   ├── config/      # constants.ts (DEFAULT_PROJECT_ID, etc.)
│   │   └── router/      # Vue router
│   ├── package.json
│   └── vite.config.ts   # Vite config with proxy setup
├── tests/               # Test suite
├── examples/            # Example agent definitions
├── logs/                # Service logs (git-ignored, created by start-web.sh)
├── pyproject.toml       # Poetry dependencies and tool config
├── .kode.json          # Project configuration (git-ignored)
├── .backend.pid        # Backend process ID (git-ignored)
├── .frontend.pid       # Frontend process ID (git-ignored)
├── WEB_STARTUP_README.md  # Detailed startup guide and troubleshooting
├── start-web.sh        # Linux/Mac startup script
├── start-web.ps1       # Windows startup script
├── stop-web.sh         # Linux/Mac stop script
└── stop-web.ps1        # Windows stop script
```

## Database & Ontology Tools **[NEW]**

Kode now supports connecting to databases and building business ontologies for intelligent data analysis.

### Supported Databases
- **PostgreSQL** (asyncpg driver)
- **MySQL** (aiomysql driver)
- **SQL Server** (pyodbc driver)
- **Oracle** (cx_oracle driver)
- **SQLite** (aiosqlite driver)

### Available Tools

**Database Tools** ([kode/tools/database_tools.py](kode/tools/database_tools.py)):
- `DatabaseConnectTool`: Connect to databases with connection pooling
- `DatabaseTestConnectionTool`: Verify connection health
- `DatabaseSchemaExtractorTool`: Extract complete schema metadata (tables, columns, constraints, relationships)
  - **✨ NEW**: Extracts table and column COMMENT/备注 information (critical for ontology building)
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

### Documentation

- **[Database Tools Guide](docs/DATABASE_TOOLS_GUIDE.md)**: Complete usage guide with examples
- **[Database Tools Design](docs/database_tools_design.md)**: Architecture and design decisions
- **[COMMENT Extraction Guide](docs/COMMENT_EXTRACTION.md)**: ✨ NEW - How to extract and use database field comments
- **[Test Suite](tests/test_database_tools.py)**: Comprehensive tests for all database tools

### Use Cases

1. **Data Discovery**: Quickly understand customer database structures
2. **Intelligent Q&A**: Natural language queries based on ontology
3. **Impact Analysis**: Understand dependencies and relationships
4. **Documentation**: Auto-generate data dictionaries and ER diagrams
5. **Data Governance**: Identify quality issues and normalization opportunities

## Test Files

- [test_run.py](test_run.py): Quick component verification without API calls
- [test_real_api.py](test_real_api.py): Full integration test with LLM API
- [test_database_tools.py](tests/test_database_tools.py): **[NEW]** Database and ontology tools tests
- [verify_project.py](verify_project.py): Project structure and dependency verification