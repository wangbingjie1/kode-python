# 关键安全问题修复清单

## 🔴 上线前必须修复（8个问题）

### 1. CORS 配置过度开放
**文件**: `kode/web/main.py:27-33`
**优先级**: CRITICAL
**修复难度**: ⭐ 非常简单

更改:
```python
# 从
allow_origins=["*"],

# 改为
allow_origins=["http://localhost:3000"],  # 生产环境改为实际域名
```

### 2. 密码哈希算法不安全
**文件**: `kode/core/security.py:20-29`
**优先级**: CRITICAL
**修复难度**: ⭐⭐ 简单

需要安装 passlib:
```bash
poetry add passlib[bcrypt]
```

替换整个 hash_password 和 verify_password 函数为 bcrypt 实现。

### 3. JWT 密钥硬编码默认值
**文件**: `kode/core/security.py:14`
**优先级**: CRITICAL
**修复难度**: ⭐ 非常简单

更改:
```python
# 从
SECRET_KEY = os.getenv("SECRET_KEY", "kode-secret-key-change-in-production")

# 改为
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable must be set")
```

### 4. 数据库密码以纯文本存储
**文件**: `kode/models/database_connection.py`
**优先级**: HIGH
**修复难度**: ⭐⭐⭐ 中等

需要:
- 添加加密/解密函数
- 创建迁移脚本加密现有密码
- 修改 to_dict() 避免返回密码

### 5. JWT 令牌通过 URL 参数传输（Google OAuth）
**文件**: `kode/web/api/auth.py:339`
**优先级**: HIGH
**修复难度**: ⭐⭐ 简单

改用 HTTP-only cookie，见报告中的建议代码。

### 6. SSE 端点令牌通过 URL 参数
**文件**: `kode/web/api/sse.py:29`
**优先级**: HIGH
**修复难度**: ⭐⭐⭐ 中等

改用 HTTP-only cookie 或 WebSocket。

### 7. 缺少管理员权限检查
**文件**: `kode/web/api/billing.py:48-62, 84-109`
**优先级**: HIGH
**修复难度**: ⭐⭐ 简单

添加 is_admin 字段到 User 模型，添加权限检查中间件。

### 8. 敏感错误信息泄露
**文件**: `kode/web/api/auth.py:320-325` （及其他地方）
**优先级**: HIGH
**修复难度**: ⭐⭐ 简单

替换所有返回详细异常的地方为通用错误消息，记录详情到日志。

---

## 🟠 第一版本后修复（9个问题）

### 9. 缺少速率限制
**优先级**: MEDIUM
**修复难度**: ⭐⭐ 简单
```bash
poetry add slowapi
```

### 10. SQL 查询执行权限不足
**文件**: `kode/web/api/database.py:495-533`
**优先级**: MEDIUM
**修复难度**: ⭐⭐ 简单

添加危险 SQL 检查函数。

### 11. Bash 命令执行风险
**文件**: `kode/tools/bash_tool.py`
**优先级**: MEDIUM
**修复难度**: ⭐⭐⭐ 中等

实现命令白名单或避免使用 shell=True。

### 12. 默认用户硬编码密码
**文件**: `kode/web/main.py:138-143`
**优先级**: MEDIUM
**修复难度**: ⭐ 非常简单

使用随机生成的密码或在生产环境禁用。

### 13. 数据库连接通过日志泄露
**文件**: `kode/services/database_manager.py`
**优先级**: MEDIUM
**修复难度**: ⭐⭐ 简单

添加密码脱敏函数。

### 14. Stripe Webhook 签名验证不完整
**文件**: `kode/web/api/billing.py:292-338`
**优先级**: MEDIUM
**修复难度**: ⭐⭐ 简单

显式验证 webhook 签名。

### 15. 缺少 HTTPS 强制和安全头
**文件**: `kode/web/main.py`
**优先级**: MEDIUM
**修复难度**: ⭐⭐ 简单

添加中间件添加安全头。

### 16. OAuth2 Redirect URI 验证不足
**文件**: `kode/web/api/auth.py:185-208, 211-341`
**优先级**: MEDIUM
**修复难度**: ⭐⭐ 简单

验证 REDIRECT_URI。

### 17. 缺少审计日志
**优先级**: LOW
**修复难度**: ⭐⭐⭐ 中等

创建审计日志系统，记录敏感操作。

---

## 修复顺序建议

1. **第一步（1 小时）**: 修复 #1, #2, #3, #7, #8, #12
   - 这些可以快速修复，影响最大

2. **第二步（2-3 小时）**: 修复 #4, #5, #6, #10, #15
   - 这些需要一些代码改动

3. **第三步（1-2 小时）**: 修复 #9, #13, #14, #16
   - 这些相对简单

4. **第四步（3-4 小时）**: 修复 #11, #17
   - 这些需要更多思考和测试

总计: 约 8-10 小时

---

## 验证清单

- [ ] 运行 HTTPS 扫描器（如 ssllabs.com）检查安全头
- [ ] 运行 OWASP ZAP 或 Burp Suite 进行渗透测试
- [ ] 检查所有日志不包含敏感信息
- [ ] 验证所有认证端点的响应不泄露信息
- [ ] 检查数据库中没有纯文本密码
- [ ] 运行代码安全扫描（如 semgrep）

