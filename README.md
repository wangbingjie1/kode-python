# Kode - AI 驱动的数据分析平台

基于 Claude AI 的原生数据分析开发平台，专为 ERP 数据分析和业务洞察设计。

## ✨ 核心特性

- 🚀 **纯 Web 服务架构** - 简单易用，开箱即用
- 🤖 **Claude AI Agent** - 基于 Anthropic Claude 的智能数据分析
- 🗄️ **多数据库支持** - PostgreSQL, MySQL, SQL Server, SQLite, Oracle
- 🧠 **自动本体构建** - 将数据库 Schema 转换为业务语义模型
- 🔄 **实时流式响应** - SSE 协议实现打字机效果
- 📊 **智能可视化** - 自动生成 ECharts 图表
- 💳 **Stripe 订阅计费** - 三层订阅计划（免费/专业/企业）

## 📋 系统要求

### 基础环境

- **Python**: 3.10 或更高版本
- **Node.js**: 16.x 或更高版本
- **操作系统**: Windows / Linux / macOS

### 依赖软件（可选）

- **PostgreSQL**: 如需连接 PostgreSQL 数据库
- **MySQL**: 如需连接 MySQL 数据库
- **SQL Server ODBC Driver 17**: 如需连接 SQL Server 数据库（仅 Windows）

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone <your-repo-url>
cd kode-python
```

### 2. 安装后端依赖

#### 方式一：使用 Poetry（推荐）

```bash
# 安装 Poetry
pip install poetry

# 安装依赖
poetry install
```

#### 方式二：使用 pip

```bash
# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置环境变量

复制环境变量模板并填写配置：

```bash
cp .env.example .env
```

**必需配置项**（编辑 `.env` 文件）：

```bash
# AI API Keys（至少需要一个）
ANTHROPIC_API_KEY=sk-ant-...       # Claude API Key
# OPENAI_API_KEY=sk-...            # OpenAI API Key（可选）

# Google OAuth 登录（可选，用于多用户）
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8001/api/auth/google/callback

# Stripe 计费（可选，用于订阅）
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# 安全密钥（用于 JWT）
SECRET_KEY=your-random-secret-key-here

# 数据库（默认使用 SQLite，无需配置）
# DATABASE_URL=sqlite+aiosqlite:///./kode.db
```

### 4. 初始化数据库

```bash
# 应用数据库迁移
alembic upgrade head
```

### 5. 安装前端依赖

```bash
cd web-frontend
npm install
cd ..
```

### 6. 启动服务

#### 推荐方式：使用启动脚本

```bash
# 启动后端（会自动清理端口）
python run.py
```

在另一个终端启动前端：

```bash
cd web-frontend
npm run dev
```

#### 手动启动

```bash
# 后端（端口 8001）
python -m kode.web.main

# 前端（端口 3000）
cd web-frontend
npm run dev
```

### 7. 访问应用

- **前端界面**: http://localhost:3000
- **后端 API**: http://localhost:8001
- **API 文档**: http://localhost:8001/docs

## 📁 配置文件说明

### `.env` - 环境变量

存储敏感信息（API keys、密钥等），**不提交到 Git**。

### `.kode.json` - Kode 配置

存储模型配置、工具参数等，支持项目级和用户级配置：

- **项目配置**: `./.kode.json`（当前项目）
- **用户配置**: `~/.kode.json`（全局默认）

示例配置：

```json
{
  "models": {
    "definitions": {
      "claude-sonnet-4-5": {
        "provider": "anthropic",
        "model": "claude-sonnet-4.5-20250929",
        "maxTokens": 8000
      }
    },
    "pointers": {
      "main": "claude-sonnet-4-5"
    }
  }
}
```

复制模板：

```bash
cp .kode.json.example .kode.json
```

## 🗄️ 数据库连接

### 支持的数据库

| 数据库 | 驱动 | 连接字符串示例 |
|--------|------|---------------|
| PostgreSQL | asyncpg | `postgresql+asyncpg://user:pass@host:5432/db` |
| MySQL | aiomysql | `mysql+aiomysql://user:pass@host:3306/db` |
| SQL Server | pyodbc | `mssql+pyodbc://user:pass@host:1433/db?driver=ODBC+Driver+17` |
| SQLite | aiosqlite | `sqlite+aiosqlite:///./data.db` |

### SQL Server 额外要求（Windows）

下载并安装 [ODBC Driver 17 for SQL Server](https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server)

### 连接测试

启动后端后，通过 Web 界面或 API 添加数据库连接：

```bash
curl -X POST http://localhost:8001/api/database/connections \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my_database",
    "connection_string": "postgresql+asyncpg://user:pass@localhost:5432/mydb"
  }'
```

## 🧪 测试

```bash
# 运行全部测试
pytest

# 测试数据库工具
pytest tests/test_database_tools.py -v

# 快速组件测试（不调用 API）
python test_run.py

# 完整集成测试（需要 API key）
python test_real_api.py
```

## 📊 数据库迁移

使用 Alembic 管理数据库 Schema：

```bash
# 创建新迁移
alembic revision --autogenerate -m "描述变更"

# 应用迁移
alembic upgrade head

# 回滚
alembic downgrade -1

# 查看当前版本
alembic current
```

## 💳 Stripe 订阅配置（可选）

如需启用订阅计费功能：

1. 注册 [Stripe 账号](https://stripe.com)
2. 获取 API Keys（测试模式）
3. 配置 Webhook：
   ```bash
   # 安装 Stripe CLI
   stripe listen --forward-to localhost:8001/api/billing/webhook
   ```
4. 在 `.env` 中填写 Stripe 配置

详见：[STRIPE_SETUP_COMPLETE.md](STRIPE_SETUP_COMPLETE.md)

## 🏗️ 项目架构

```
kode-python/
├── kode/                    # 后端主代码
│   ├── web/                 # FastAPI Web 层
│   │   ├── main.py          # 入口（端口 8001）
│   │   └── api/             # REST 端点
│   ├── services/            # 业务逻辑
│   │   └── conversation.py  # 对话服务（核心）
│   ├── tools/               # AI 工具集
│   ├── agents/              # Agent 系统
│   ├── models/              # 数据库模型
│   └── core/                # 核心组件
├── web-frontend/            # Vue 3 前端
│   ├── src/
│   │   ├── views/           # 页面
│   │   ├── components/      # 组件
│   │   ├── stores/          # Pinia 状态
│   │   └── services/        # API/SSE 客户端
├── migrations/              # Alembic 迁移文件
├── .env                     # 环境变量（不提交）
├── .kode.json               # Kode 配置（不提交）
└── run.py                   # 启动脚本
```

## 🛠️ 开发指南

### 代码格式化

```bash
# Black 格式化
poetry run black kode/ tests/

# Ruff 代码检查
poetry run ruff check kode/ tests/

# 类型检查
poetry run mypy kode/
```

### 添加新工具

1. 在 `kode/tools/` 创建工具文件，继承 `KodeTool`
2. 在 `kode/services/conversation.py` 注册工具
3. 重启服务测试

详见：[CLAUDE.md](CLAUDE.md) 开发指南部分

## 📚 文档

- **[CLAUDE.md](CLAUDE.md)** - 完整开发文档（架构、API、最佳实践）
- **[BILLING_MODULE_README.md](BILLING_MODULE_README.md)** - 计费模块文档
- **[STRIPE_SETUP_COMPLETE.md](STRIPE_SETUP_COMPLETE.md)** - Stripe 配置指南

## ❓ 常见问题

### 1. 端口被占用

运行 `python run.py` 会自动清理 8001 端口，或手动清理：

```bash
# Windows
netstat -ano | findstr :8001
taskkill /F /PID <PID>

# Linux/macOS
lsof -ti:8001 | xargs kill -9
```

### 2. 数据库连接失败

- 检查数据库服务是否运行
- 确认连接字符串格式正确
- 检查防火墙和网络设置
- 查看后端日志获取详细错误信息

### 3. API Key 错误

- 确认 `.env` 文件中 `ANTHROPIC_API_KEY` 已正确配置
- 检查 API key 是否有效（访问 Anthropic Console）
- 重启后端服务使环境变量生效

### 4. 前端无法连接后端

- 确认后端已启动（http://localhost:8001/health 应返回 OK）
- 检查 Vite 配置中的 proxy 设置（`web-frontend/vite.config.ts`）
- 查看浏览器控制台的网络请求错误

## 📄 许可证

[您的许可证类型]

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

**技术支持**: 查看 [CLAUDE.md](CLAUDE.md) 获取详细开发文档
