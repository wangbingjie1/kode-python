-- Migration: Add is_admin field to users table
-- Created: 2025-11-07
-- Purpose: Support admin permission checks for billing API

-- Add is_admin column to users table
ALTER TABLE users
ADD COLUMN is_admin BOOLEAN DEFAULT FALSE
COMMENT '管理员权限标识';

-- Optional: Set first user as admin (uncomment if needed)
-- UPDATE users
-- SET is_admin = TRUE
-- WHERE id = (SELECT id FROM (SELECT id FROM users ORDER BY created_at ASC LIMIT 1) AS tmp);

-- Optional: Set specific user as admin by username
-- UPDATE users SET is_admin = TRUE WHERE username = 'admin';

-- Verify the migration
SELECT COUNT(*) as total_users,
       SUM(CASE WHEN is_admin = TRUE THEN 1 ELSE 0 END) as admin_count
FROM users;
