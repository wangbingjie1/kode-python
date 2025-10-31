# Kode AI Web 界面启动指南

本文档详细说明如何启动 Kode AI 的 Web 后端服务和前端界面。

## 🚀 快速启动

### Windows 系统

使用提供的一键启动脚本:

```powershell
# 在项目根目录执行
.\start-web.ps1
```

停止服务:
```powershell
.\stop-web.ps1
```

### Linux/Mac 系统

```bash
# 在项目根目录执行
./start-web.sh
```

停止服务:
```bash
./stop-web.sh
```

**启动脚本功能**:
- ✅ 自动检测 Poetry 和 Node.js
- ✅ 自动安装缺失的依赖
- ✅ 智能识别 `.venv` 虚拟环境或使用 Poetry
- ✅ 检查端口占用情况
- ✅ 验证 API 密钥配置
- ✅ 后端服务 (端口 8000)
- ✅ 前端开发服务器 (端口 3000)
- ✅ Windows: 在新窗口中启动服务
- ✅ Linux/Mac: 后台运行并记录日志到 `logs/` 目录

## 📋 手动启动步骤

如果您需要分别控制后端和前端服务,可以按照以下步骤操作:

### 1️⃣ 启动后端服务

#### 前置条件

- Python 3.10+
- Poetry 包管理器

#### 安装依赖

```bash
# 如果还未安装依赖
poetry install
```

#### 配置环境变量

创建 `.env` 文件或配置环境变量:

```bash
# 方式 1: 使用 .env 文件
cp .env.example .env
# 编辑 .env 文件,添加您的 API 密钥

# 方式 2: 直接设置环境变量
export ANTHROPIC_API_KEY=your_api_key_here
# 或者 Windows CMD:
# set ANTHROPIC_API_KEY=your_api_key_here
# Windows PowerShell:
# $env:ANTHROPIC_API_KEY="your_api_key_here"
```

#### 启动后端

**方式 1: 使用 .venv 虚拟环境** (推荐)

```bash
# Windows PowerShell
.venv\Scripts\Activate.ps1
python -m kode.web.main

# Linux/Mac
source .venv/bin/activate
python -m kode.web.main
```

**方式 2: 使用 Poetry**

```bash
# 使用 Poetry 运行
poetry run python -m kode.web.main

# 或者激活 Poetry shell
poetry shell
python -m kode.web.main
```

后端服务将在 `http://localhost:8000` 启动。

#### 验证后端运行

打开浏览器访问:
- API 文档: http://localhost:8000/docs
- API 健康检查: http://localhost:8000/api/health

### 2️⃣ 启动前端开发服务器

#### 前置条件

- Node.js 16+
- npm 或 pnpm

#### 安装依赖

```bash
cd web-frontend
npm install
# 或使用 pnpm
# pnpm install
```

#### 启动前端

```bash
# 在 web-frontend 目录下
npm run dev

# 或使用 pnpm
# pnpm dev
```

前端开发服务器将在 `http://localhost:3000` 启动。

#### 访问应用

打开浏览器访问: http://localhost:3000

## 🔧 配置说明

### 后端配置

后端支持多层级配置,优先级从高到低:

1. **环境变量** (最高优先级)
   - `ANTHROPIC_API_KEY`: Anthropic API 密钥
   - `OPENAI_API_KEY`: OpenAI API 密钥
   - `KODE_DATABASE_URL`: 数据库连接 URL (默认: SQLite)

2. **命令行参数**
   ```bash
   python -m kode.web.main --host 0.0.0.0 --port 8080
   ```

3. **项目配置文件** (`./.kode.json`)
   ```json
   {
     "models": {
       "main": "claude-sonnet-4-5"
     },
     "api_keys": {
       "anthropic": "your_key"
     }
   }
   ```

4. **用户配置文件** (`~/.kode.json`)

### 前端配置

前端通过 Vite 配置文件 [vite.config.ts](web-frontend/vite.config.ts) 进行配置:

```typescript
export default defineConfig({
  server: {
    port: 3000,  // 前端端口
    proxy: {
      '/api': {
        target: 'http://localhost:8000',  // 后端 API 地址
        changeOrigin: true
      },
      '/ws': {
        target: 'ws://localhost:8000',  // WebSocket 地址
        ws: true
      }
    }
  }
})
```

## 🛠️ 常见问题

### 1. 后端启动失败

**问题**: `ModuleNotFoundError` 或依赖缺失

**解决方案**:
```bash
# 重新安装依赖
poetry install --no-root
poetry install
```

### 2. 前端连接失败 (显示"未连接")

**可能原因**:
- 后端服务未启动
- 端口配置不匹配
- 防火墙阻止连接

**解决方案**:
```bash
# 1. 检查后端是否运行
netstat -an | findstr :8000  # Windows
netstat -an | grep :8000     # Linux/Mac

# 2. 检查前端代理配置
# 确保 vite.config.ts 中的 proxy 配置正确

# 3. 检查浏览器控制台错误信息
# 按 F12 打开开发者工具查看网络请求
```

### 3. WebSocket 连接失败

**问题**: 消息无法发送,显示连接断开

**解决方案**:
1. 确认后端和前端都在运行
2. 检查浏览器控制台的 WebSocket 连接错误
3. 确认防火墙未阻止 WebSocket 连接
4. 尝试刷新页面重新建立连接

### 4. API 密钥未配置

**问题**: 后端报错 "API key not found"

**解决方案**:
```bash
# 设置环境变量
export ANTHROPIC_API_KEY=sk-ant-...

# 或创建配置文件
echo '{"api_keys": {"anthropic": "sk-ant-..."}}' > .kode.json
```

### 5. 端口被占用

**问题**: `Address already in use`

**解决方案**:
```bash
# Windows: 查找占用端口的进程
netstat -ano | findstr :8000
taskkill /PID <进程ID> /F

# Linux/Mac: 查找并终止进程
lsof -ti:8000 | xargs kill -9
```

## 📚 相关文档

- [主 README](README.md) - 项目总览
- [CLAUDE.md](CLAUDE.md) - 项目架构和开发指南
- [WEB_README.md](WEB_README.md) - Web 功能详细文档
- [API 文档](http://localhost:8000/docs) - 启动后端后可访问

## 🔍 开发模式

### 后端热重载

```bash
# 使用 uvicorn 的 reload 模式
poetry run uvicorn kode.web.main:app --reload --host 0.0.0.0 --port 8000
```

### 前端开发模式

```bash
# Vite 自带热重载
cd web-frontend
npm run dev
```

### 同时监控后端和前端日志

```bash
# Windows PowerShell
Start-Process powershell -ArgumentList "-NoExit", "-Command", "poetry run python -m kode.web.main"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd web-frontend; npm run dev"

# Linux/Mac (使用 tmux)
tmux new-session -d -s kode 'poetry run python -m kode.web.main'
tmux split-window -h 'cd web-frontend && npm run dev'
tmux attach -t kode
```

## ✅ 启动检查清单

在启动前确认:

- [ ] Python 3.10+ 已安装
- [ ] Poetry 已安装
- [ ] Node.js 16+ 已安装
- [ ] 依赖已安装 (`poetry install` 和 `npm install`)
- [ ] API 密钥已配置
- [ ] 端口 8000 和 3000 未被占用
- [ ] 数据库可访问 (默认使用 SQLite)

启动后验证:

- [ ] 后端健康检查通过: http://localhost:8000/api/health
- [ ] API 文档可访问: http://localhost:8000/docs
- [ ] 前端页面加载: http://localhost:3000
- [ ] WebSocket 连接成功 (页面显示"已连接")

## 💡 提示

1. **首次使用建议**: 使用一键启动脚本,减少配置错误
2. **开发调试**: 分别启动后端和前端,便于查看日志
3. **生产部署**: 参考 [WEB_README.md](WEB_README.md) 的生产部署章节
4. **性能优化**: 开发环境会比生产环境慢,这是正常现象

---

如有问题,请查阅 [常见问题](#-常见问题) 或提交 Issue。
