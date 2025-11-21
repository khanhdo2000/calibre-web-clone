"""Add kindle_email to users table

Revision ID: 003
Revises: 002
Create Date: 2024-01-15 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('kindle_email', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'kindle_email')

