# 后端架构整改计划

> 目标：从 Demo 阶段升级为正式研发架构，实现多租户组织化管理

## 一、架构对比

### 当前架构
```
User (1) ──────> (∞) Project
  │
  └──────────> (∞) DatabaseConnection
  │
  └──────────> (∞) OntologyVersion
```

### 目标架构（根据业务逻辑图）
```
User (1) ═══════ (1) Organization
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
     DataSource    Project    (其他资源)
          │           │
          └─── M:N ───┘
                      │
                      ▼ 1:1
                  Ontology
```

---

## 二、数据模型改动

### 阶段1：新增 Organization 模型

**文件**: `kode/models/organization.py`

```python
class Organization(Base):
    __tablename__ = "organizations"

    id = Column(String(36), primary_key=True, default=uuid4)
    name = Column(String(100), nullable=False)          # 组织名称
    owner_id = Column(String(36), ForeignKey("users.id"), unique=True)  # 1:1 关系

    # 配额（从 Plan 继承或独立设置）
    max_projects = Column(Integer, default=3)
    max_data_sources = Column(Integer, default=5)
    max_storage_bytes = Column(BigInteger, default=500*1024*1024)  # 500MB

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # 关系
    owner = relationship("User", back_populates="organization")
    projects = relationship("Project", back_populates="organization")
    data_sources = relationship("DataSource", back_populates="organization")
```

**改动**: `kode/models/user.py`
```python
# 新增关系
organization = relationship("Organization", back_populates="owner", uselist=False)
```

---

### 阶段2：新增 DataSource 模型（统一抽象）

**文件**: `kode/models/data_source.py`

```python
class DataSourceType(str, Enum):
    FILE = "file"                # 文件上传（Excel, CSV, JSON）
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLSERVER = "sqlserver"
    SQLITE = "sqlite"
    SNOWFLAKE = "snowflake"
    BIGQUERY = "bigquery"
    MONGODB = "mongodb"
    # 未来扩展
    GOOGLE_ADS = "google_ads"
    SALESFORCE = "salesforce"
    S3 = "s3"

class DataSourceStatus(str, Enum):
    PENDING = "pending"          # 待处理（文件上传中/连接未验证）
    READY = "ready"              # 可用
    ERROR = "error"              # 错误
    ARCHIVED = "archived"        # 已归档

class DataSource(Base):
    __tablename__ = "data_sources"

    id = Column(String(36), primary_key=True, default=uuid4)
    organization_id = Column(String(36), ForeignKey("organizations.id"), index=True)

    name = Column(String(100), nullable=False)          # 数据源名称
    source_type = Column(Enum(DataSourceType), nullable=False)
    status = Column(Enum(DataSourceStatus), default=DataSourceStatus.PENDING)

    # === 文件类型专用字段 ===
    file_path = Column(String(500))                     # 文件存储路径
    original_filename = Column(String(255))             # 原始文件名
    file_size = Column(BigInteger)                      # 文件大小（字节）
    file_mime_type = Column(String(100))                # MIME 类型

    # === 数据库类型专用字段 ===
    host = Column(String(255))
    port = Column(Integer)
    database = Column(String(255))
    username = Column(String(100))
    encrypted_password = Column(Text)                   # 加密存储
    db_schema = Column(String(100))
    ssl_enabled = Column(Boolean, default=False)

    # === 通用元数据 ===
    config = Column(JSON)                               # 扩展配置（如 S3 bucket, BigQuery project）
    schema_cache = Column(JSON)                         # 缓存的 schema 信息
    schema_cached_at = Column(DateTime)                 # schema 缓存时间

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # 关系
    organization = relationship("Organization", back_populates="data_sources")
    project_associations = relationship("ProjectDataSource", back_populates="data_source")

    # 约束：同组织内名称唯一
    __table_args__ = (
        UniqueConstraint('organization_id', 'name', name='uq_org_datasource_name'),
    )
```

---

### 阶段3：新增 ProjectDataSource 关联表（多对多）

**文件**: `kode/models/project_data_source.py`

```python
class ProjectDataSourceStatus(str, Enum):
    LINKED = "linked"            # 仅关联，未融合到本体
    MERGED = "merged"            # 已融合到本体
    PENDING_MERGE = "pending_merge"  # 等待融合

class ProjectDataSource(Base):
    """项目-数据源关联表"""
    __tablename__ = "project_data_sources"

    id = Column(String(36), primary_key=True, default=uuid4)
    project_id = Column(String(36), ForeignKey("projects.id"), index=True)
    data_source_id = Column(String(36), ForeignKey("data_sources.id"), index=True)

    status = Column(Enum(ProjectDataSourceStatus), default=ProjectDataSourceStatus.LINKED)
    merged_at = Column(DateTime)                        # 融合时间
    merged_by_conversation_id = Column(String(36))      # 哪个对话触发的融合

    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    project = relationship("Project", back_populates="data_source_associations")
    data_source = relationship("DataSource", back_populates="project_associations")

    # 约束：同一数据源不能重复关联到同一项目
    __table_args__ = (
        UniqueConstraint('project_id', 'data_source_id', name='uq_project_datasource'),
    )
```

---

### 阶段4：修改 Project 模型

**文件**: `kode/models/project.py`

```python
# 改动：将 user_id 改为 organization_id
class Project(Base):
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=uuid4)
    name = Column(String(100), nullable=False)
    description = Column(String(500))

    # 改动：从 user_id 改为 organization_id
    organization_id = Column(String(36), ForeignKey("organizations.id"), index=True)

    config = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # 新增关系
    organization = relationship("Organization", back_populates="projects")
    data_source_associations = relationship("ProjectDataSource", back_populates="project")
    ontology = relationship("ProjectOntology", back_populates="project", uselist=False)  # 1:1

    # 便捷属性：获取关联的数据源
    @property
    def data_sources(self):
        return [assoc.data_source for assoc in self.data_source_associations]
```

---

### 阶段5：新增 ProjectOntology 模型（项目本体 1:1）

**文件**: `kode/models/project_ontology.py`

```python
class ProjectOntology(Base):
    """项目本体（与项目 1:1 关系）"""
    __tablename__ = "project_ontologies"

    id = Column(String(36), primary_key=True, default=uuid4)
    project_id = Column(String(36), ForeignKey("projects.id"), unique=True)  # 1:1

    # 本体数据
    ontology_data = Column(JSON)                        # 本体 JSON
    ontology_hash = Column(String(64), index=True)      # SHA256 哈希

    # 版本控制
    version = Column(Integer, default=1)

    # 向量索引
    vector_index_status = Column(String(20), default="pending")
    vector_index_path = Column(String(500))
    vector_index_built_at = Column(DateTime)

    # 融合的数据源追踪
    merged_data_source_ids = Column(JSON)               # [data_source_id, ...]

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # 关系
    project = relationship("Project", back_populates="ontology")
```

---

## 三、API 端点改动

### 阶段1：组织 API（自动创建，无需手动管理）

无需暴露独立 API，用户注册时自动创建组织。

**改动**: `kode/services/user_service.py` 或注册逻辑
```python
async def create_user(...):
    user = User(...)
    db.add(user)

    # 自动创建组织
    org = Organization(
        name=f"{user.username}的工作区",
        owner_id=user.id
    )
    db.add(org)
    await db.commit()
```

---

### 阶段2：数据源 API

**新增文件**: `kode/web/api/data_source.py`

```
POST   /api/data-sources/upload          # 上传文件数据源
POST   /api/data-sources/connection      # 创建数据库连接数据源
GET    /api/data-sources                 # 列表数据源（当前组织）
GET    /api/data-sources/{id}            # 获取数据源详情
DELETE /api/data-sources/{id}            # 删除数据源（检查引用）
POST   /api/data-sources/{id}/test       # 测试连接（数据库类型）
GET    /api/data-sources/{id}/schema     # 获取 schema（数据库/文件）
```

**删除检查逻辑**:
```python
@router.delete("/data-sources/{id}")
async def delete_data_source(id: str, org: Organization = Depends(get_current_org)):
    # 检查是否被项目引用
    associations = await db.query(ProjectDataSource).filter_by(data_source_id=id).all()
    if associations:
        project_names = [a.project.name for a in associations]
        raise HTTPException(
            status_code=409,
            detail=f"数据源被以下项目引用，无法删除: {', '.join(project_names)}"
        )
    # 执行删除...
```

---

### 阶段3：项目 API 改动

**修改文件**: `kode/web/api/project.py`

```
POST   /api/projects                     # 创建项目（可同时关联数据源）
GET    /api/projects                     # 列表项目（当前组织）
GET    /api/projects/{id}                # 获取项目详情（含数据源列表）
DELETE /api/projects/{id}                # 删除项目
```

**创建项目请求体**:
```python
class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    data_source_ids: Optional[List[str]] = []  # 初始关联的数据源
```

---

### 阶段4：项目-数据源关联 API

**新增端点**:
```
POST   /api/projects/{project_id}/data-sources/{data_source_id}     # 关联数据源
DELETE /api/projects/{project_id}/data-sources/{data_source_id}     # 解绑数据源
POST   /api/projects/{project_id}/data-sources/{data_source_id}/merge   # 融合到本体
POST   /api/projects/{project_id}/data-sources/{data_source_id}/unmerge # 从本体剥离
```

**关联逻辑**:
```python
@router.post("/projects/{project_id}/data-sources/{data_source_id}")
async def link_data_source(project_id: str, data_source_id: str):
    # 创建关联
    assoc = ProjectDataSource(
        project_id=project_id,
        data_source_id=data_source_id,
        status=ProjectDataSourceStatus.LINKED
    )
    db.add(assoc)
    await db.commit()

    return {"message": "数据源已关联", "prompt_merge": True}  # 提醒用户是否融合
```

**解绑逻辑**:
```python
@router.delete("/projects/{project_id}/data-sources/{data_source_id}")
async def unlink_data_source(project_id: str, data_source_id: str):
    assoc = await db.query(ProjectDataSource).filter_by(...).first()

    if assoc.status == ProjectDataSourceStatus.MERGED:
        # 已融合，需要先从本体剥离
        raise HTTPException(
            status_code=409,
            detail="数据源已融合到本体，请先执行剥离操作"
        )

    await db.delete(assoc)
    await db.commit()
```

---

### 阶段5：本体 API 改动

**修改文件**: `kode/web/api/database.py`（本体部分）

```
GET    /api/projects/{project_id}/ontology           # 获取项目本体
POST   /api/projects/{project_id}/ontology/rebuild   # 重建本体（基于关联的数据源）
GET    /api/projects/{project_id}/ontology/search    # 本体语义搜索
```

---

## 四、数据库迁移策略

### 迁移顺序

1. **创建新表**（无依赖）
   - organizations
   - data_sources
   - project_data_sources
   - project_ontologies

2. **数据迁移**
   ```sql
   -- 为每个用户创建组织
   INSERT INTO organizations (id, name, owner_id, created_at)
   SELECT uuid(), CONCAT(username, '的工作区'), id, NOW()
   FROM users;

   -- 迁移 database_connections 到 data_sources
   INSERT INTO data_sources (id, organization_id, name, source_type, ...)
   SELECT
       dc.id,
       o.id,
       dc.name,
       dc.db_type,
       ...
   FROM database_connections dc
   JOIN organizations o ON o.owner_id = dc.user_id;
   ```

3. **修改 projects 表**
   ```sql
   -- 添加 organization_id 列
   ALTER TABLE projects ADD COLUMN organization_id VARCHAR(36);

   -- 填充数据
   UPDATE projects p
   SET organization_id = (
       SELECT o.id FROM organizations o WHERE o.owner_id = p.user_id
   );

   -- 删除旧列（延迟执行，确认无问题后）
   -- ALTER TABLE projects DROP COLUMN user_id;
   ```

4. **清理旧表**（延迟执行）
   - database_connections（迁移完成后）
   - ontology_versions（重构为 project_ontologies 后）

---

## 五、实施计划

### 第一周：基础模型

| 任务 | 优先级 | 预计工时 |
|-----|--------|---------|
| 创建 Organization 模型 | P0 | 2h |
| 修改用户注册逻辑，自动创建组织 | P0 | 2h |
| 创建 DataSource 模型 | P0 | 3h |
| 创建 ProjectDataSource 模型 | P0 | 2h |
| 生成 Alembic 迁移 | P0 | 1h |
| 编写数据迁移脚本 | P0 | 3h |

### 第二周：API 实现

| 任务 | 优先级 | 预计工时 |
|-----|--------|---------|
| 数据源 API（上传/连接/列表/删除） | P0 | 6h |
| 项目 API 改造（关联组织） | P0 | 4h |
| 项目-数据源关联 API | P0 | 4h |
| 删除保护逻辑（引用检查） | P1 | 2h |

### 第三周：本体重构

| 任务 | 优先级 | 预计工时 |
|-----|--------|---------|
| ProjectOntology 模型 | P1 | 2h |
| 本体融合/剥离逻辑 | P1 | 6h |
| 本体 API 改造 | P1 | 4h |
| 向量索引迁移 | P2 | 4h |

### 第四周：测试和清理

| 任务 | 优先级 | 预计工时 |
|-----|--------|---------|
| 集成测试 | P0 | 6h |
| 旧表清理 | P2 | 2h |
| 文档更新 | P2 | 2h |

---

## 六、风险和注意事项

### 兼容性风险

1. **现有数据迁移**：需要为所有现有用户创建组织，并迁移关联关系
2. **API 破坏性变更**：`/api/database/connections` 将被 `/api/data-sources` 替代
3. **本体存储路径**：从 `user_id/connection_name` 改为 `project_id`

### 建议的过渡策略

1. **并行运行**：新旧 API 并存 2 周
2. **版本号标记**：API 路径加 `/v2/` 前缀（可选）
3. **数据库回滚点**：迁移前创建完整备份

---

## 七、文件变更清单

### 新增文件
- `kode/models/organization.py`
- `kode/models/data_source.py`
- `kode/models/project_data_source.py`
- `kode/models/project_ontology.py`
- `kode/web/api/data_source.py`
- `kode/services/data_source_service.py`
- `kode/services/organization_service.py`
- `kode/schemas/data_source.py`
- `kode/schemas/organization.py`
- `migrations/versions/xxx_add_organization_datasource.py`

### 修改文件
- `kode/models/__init__.py` - 导出新模型
- `kode/models/user.py` - 添加 organization 关系
- `kode/models/project.py` - user_id → organization_id
- `kode/web/api/project.py` - 关联组织和数据源
- `kode/web/main.py` - 注册新路由
- `kode/services/conversation.py` - 适配新的本体结构

### 废弃文件（迁移后删除）
- `kode/models/database_connection.py` - 合并到 DataSource
- `kode/web/api/database.py` - 连接部分迁移到 data_source.py

---

## 八、API 设计总结

### 最终 API 结构

```
/api/auth
    POST /google                         # Google OAuth
    GET  /google/callback                # OAuth 回调

/api/data-sources
    POST /upload                         # 上传文件数据源
    POST /connection                     # 创建数据库连接
    GET  /                               # 列表数据源
    GET  /{id}                           # 获取详情
    DELETE /{id}                         # 删除（检查引用）
    POST /{id}/test                      # 测试连接
    GET  /{id}/schema                    # 获取 schema

/api/projects
    POST /                               # 创建项目
    GET  /                               # 列表项目
    GET  /{id}                           # 获取详情
    DELETE /{id}                         # 删除项目

    # 数据源关联
    POST /{id}/data-sources/{ds_id}      # 关联数据源
    DELETE /{id}/data-sources/{ds_id}    # 解绑数据源
    POST /{id}/data-sources/{ds_id}/merge    # 融合到本体
    POST /{id}/data-sources/{ds_id}/unmerge  # 从本体剥离

    # 本体
    GET  /{id}/ontology                  # 获取本体
    POST /{id}/ontology/rebuild          # 重建本体
    POST /{id}/ontology/search           # 语义搜索

/api/chat
    POST /conversations                  # 创建对话
    GET  /conversations/{id}             # 获取对话
    DELETE /conversations/{id}           # 删除对话

/api/sse
    GET  /chat/{conv_id}/stream          # SSE 流式响应
    POST /chat/{conv_id}/message         # 发送消息

/api/billing
    GET  /plans                          # 订阅计划
    POST /checkout                       # Stripe 结账
```

---

**下一步**：确认此计划后，我将按顺序实现各阶段代码。
