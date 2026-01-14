"""DataSource API Routes"""

import os
import uuid
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from kode.database.session import get_db
from kode.web.dependencies import get_current_user, get_current_organization
from kode.models import User
from kode.models.organization import Organization
from kode.models.data_source import DataSourceType, DataSourceStatus
from kode.services.data_source_service import DataSourceService
from kode.schemas.data_source import (
    DatabaseConnectionCreate,
    DataSourceUpdate,
    DataSourceResponse,
    DataSourceListResponse,
    TestConnectionRequest,
    TestConnectionResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# 上传配置
UPLOAD_DIR = Path("./uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB
ALLOWED_EXTENSIONS = {".xlsx", ".xls", ".csv", ".json", ".parquet"}


@router.post(
    "/upload", response_model=DataSourceResponse, status_code=status.HTTP_201_CREATED
)
async def upload_file_data_source(
    file: UploadFile = File(...),
    name: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
):
    """上传文件创建数据源"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    # 检查扩展名
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: {ext}。支持: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # 读取文件
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="文件大小超过500MB限制")

    # 保存文件
    org_dir = UPLOAD_DIR / organization.id
    org_dir.mkdir(parents=True, exist_ok=True)

    unique_filename = f"{uuid.uuid4().hex}{ext}"
    file_path = org_dir / unique_filename

    with open(file_path, "wb") as f:
        f.write(content)

    # 创建数据源记录
    service = DataSourceService(db)
    ds_name = name or Path(file.filename).stem

    # 检查名称是否重复
    existing = await service.get_by_name(ds_name, organization.id)
    if existing:
        # 添加随机后缀
        ds_name = f"{ds_name}_{uuid.uuid4().hex[:6]}"

    ds = await service.create_file_data_source(
        organization_id=organization.id,
        name=ds_name,
        file_path=str(file_path.absolute()),
        original_filename=file.filename,
        file_size=len(content),
        file_mime_type=file.content_type,
    )

    logger.info(f"File data source created: {ds.name} by user {current_user.id}")
    return DataSourceResponse.model_validate(ds)


@router.post(
    "/connection",
    response_model=DataSourceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_database_connection(
    data: DatabaseConnectionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
):
    """创建数据库连接数据源"""
    service = DataSourceService(db)

    # 检查名称是否重复
    existing = await service.get_by_name(data.name, organization.id)
    if existing:
        raise HTTPException(status_code=409, detail=f"数据源名称 '{data.name}' 已存在")

    ds = await service.create_database_data_source(
        organization_id=organization.id,
        name=data.name,
        source_type=data.source_type,
        host=data.host,
        port=data.port,
        database=data.database,
        username=data.username,
        password=data.password,
        db_schema=data.db_schema,
        ssl_enabled=data.ssl_enabled,
        config=data.config,
    )

    logger.info(f"Database data source created: {ds.name} by user {current_user.id}")
    return DataSourceResponse.model_validate(ds)


@router.get("", response_model=DataSourceListResponse)
async def list_data_sources(
    source_type: Optional[DataSourceType] = None,
    status: Optional[DataSourceStatus] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
):
    """列出当前组织的所有数据源"""
    service = DataSourceService(db)
    items, total = await service.list_by_organization(
        organization_id=organization.id,
        source_type=source_type,
        status=status,
        skip=skip,
        limit=limit,
    )

    return DataSourceListResponse(
        items=[DataSourceResponse.model_validate(ds) for ds in items],
        total=total,
    )


@router.get("/{data_source_id}", response_model=DataSourceResponse)
async def get_data_source(
    data_source_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
):
    """获取数据源详情"""
    service = DataSourceService(db)
    ds = await service.get_by_id(data_source_id, organization.id)

    if not ds:
        raise HTTPException(status_code=404, detail="数据源不存在")

    return DataSourceResponse.model_validate(ds)


@router.delete("/{data_source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_data_source(
    data_source_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
):
    """删除数据源（已被引用的不能删除）"""
    service = DataSourceService(db)
    success, message = await service.delete(data_source_id, organization.id)

    if not success:
        raise HTTPException(status_code=409, detail=message)


@router.post("/{data_source_id}/test", response_model=TestConnectionResponse)
async def test_connection(
    data_source_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
):
    """测试已有数据库连接"""
    service = DataSourceService(db)
    success, message, latency = await service.test_connection(
        data_source_id, organization.id
    )

    return TestConnectionResponse(
        success=success,
        message=message,
        latency_ms=latency,
    )


@router.post("/test-connection", response_model=TestConnectionResponse)
async def test_connection_params(
    data: TestConnectionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
):
    """测试连接参数（创建前测试）"""
    service = DataSourceService(db)
    success, message, latency = await service.test_connection_params(
        source_type=data.source_type,
        host=data.host,
        port=data.port,
        database=data.database,
        username=data.username,
        password=data.password,
        db_schema=data.db_schema,
        ssl_enabled=data.ssl_enabled,
    )

    return TestConnectionResponse(
        success=success,
        message=message,
        latency_ms=latency,
    )
