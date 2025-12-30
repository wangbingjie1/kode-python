# 🔄 重启后端服务

## 问题诊断

后端返回 500 错误是因为 Pydantic 序列化问题。

**根本原因**: 数据库返回的 `created_at` 是 `datetime` 对象，但原来的代码期望字符串。

**已修复**: 添加了 `@field_serializer` 装饰器来自动转换 datetime → ISO 字符串。

---

## 🚀 立即重启后端

### 步骤 1: 停止后端

在运行 `python run.py` 的终端按 **Ctrl+C**

### 步骤 2: 重新启动

```bash
python run.py
```

### 步骤 3: 验证启动成功

看到以下日志说明启动成功：
```
INFO:     Uvicorn running on http://0.0.0.0:8001
INFO:     Application startup complete.
```

---

## ✅ 验证修复

重启后，在浏览器中：

1. **刷新页面**（Ctrl+Shift+R 硬刷新）
2. 进入"数据库管理" → "本体管理"
3. 选择"yanfa"连接
4. 点击"版本管理"标签

**预期结果**:
- ✅ 显示版本列表（1 个版本）
- ✅ 版本卡片显示完整信息
- ✅ 控制台日志：
  ```
  [OntologyViewer] 开始加载版本列表: yanfa
  [OntologyViewer] 版本列表响应: {total: 1, versions: [...]}
  [OntologyViewer] 加载成功，版本数: 1
  ```

---

## 🔍 如果还有问题

### 检查后端日志

在后端控制台查看是否有错误堆栈。

### 手动测试 API

```bash
# 获取 Token（替换你的密码）
curl -X POST "http://localhost:8001/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "694623326@qq.com", "password": "YOUR_PASSWORD"}'

# 使用 Token 测试版本 API
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
      "version_number": 1,
      "created_at": "2025-12-29T14:47:33",
      ...
    }
  ]
}
```

---

## 📝 已修改的文件

1. **kode/web/api/ontology.py**
   - 添加 `field_serializer` 装饰器
   - 将 `from_orm` 替换为 `model_validate`（Pydantic V2 新 API）

2. **web-frontend/src/components/OntologyViewer.vue**
   - 添加详细的 console.log 日志
   - 增强错误处理

3. **web-frontend/src/services/api.ts**
   - 添加完整的版本管理 API 函数

---

## 💡 提示

如果重启后仍然失败，请：

1. 检查后端控制台的完整错误堆栈
2. 运行浏览器诊断脚本（见 DEBUG_VERSION_LOADING.md）
3. 将错误信息发送给我

重启后应该就能正常工作了！🎉
