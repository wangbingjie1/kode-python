# 版本加载失败问题诊断清单

## 问题现象
前端显示"加载版本列表失败"

## 已验证正常的部分 ✅
1. ✅ 后端 API 路由已正确注册
2. ✅ 数据库中有版本数据（yanfa 连接有 v1 版本）
3. ✅ Python 测试脚本能正常读取版本数据

## 需要你检查的内容

### 1. 浏览器控制台日志

打开浏览器开发者工具（F12），刷新页面后：

1. **切换到 Console 标签**
   - 查找带 `[OntologyViewer]` 前缀的日志
   - 应该能看到类似这样的输出：
     ```
     [OntologyViewer] 选择本体: yanfa
     [OntologyViewer] 准备加载版本列表...
     [OntologyViewer] 开始加载版本列表: yanfa
     ```
   - 记录具体的错误信息

2. **切换到 Network 标签**
   - 过滤：只显示 XHR/Fetch 请求
   - 查找路径包含 `/ontology/versions/` 的请求
   - 点击该请求，查看：
     - **Status**: 应该是 200（如果是 401/403/404/500 等，记录下来）
     - **Response**: 查看返回的 JSON 数据
     - **Headers**: 查看 `Authorization` 头是否存在

### 2. 认证状态检查

在浏览器控制台运行：

```javascript
// 检查 Token
console.log('Access Token:', localStorage.getItem('access_token'))

// 检查用户信息
console.log('User Info:', JSON.parse(localStorage.getItem('userInfo') || '{}'))
```

**预期结果**:
- `access_token` 应该是一个以 `eyJ` 开头的长字符串
- `userInfo` 应该包含 `id`, `email` 等字段

如果 token 为空或 userInfo 为空 → **需要重新登录**

### 3. API 请求测试

在浏览器控制台手动调用 API：

```javascript
// 导入 API 函数（需要在 Vue DevTools 中执行）
// 或者直接用 fetch 测试

fetch('/api/ontology/versions/yanfa?limit=10&offset=0', {
  headers: {
    'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
    'Content-Type': 'application/json'
  }
})
.then(res => res.json())
.then(data => console.log('版本列表:', data))
.catch(err => console.error('错误:', err))
```

**预期结果**:
```json
{
  "total": 1,
  "versions": [
    {
      "id": "...",
      "version_number": 1,
      "is_current": true,
      ...
    }
  ]
}
```

### 4. 常见错误及解决方案

#### 错误 A: 401 Unauthorized
**原因**: Token 过期或无效
**解决**:
```bash
# 退出登录
localStorage.clear()
# 刷新页面，重新登录
```

#### 错误 B: 404 Not Found
**原因**: API 路径不匹配
**检查**:
- 前端请求的路径是否为 `/ontology/versions/{connection_name}`
- 后端路由前缀是否为 `/api/ontology`

#### 错误 C: 500 Internal Server Error
**原因**: 后端代码错误
**检查**:
- 后端控制台的错误堆栈
- 数据库连接是否正常

#### 错误 D: CORS 错误
**原因**: 跨域请求被阻止
**特征**:
```
Access to fetch at '...' from origin '...' has been blocked by CORS policy
```
**解决**:
- 检查后端 `kode/web/main.py` 的 CORS 配置
- 确保 `http://localhost:3000` 在 allowed_origins 中

### 5. 手动 API 测试

使用 curl 或 Postman 测试（需要替换 YOUR_TOKEN）：

```bash
# 获取 Token（登录）
curl -X POST "http://localhost:8001/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "694623326@qq.com", "password": "your-password"}'

# 使用返回的 Token 测试版本 API
curl -X GET "http://localhost:8001/api/ontology/versions/yanfa?limit=10&offset=0" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**预期返回**:
```json
{
  "total": 1,
  "versions": [
    {
      "id": "...",
      "user_id": "14b611c2-3051-4674-bc0f-b5db43861f52",
      "connection_name": "yanfa",
      "version_number": 1,
      "is_current": true,
      ...
    }
  ]
}
```

### 6. 前端代码检查

确认以下文件的修改已生效：

```bash
# 检查 api.ts 是否有版本管理函数
grep -n "listOntologyVersions" web-frontend/src/services/api.ts

# 检查 OntologyViewer.vue 是否有 loadVersions 函数
grep -n "loadVersions" web-frontend/src/components/OntologyViewer.vue
```

如果找不到这些函数 → **需要重新拉取代码或检查文件是否保存**

### 7. 重启服务

有时缓存或热重载可能导致问题，尝试完全重启：

```bash
# 后端
Ctrl+C 停止
python run.py

# 前端
Ctrl+C 停止
cd web-frontend
npm run dev
```

然后硬刷新浏览器（Ctrl+Shift+R 或 Ctrl+F5）

---

## 问题反馈模板

请复制以下模板并填写信息：

```
### 浏览器控制台日志
```
[粘贴 Console 标签的输出]
```

### Network 请求详情
- 请求 URL:
- 状态码:
- Response:
```
[粘贴 Response 内容]
```

### Token 检查
- access_token 存在: [是/否]
- token 前缀: [前几个字符]

### 手动 API 测试结果
```
[粘贴 curl 或 fetch 测试结果]
```

### 其他观察
[任何其他相关信息]
```

---

## 快速诊断脚本

将以下代码粘贴到浏览器控制台：

```javascript
// 快速诊断脚本
(async function() {
  console.log('=== 版本加载诊断 ===')

  // 1. 检查 Token
  const token = localStorage.getItem('access_token')
  console.log('1. Token 存在:', !!token)
  if (token) {
    console.log('   Token 前缀:', token.substring(0, 20) + '...')
  }

  // 2. 检查用户信息
  const userInfo = localStorage.getItem('userInfo')
  console.log('2. 用户信息:', userInfo ? JSON.parse(userInfo) : null)

  // 3. 测试 API
  if (token) {
    try {
      console.log('3. 测试 API 请求...')
      const res = await fetch('/api/ontology/versions/yanfa?limit=10&offset=0', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      })

      console.log('   状态码:', res.status, res.statusText)

      if (res.ok) {
        const data = await res.json()
        console.log('   ✅ API 调用成功!')
        console.log('   版本数量:', data.total)
        console.log('   版本列表:', data.versions)
      } else {
        const error = await res.text()
        console.log('   ❌ API 调用失败:', error)
      }
    } catch (err) {
      console.log('   ❌ 请求错误:', err)
    }
  } else {
    console.log('   ⚠️  未登录，跳过 API 测试')
  }

  console.log('=== 诊断完成 ===')
})()
```

运行后将所有输出截图或复制给我。
