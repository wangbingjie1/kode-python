-- 添加OAuth相关字段到users表
-- SQLite兼容的迁移脚本

-- 1. 修改hashed_password允许NULL
-- SQLite不支持ALTER COLUMN，需要重建表

BEGIN TRANSACTION;

-- 创建新表
CREATE TABLE users_new (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    hashed_password TEXT,  -- 改为可空
    is_active INTEGER NOT NULL DEFAULT 1,
    auth_provider TEXT DEFAULT 'local',  -- 新增
    google_id TEXT UNIQUE,  -- 新增
    avatar_url TEXT,  -- 新增
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- 复制数据
INSERT INTO users_new (id, username, email, hashed_password, is_active, created_at, updated_at)
SELECT id, username, email, hashed_password, is_active, created_at, updated_at
FROM users;

-- 删除旧表
DROP TABLE users;

-- 重命名新表
ALTER TABLE users_new RENAME TO users;

-- 重建索引
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_google_id ON users(google_id);

COMMIT;
