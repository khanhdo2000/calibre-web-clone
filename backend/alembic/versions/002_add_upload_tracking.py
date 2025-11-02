"""Add upload tracking table

Revision ID: 002
Revises: 001
Create Date: 2024-01-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'upload_tracking',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('book_id', sa.Integer(), nullable=False),
        sa.Column('book_path', sa.String(), nullable=False),
        sa.Column('file_type', sa.String(), nullable=False),
        sa.Column('storage_type', sa.String(), nullable=False),
        sa.Column('storage_url', sa.String(), nullable=True),
        sa.Column('upload_date', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('file_size', sa.BigInteger(), nullable=True),
        sa.Column('checksum', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('book_id', 'file_type', 'storage_type', name='uq_book_file_storage')
    )
    op.create_index(op.f('ix_upload_tracking_id'), 'upload_tracking', ['id'], unique=False)
    op.create_index(op.f('ix_upload_tracking_book_id'), 'upload_tracking', ['book_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_upload_tracking_book_id'), table_name='upload_tracking')
    op.drop_index(op.f('ix_upload_tracking_id'), table_name='upload_tracking')
    op.drop_table('upload_tracking')

