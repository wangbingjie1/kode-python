"""Add ontology version management (simplified)

Revision ID: simplified_ontology
Revises: 94aa54850c39
Create Date: 2025-12-22 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'simplified_ontology'
down_revision: Union[str, Sequence[str], None] = '94aa54850c39'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - only ontology version management."""

    # 创建 ontology_versions 表
    op.create_table(
        'ontology_versions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False, comment='用户ID'),
        sa.Column('connection_name', sa.String(length=100), nullable=False, comment='数据库连接名称'),
        sa.Column('version_number', sa.Integer(), nullable=False, comment='版本号（自增）'),
        sa.Column('version_tag', sa.String(length=100), nullable=True, comment="版本标签（可选，如 'v1.0.0')"),
        sa.Column('is_snapshot', sa.Boolean(), default=False, nullable=False, comment='是否为快照版本'),
        sa.Column('parent_version_id', sa.String(length=36), nullable=True, comment='父版本ID'),
        sa.Column('storage_type', sa.String(length=20), default='file', comment='存储类型：file/db'),
        sa.Column('file_path', sa.String(length=500), nullable=True, comment='文件路径（相对于 ontology_store/）'),
        sa.Column('ontology_data', sa.JSON(), nullable=True, comment='本体数据（小版本存DB，大版本存文件）'),
        sa.Column('ontology_hash', sa.String(length=64), nullable=False, comment='本体内容SHA256哈希（去重用）'),
        sa.Column('vector_index_status', sa.String(length=20), nullable=False, default='pending', comment='向量索引状态：pending/building/ready/failed'),
        sa.Column('vector_index_path', sa.String(length=500), nullable=True, comment='向量索引目录路径'),
        sa.Column('vector_index_built_at', sa.DateTime(), nullable=True, comment='向量索引构建完成时间'),
        sa.Column('vector_index_error', sa.Text(), nullable=True, comment='向量索引构建错误信息'),
        sa.Column('size_bytes', sa.Integer(), nullable=True, comment='本体文件大小（字节）'),
        sa.Column('change_summary', sa.Text(), nullable=True, comment='变更摘要'),
        sa.Column('created_by_conversation_id', sa.String(length=36), nullable=True, comment='创建该版本的对话ID'),
        sa.Column('status', sa.String(length=20), default='active', comment='状态：active/archived/deleted'),
        sa.Column('is_current', sa.Boolean(), default=True, comment='是否为当前活跃版本'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), comment='创建时间'),
        sa.Column('archived_at', sa.DateTime(), nullable=True, comment='归档时间'),
        sa.ForeignKeyConstraint(['created_by_conversation_id'], ['conversations.id'], ),
        sa.ForeignKeyConstraint(['parent_version_id'], ['ontology_versions.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 创建索引
    op.create_index('ix_ontology_versions_connection_name', 'ontology_versions', ['connection_name'])
    op.create_index('ix_ontology_versions_ontology_hash', 'ontology_versions', ['ontology_hash'])
    op.create_index('ix_ontology_versions_user_id', 'ontology_versions', ['user_id'])
    op.create_index('ix_ontology_versions_vector_index_status', 'ontology_versions', ['vector_index_status'])

    # 修改 ontology_changes 表，添加 user_id 和 ontology_version_id
    op.add_column('ontology_changes', sa.Column('user_id', sa.String(length=36), nullable=False, comment='用户ID'))
    op.add_column('ontology_changes', sa.Column('ontology_version_id', sa.String(length=36), nullable=True, comment='关联的本体版本ID'))

    # 创建索引
    op.create_index('ix_ontology_changes_user_id', 'ontology_changes', ['user_id'])
    op.create_index('ix_ontology_changes_ontology_version_id', 'ontology_changes', ['ontology_version_id'])

    # 创建外键
    op.create_foreign_key('fk_ontology_changes_user', 'ontology_changes', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_ontology_changes_version', 'ontology_changes', 'ontology_versions', ['ontology_version_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    """Downgrade schema."""

    # 删除外键
    op.drop_constraint('fk_ontology_changes_version', 'ontology_changes', type_='foreignkey')
    op.drop_constraint('fk_ontology_changes_user', 'ontology_changes', type_='foreignkey')

    # 删除索引
    op.drop_index('ix_ontology_changes_ontology_version_id', table_name='ontology_changes')
    op.drop_index('ix_ontology_changes_user_id', table_name='ontology_changes')

    # 删除列
    op.drop_column('ontology_changes', 'ontology_version_id')
    op.drop_column('ontology_changes', 'user_id')

    # 删除索引
    op.drop_index('ix_ontology_versions_vector_index_status', table_name='ontology_versions')
    op.drop_index('ix_ontology_versions_user_id', table_name='ontology_versions')
    op.drop_index('ix_ontology_versions_ontology_hash', table_name='ontology_versions')
    op.drop_index('ix_ontology_versions_connection_name', table_name='ontology_versions')

    # 删除表
    op.drop_table('ontology_versions')
