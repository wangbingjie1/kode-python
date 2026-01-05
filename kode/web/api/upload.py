"""
File Upload API Routes

REST endpoints for file upload and management.
"""

import os
import uuid
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from kode.web.dependencies import get_current_user
from kode.models import User
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# 上传目录配置
UPLOAD_DIR = Path("./uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# 支持的文件类型
ALLOWED_EXTENSIONS = {
    '.pdf', '.docx', '.xlsx', '.xls', '.csv', '.txt', '.md', '.json'
}

# 最大文件大小 (50MB)
MAX_FILE_SIZE = 50 * 1024 * 1024


class UploadResponse(BaseModel):
    """上传响应"""
    success: bool
    files: List[dict]
    message: str


class FileInfo(BaseModel):
    """文件信息"""
    filename: str
    original_name: str
    path: str
    size: int
    content_type: Optional[str]


def get_user_upload_dir(user_id: str) -> Path:
    """获取用户上传目录"""
    user_dir = UPLOAD_DIR / user_id
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir


def validate_file(file: UploadFile) -> None:
    """验证上传文件"""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文件名不能为空"
        )

    # 检查扩展名
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件格式: {ext}。支持的格式: {', '.join(ALLOWED_EXTENSIONS)}"
        )


@router.post("/files", response_model=UploadResponse)
async def upload_files(
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user)
) -> UploadResponse:
    """
    上传文件

    支持批量上传，文件会保存到用户专属目录。

    Args:
        files: 上传的文件列表
        current_user: 当前用户

    Returns:
        UploadResponse: 上传结果
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请选择要上传的文件"
        )

    user_dir = get_user_upload_dir(current_user.id)
    uploaded_files = []

    for file in files:
        try:
            # 验证文件
            validate_file(file)

            # 生成唯一文件名
            ext = Path(file.filename).suffix.lower()
            unique_name = f"{uuid.uuid4().hex}{ext}"
            file_path = user_dir / unique_name

            # 保存文件
            content = await file.read()

            # 检查文件大小
            if len(content) > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"文件 {file.filename} 超过 50MB 限制"
                )

            with open(file_path, "wb") as f:
                f.write(content)

            uploaded_files.append({
                "filename": unique_name,
                "original_name": file.filename,
                "path": str(file_path.absolute()),
                "size": len(content),
                "content_type": file.content_type
            })

            logger.info(f"File uploaded: {file.filename} -> {file_path}")

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to upload file {file.filename}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"上传文件失败: {file.filename}"
            )

    return UploadResponse(
        success=True,
        files=uploaded_files,
        message=f"成功上传 {len(uploaded_files)} 个文件"
    )


@router.get("/files")
async def list_files(
    current_user: User = Depends(get_current_user)
) -> List[dict]:
    """
    列出用户上传的文件

    Returns:
        文件列表
    """
    user_dir = get_user_upload_dir(current_user.id)

    files = []
    for file_path in user_dir.iterdir():
        if file_path.is_file():
            stat = file_path.stat()
            files.append({
                "filename": file_path.name,
                "path": str(file_path.absolute()),
                "size": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat()
            })

    return files


@router.delete("/files/{filename}")
async def delete_file(
    filename: str,
    current_user: User = Depends(get_current_user)
):
    """
    删除上传的文件

    Args:
        filename: 文件名
        current_user: 当前用户
    """
    user_dir = get_user_upload_dir(current_user.id)
    file_path = user_dir / filename

    # 安全检查：确保路径在用户目录内
    try:
        file_path.resolve().relative_to(user_dir.resolve())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问此文件"
        )

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在"
        )

    file_path.unlink()
    logger.info(f"File deleted: {file_path}")

    return {"success": True, "message": "文件已删除"}
