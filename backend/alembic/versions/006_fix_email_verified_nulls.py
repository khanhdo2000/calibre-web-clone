"""fix email_verified null values

Revision ID: 006
Revises: 005
Create Date: 2024-11-20

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Update any NULL email_verified values to False
    op.execute("UPDATE users SET email_verified = false WHERE email_verified IS NULL")


def downgrade() -> None:
    # No downgrade needed - we don't want to revert data changes
    pass
