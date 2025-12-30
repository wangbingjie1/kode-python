# 本体版本管理功能测试清单

## 测试前准备

### 1. 启动服务

```bash
# 后端
python run.py

# 前端（另一个终端）
cd web-frontend
npm run dev
```

### 2. 确保有测试数据

- 至少有 1 个数据库连接
- 至少构建过 1 次本体（执行过 OntologyBuilder）

---

## 功能测试

### ✅ 测试 1: 查看版本列表

**步骤:**
1. 登录系统
2. 进入"数据库管理" -> "本体管理"
3. 在左侧选择一个本体连接
4. 点击"版本管理"标签页

**预期结果:**
- 显示所有历史版本（按版本号降序）
- 当前版本显示绿色边框 + "当前"徽章
- 每个版本卡片显示：
  - 版本号（v1, v2, ...）
  - 创建时间
  - 存储类型（数据库/文件）
  - 文件大小
  - 向量索引状态（待构建/构建中/已完成/失败）
  - 哈希值前 16 位

---

### ✅ 测试 2: 切换到历史版本

**步骤:**
1. 在版本列表中点击任意非当前版本

**预期结果:**
- 点击的版本卡片显示蓝色边框（选中状态）
- 本体数据自动加载该版本的内容
- 可在"概念"、"关系"、"关系图"标签页查看
- 右上角显示通知："版本切换成功，已切换到 vX"

---

### ✅ 测试 3: 回滚到历史版本

**步骤:**
1. 在版本列表中找到一个历史版本（非当前版本）
2. 点击"回滚"按钮
3. 在确认对话框中点击"确定"

**预期结果:**
- 显示通知："回滚成功，已回滚到 vX，新版本号: vY"
- 版本列表自动刷新
- 新增一个版本 vY（is_current = true）
- vY 的内容与 vX 完全相同（哈希值一致）
- 原来的当前版本不再显示"当前"徽章

**后端验证:**
```bash
# 检查数据库
sqlite3 kode.db "SELECT version_number, is_current, ontology_hash, change_summary FROM ontology_versions WHERE connection_name='xxx' ORDER BY version_number DESC LIMIT 5;"
```

---

### ✅ 测试 4: 删除历史版本

**步骤:**
1. 在版本列表中找到一个历史版本（非当前版本）
2. 点击"删除"按钮
3. 在确认对话框中点击"确定"

**预期结果:**
- 显示通知："删除成功，版本 vX 已删除"
- 版本列表自动刷新
- 该版本从列表中消失

**边界测试:**
- 尝试删除当前版本 → 应显示错误："不能删除当前活跃版本"

**后端验证:**
```bash
# 检查是软删除（status='archived'）
sqlite3 kode.db "SELECT version_number, status FROM ontology_versions WHERE connection_name='xxx' ORDER BY version_number DESC;"
```

---

### ✅ 测试 5: 重建向量索引

**步骤:**
1. 找到一个索引状态为"失败"或"待构建"的版本
2. 点击"重建索引"按钮

**预期结果:**
- 显示通知："索引重建任务已提交，向量索引将在后台重建"
- 2 秒后版本列表自动刷新
- 索引状态可能变为"构建中"或"已完成"

**手动触发失败状态（测试用）:**
```sql
-- 模拟索引失败
UPDATE ontology_versions
SET vector_index_status = 'failed',
    vector_index_error = '测试错误信息'
WHERE version_number = 1 AND connection_name = 'xxx';
```

---

### ✅ 测试 6: 版本去重

**步骤:**
1. 通过聊天触发本体更新："请重新构建本体"
2. 如果本体内容未变化，检查是否创建了新版本

**预期结果:**
- 如果本体内容未变化（哈希值相同）→ 不创建新版本，复用已有版本
- 后端日志显示："本体内容未变化，复用已有版本 vX"

---

### ✅ 测试 7: 大文件存储切换

**步骤:**
1. 创建一个小本体（< 100KB）
2. 检查 storage_type 字段
3. 创建一个大本体（> 100KB）
4. 检查 storage_type 字段

**预期结果:**
- 小本体: storage_type = 'db'，file_path = null
- 大本体: storage_type = 'file'，file_path = 'ontology_vX.json'

**验证文件存在:**
```bash
ls -lh "ontology_store/{user_id}/{connection_name}/versions/"
```

---

### ✅ 测试 8: 版本信息展示

**步骤:**
1. 查看版本列表中每个版本的详细信息

**预期结果:**
- 创建时间格式正确（YYYY-MM-DD HH:mm:ss）
- 文件大小显示友好格式（B, KB, MB, GB）
- 向量索引状态显示中文文本：
  - pending → "待构建"（橙色）
  - building → "构建中"（蓝色）
  - completed → "已完成"（绿色）
  - failed → "失败"（红色）
- 如果有索引错误，显示错误文本（红色）
- 如果有变更说明，显示在"变更说明"行

---

## API 测试

### 测试 9: 后端 API 端点

使用 curl 或 Postman 测试以下端点：

**9.1 列出版本**
```bash
curl -X GET "http://localhost:8001/api/ontology/versions/yanfa?limit=10&offset=0" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**9.2 获取当前版本**
```bash
curl -X GET "http://localhost:8001/api/ontology/versions/yanfa/current" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**9.3 获取指定版本**
```bash
curl -X GET "http://localhost:8001/api/ontology/versions/yanfa/3" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**9.4 回滚版本**
```bash
curl -X POST "http://localhost:8001/api/ontology/versions/yanfa/rollback" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"target_version_number": 2}'
```

**9.5 删除版本**
```bash
curl -X DELETE "http://localhost:8001/api/ontology/versions/yanfa/2" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**9.6 重建索引**
```bash
curl -X POST "http://localhost:8001/api/ontology/versions/yanfa/3/rebuild-index" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"force_rebuild": true}'
```

**9.7 查询索引状态**
```bash
curl -X GET "http://localhost:8001/api/ontology/versions/yanfa/3/index-status" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 性能测试

### 测试 10: 大量版本加载性能

**步骤:**
1. 创建 50+ 个版本（通过多次本体更新）
2. 打开版本管理标签页
3. 测量加载时间

**预期结果:**
- 加载时间 < 2 秒
- 滚动流畅，无卡顿
- 分页参数正确（limit=50）

---

### 测试 11: 大文件版本切换性能

**步骤:**
1. 创建一个大本体版本（> 5MB）
2. 在版本列表中切换查看

**预期结果:**
- 切换时间 < 3 秒
- 无明显卡顿
- 图表正常渲染

---

## 边界测试

### 测试 12: 权限隔离

**步骤:**
1. 用户 A 登录，创建本体版本
2. 用户 B 登录，尝试访问用户 A 的版本

**预期结果:**
- 用户 B 看不到用户 A 的版本
- API 返回 404 或空列表

---

### 测试 13: 并发创建版本

**步骤:**
1. 同时触发多次本体构建（例如多个聊天窗口）
2. 检查版本号是否连续且唯一

**预期结果:**
- 版本号连续递增
- 无版本号冲突
- 所有版本创建成功

---

### 测试 14: 删除当前版本保护

**步骤:**
1. 尝试删除当前活跃版本

**预期结果:**
- 前端按钮禁用或隐藏
- 后端返回 400 错误："不能删除当前活跃版本"

---

### 测试 15: 异常处理

**步骤:**
1. 断开网络连接
2. 尝试加载版本列表

**预期结果:**
- 显示友好错误提示
- 不崩溃

**步骤:**
1. 删除本体文件（手动删除 ontology_vX.json）
2. 尝试加载该版本

**预期结果:**
- 返回 500 错误或友好提示
- 前端显示错误通知

---

## UI/UX 测试

### 测试 16: 响应式布局

**步骤:**
1. 在不同屏幕尺寸下查看版本列表
   - 1920x1080
   - 1366x768
   - iPad (768x1024)
   - iPhone (375x667)

**预期结果:**
- 布局适配良好
- 按钮不重叠
- 文字可读

---

### 测试 17: 交互反馈

**步骤:**
1. 悬停在版本卡片上
2. 点击版本卡片
3. 点击操作按钮

**预期结果:**
- 悬停时显示蓝色边框和阴影
- 点击时显示选中状态（蓝色背景）
- 当前版本显示绿色样式
- 按钮 hover 时颜色变深

---

### 测试 18: 加载状态

**步骤:**
1. 点击版本管理标签页
2. 观察加载过程

**预期结果:**
- 显示"加载版本列表中..."提示
- 加载完成后显示版本列表
- 如果无版本，显示"暂无版本记录"

---

## 数据一致性测试

### 测试 19: 版本链完整性

**步骤:**
1. 创建多个版本 v1, v2, v3
2. 检查 parent_version_id 字段

**预期结果:**
- v1.parent_version_id = null
- v2.parent_version_id = v1.id
- v3.parent_version_id = v2.id
- 形成完整的版本链

**验证 SQL:**
```sql
SELECT
  version_number,
  id,
  parent_version_id,
  is_current
FROM ontology_versions
WHERE connection_name = 'yanfa'
ORDER BY version_number;
```

---

### 测试 20: 哈希一致性

**步骤:**
1. 加载版本 v2 的数据
2. 手动计算 SHA256 哈希
3. 与数据库中的 ontology_hash 对比

**验证命令:**
```bash
# 计算文件哈希
shasum -a 256 "ontology_store/{user_id}/{connection_name}/versions/v2/ontology_v2.json"

# 对比数据库
sqlite3 kode.db "SELECT ontology_hash FROM ontology_versions WHERE version_number=2 AND connection_name='yanfa';"
```

**预期结果:**
- 两个哈希值完全一致

---

## 已知问题 & Workarounds

### 问题 1: TypeScript 编译警告

**现象**: `npm run build` 出现 TS2705 等警告

**原因**: tsconfig.json 的 lib 配置不包含 ES2015

**影响**: 不影响运行，仅影响类型检查

**解决方案**: 更新 `web-frontend/tsconfig.json`:
```json
{
  "compilerOptions": {
    "lib": ["ES2015", "DOM", "DOM.Iterable"]
  }
}
```

---

## 测试通过标准

✅ 所有功能测试通过（测试 1-8）
✅ 所有 API 测试返回正确响应（测试 9）
✅ 性能测试满足要求（测试 10-11）
✅ 边界测试正确处理异常（测试 12-15）
✅ UI/UX 友好易用（测试 16-18）
✅ 数据一致性保证（测试 19-20）

---

## 测试报告模板

**测试日期**: YYYY-MM-DD
**测试人**: XXX
**版本**: vX.X.X

| 测试项 | 状态 | 备注 |
|--------|------|------|
| 测试 1: 查看版本列表 | ✅ / ❌ | |
| 测试 2: 切换到历史版本 | ✅ / ❌ | |
| 测试 3: 回滚到历史版本 | ✅ / ❌ | |
| 测试 4: 删除历史版本 | ✅ / ❌ | |
| 测试 5: 重建向量索引 | ✅ / ❌ | |
| 测试 6: 版本去重 | ✅ / ❌ | |
| 测试 7: 大文件存储切换 | ✅ / ❌ | |
| 测试 8: 版本信息展示 | ✅ / ❌ | |
| 测试 9: 后端 API 端点 | ✅ / ❌ | |
| 测试 10: 大量版本加载性能 | ✅ / ❌ | |
| 测试 11: 大文件版本切换性能 | ✅ / ❌ | |
| 测试 12: 权限隔离 | ✅ / ❌ | |
| 测试 13: 并发创建版本 | ✅ / ❌ | |
| 测试 14: 删除当前版本保护 | ✅ / ❌ | |
| 测试 15: 异常处理 | ✅ / ❌ | |
| 测试 16: 响应式布局 | ✅ / ❌ | |
| 测试 17: 交互反馈 | ✅ / ❌ | |
| 测试 18: 加载状态 | ✅ / ❌ | |
| 测试 19: 版本链完整性 | ✅ / ❌ | |
| 测试 20: 哈希一致性 | ✅ / ❌ | |

**总体评价**:

**发现的问题**:
1.
2.

**建议改进**:
1.
2.
