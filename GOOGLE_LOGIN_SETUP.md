# 谷歌登录配置指南

本文档说明如何配置谷歌 OAuth2 登录功能。

## 功能概述

项目已集成谷歌 OAuth2 登录，用户可以：
- 使用谷歌账号快速登录
- 自动创建用户账户
- 关联已有邮箱账户到谷歌登录

## 配置步骤

### 1. 获取谷歌 OAuth2 凭据

1. 访问 [Google Cloud Console](https://console.cloud.google.com/)
2. 创建新项目或选择现有项目
3. 启用 Google+ API：
   - 进入 "API和服务" > "库"
   - 搜索 "Google+ API"
   - 点击启用

4. 创建 OAuth 2.0 凭据：
   - 进入 "API和服务" > "凭据"
   - 点击 "创建凭据" > "OAuth 客户端 ID"
   - 应用类型选择 "Web 应用"
   - 配置授权重定向 URI：
     - 开发环境：`http://localhost:8001/api/auth/google/callback`
     - 生产环境：`https://yourdomain.com/api/auth/google/callback`

5. 记录生成的：
   - Client ID（客户端ID）
   - Client Secret（客户端密钥）

### 2. 配置环境变量

编辑项目根目录的 `.env` 文件（如果没有，复制 `.env.example`）：

```bash
# 复制模板
cp .env.example .env

# 编辑 .env 文件
```

添加以下配置：

```env
# JWT密钥（必须修改）
SECRET_KEY=your-strong-random-secret-key-here

# 谷歌 OAuth2 配置
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8001/api/auth/google/callback
```

**安全提示**：
- `SECRET_KEY` 必须是强随机字符串，生产环境绝不能使用默认值
- 不要将 `.env` 文件提交到版本控制（已在 `.gitignore` 中排除）

### 3. 安装依赖

```bash
# 安装后端依赖（包含 authlib 和 httpx）
pip install -r requirements.txt

# 或使用 Poetry
poetry install
```

### 4. 运行数据库迁移

```bash
# 执行 SQL 迁移脚本（如果使用 SQLite）
sqlite3 kode.db < migrations/add_oauth_fields.sql

# 或重新创建数据库（开发环境）
rm kode.db  # 删除旧数据库
python -m kode.web.main  # 启动服务，自动创建新表
```

### 5. 启动服务

```bash
# 启动后端（端口 8001）
python run.py

# 启动前端（另一个终端，端口 3000）
cd web-frontend
npm run dev
```

### 6. 测试谷歌登录

1. 访问 http://localhost:3000/login
2. 点击 "使用谷歌账号登录" 按钮
3. 跳转到谷歌授权页面
4. 授权后自动返回应用并登录

## 技术架构

### 后端实现

**文件结构**：
```
kode/
├── core/
│   ├── oauth.py          # OAuth2 配置和客户端
│   └── security.py       # JWT token 生成和验证
├── models/
│   └── user.py          # User 模型（扩展了 OAuth 字段）
├── web/
│   └── api/
│       └── auth.py      # 认证端点（包含谷歌登录）
└── schemas/
    └── auth.py          # Pydantic schemas
```

**API 端点**：
- `GET /api/auth/google/login` - 获取谷歌授权 URL
- `POST /api/auth/google/callback` - 处理谷歌回调，返回 JWT token

**登录流程**：
1. 前端请求授权 URL
2. 用户跳转到谷歌授权页面
3. 谷歌回调返回 `code`
4. 后端交换 `code` 获取 `access_token`
5. 使用 `access_token` 获取用户信息
6. 创建/关联用户，生成 JWT token
7. 前端保存 token 并跳转到首页

### 前端实现

**文件结构**：
```
web-frontend/src/
├── stores/
│   └── auth.ts          # 认证状态管理（Pinia）
├── views/
│   └── LoginView.vue    # 登录页面（包含谷歌登录按钮）
└── router/
    └── index.ts         # 路由守卫（检查认证状态）
```

**关键方法**：
- `authStore.getGoogleAuthUrl()` - 获取授权 URL
- `authStore.loginWithGoogle(code)` - 使用授权码登录
- 路由守卫自动重定向未登录用户到 `/login`

### 数据库 Schema

**User 表扩展字段**：
```sql
-- OAuth 相关字段
auth_provider VARCHAR(20) DEFAULT 'local'  -- local, google, github等
google_id VARCHAR(255) UNIQUE              -- Google唯一标识
avatar_url VARCHAR(500)                     -- 用户头像URL
```

## 常见问题

### Q1: 提示 "谷歌登录未配置"

**原因**：缺少 `GOOGLE_CLIENT_ID` 或 `GOOGLE_CLIENT_SECRET`

**解决**：
1. 检查 `.env` 文件是否存在
2. 确认环境变量已正确设置
3. 重启后端服务

### Q2: 回调失败，报 "授权码验证失败"

**原因**：`GOOGLE_REDIRECT_URI` 配置错误

**解决**：
1. 确保 `.env` 中的 `GOOGLE_REDIRECT_URI` 与 Google Cloud Console 中配置的一致
2. 检查 URL 协议（http/https）和端口是否正确
3. 开发环境使用 `http://localhost:8001/api/auth/google/callback`

### Q3: 用户信息不完整

**原因**：OAuth scope 权限不足

**解决**：确认授权 scope 包含 `openid email profile`（已在代码中配置）

### Q4: 数据库错误 "column not found"

**原因**：未执行数据库迁移

**解决**：
```bash
# SQLite
sqlite3 kode.db < migrations/add_oauth_fields.sql

# 或重新创建数据库（开发环境）
rm kode.db
python -m kode.web.main
```

## 生产环境配置

### 1. 更新重定向 URI

在 Google Cloud Console 中添加生产环境的回调 URL：
```
https://yourdomain.com/api/auth/google/callback
```

### 2. 更新环境变量

```env
GOOGLE_REDIRECT_URI=https://yourdomain.com/api/auth/google/callback
SECRET_KEY=<strong-random-production-key>
```

### 3. 使用 HTTPS

谷歌 OAuth2 要求生产环境必须使用 HTTPS。

### 4. 配置域名验证

在 Google Cloud Console 中：
1. 进入 "OAuth 同意屏幕"
2. 添加授权域名
3. 验证域名所有权

## 扩展功能

### 添加其他 OAuth 提供商

参考 `kode/core/oauth.py` 和 `kode/web/api/auth.py`：
1. 在 `oauth.py` 中注册新的 OAuth 客户端（如 GitHub）
2. 在 `auth.py` 中添加对应的回调端点
3. 在 User 模型中添加 `github_id` 字段
4. 前端添加登录按钮

### 用户头像显示

User 模型已包含 `avatar_url` 字段，可在前端显示：
```typescript
const user = authStore.currentUser
if (user.avatar_url) {
  // 显示头像
}
```

## 参考资料

- [Google OAuth2 文档](https://developers.google.com/identity/protocols/oauth2)
- [Authlib 文档](https://docs.authlib.org/)
- [FastAPI OAuth2 示例](https://fastapi.tiangolo.com/advanced/security/oauth2-scopes/)
