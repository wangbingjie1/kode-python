#!/bin/bash
# Kode AI Web 启动脚本 (Linux/Mac)
# 此脚本将启动后端服务和前端开发服务器

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

echo -e "${CYAN}==================================${NC}"
echo -e "${CYAN}  Kode AI Web 启动脚本${NC}"
echo -e "${CYAN}==================================${NC}"
echo ""

# 检查 Poetry 是否安装
echo -e "${YELLOW}检查 Poetry...${NC}"
if ! command -v poetry &> /dev/null; then
    echo -e "${RED}错误: 未找到 Poetry。请先安装 Poetry。${NC}"
    echo -e "${YELLOW}安装方法: https://python-poetry.org/docs/#installation${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Poetry 已安装${NC}"

# 检查 Node.js 是否安装
echo -e "${YELLOW}检查 Node.js...${NC}"
if ! command -v node &> /dev/null; then
    echo -e "${RED}错误: 未找到 Node.js。请先安装 Node.js。${NC}"
    echo -e "${YELLOW}下载地址: https://nodejs.org/${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Node.js 已安装 (版本: $(node --version))${NC}"

# 检查是否在项目根目录
if [ ! -f "pyproject.toml" ]; then
    echo -e "${RED}错误: 请在项目根目录运行此脚本。${NC}"
    exit 1
fi

# 检查后端依赖是否安装
echo ""
echo -e "${YELLOW}检查后端依赖...${NC}"
if ! poetry env info --path &> /dev/null; then
    echo -e "${YELLOW}后端依赖未安装，正在安装...${NC}"
    poetry install
fi
echo -e "${GREEN}✓ 后端依赖已就绪${NC}"

# 检查前端依赖是否安装
echo -e "${YELLOW}检查前端依赖...${NC}"
if [ ! -d "web-frontend/node_modules" ]; then
    echo -e "${YELLOW}前端依赖未安装，正在安装...${NC}"
    cd web-frontend
    npm install
    cd ..
fi
echo -e "${GREEN}✓ 前端依赖已就绪${NC}"

# 检查 API 密钥配置
echo ""
echo -e "${YELLOW}检查 API 密钥配置...${NC}"
API_KEY_WARNING=false
if [ -z "$ANTHROPIC_API_KEY" ]; then
    if [ ! -f ".kode.json" ]; then
        echo -e "${YELLOW}警告: 未找到 ANTHROPIC_API_KEY 环境变量或 .kode.json 配置文件。${NC}"
        echo -e "${YELLOW}后端可能无法正常工作。请配置 API 密钥。${NC}"
        API_KEY_WARNING=true
    fi
fi
if [ "$API_KEY_WARNING" = false ]; then
    echo -e "${GREEN}✓ API 密钥配置检查通过${NC}"
fi

# 检查端口是否被占用
echo ""
echo -e "${YELLOW}检查端口占用情况...${NC}"

# 检查端口 8000
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${YELLOW}警告: 端口 8000 已被占用。${NC}"
    echo -e "${YELLOW}如果不是 Kode 后端服务，请先关闭占用该端口的程序。${NC}"
    read -p "是否继续？(y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 0
    fi
fi

# 检查端口 3000
if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${YELLOW}警告: 端口 3000 已被占用。${NC}"
    echo -e "${YELLOW}如果不是 Kode 前端服务，请先关闭占用该端口的程序。${NC}"
    read -p "是否继续？(y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 0
    fi
fi

echo ""
echo -e "${CYAN}==================================${NC}"
echo -e "${CYAN}  启动服务${NC}"
echo -e "${CYAN}==================================${NC}"
echo ""

# 创建日志目录
mkdir -p logs

# 清理旧的 PID 文件
rm -f .backend.pid .frontend.pid

# 检测虚拟环境
if [ -f ".venv/bin/activate" ]; then
    echo -e "${GRAY}使用 .venv 虚拟环境...${NC}"
    PYTHON_CMD=".venv/bin/python"
elif [ -f ".venv/Scripts/activate" ]; then
    echo -e "${GRAY}使用 .venv 虚拟环境 (Windows)...${NC}"
    PYTHON_CMD=".venv/Scripts/python"
else
    echo -e "${GRAY}使用 Poetry 运行...${NC}"
    PYTHON_CMD="poetry run python"
fi

# 启动后端服务
echo -e "${YELLOW}正在启动后端服务（端口 8000）...${NC}"
$PYTHON_CMD -m kode.web.main > logs/backend.log 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > .backend.pid
echo -e "${GREEN}✓ 后端服务已启动 (PID: $BACKEND_PID)${NC}"

# 等待后端启动
echo -e "${YELLOW}等待后端服务就绪...${NC}"
MAX_WAIT=30
WAITED=0
BACKEND_READY=false

while [ $WAITED -lt $MAX_WAIT ]; do
    sleep 1
    WAITED=$((WAITED + 1))
    if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
        BACKEND_READY=true
        break
    fi
    echo -n "."
done

echo ""

if [ "$BACKEND_READY" = false ]; then
    echo -e "${YELLOW}警告: 后端服务可能未成功启动（超时 ${MAX_WAIT}s）。${NC}"
    echo -e "${YELLOW}请查看日志: tail -f logs/backend.log${NC}"
else
    echo -e "${GREEN}✓ 后端服务已就绪${NC}"
fi

# 启动前端服务
echo -e "${YELLOW}正在启动前端服务（端口 3000）...${NC}"
cd web-frontend
npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..
echo $FRONTEND_PID > .frontend.pid
echo -e "${GREEN}✓ 前端服务已启动 (PID: $FRONTEND_PID)${NC}"

echo ""
echo -e "${GREEN}==================================${NC}"
echo -e "${GREEN}  服务启动完成！${NC}"
echo -e "${GREEN}==================================${NC}"
echo ""
echo -e "${CYAN}后端服务: http://localhost:8000${NC}"
echo -e "${CYAN}API 文档: http://localhost:8000/docs${NC}"
echo -e "${CYAN}前端界面: http://localhost:3000${NC}"
echo ""
echo -e "${YELLOW}提示: 前端服务可能需要几秒钟完成编译。${NC}"
echo -e "${YELLOW}请等待编译完成后再访问。${NC}"
echo ""
echo -e "${GRAY}日志文件:${NC}"
echo -e "${GRAY}  后端: tail -f logs/backend.log${NC}"
echo -e "${GRAY}  前端: tail -f logs/frontend.log${NC}"
echo ""
echo -e "${YELLOW}停止服务: ./stop-web.sh${NC}"
echo -e "${YELLOW}或手动执行: kill \$(cat .backend.pid .frontend.pid)${NC}"
echo ""
