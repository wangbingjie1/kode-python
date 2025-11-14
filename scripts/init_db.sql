-- 数据库初始化脚本
-- 由 Docker Compose 在 PostgreSQL 容器启动时自动执行

-- 创建扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- 用于文本相似度搜索

-- 设置时区
SET timezone = 'Asia/Shanghai';

-- 创建 schema（如果需要）
-- CREATE SCHEMA IF NOT EXISTS kode;

-- 注意：实际的表结构由 Alembic 迁移管理
-- 这个脚本只做基础设置和扩展安装

-- 创建只读用户（可选，用于报表查询）
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_user WHERE usename = 'kode_readonly') THEN
        CREATE USER kode_readonly WITH PASSWORD 'readonly_password_change_me';
    END IF;
END
$$;

-- 授予只读权限
GRANT CONNECT ON DATABASE kode TO kode_readonly;
GRANT USAGE ON SCHEMA public TO kode_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO kode_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO kode_readonly;

-- 输出初始化完成信息
SELECT 'Database initialized successfully' AS status;
