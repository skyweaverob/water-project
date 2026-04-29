"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-04-28
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")
    # All tables are created from metadata in env.py via SQLAlchemy. This migration just installs
    # the required extensions; subsequent migrations track schema deltas. For dev convenience,
    # use `python -m app.scripts.create_all` to provision all tables from models.


def downgrade() -> None:
    pass
