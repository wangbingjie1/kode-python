"""Add Organization, DataSource, ProjectDataSource models

Revision ID: 9a87573da051
Revises: 9a4011b84ba7
Create Date: 2026-01-14 11:21:27.193295

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '9a87573da051'
down_revision: Union[str, Sequence[str], None] = '9a4011b84ba7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create organizations table
    op.create_table('organizations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('owner_id', sa.String(length=36), nullable=True),
        sa.Column('max_projects', sa.Integer(), nullable=True, default=3),
        sa.Column('max_data_sources', sa.Integer(), nullable=True, default=5),
        sa.Column('max_storage_bytes', sa.BigInteger(), nullable=True, default=500*1024*1024),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_organizations_owner_id'), 'organizations', ['owner_id'], unique=True)

    # Create data_sources table
    op.create_table('data_sources',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('organization_id', sa.String(length=36), nullable=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('source_type', sa.Enum('FILE', 'POSTGRESQL', 'MYSQL', 'SQLSERVER', 'SQLITE', 'SNOWFLAKE', 'BIGQUERY', 'MONGODB', name='datasourcetype'), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'READY', 'ERROR', 'ARCHIVED', name='datasourcestatus'), nullable=True),
        sa.Column('file_path', sa.String(length=500), nullable=True),
        sa.Column('original_filename', sa.String(length=255), nullable=True),
        sa.Column('file_size', sa.BigInteger(), nullable=True),
        sa.Column('file_mime_type', sa.String(length=100), nullable=True),
        sa.Column('host', sa.String(length=255), nullable=True),
        sa.Column('port', sa.Integer(), nullable=True),
        sa.Column('database', sa.String(length=255), nullable=True),
        sa.Column('username', sa.String(length=100), nullable=True),
        sa.Column('encrypted_password', sa.Text(), nullable=True),
        sa.Column('db_schema', sa.String(length=100), nullable=True),
        sa.Column('ssl_enabled', sa.Boolean(), nullable=True),
        sa.Column('config', sa.JSON(), nullable=True),
        sa.Column('schema_cache', sa.JSON(), nullable=True),
        sa.Column('schema_cached_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'name', name='uq_org_datasource_name')
    )
    op.create_index(op.f('ix_data_sources_organization_id'), 'data_sources', ['organization_id'], unique=False)

    # Create project_data_sources table
    op.create_table('project_data_sources',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=True),
        sa.Column('data_source_id', sa.String(length=36), nullable=True),
        sa.Column('status', sa.Enum('LINKED', 'MERGED', 'PENDING_MERGE', name='projectdatasourcestatus'), nullable=True),
        sa.Column('merged_at', sa.DateTime(), nullable=True),
        sa.Column('merged_by_conversation_id', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['data_source_id'], ['data_sources.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id', 'data_source_id', name='uq_project_datasource')
    )
    op.create_index(op.f('ix_project_data_sources_data_source_id'), 'project_data_sources', ['data_source_id'], unique=False)
    op.create_index(op.f('ix_project_data_sources_project_id'), 'project_data_sources', ['project_id'], unique=False)

    # Create project_ontologies table
    op.create_table('project_ontologies',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=True),
        sa.Column('ontology_data', sa.JSON(), nullable=True),
        sa.Column('ontology_hash', sa.String(length=64), nullable=True),
        sa.Column('version', sa.Integer(), nullable=True),
        sa.Column('vector_index_status', sa.String(length=20), nullable=True),
        sa.Column('vector_index_path', sa.String(length=500), nullable=True),
        sa.Column('vector_index_built_at', sa.DateTime(), nullable=True),
        sa.Column('vector_index_error', sa.Text(), nullable=True),
        sa.Column('merged_data_source_ids', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_project_ontologies_ontology_hash'), 'project_ontologies', ['ontology_hash'], unique=False)
    op.create_index(op.f('ix_project_ontologies_project_id'), 'project_ontologies', ['project_id'], unique=True)

    # Add organization_id to projects table
    op.add_column('projects', sa.Column('organization_id', sa.String(length=36), nullable=True))
    op.create_index(op.f('ix_projects_organization_id'), 'projects', ['organization_id'], unique=False)
    op.create_foreign_key('fk_projects_organization_id', 'projects', 'organizations', ['organization_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    # Remove organization_id from projects
    op.drop_constraint('fk_projects_organization_id', 'projects', type_='foreignkey')
    op.drop_index(op.f('ix_projects_organization_id'), table_name='projects')
    op.drop_column('projects', 'organization_id')

    # Drop project_ontologies table
    op.drop_index(op.f('ix_project_ontologies_project_id'), table_name='project_ontologies')
    op.drop_index(op.f('ix_project_ontologies_ontology_hash'), table_name='project_ontologies')
    op.drop_table('project_ontologies')

    # Drop project_data_sources table
    op.drop_index(op.f('ix_project_data_sources_project_id'), table_name='project_data_sources')
    op.drop_index(op.f('ix_project_data_sources_data_source_id'), table_name='project_data_sources')
    op.drop_table('project_data_sources')

    # Drop data_sources table
    op.drop_index(op.f('ix_data_sources_organization_id'), table_name='data_sources')
    op.drop_table('data_sources')

    # Drop organizations table
    op.drop_index(op.f('ix_organizations_owner_id'), table_name='organizations')
    op.drop_table('organizations')
