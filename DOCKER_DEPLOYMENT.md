# Kode Docker 部署指南

## 快速开始

### 1. 环境准备

确保已安装：
- Docker 20.10+
- Docker Compose 2.0+

### 2. 配置环境变量

复制环境变量模板并编辑：

```bash
cp .env.example .env
```

**必须配置的环境变量：**

```bash
# AI API Keys（必填）
ANTHROPIC_API_KEY=sk-ant-xxxxx

# 数据库密码
POSTGRES_PASSWORD=your_strong_password
REDIS_PASSWORD=your_redis_password

# 安全密钥（生成随机字符串）
SECRET_KEY=your_secret_key_minimum_32_characters

# Google OAuth（可选）
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8001/api/auth/google/callback

# Stripe 支付（可选）
STRIPE_SECRET_KEY=sk_test_xxxxx
STRIPE_PUBLISHABLE_KEY=pk_test_xxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxx
```

### 3. 启动服务

**开发环境（不启动 Nginx）：**

```bash
docker-compose up -d
```

**生产环境（启用 Nginx + HTTPS）：**

```bash
# 准备 SSL 证书
mkdir -p nginx/ssl
# 将证书文件放到 nginx/ssl/ 目录：cert.pem 和 key.pem

# 启动完整服务栈
docker-compose --profile production up -d
```

### 4. 初始化数据库

```bash
# 进入后端容器
docker exec -it kode-backend bash

# 运行数据库迁移
alembic upgrade head

# 退出容器
exit
```

### 5. 访问服务

- **前端界面**: http://localhost（或 https://yourdomain.com）
- **后端 API**: http://localhost:8001
- **API 文档**: http://localhost:8001/docs
- **健康检查**: http://localhost:8001/health

## 服务架构

```
┌─────────────┐
│   Nginx     │ :443 (HTTPS)
│  (可选)     │ :80 (HTTP → HTTPS)
└──────┬──────┘
       │
   ┌───┴────┬────────┐
   │        │        │
┌──▼──┐  ┌──▼──┐  ┌──▼──────┐
│Front│  │Back │  │ Postgres│
│ end │  │ end │  │ + Redis │
└─────┘  └─────┘  └─────────┘
```

**服务说明：**

| 服务 | 端口 | 说明 |
|------|------|------|
| frontend | 80 | Vue 前端（Nginx 静态文件服务） |
| backend | 8001 | FastAPI 后端 |
| postgres | 5432 | PostgreSQL 数据库 |
| redis | 6379 | Redis 缓存 |
| nginx | 443, 8080 | 反向代理（仅生产环境） |

## 常用命令

### 查看日志

```bash
# 所有服务日志
docker-compose logs -f

# 特定服务日志
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f postgres
```

### 重启服务

```bash
# 重启所有服务
docker-compose restart

# 重启特定服务
docker-compose restart backend
```

### 停止服务

```bash
# 停止所有服务
docker-compose down

# 停止并删除数据卷（危险！会丢失数据）
docker-compose down -v
```

### 重新构建镜像

```bash
# 重新构建所有镜像
docker-compose build

# 重新构建特定服务
docker-compose build backend

# 重新构建并启动
docker-compose up -d --build
```

### 进入容器

```bash
# 进入后端容器
docker exec -it kode-backend bash

# 进入数据库容器
docker exec -it kode-postgres psql -U kode -d kode
```

## 数据库管理

### 创建迁移

```bash
docker exec -it kode-backend bash
alembic revision --autogenerate -m "描述变更"
exit
```

### 应用迁移

```bash
docker exec -it kode-backend alembic upgrade head
```

### 备份数据库

```bash
# PostgreSQL 备份
docker exec kode-postgres pg_dump -U kode kode > backup_$(date +%Y%m%d_%H%M%S).sql

# 恢复备份
cat backup_20250114_120000.sql | docker exec -i kode-postgres psql -U kode -d kode
```

### 连接数据库

```bash
docker exec -it kode-postgres psql -U kode -d kode
```

## 生产环境部署

### 1. SSL 证书配置

**使用 Let's Encrypt 免费证书：**

```bash
# 安装 certbot
sudo apt-get update
sudo apt-get install certbot

# 获取证书
sudo certbot certonly --standalone -d yourdomain.com

# 复制证书到项目目录
mkdir -p nginx/ssl
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem nginx/ssl/cert.pem
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem nginx/ssl/key.pem
```

**自签名证书（仅测试）：**

```bash
mkdir -p nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/key.pem \
  -out nginx/ssl/cert.pem \
  -subj "/CN=localhost"
```

### 2. 环境变量安全

生产环境必须修改所有默认密码：

```bash
# 生成强密码
openssl rand -base64 32

# 修改 .env 文件
POSTGRES_PASSWORD=<生成的强密码>
REDIS_PASSWORD=<生成的强密码>
SECRET_KEY=<生成的强密码>
```

### 3. 资源限制

编辑 `docker-compose.yml` 添加资源限制：

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
```

### 4. 健康检查

确保所有服务的健康检查正常：

```bash
# 检查服务状态
docker-compose ps

# 查看健康状态
curl http://localhost:8001/health
```

### 5. 日志管理

配置日志轮转避免磁盘占满：

```yaml
services:
  backend:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

## 监控和维护

### 性能监控

```bash
# 查看容器资源使用
docker stats

# 查看磁盘使用
docker system df
```

### 清理磁盘空间

```bash
# 清理未使用的镜像
docker image prune -a

# 清理未使用的容器
docker container prune

# 清理未使用的数据卷
docker volume prune

# 清理所有未使用资源
docker system prune -a --volumes
```

### 更新服务

```bash
# 拉取最新代码
git pull

# 重新构建并启动
docker-compose up -d --build

# 应用数据库迁移
docker exec -it kode-backend alembic upgrade head
```

## 故障排查

### 容器无法启动

```bash
# 查看详细日志
docker-compose logs backend

# 检查配置文件
docker-compose config

# 检查端口占用
netstat -tuln | grep 8001
```

### 数据库连接失败

```bash
# 检查数据库是否运行
docker-compose ps postgres

# 查看数据库日志
docker-compose logs postgres

# 测试数据库连接
docker exec -it kode-postgres pg_isready -U kode
```

### 前端无法访问后端

```bash
# 检查网络连接
docker network ls
docker network inspect kode-python_kode-network

# 测试后端 API
curl http://localhost:8001/health
```

### 内存不足

```bash
# 增加 Docker Desktop 内存限制
# Settings → Resources → Memory → 调整为 8GB+

# 或者减少服务数量，使用外部数据库
```

## 扩展配置

### 使用外部数据库

修改 `.env` 文件：

```bash
DATABASE_URL=postgresql+asyncpg://user:pass@external-db-host:5432/kode
```

注释 `docker-compose.yml` 中的 postgres 服务。

### 使用外部 Redis

```bash
REDIS_URL=redis://:password@external-redis-host:6379/0
```

注释 `docker-compose.yml` 中的 redis 服务。

### 多实例部署

```bash
# 启动多个后端实例
docker-compose up -d --scale backend=3
```

需要配合负载均衡器（如 Nginx upstream）使用。

## 安全建议

1. **修改所有默认密码**
2. **使用 HTTPS（生产环境必须）**
3. **限制容器资源使用**
4. **定期更新镜像和依赖**
5. **配置防火墙规则**
6. **启用日志审计**
7. **定期备份数据库**
8. **使用 secrets 管理敏感信息**（推荐 Docker Swarm 或 Kubernetes）

## 性能优化

1. **启用 Redis 缓存**
2. **配置 Nginx Gzip 压缩**
3. **使用 CDN 加速静态资源**
4. **优化数据库索引**
5. **启用连接池**
6. **配置合适的 worker 数量**

## 支持

遇到问题请查看：
- [项目文档](CLAUDE.md)
- [API 文档](http://localhost:8001/docs)
- [GitHub Issues](https://github.com/your-repo/issues)
