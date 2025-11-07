# MySQL 数据库迁移指南

## 本次修复需要的数据库变更

### 1. Users 表添加 is_admin 字段

**迁移脚本**: `migrations/001_add_user_is_admin.sql`

```sql
-- 添加管理员权限字段
ALTER TABLE users
ADD COLUMN is_admin BOOLEAN DEFAULT FALSE
COMMENT '管理员权限标识';
```

### 执行步骤

```bash
# 方式一：使用mysql命令行
mysql -u your_username -p your_database < migrations/001_add_user_is_admin.sql

# 方式二：登录MySQL后执行
mysql -u your_username -p
use your_database;
source migrations/001_add_user_is_admin.sql;

# 方式三：直接执行SQL
mysql -u your_username -p -e "ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE COMMENT '管理员权限标识';" your_database
```

### 验证迁移

```sql
-- 检查字段是否添加成功
DESC users;

-- 应该看到类似输出：
-- is_admin | tinyint(1) | YES | | 0 | 管理员权限标识

-- 检查现有用户
SELECT id, username, email, is_admin FROM users;
```

### 设置管理员用户

```sql
-- 将第一个注册的用户设为管理员
UPDATE users
SET is_admin = TRUE
WHERE id = (SELECT id FROM (SELECT id FROM users ORDER BY created_at ASC LIMIT 1) AS tmp);

-- 或者指定用户名
UPDATE users SET is_admin = TRUE WHERE username = 'your_admin_username';

-- 或者指定ID
UPDATE users SET is_admin = TRUE WHERE id = 'user_id_here';
```

### 验证管理员设置

```sql
SELECT username, email, is_admin, created_at
FROM users
WHERE is_admin = TRUE;
```

---

## 其他数据库变更（无需迁移）

### DatabaseConnectionModel 密码加密

- **无需执行SQL**: 现有的明文密码会在下次保存时自动加密
- **加密方式**: Fernet 对称加密
- **环境变量**: 需要设置 `ENCRYPTION_KEY` 或 `SECRET_KEY`

### 用户密码哈希升级 (SHA256 → bcrypt)

- **影响**: 现有用户无法使用旧密码登录
- **原因**: SHA256 哈希无法转换为 bcrypt
- **解决方案**:
  1. 用户使用"忘记密码"功能重置
  2. 管理员手动重置用户密码

---

## 回滚方案（如果需要）

```sql
-- 移除 is_admin 字段
ALTER TABLE users DROP COLUMN is_admin;
```

---

## 注意事项

1. **备份数据库**: 迁移前务必备份
   ```bash
   mysqldump -u username -p database_name > backup_before_migration.sql
   ```

2. **检查权限**: 确保有 ALTER TABLE 权限
   ```sql
   SHOW GRANTS FOR CURRENT_USER();
   ```

3. **生产环境**: 建议在非高峰期执行
   - ALTER TABLE 会锁表
   - 对于大表可能需要几秒到几分钟

4. **测试环境先验证**: 在测试环境完整测试后再应用到生产环境

---

## 完整迁移检查清单

- [ ] 备份生产数据库
- [ ] 在测试环境执行迁移
- [ ] 验证字段添加成功
- [ ] 设置至少一个管理员用户
- [ ] 测试管理员权限 (创建套餐 API)
- [ ] 测试非管理员用户被拒绝
- [ ] 在生产环境执行迁移
- [ ] 验证生产环境管理员用户

---

## 可能的错误及解决方案

### 错误1: Column already exists
```
ERROR 1060 (42S21): Duplicate column name 'is_admin'
```
**原因**: 字段已经存在
**解决**: 跳过此迁移或先删除字段

### 错误2: Access denied
```
ERROR 1142 (42000): ALTER command denied
```
**原因**: 用户没有 ALTER 权限
**解决**: 使用有足够权限的用户或联系DBA

### 错误3: Table is locked
```
ERROR 1205 (HY000): Lock wait timeout exceeded
```
**原因**: 表被其他进程锁定
**解决**: 等待锁释放或在低峰期执行
