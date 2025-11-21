"""Make username optional in users table

Revision ID: 004
Revises: 003
Create Date: 2024-01-16 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Make username nullable
    op.alter_column('users', 'username',
                    existing_type=sa.String(),
                    nullable=True)


def downgrade() -> None:
    # Before making it non-nullable, we need to ensure all users have a username
    # Generate username from email for any NULL usernames
    op.execute("""
        UPDATE users 
        SET username = SPLIT_PART(email, '@', 1) 
        WHERE username IS NULL
    """)
    op.alter_column('users', 'username',
                    existing_type=sa.String(),
                    nullable=False)



