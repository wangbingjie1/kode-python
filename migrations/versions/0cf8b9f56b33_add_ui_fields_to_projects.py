"""Add UI fields to projects

Revision ID: 0cf8b9f56b33
Revises: 9a87573da051
Create Date: 2026-01-16 14:35:08.590242

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0cf8b9f56b33'
down_revision: Union[str, Sequence[str], None] = '9a87573da051'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add UI fields to projects table."""
    op.add_column('projects', sa.Column('icon', sa.String(length=10), nullable=True, server_default='📊'))
    op.add_column('projects', sa.Column('business_type', sa.String(length=50), nullable=True))
    op.add_column('projects', sa.Column('status', sa.String(length=20), nullable=True, server_default='active'))
    op.add_column('projects', sa.Column('is_pinned', sa.Boolean(), nullable=True, server_default='0'))
    op.add_column('projects', sa.Column('needs_etl', sa.Boolean(), nullable=True, server_default='1'))
    op.add_column('projects', sa.Column('ontology_built', sa.Boolean(), nullable=True, server_default='0'))


def downgrade() -> None:
    """Remove UI fields from projects table."""
    op.drop_column('projects', 'ontology_built')
    op.drop_column('projects', 'needs_etl')
    op.drop_column('projects', 'is_pinned')
    op.drop_column('projects', 'status')
    op.drop_column('projects', 'business_type')
    op.drop_column('projects', 'icon')
