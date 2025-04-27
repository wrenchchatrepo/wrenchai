"""Update schema with UUID support and consolidated models

Revision ID: 2a2c0d4b5e6f
Revises: 1a1c0d3b4e5f
Create Date: 2024-03-28 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision: str = '2a2c0d4b5e6f'
down_revision: Union[str, None] = '1a1c0d3b4e5f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Create users table with UUID
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255)),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_superuser', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    )
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_users_id', 'users', ['id'])

    # Create agents table
    op.create_table(
        'agents',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('role', sa.String(50), nullable=False),
        sa.Column('config', sa.JSON(), nullable=False, default={}),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('owner_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    )
    op.create_index('ix_agents_id', 'agents', ['id'])
    op.create_index('ix_agents_role', 'agents', ['role'])
    op.create_index('ix_agents_owner_id', 'agents', ['owner_id'])

    # Create tasks table
    op.create_table(
        'tasks',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('agent_id', sa.String(36), sa.ForeignKey('agents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('task_type', sa.String(50), nullable=False),
        sa.Column('input_data', sa.JSON(), nullable=False),
        sa.Column('config', sa.JSON(), nullable=False, default={}),
        sa.Column('status', sa.String(20), nullable=False, default='pending'),
        sa.Column('progress', sa.Float(), nullable=False, default=0.0),
        sa.Column('message', sa.String(500)),
        sa.Column('result', sa.JSON()),
        sa.Column('error', sa.String(500)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    )
    op.create_index('ix_tasks_id', 'tasks', ['id'])
    op.create_index('ix_tasks_agent_id', 'tasks', ['agent_id'])
    op.create_index('ix_tasks_task_type', 'tasks', ['task_type'])
    op.create_index('ix_tasks_status', 'tasks', ['status'])

    # Create task_executions table
    op.create_table(
        'task_executions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('task_id', sa.String(36), sa.ForeignKey('tasks.id', ondelete='CASCADE'), nullable=False),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True)),
        sa.Column('status', sa.String(20), nullable=False, default='running'),
        sa.Column('metrics', sa.JSON()),
        sa.Column('logs', sa.String(5000)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    )
    op.create_index('ix_task_executions_id', 'task_executions', ['id'])
    op.create_index('ix_task_executions_task_id', 'task_executions', ['task_id'])
    op.create_index('ix_task_executions_status', 'task_executions', ['status'])

def downgrade() -> None:
    op.drop_table('task_executions')
    op.drop_table('tasks')
    op.drop_table('agents')
    op.drop_table('users') 