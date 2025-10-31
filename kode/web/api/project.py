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

router = APIRouter()


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
