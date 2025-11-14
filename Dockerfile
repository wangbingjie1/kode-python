# 多阶段构建：减小镜像体积
FROM python:3.10-slim as builder

# 设置工作目录
WORKDIR /app

# 安装系统依赖（编译时需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt pyproject.toml poetry.lock* ./

# 安装 Poetry 并导出依赖
RUN pip install --no-cache-dir poetry && \
    poetry export -f requirements.txt --output requirements-export.txt --without-hashes

# 安装 Python 依赖到 /install 目录
RUN pip install --no-cache-dir --prefix=/install -r requirements-export.txt

# 运行阶段：最小化运行时镜像
FROM python:3.10-slim

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/install/bin:$PATH" \
    PYTHONPATH="/app:$PYTHONPATH"

# 安装运行时系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 创建非 root 用户
RUN useradd -m -u 1000 kodeuser && \
    mkdir -p /app /data && \
    chown -R kodeuser:kodeuser /app /data

# 复制编译好的依赖
COPY --from=builder /install /usr/local

# 切换工作目录
WORKDIR /app

# 复制应用代码（使用 .dockerignore 排除不需要的文件）
COPY --chown=kodeuser:kodeuser . .

# 创建必要的目录
RUN mkdir -p /app/schema_store /app/ontology_store /app/logs && \
    chown -R kodeuser:kodeuser /app/schema_store /app/ontology_store /app/logs

# 切换到非 root 用户
USER kodeuser

# 暴露端口
EXPOSE 8001

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# 启动命令
CMD ["python", "-m", "kode.web.main"]
