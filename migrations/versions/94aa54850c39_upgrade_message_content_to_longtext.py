"""upgrade_message_content_to_longtext

Revision ID: 94aa54850c39
Revises: 72303907ed6b
Create Date: 2025-12-01 14:50:44.610711

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '94aa54850c39'
down_revision: Union[str, Sequence[str], None] = '72303907ed6b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
