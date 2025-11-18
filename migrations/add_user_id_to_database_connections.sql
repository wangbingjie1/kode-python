-- 数据库连接表安全加固 SQL 脚本
-- 功能：
-- 1. 添加组合唯一索引（user_id + name）- 实现按用户隔离连接名称
-- 2. 添加密码字段注释说明加密方式
--
-- 注意：
-- - user_id 字段和外键已存在，无需重复添加
-- - 密码加密通过应用层实现（使用 Fernet 对称加密）
-- - 需确保 .env 中配置了 SECRET_KEY 或 DB_ENCRYPTION_KEY

-- 步骤1: 创建组合唯一索引（user_id + name）
-- 这样每个用户的连接名称是唯一的，但不同用户可以有同名连接
ALTER TABLE database_connections
ADD UNIQUE INDEX uq_user_connection_name (user_id, name);

-- 步骤2: 添加注释说明
ALTER TABLE database_connections
MODIFY COLUMN password TEXT NOT NULL COMMENT '加密后的数据库密码（使用 Fernet AES-128 加密）';

-- 验证结果
SELECT
    TABLE_NAME,
    COLUMN_NAME,
    COLUMN_TYPE,
    IS_NULLABLE,
    COLUMN_KEY,
    COLUMN_COMMENT
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
AND TABLE_NAME = 'database_connections'
ORDER BY ORDINAL_POSITION;

-- 显示索引信息
SHOW INDEX FROM database_connections;
