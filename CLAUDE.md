# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Kode is a Python port of an AI-native coding assistant powered by LangChain. It provides a modular framework for building AI agents with various tools for code interaction, similar to Claude Code itself. The project aims to build an AI-native ERP system with a zero-code configurable platform.

## Core Architecture

### 6-Layer System Design (Extended with Web Layer)

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

5. **Services Layer** ([kode/services/](kode/services/)) **[NEW]**
   - `conversation.py`: Async conversation service with streaming support
   - Wraps REPL logic for web consumption
   - Provides business logic for web API

6. **CLI Layer** ([kode/cli/](kode/cli/))
   - `main.py`: Typer-based CLI with commands: run, agents, config, version
   - `repl.py`: Interactive REPL session

7. **Web Layer** ([kode/web/](kode/web/))
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

Hierarchical configuration with 5-tier priority ([kode/utils/config.py](kode/utils/config.py)):

1. Environment variables (highest priority)
2. CLI parameters
3. Project config (`./.kode.json`)
4. User config (`~/.kode.json`)
5. Default values (lowest priority)

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

# Or initialize project with setup script
./setup.sh          # Unix/Linux/Mac
.\setup.ps1         # Windows PowerShell
```

### Running Kode

**CLI Mode:**

```bash
# Interactive REPL mode
python -m kode.cli.main
# Or with virtual environment:
.venv/Scripts/python -m kode.cli.main  # Windows
.venv/bin/python -m kode.cli.main      # Linux/Mac

# Execute single task
python -m kode.cli.main run "your task here"

# With options
python -m kode.cli.main --model claude-sonnet-4-5 --verbose
```

**Web Mode:**

```bash
# Quick start with automated script (recommended)
.\start-web.ps1          # Windows
./start-web.sh           # Linux/Mac

# Stop services
.\stop-web.ps1           # Windows
./stop-web.sh            # Linux/Mac

# Or manually:
# Backend (port 8000)
.venv\Scripts\Activate.ps1  # Windows
source .venv/bin/activate   # Linux/Mac
python -m kode.web.main

# Frontend (port 3000, in separate terminal)
cd web-frontend
npm run dev
```

**Startup Scripts Features:**
- Auto-detect `.venv` virtual environment (preferred) or Poetry
- Check dependencies (Python, Node.js, packages)
- Verify API key configuration
- Check port availability (8000, 8001)
- Launch backend and frontend services
- Health check backend startup
- Windows: Opens services in new PowerShell windows
- Linux/Mac: Runs in background with logs in `logs/` directory

See [WEB_STARTUP_README.md](WEB_STARTUP_README.md) for troubleshooting and detailed instructions.

### Configuration Management

```bash
# Show current configuration
poetry run kode config --show

# Create example configuration
poetry run kode config --init
```

### Agent Management

```bash
# List all available agents
poetry run kode agents --list

# Show agent details
poetry run kode agents --info code-reviewer
```

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

## Test Files

- [test_run.py](test_run.py): Quick component verification without API calls
- [test_real_api.py](test_real_api.py): Full integration test with LLM API
- [verify_project.py](verify_project.py): Project structure and dependency verification