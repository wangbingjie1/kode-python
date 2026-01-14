"""add deleted_at to conversations for soft delete

Revision ID: 9a4011b84ba7
Revises: simplified_ontology
Create Date: 2025-12-27 11:02:10.750713

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '9a4011b84ba7'
down_revision: Union[str, Sequence[str], None] = 'simplified_ontology'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add deleted_at column to conversations for soft delete."""
    op.add_column('conversations', sa.Column('deleted_at', sa.DateTime(), nullable=True))
    op.create_index(op.f('ix_conversations_deleted_at'), 'conversations', ['deleted_at'], unique=False)


def downgrade() -> None:
    """Remove deleted_at column from conversations."""
    op.drop_index(op.f('ix_conversations_deleted_at'), table_name='conversations')
    op.drop_column('conversations', 'deleted_at')
