# Kode 后端安全审计报告

**审计时间**: 2025-11-07
**审计范围**: API 端点、认证系统、数据库工具、敏感数据处理
**严重程度**: 包含多个 HIGH 和 CRITICAL 级别问题

---

## 发现的安全问题

### 1. CORS 配置过度开放 [CRITICAL]

**文件**: `/home/user/kode-python/kode/web/main.py`
**行号**: 27-33
**严重程度**: CRITICAL

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Configure based on environment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**问题**: 
- 允许任何源访问，加上 `allow_credentials=True`，意味着任何网站都可以代表用户发起 API 请求
- 允许所有 HTTP 方法和所有自定义头，扩大了攻击面

**风险**: CSRF 攻击、未授权的数据访问、API 滥用

**建议**: 
```python
allow_origins=["http://localhost:3000"]  # 仅允许前端域名
allow_methods=["GET", "POST", "PUT", "DELETE"]  # 显式列出需要的方法
allow_headers=["content-type", "authorization"]  # 显式列出需要的头
allow_credentials=False  # 如果跨域请求不需要凭证，设置为False
```

---

### 2. 密码哈希算法不安全 [CRITICAL]

**文件**: `/home/user/kode-python/kode/core/security.py`
**行号**: 20-29
**严重程度**: CRITICAL

```python
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码（使用SHA256）"""
    return hash_password(plain_password) == hashed_password

def hash_password(password: str) -> str:
    """加密密码（使用SHA256 + salt）"""
    salted_password = f"{password}{SECRET_KEY}"
    return hashlib.sha256(salted_password.encode('utf-8')).hexdigest()
```

**问题**:
- SHA256 不是密码哈希函数，设计用于快速计算
- 盐值（SECRET_KEY）固定，降低了防彩虹表的能力
- 没有防暴力破解的机制（如自适应成本因子）
- SHA256 速度太快，容易被 GPU/ASIC 攻击破解

**风险**: 数据库泄露后，密码可被快速暴力破解

**建议**: 使用 bcrypt 或 argon2
```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
```

---

### 3. JWT 密钥硬编码默认值 [CRITICAL]

**文件**: `/home/user/kode-python/kode/core/security.py`
**行号**: 14
**严重程度**: CRITICAL

```python
SECRET_KEY = os.getenv("SECRET_KEY", "kode-secret-key-change-in-production")
```

**问题**:
- 有默认值意味着如果环境变量未设置，使用已知的密钥
- 所有使用此默认值的生产实例都使用相同的密钥
- 任何人都可以伪造 JWT 令牌

**风险**: 完全绕过身份认证

**建议**:
```python
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable must be set")
```

---

### 4. 数据库密码以纯文本存储 [HIGH]

**文件**: `/home/user/kode-python/kode/models/database_connection.py`
**行号**: 26-27
**严重程度**: HIGH

```python
# Encrypted password storage - should use encryption in production
password = Column(Text, nullable=False)
```

**问题**:
- 注释明确说"应该使用加密"，但没有实现
- 任何能访问数据库的人都能读取用户的数据库凭证
- 连接字符串中的密码通过 API 返回时需要小心处理

**风险**: 用户数据库凭证泄露，攻击者可访问用户的数据库

**建议**: 使用加密库如 cryptography
```python
from cryptography.fernet import Fernet

cipher_suite = Fernet(os.getenv("ENCRYPTION_KEY").encode())

def store_password(password: str) -> str:
    return cipher_suite.encrypt(password.encode()).decode()

def retrieve_password(encrypted_password: str) -> str:
    return cipher_suite.decrypt(encrypted_password.encode()).decode()
```

---

### 5. JWT 令牌通过 URL 参数传输 [HIGH]

**文件**: `/home/user/kode-python/kode/web/api/auth.py`
**行号**: 339
**严重程度**: HIGH

```python
frontend_url = f"http://localhost:3000/login?google_success=true&access_token={jwt_access_token}&refresh_token={jwt_refresh_token}"
return RedirectResponse(url=frontend_url)
```

**问题**:
- JWT 令牌在 URL 中以明文传输
- 令牌会被记录在浏览器历史、服务器日志、中间代理日志中
- 令牌可能通过 Referer 头泄露给第三方网站

**风险**: 令牌泄露、会话劫持

**建议**: 使用 HTTP-only cookie
```python
from fastapi.responses import RedirectResponse

response = RedirectResponse(url="http://localhost:3000/login?google_success=true")
response.set_cookie(
    key="access_token",
    value=jwt_access_token,
    httponly=True,
    secure=True,  # HTTPS only
    samesite="lax"
)
response.set_cookie(
    key="refresh_token",
    value=jwt_refresh_token,
    httponly=True,
    secure=True,
    samesite="lax"
)
return response
```

---

### 6. SSE 端点令牌通过 URL 参数 [HIGH]

**文件**: `/home/user/kode-python/kode/web/api/sse.py`
**行号**: 29, 168-171
**严重程度**: HIGH

```python
async def get_user_from_token_or_header(
    token: Optional[str] = Query(None, description="JWT access token (for SSE)"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """从token参数或Authorization头获取当前用户"""
    if token:
        payload = verify_token(token, token_type="access")
```

**问题**:
- EventSource API 不支持自定义头，所以设计者通过 URL 参数传输令牌
- 令牌在 URL 中以明文传输，有与问题 #5 相同的风险

**风险**: 令牌泄露

**建议**: 
- 使用 HTTP-only cookie + 自定义 XMLHttpRequest/Fetch 而不是 EventSource
- 或使用预签名 URL（带有时间限制）
- 或使用 WebSocket 代替 SSE（支持自定义认证）

---

### 7. 缺少管理员权限检查 [HIGH]

**文件**: `/home/user/kode-python/kode/web/api/billing.py`
**行号**: 48-62, 84-109
**严重程度**: HIGH

```python
@router.post("/plans", response_model=PlanResponse, status_code=status.HTTP_201_CREATED)
async def create_plan(
    plan: PlanCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建新套餐（管理员功能）"""
    # TODO: 添加管理员权限检查
    new_plan = Plan(**plan.dict())
```

**问题**:
- 没有检查用户是否是管理员
- 任何认证用户都可以创建/修改计费套餐
- 没有审计日志

**风险**: 非管理员可以修改定价、配额等关键业务设置

**建议**:
```python
def get_admin_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

@router.post("/plans", response_model=PlanResponse)
async def create_plan(
    plan: PlanCreate,
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    # 现在可以安全地创建计划
    logger.info(f"Plan created by admin {admin_user.id}: {plan.name}")
```

---

### 8. 敏感错误信息泄露 [HIGH]

**文件**: `/home/user/kode-python/kode/web/api/auth.py`
**行号**: 320-325
**严重程度**: HIGH

```python
except Exception as e:
    await db.rollback()
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"创建用户失败: {str(e)}",
    )
```

**问题**:
- 异常详情在 HTTP 响应中返回
- 可能泄露数据库结构、内部 API、系统路径等信息
- 攻击者可利用这些信息进行更精细的攻击

**风险**: 信息泄露

**建议**:
```python
except Exception as e:
    logger.error(f"User creation error: {str(e)}", exc_info=True)
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="用户创建失败，请稍后重试"  # 通用错误消息
    )
```

---

### 9. 缺少速率限制 [MEDIUM]

**文件**: 整个 API
**严重程度**: MEDIUM

**问题**:
- 没有对 API 端点的速率限制
- 容易被暴力破解、DOS 攻击、API 滥用

**风险**: DOS 攻击、暴力破解认证、API 资源耗尽

**建议**:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@router.post("/login")
@limiter.limit("5/minute")  # 每分钟最多 5 次登录尝试
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    # ...
```

---

### 10. SQL 查询执行权限不足 [MEDIUM]

**文件**: `/home/user/kode-python/kode/web/api/database.py`
**行号**: 495-533
**严重程度**: MEDIUM

```python
@router.post("/connections/{name}/query", response_model=Dict[str, Any])
async def execute_query(name: str, request_data: Dict[str, Any]):
    """Execute SQL query on a database connection"""
    sql = request_data.get("sql", "")
    # ... 直接执行任意 SQL
```

**问题**:
- 允许执行任意 SQL（包括 DROP TABLE、TRUNCATE、ALTER 等危险操作）
- 没有限制 SQL 类型或操作范围
- 虽然有参数化查询防止 SQL 注入，但缺乏业务逻辑控制

**风险**: 数据丢失、数据修改、数据库损坏

**建议**:
```python
def _is_dangerous_query(sql: str) -> bool:
    """检查查询是否包含危险操作"""
    dangerous_keywords = ["DROP", "TRUNCATE", "DELETE", "ALTER", "CREATE", "GRANT"]
    sql_upper = sql.strip().upper()
    return any(sql_upper.startswith(kw) for kw in dangerous_keywords)

@router.post("/connections/{name}/query")
async def execute_query(name: str, request_data: Dict[str, Any]):
    sql = request_data.get("sql", "")
    
    if _is_dangerous_query(sql):
        raise HTTPException(
            status_code=403,
            detail="危险的 SQL 操作不被允许"
        )
    # ... 继续执行
```

---

### 11. Bash 命令执行风险 [MEDIUM]

**文件**: `/home/user/kode-python/kode/tools/bash_tool.py`
**行号**: 43-58
**严重程度**: MEDIUM

```python
result = subprocess.run(
    command,
    shell=True,
    capture_output=True,
    text=True,
    timeout=timeout,
    cwd=cwd,
)
```

**问题**:
- 使用 `shell=True` 允许 shell 注入
- 虽然有权限检查，但仍然很危险
- 命令可能包含管道、重定向、命令替换等

**风险**: 命令注入、RCE

**建议**:
```python
import shlex

# 如果必须支持 shell 功能，至少进行严格验证
# 更好的做法是避免使用 shell=True，改用 shell 白名单

# 方案 1: 使用白名单
ALLOWED_COMMANDS = ["git", "npm", "docker", "python", "node"]

def _is_command_allowed(command: str) -> bool:
    cmd = command.strip().split()[0]
    return cmd in ALLOWED_COMMANDS

# 方案 2: 避免 shell=True，使用参数列表
result = subprocess.run(
    shlex.split(command),  # 安全的解析
    capture_output=True,
    text=True,
    timeout=timeout,
    cwd=cwd,
)
```

---

### 12. 默认用户硬编码密码 [MEDIUM]

**文件**: `/home/user/kode-python/kode/web/main.py`
**行号**: 138-143
**严重程度**: MEDIUM

```python
user = User(
    id="default",
    username="default",
    email="default@kode.local",
    hashed_password="default",  # Placeholder password for demo
)
```

**问题**:
- 使用 "default" 作为密码并使用不安全的哈希
- 如果生产环境中运行此代码，默认用户可被轻易破解

**风险**: 未授权访问

**建议**:
```python
# 生产环境不应创建默认用户，或使用强随机密码
import secrets

if not user:
    user = User(
        id="default",
        username="default",
        email="default@kode.local",
        hashed_password=hash_password(secrets.token_urlsafe(32)),
    )
    logger.warning("Default user created with random password. DO NOT USE IN PRODUCTION.")
```

---

### 13. 数据库连接通过日志泄露 [MEDIUM]

**文件**: `/home/user/kode-python/kode/services/database_manager.py`
**行号**: 55-111
**严重程度**: MEDIUM

```python
def get_connection_url(self, async_mode: bool = False) -> str:
    """Generate SQLAlchemy connection URL."""
    encoded_password = quote_plus(self.password)
    
    if self.db_type == "postgresql":
        url = (
            f"postgresql+{driver}://{self.username}:{encoded_password}"
            f"@{self.host}:{self.port}/{self.database}"
        )
```

**问题**:
- 连接字符串包含密码
- 如果这个 URL 被记录到日志，密码会被泄露
- SQLAlchemy echo=True 时会打印完整的连接字符串

**风险**: 密码泄露

**建议**:
```python
# 在任何地方使用连接字符串前，移除密码
import re

def redact_password(connection_string: str) -> str:
    """移除连接字符串中的密码用于日志"""
    return re.sub(r'(:\w+@)', ':***@', connection_string)

# 日志时使用 redacted 版本
logger.debug(f"Connecting to: {redact_password(url)}")
```

---

### 14. Stripe Webhook 签名验证不完整 [MEDIUM]

**文件**: `/home/user/kode-python/kode/web/api/billing.py`
**行号**: 292-338
**严重程度**: MEDIUM

```python
@router.post("/stripe/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="stripe-signature"),
    db: AsyncSession = Depends(get_db),
):
    """处理 Stripe Webhook 事件"""
    # ...
    if not stripe_signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Stripe signature",
        )
```

**问题**:
- 虽然检查了 header 是否存在，但代码没有看到实际的签名验证逻辑
- 假设 stripe_service.handle_webhook() 进行了验证，但应该在这里显式验证

**风险**: 伪造 webhook 事件可导致计费混乱

**建议**:
```python
@router.post("/stripe/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="stripe-signature"),
):
    config = ConfigManager()
    webhook_secret = config.get("stripe.webhook_secret")
    
    payload = await request.body()
    
    try:
        # 显式验证签名
        import stripe
        event = stripe.Webhook.construct_event(
            payload,
            stripe_signature,
            webhook_secret
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # 处理事件
```

---

### 15. 缺少 HTTPS 强制和安全头 [MEDIUM]

**文件**: `/home/user/kode-python/kode/web/main.py`
**严重程度**: MEDIUM

**问题**:
- 没有看到 HTTPS 重定向
- 没有看到 HSTS（Strict-Transport-Security）头
- 没有看到其他安全头如 X-Frame-Options、X-Content-Type-Options 等

**风险**: 中间人攻击、点击劫持、MIME 类型嗅探

**建议**:
```python
from fastapi.middleware.trustedhost import TrustedHostMiddleware

app.add_middleware(TrustedHostMiddleware, allowed_hosts=["example.com"])

# 添加安全头中间件
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response
```

---

### 16. OAuth2 Redirect URI 验证不足 [MEDIUM]

**文件**: `/home/user/kode-python/kode/web/api/auth.py`
**行号**: 185-208, 211-341
**严重程度**: MEDIUM

```python
@router.get("/google/login")
async def google_login():
    """发起谷歌OAuth2登录"""
    google_auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={GOOGLE_CLIENT_ID}&"
        f"redirect_uri={GOOGLE_REDIRECT_URI}&"
        # ...
    )
```

**问题**:
- 没有验证 GOOGLE_REDIRECT_URI 是否与 Google 应用注册的 URI 匹配
- 没有防止 Open Redirect 攻击
- REDIRECT_URI 硬编码为 localhost:3000

**风险**: Open redirect 攻击、CSRF

**建议**:
```python
# 在配置中定义允许的重定向 URI
ALLOWED_REDIRECT_URIS = {
    "http://localhost:3000",
    "https://example.com",
}

@router.get("/google/login")
async def google_login(redirect_uri: str = None):
    # 验证重定向 URI
    if redirect_uri and redirect_uri not in ALLOWED_REDIRECT_URIS:
        raise HTTPException(
            status_code=400,
            detail="Invalid redirect URI"
        )
    # ...
```

---

### 17. 缺少审计日志 [LOW]

**文件**: 整个应用
**严重程度**: LOW

**问题**:
- 关键操作（删除数据、修改配置、用户认证失败等）缺少审计日志
- 难以追踪谁做了什么以及何时做的

**风险**: 无法检测和调查安全事件

**建议**:
```python
class AuditLog:
    """审计日志模型"""
    user_id: str
    action: str
    resource_type: str
    resource_id: str
    changes: dict
    timestamp: datetime
    ip_address: str

# 在关键操作中记录
logger.audit(
    user_id=current_user.id,
    action="delete_conversation",
    resource_id=conversation_id,
    ip_address=request.client.host
)
```

---

## 总结

### 按严重程度统计

| 级别 | 数量 | 问题 |
|------|------|------|
| CRITICAL | 3 | CORS配置、密码哈希、JWT密钥 |
| HIGH | 5 | 数据库密码存储、令牌通过URL、权限检查、错误泄露、SQL执行权限 |
| MEDIUM | 8 | 速率限制、Bash执行、默认密码、日志泄露、Webhook验证、安全头、OAuth验证、缺少审计 |
| LOW | 1 | 审计日志 |

### 立即修复（上线前必须）

1. 修复 CORS 配置 - 只允许前端域名
2. 实现安全的密码哈希（bcrypt/argon2）
3. 移除 JWT 密钥硬编码默认值
4. 加密数据库密码存储
5. 移除 URL 中的令牌传输，使用 HTTP-only cookie
6. 添加管理员权限检查
7. 避免在错误消息中泄露敏感信息
8. 添加 HTTPS 强制和安全头

### 建议在第一个版本之后修复

1. 实现速率限制
2. 限制 SQL 查询权限
3. 改进 Bash 命令执行的安全性
4. 完整的 Stripe Webhook 签名验证
5. 全面的审计日志系统
