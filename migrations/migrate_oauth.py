"""
数据库迁移脚本：添加 OAuth 字段

为 users 表添加 Google OAuth2 支持字段
"""
import sqlite3
import sys
from pathlib import Path

# 设置输出编码为 UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 确保从项目根目录运行
project_root = Path(__file__).parent.parent
db_path = project_root / "kode.db"

if not db_path.exists():
    print(f"错误：数据库文件不存在: {db_path}")
    sys.exit(1)

print(f"开始迁移数据库: {db_path}")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # 开始事务
    cursor.execute("BEGIN TRANSACTION")

    # 检查是否已经迁移
    cursor.execute("PRAGMA table_info(users)")
    columns = [row[1] for row in cursor.fetchall()]

    if 'auth_provider' in columns:
        print("✓ 数据库已迁移，无需重复执行")
        conn.close()
        sys.exit(0)

    print("正在备份旧表...")

    # 创建新表
    cursor.execute("""
        CREATE TABLE users_new (
            id TEXT PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            hashed_password TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            auth_provider TEXT DEFAULT 'local',
            google_id TEXT UNIQUE,
            avatar_url TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    print("✓ 创建新表 users_new")

    # 复制数据
    cursor.execute("""
        INSERT INTO users_new
            (id, username, email, hashed_password, is_active, created_at, updated_at)
        SELECT
            id, username, email, hashed_password, is_active, created_at, updated_at
        FROM users
    """)
    print("✓ 数据迁移完成")

    # 删除旧表
    cursor.execute("DROP TABLE users")
    print("✓ 删除旧表")

    # 重命名新表
    cursor.execute("ALTER TABLE users_new RENAME TO users")
    print("✓ 重命名新表")

    # 创建索引
    cursor.execute("CREATE INDEX idx_users_username ON users(username)")
    cursor.execute("CREATE INDEX idx_users_email ON users(email)")
    cursor.execute("CREATE INDEX idx_users_google_id ON users(google_id)")
    print("✓ 创建索引")

    # 提交事务
    conn.commit()
    print("✓ 迁移成功！")

except Exception as e:
    conn.rollback()
    print(f"✗ 迁移失败: {e}")
    sys.exit(1)

finally:
    conn.close()

print("\n数据库迁移完成。新增字段：")
print("  - auth_provider (登录方式: local, google)")
print("  - google_id (谷歌用户唯一标识)")
print("  - avatar_url (用户头像URL)")
