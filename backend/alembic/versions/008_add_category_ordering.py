"""add category ordering

Revision ID: 008_add_category_ordering
Revises: 007_add_categories
Create Date: 2025-11-21

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '008_add_category_ordering'
down_revision = '007_add_categories'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add display_order column to categories table
    op.add_column('categories', sa.Column('display_order', sa.Integer(), nullable=True))

    # Set default ordering based on current id order
    op.execute("""
        UPDATE categories
        SET display_order = id * 10
    """)

    # Make display_order not nullable after setting values
    op.alter_column('categories', 'display_order', nullable=False)

    # Add index for faster ordering queries
    op.create_index('ix_categories_display_order', 'categories', ['display_order'])


def downgrade() -> None:
    op.drop_index('ix_categories_display_order', table_name='categories')
    op.drop_column('categories', 'display_order')
