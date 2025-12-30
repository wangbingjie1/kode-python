# 本体版本管理功能实现文档

## 概述

本文档记录了本体版本管理功能的完整实现，包括后端 API 和前端 UI。

## 功能特性

### 核心功能

✅ **版本列表查看** - 查看所有历史版本，按版本号降序排列
✅ **版本切换** - 在不同版本之间切换查看本体内容
✅ **版本回滚** - 回滚到指定历史版本（创建新版本，内容与目标版本相同）
✅ **版本删除** - 删除非当前版本（软删除）
✅ **向量索引管理** - 手动触发向量索引重建
✅ **版本对比** - 查看版本元数据差异（哈希值、大小、创建时间等）

### 版本信息展示

- **版本号** - 自动递增的版本标识
- **版本标签** - 可选的自定义标签
- **当前版本标记** - 清晰标识当前活跃版本
- **创建时间** - 版本创建的时间戳
- **变更说明** - 本次变更的摘要信息
- **存储类型** - 数据库存储或文件存储
- **文件大小** - 本体数据的字节大小
- **向量索引状态** - pending / building / completed / failed
- **内容哈希** - SHA256 哈希值，用于去重

## 技术架构

### 后端实现

#### 1. 数据库模型

**OntologyVersion** (`kode/models/ontology_version.py`)
- 存储版本元数据
- 支持文件和数据库两种存储方式
- 包含向量索引状态跟踪

**OntologyChange** (`kode/models/ontology_change.py`)
- 记录版本间的变更历史

#### 2. 服务层

**OntologyVersionManager** (`kode/services/ontology_version_manager.py`)

核心方法：
```python
async def create_version()        # 创建新版本（自动去重）
async def get_latest_version()    # 获取最新版本
async def get_version_by_number() # 根据版本号获取
async def list_versions()         # 列出所有版本
async def rollback_to_version()   # 回滚到指定版本
async def delete_version()        # 软删除版本
async def load_ontology_data()    # 加载版本数据
```

特性：
- ✅ 内容去重（基于 SHA256 哈希）
- ✅ 分层存储（小于 100KB 存数据库，否则存文件）
- ✅ 版本链追踪（parent_version_id）
- ✅ 向量索引异步构建

#### 3. API 端点

**Ontology Router** (`kode/web/api/ontology.py`)

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/ontology/versions/{connection_name}` | GET | 列出所有版本 |
| `/api/ontology/versions/{connection_name}/current` | GET | 获取当前版本 |
| `/api/ontology/versions/{connection_name}/{version_number}` | GET | 获取指定版本 |
| `/api/ontology/versions/{connection_name}/rollback` | POST | 回滚到指定版本 |
| `/api/ontology/versions/{connection_name}/{version_number}` | DELETE | 删除版本 |
| `/api/ontology/versions/{connection_name}/{version_number}/rebuild-index` | POST | 重建向量索引 |
| `/api/ontology/versions/{connection_name}/{version_number}/index-status` | GET | 查询索引状态 |

### 前端实现

#### 1. API 客户端

**API Types & Functions** (`web-frontend/src/services/api.ts`)

新增接口：
```typescript
interface OntologyVersion { ... }          // 版本数据模型
interface OntologyVersionListResponse { ... }
interface OntologyRollbackRequest { ... }

listOntologyVersions()            // 列出版本
getCurrentOntologyVersion()       // 获取当前版本
getOntologyVersionByNumber()      // 获取指定版本
rollbackOntologyVersion()         // 回滚版本
deleteOntologyVersion()           // 删除版本
rebuildOntologyVectorIndex()      // 重建索引
getOntologyVectorIndexStatus()    // 查询索引状态
```

#### 2. UI 组件

**OntologyViewer.vue** (`web-frontend/src/components/OntologyViewer.vue`)

新增功能：
- ✅ **版本管理标签页** - 第 4 个标签页显示版本列表
- ✅ **版本卡片** - 展示版本详细信息
- ✅ **视觉反馈** - 当前版本绿色高亮，选中版本蓝色高亮
- ✅ **操作按钮** - 回滚、删除、重建索引
- ✅ **状态徽章** - 向量索引状态的颜色标识
- ✅ **辅助函数** - formatBytes(), getIndexStatusText()

新增状态：
```typescript
const versions = ref<OntologyVersion[]>([])
const currentVersion = ref<OntologyVersion | null>(null)
const selectedVersion = ref<OntologyVersion | null>(null)
const loadingVersions = ref(false)
```

核心方法：
```typescript
async loadVersions()          // 加载版本列表
async switchToVersion()       // 切换版本
async rollbackToVersion()     // 回滚版本
async deleteVersion()         // 删除版本
async rebuildVectorIndex()    // 重建索引
```

#### 3. 样式设计

版本卡片设计：
- **常规版本** - 灰色边框
- **当前版本** - 绿色边框 + 浅绿背景 + "当前"徽章
- **选中版本** - 蓝色边框 + 浅蓝背景
- **悬停效果** - 蓝色边框 + 阴影

状态徽章颜色：
- **待构建 (pending)** - 橙色
- **构建中 (building)** - 蓝色
- **已完成 (completed)** - 绿色
- **失败 (failed)** - 红色
- **无 (none)** - 灰色

## 使用流程

### 1. 查看版本列表

```
1. 进入"数据库管理" -> "本体管理"
2. 选择一个本体连接
3. 点击"版本管理"标签页
4. 查看所有历史版本
```

### 2. 切换到历史版本

```
1. 在版本列表中点击任意版本卡片
2. 自动加载该版本的本体数据
3. 可在"概念"、"关系"、"关系图"标签页查看
```

### 3. 回滚到历史版本

```
1. 在版本列表中找到目标版本
2. 点击"回滚"按钮
3. 确认操作
4. 系统创建新版本（内容与目标版本相同）
5. 自动刷新版本列表
```

### 4. 删除历史版本

```
1. 在版本列表中找到要删除的版本（非当前版本）
2. 点击"删除"按钮
3. 确认操作
4. 软删除成功
```

### 5. 重建向量索引

```
1. 查看版本的"向量索引"状态
2. 如果状态为"失败"或"待构建"
3. 点击"重建索引"按钮
4. 后台异步执行重建任务
```

## 数据流程

### 版本创建流程

```
1. 用户触发本体更新（通过聊天或工具调用）
   ↓
2. OntologyUpdateManager 计算本体数据的 SHA256 哈希
   ↓
3. 检查数据库中是否存在相同哈希的版本
   ↓
4a. 如果存在 → 复用已有版本（去重）
4b. 如果不存在 → 创建新版本
   ↓
5. 判断存储策略（< 100KB 存数据库，否则存文件）
   ↓
6. 保存到对应位置：
   - 数据库：ontology_data 字段
   - 文件：ontology_store/{user_id}/{connection_name}/versions/v{N}/ontology_vN.json
   ↓
7. 创建数据库记录（OntologyVersion）
   ↓
8. 异步触发向量索引构建任务
```

### 版本回滚流程

```
1. 用户选择目标版本并点击"回滚"
   ↓
2. 后端加载目标版本的本体数据
   ↓
3. 基于该数据创建新版本（版本号 +1）
   ↓
4. 将旧的 is_current 设置为 False
   ↓
5. 新版本的 is_current 设置为 True
   ↓
6. 返回新版本给前端
   ↓
7. 前端刷新版本列表和本体数据
```

### 向量索引构建流程

```
1. 版本创建时自动触发或手动点击"重建索引"
   ↓
2. 提交 Celery 异步任务
   ↓
3. VectorIndexManager 构建 FAISS 索引
   ↓
4. 保存到：ontology_store/{user_id}/{connection_name}/vectors/v{N}/
   ↓
5. 更新数据库字段：
   - vector_index_status = "completed"
   - vector_index_built_at = 当前时间
   ↓
6. 如果失败：
   - vector_index_status = "failed"
   - vector_index_error = 错误信息
```

## 存储结构

### 文件系统

```
ontology_store/
├── {user_id}/
│   ├── {connection_name}/
│   │   ├── versions/
│   │   │   ├── v1/
│   │   │   │   └── ontology_v1.json
│   │   │   ├── v2/
│   │   │   │   └── ontology_v2.json
│   │   │   └── v3/
│   │   │       └── ontology_v3.json
│   │   ├── vectors/
│   │   │   ├── v1/
│   │   │   │   ├── index.faiss
│   │   │   │   └── metadata.json
│   │   │   ├── v2/
│   │   │   └── v3/
│   │   └── ontology_v3.json  # 当前版本的快捷链接
```

### 数据库表

**ontology_versions**
- id (UUID, 主键)
- user_id (外键 → users.id)
- connection_name (字符串)
- version_number (整数，自增)
- version_tag (可选标签)
- is_snapshot (是否快照)
- parent_version_id (父版本ID)
- storage_type ('db' 或 'file')
- file_path (文件路径)
- ontology_data (JSONB，小文件直接存储)
- ontology_hash (SHA256)
- vector_index_status (向量索引状态)
- vector_index_path (索引路径)
- vector_index_built_at (索引构建时间)
- vector_index_error (索引错误信息)
- size_bytes (文件大小)
- change_summary (变更摘要)
- created_by_conversation_id (创建对话ID)
- status ('active' 或 'archived')
- is_current (是否当前版本)
- created_at (创建时间)
- archived_at (归档时间)

**ontology_changes**
- 记录版本间的详细变更

## 安全与权限

### 权限控制

- ✅ 所有 API 端点需要用户认证（JWT Token）
- ✅ 只能访问自己创建的本体版本
- ✅ 通过 `current_user.id` 进行隔离

### 数据保护

- ✅ 软删除机制（status = 'archived'）
- ✅ 版本链完整性（parent_version_id）
- ✅ 哈希去重（避免存储重复数据）

## 性能优化

### 后端优化

- ✅ **哈希去重** - 相同内容的本体只存储一次
- ✅ **分层存储** - 小文件存数据库，大文件存文件系统
- ✅ **异步索引** - 向量索引构建在后台进行
- ✅ **分页查询** - 版本列表支持 limit/offset

### 前端优化

- ✅ **按需加载** - 只在切换到版本管理标签时加载
- ✅ **缓存策略** - 已加载的版本数据在内存中缓存
- ✅ **响应式 UI** - 使用 Vue 3 Composition API

## 未来扩展

### 计划功能

1. **版本对比** - 可视化两个版本之间的差异
2. **版本合并** - 合并多个分支版本
3. **版本导出** - 导出特定版本为 JSON 文件
4. **版本注释** - 为每个版本添加详细注释
5. **批量操作** - 批量删除或归档版本
6. **版本统计** - 可视化版本历史趋势图

### 技术改进

1. **增量索引** - 向量索引增量更新而非全量重建
2. **压缩存储** - 大文件使用 gzip 压缩
3. **CDN 加速** - 文件存储使用对象存储 + CDN
4. **实时推送** - WebSocket 实时推送索引构建进度

## 故障排查

### 常见问题

**Q: 版本列表为空？**
A: 检查是否已构建本体。只有执行过 OntologyBuilder 工具的连接才会有版本记录。

**Q: 向量索引状态一直是"待构建"？**
A: 检查 Celery worker 是否正常运行。手动点击"重建索引"重试。

**Q: 回滚后数据没变化？**
A: 回滚创建的是新版本，需要刷新页面或重新加载本体。

**Q: 删除版本后能恢复吗？**
A: 目前是软删除（status='archived'），可通过数据库手动恢复。

### 日志位置

- **后端日志**: 控制台输出或配置的日志文件
- **前端错误**: 浏览器开发者工具 Console
- **Celery 任务**: Celery worker 日志

## 总结

本体版本管理功能提供了完整的版本控制能力，支持版本查看、切换、回滚、删除和索引管理。后端采用分层存储和哈希去重优化性能，前端提供直观的 UI 交互。整个系统设计健壮、易扩展，为用户提供了可靠的本体演化追踪能力。
