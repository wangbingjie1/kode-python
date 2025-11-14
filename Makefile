# Kode Docker 快捷命令

.PHONY: help build up down restart logs shell db-shell db-migrate db-backup clean

# 默认目标
help:
	@echo "Kode Docker 管理命令:"
	@echo "  make build       - 构建所有镜像"
	@echo "  make up          - 启动所有服务"
	@echo "  make down        - 停止所有服务"
	@echo "  make restart     - 重启所有服务"
	@echo "  make logs        - 查看所有日志"
	@echo "  make shell       - 进入后端容器 shell"
	@echo "  make db-shell    - 进入数据库 shell"
	@echo "  make db-migrate  - 运行数据库迁移"
	@echo "  make db-backup   - 备份数据库"
	@echo "  make clean       - 清理未使用的资源"
	@echo "  make dev-up      - 启动开发环境（仅数据库）"
	@echo "  make prod-up     - 启动生产环境（含 Nginx）"

# 构建镜像
build:
	docker-compose build

# 启动服务
up:
	docker-compose up -d

# 停止服务
down:
	docker-compose down

# 重启服务
restart:
	docker-compose restart

# 查看日志
logs:
	docker-compose logs -f

# 进入后端容器
shell:
	docker exec -it kode-backend bash

# 进入数据库
db-shell:
	docker exec -it kode-postgres psql -U kode -d kode

# 运行数据库迁移
db-migrate:
	docker exec -it kode-backend alembic upgrade head

# 备份数据库
db-backup:
	docker exec kode-postgres pg_dump -U kode kode > backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "数据库已备份到 backup_$$(date +%Y%m%d_%H%M%S).sql"

# 清理资源
clean:
	docker system prune -f

# 开发环境（仅数据库）
dev-up:
	docker-compose -f docker-compose.dev.yml up -d

# 生产环境（含 Nginx）
prod-up:
	docker-compose --profile production up -d

# 重新构建并启动
rebuild:
	docker-compose up -d --build

# 查看服务状态
status:
	docker-compose ps

# 查看资源使用
stats:
	docker stats
