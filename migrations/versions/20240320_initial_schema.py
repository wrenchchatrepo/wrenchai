"""Initial database schema

Revision ID: 1a1c0d3b4e5f
Revises: 
Create Date: 2024-03-20 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision: str = '1a1c0d3b4e5f'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('user', sa.String(length=255), nullable=False),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('table_name', sa.String(length=255), nullable=False),
        sa.Column('query', sa.Text(), nullable=False),
        sa.Column('affected_rows', sa.Integer(), nullable=False),
        sa.Column('execution_time', sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_audit_logs_timestamp', 'audit_logs', ['timestamp'])
    op.create_index('idx_audit_logs_user', 'audit_logs', ['user'])

    # Create query_metrics table
    op.create_table(
        'query_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('query_hash', sa.String(length=64), nullable=False),
        sa.Column('normalized_query', sa.Text(), nullable=False),
        sa.Column('execution_count', sa.Integer(), nullable=False, default=0),
        sa.Column('total_execution_time', sa.Float(), nullable=False, default=0.0),
        sa.Column('avg_execution_time', sa.Float(), nullable=False, default=0.0),
        sa.Column('min_execution_time', sa.Float(), nullable=False),
        sa.Column('max_execution_time', sa.Float(), nullable=False),
        sa.Column('last_executed', sa.DateTime(), nullable=False),
        sa.Column('row_count', sa.Integer(), nullable=False, default=0),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('query_hash')
    )
    op.create_index('idx_query_metrics_hash', 'query_metrics', ['query_hash'])
    op.create_index('idx_query_metrics_last_executed', 'query_metrics', ['last_executed'])

    # Create schema_versions table
    op.create_table(
        'schema_versions',
        sa.Column('version_id', sa.String(length=32), nullable=False),
        sa.Column('applied_at', sa.DateTime(), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=False),
        sa.Column('checksum', sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint('version_id')
    )

def downgrade() -> None:
    op.drop_table('schema_versions')
    op.drop_table('query_metrics')
    op.drop_table('audit_logs') 