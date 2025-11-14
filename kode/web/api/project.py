"""
Project API Routes

REST endpoints for project management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from kode.database.session import get_db
from kode.models import Project, User
from kode.schemas.project import ProjectCreate, ProjectResponse
from kode.web.dependencies import get_current_user
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project: ProjectCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new project"""
    # Verify user exists
    user_result = await db.execute(
        select(User).where(User.id == project.user_id)
    )
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {project.user_id} not found",
        )

    # Create project
    db_project = Project(
        name=project.name,
        description=project.description,
        user_id=project.user_id,
        config=project.config or {},
    )

    db.add(db_project)
    await db.commit()
    await db.refresh(db_project)

    return db_project


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get project by ID"""
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )

    return project


@router.get("/projects", response_model=List[ProjectResponse])
async def list_projects(
    user_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List all projects, optionally filtered by user"""
    query = select(Project)

    if user_id:
        query = query.where(Project.user_id == user_id)

    result = await db.execute(query.order_by(Project.updated_at.desc()))
    projects = result.scalars().all()

    return projects


@router.get("/projects/user/default", response_model=ProjectResponse)
async def get_or_create_default_project(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取或创建当前用户的默认项目

    如果用户没有任何项目，自动创建一个默认项目
    如果用户有项目，返回最近使用的项目
    """
    # 查找用户的所有项目
    result = await db.execute(
        select(Project)
        .where(Project.user_id == current_user.id)
        .order_by(Project.updated_at.desc())
    )
    existing_project = result.scalar_one_or_none()

    if existing_project:
        # 用户已有项目，返回最近使用的项目
        return existing_project

    # 用户没有项目，创建默认项目
    logger.info(f"Creating default project for user {current_user.id}")
    default_project = Project(
        name="默认项目",
        description="默认工作空间",
        user_id=current_user.id,
        config={},
    )

    db.add(default_project)
    await db.commit()
    await db.refresh(default_project)

    logger.info(f"Created default project {default_project.id} for user {current_user.id}")
    return default_project


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a project"""
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )

    await db.delete(project)
    await db.commit()
