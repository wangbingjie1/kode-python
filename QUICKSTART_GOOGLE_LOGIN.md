# 谷歌登录快速启动指南

## 已完成的工作

谷歌 OAuth2 登录功能已经完全集成到项目中，包括：

### 后端实现 ✓
- [x] 安装依赖：`authlib`、`httpx`
- [x] 扩展 User 模型：添加 `google_id`、`avatar_url`、`auth_provider` 字段
- [x] 实现 OAuth2 配置模块 ([kode/core/oauth.py](kode/core/oauth.py))
- [x] 实现谷歌登录端点 ([kode/web/api/auth.py](kode/web/api/auth.py:184-321))
  - `GET /api/auth/google/login` - 获取授权 URL
  - `POST /api/auth/google/callback` - 处理回调，返回 JWT
- [x] 数据库迁移完成（OAuth 字段已添加）

### 前端实现 ✓
- [x] 更新认证 Store ([web-frontend/src/stores/auth.ts](web-frontend/src/stores/auth.ts))
  - `getGoogleAuthUrl()` - 获取授权 URL
  - `loginWithGoogle(code)` - 使用授权码登录
- [x] 登录页面添加谷歌登录按钮 ([web-frontend/src/views/LoginView.vue](web-frontend/src/views/LoginView.vue:56-76))
- [x] 路由守卫已配置（自动重定向未登录用户）

### 配置文档 ✓
- [x] 详细配置指南 ([GOOGLE_LOGIN_SETUP.md](GOOGLE_LOGIN_SETUP.md))
- [x] 环境变量模板 ([.env.example](.env.example:85-98))
- [x] 数据库迁移脚本 ([migrations/migrate_oauth.py](migrations/migrate_oauth.py))

## 现在就开始使用

### 第一步：配置谷歌 OAuth2 凭据

1. **访问 Google Cloud Console**
   - 网址：https://console.cloud.google.com/
   - 创建项目或选择现有项目

2. **创建 OAuth 2.0 凭据**
   - 导航：API和服务 > 凭据
   - 点击：创建凭据 > OAuth 客户端 ID
   - 应用类型：Web 应用
   - 授权重定向 URI：`http://localhost:8001/api/auth/google/callback`

3. **记录凭据**
   - Client ID（客户端ID）
   - Client Secret（客户端密钥）

### 第二步：配置环境变量

编辑 `.env` 文件（如果没有则复制 `.env.example`）：

```bash
# 复制模板
cp .env.example .env
```

添加以下配置到 `.env`：

```env
# JWT 密钥（必须修改为强密码）
SECRET_KEY=your-super-secret-key-change-this-in-production

# 谷歌 OAuth2 配置
GOOGLE_CLIENT_ID=你的客户端ID.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=你的客户端密钥
GOOGLE_REDIRECT_URI=http://localhost:8001/api/auth/google/callback
```

### 第三步：启动服务

**方式一：使用启动脚本（推荐）**

```bash
# Windows
.\start-backend.ps1

# 前端（另一个终端）
cd web-frontend
npm run dev
```

**方式二：手动启动**

```bash
# 后端（端口 8001）
python run.py

# 前端（另一个终端，端口 3000）
cd web-frontend
npm run dev
```

### 第四步：测试登录

1. 打开浏览器访问：http://localhost:3000/login
2. 点击 "使用谷歌账号登录" 按钮
3. 跳转到谷歌授权页面
4. 授权后自动返回应用并登录成功

## 技术特性

### 智能用户关联
- **新用户**：自动创建账户，使用谷歌信息填充
- **已有用户**：通过邮箱关联现有账户到谷歌登录
- **混合登录**：支持传统密码登录和谷歌登录共存

### 安全特性
- JWT 令牌认证（access token + refresh token）
- 自动 token 刷新机制
- 路由守卫保护需要认证的页面
- OAuth2 标准流程（Authorization Code Grant）

### 用户体验
- 一键登录，无需记住密码
- 自动获取谷歌头像
- 登录状态持久化（localStorage）
- 优雅的错误提示

## 目录结构

```
kode-python/
├── kode/
│   ├── core/
│   │   ├── oauth.py              # OAuth2 配置
│   │   └── security.py           # JWT token 管理
│   ├── models/
│   │   └── user.py              # User 模型（含 OAuth 字段）
│   ├── web/
│   │   └── api/
│   │       └── auth.py          # 认证端点
│   └── schemas/
│       └── auth.py              # Pydantic schemas
├── web-frontend/src/
│   ├── stores/
│   │   └── auth.ts              # 认证状态管理
│   ├── views/
│   │   └── LoginView.vue        # 登录页面
│   └── router/
│       └── index.ts             # 路由守卫
├── migrations/
│   ├── migrate_oauth.py         # Python 迁移脚本 ✓
│   └── add_oauth_fields.sql     # SQL 迁移脚本
├── .env.example                 # 环境变量模板
├── GOOGLE_LOGIN_SETUP.md       # 详细配置指南
└── QUICKSTART_GOOGLE_LOGIN.md  # 本文件
```

## API 端点

### 获取谷歌授权 URL
```http
GET /api/auth/google/login
```

**响应示例**：
```json
{
  "auth_url": "https://accounts.google.com/o/oauth2/v2/auth?client_id=..."
}
```

### 谷歌登录回调
```http
POST /api/auth/google/callback
Content-Type: application/json

{
  "code": "4/0AfJ..."
}
```

**响应示例**：
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "bearer"
}
```

### 获取用户信息
```http
GET /api/auth/profile
Authorization: Bearer {access_token}
```

**响应示例**：
```json
{
  "id": "uuid",
  "username": "张三",
  "email": "zhangsan@gmail.com",
  "is_active": true,
  "auth_provider": "google",
  "avatar_url": "https://lh3.googleusercontent.com/...",
  "created_at": "2025-01-06T10:00:00"
}
```

## 常见问题

### Q: 提示 "谷歌登录未配置"
**A**: 检查 `.env` 文件是否包含 `GOOGLE_CLIENT_ID` 和 `GOOGLE_CLIENT_SECRET`，重启后端服务。

### Q: 回调失败 "授权码验证失败"
**A**: 确认 `GOOGLE_REDIRECT_URI` 与 Google Cloud Console 中配置的完全一致。

### Q: 用户名冲突
**A**: 系统会自动使用谷歌提供的名称，如果冲突会添加后缀。

### Q: 如何切换登录方式？
**A**:
- 谷歌用户可以通过邮箱设置密码，即可使用密码登录
- 传统用户首次用谷歌登录时会自动关联账户（通过邮箱匹配）

## 下一步

等你给我谷歌 OAuth2 凭据后：
1. 我会帮你配置到 `.env` 文件
2. 启动服务进行测试
3. 验证完整的登录流程

**当前状态**：✅ 所有代码已完成，等待凭据配置

详细配置步骤请参考：[GOOGLE_LOGIN_SETUP.md](GOOGLE_LOGIN_SETUP.md)
