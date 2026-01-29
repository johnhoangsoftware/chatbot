"""init_rag_schema

Revision ID: 0001_rag_schema
Revises:
Create Date: 2026-01-28
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0001_rag_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";")

    # Users
    op.create_table(
        'users',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('email', sa.Text(), unique=True, nullable=False),
        sa.Column('name', sa.Text()),
        sa.Column('role', sa.Text(), nullable=False, server_default='user'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('NOW()'))
    )

    # Projects
    op.create_table(
        'projects',
        sa.Column('project_id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('owner_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.user_id')),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('NOW()'))
    )

    # Permissions
    op.create_table(
        'permissions',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.user_id', ondelete="CASCADE"), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.project_id', ondelete="CASCADE"), nullable=False),
        sa.Column('read_allowed', sa.Boolean(), server_default=sa.text('TRUE')),
        sa.Column('write_allowed', sa.Boolean(), server_default=sa.text('FALSE')),
        sa.PrimaryKeyConstraint('user_id', 'project_id')
    )

    # Project Versions
    op.create_table(
        'project_versions',
        sa.Column('version_id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.project_id', ondelete="CASCADE")),
        sa.Column('version_number', sa.Text(), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('NOW()')),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('TRUE'))
    )

    # Files
    op.create_table(
        'files',
        sa.Column('file_id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.project_id', ondelete="CASCADE")),
        sa.Column('version_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('project_versions.version_id', ondelete="CASCADE")),
        sa.Column('uploader_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.user_id')),
        sa.Column('filename', sa.Text(), nullable=False),
        sa.Column('filepath', sa.Text(), nullable=False),
        sa.Column('filetype', sa.Text(), nullable=False),
        sa.Column('status', sa.Text(), nullable=False, server_default='uploaded'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('NOW()'))
    )

    # Parsed documents
    op.create_table(
        'parsed_documents',
        sa.Column('doc_id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('file_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('files.file_id', ondelete="CASCADE")),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.project_id', ondelete="CASCADE")),
        sa.Column('version_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('project_versions.version_id', ondelete="CASCADE")),
        sa.Column('content_json', postgresql.JSONB(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('NOW()'))
    )

    # Chunks
    op.create_table(
        'chunks',
        sa.Column('chunk_id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('doc_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('parsed_documents.doc_id', ondelete="CASCADE")),
        sa.Column('file_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('files.file_id', ondelete="CASCADE")),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.project_id', ondelete="CASCADE")),
        sa.Column('version_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('project_versions.version_id', ondelete="CASCADE")),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('content_type', sa.Text(), nullable=False, server_default='semantic'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('NOW()'))
    )

    # Traces
    op.create_table(
        'traces',
        sa.Column('trace_id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('query', sa.Text(), nullable=False),
        sa.Column('answer', sa.Text(), nullable=False),
        sa.Column('similarity', sa.Float()),
        sa.Column('embedding_id', sa.Text(), nullable=False),
        sa.Column('chunk_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('chunks.chunk_id', ondelete="CASCADE")),
        sa.Column('file_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('files.file_id')),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.project_id')),
        sa.Column('version_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('project_versions.version_id')),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('NOW()'))
    )

    # Indexes
    op.create_index('idx_files_project', 'files', ['project_id'])
    op.create_index('idx_files_version', 'files', ['version_id'])
    op.create_index('idx_docs_project', 'parsed_documents', ['project_id'])
    op.create_index('idx_docs_version', 'parsed_documents', ['version_id'])
    op.create_index('idx_chunks_project', 'chunks', ['project_id'])
    op.create_index('idx_chunks_version', 'chunks', ['version_id'])
    op.create_index('idx_traces_project', 'traces', ['project_id'])
    op.create_index('idx_traces_version', 'traces', ['version_id'])


def downgrade():
    op.drop_table('traces')
    op.drop_table('chunks')
    op.drop_table('parsed_documents')
    op.drop_table('files')
    op.drop_table('project_versions')
    op.drop_table('permissions')
    op.drop_table('projects')
    op.drop_table('users')
