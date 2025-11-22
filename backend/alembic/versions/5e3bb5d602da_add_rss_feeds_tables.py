"""add_rss_feeds_tables

Revision ID: 5e3bb5d602da
Revises: 008
Create Date: 2025-11-21 16:10:43.924226

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '5e3bb5d602da'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('rss_feeds',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('url', sa.String(length=1024), nullable=False),
    sa.Column('category', sa.String(length=100), nullable=True),
    sa.Column('max_articles', sa.Integer(), nullable=True),
    sa.Column('enabled', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('url')
    )
    op.create_index(op.f('ix_rss_feeds_id'), 'rss_feeds', ['id'], unique=False)
    op.create_table('rss_generated_books',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('feed_id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=500), nullable=False),
    sa.Column('filename', sa.String(length=500), nullable=False),
    sa.Column('file_path', sa.String(length=1024), nullable=False),
    sa.Column('file_size', sa.Integer(), nullable=True),
    sa.Column('article_count', sa.Integer(), nullable=True),
    sa.Column('generation_date', sa.Date(), nullable=False),
    sa.Column('calibre_book_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('filename')
    )
    op.create_index(op.f('ix_rss_generated_books_feed_id'), 'rss_generated_books', ['feed_id'], unique=False)
    op.create_index(op.f('ix_rss_generated_books_generation_date'), 'rss_generated_books', ['generation_date'], unique=False)
    op.create_index(op.f('ix_rss_generated_books_id'), 'rss_generated_books', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_rss_generated_books_id'), table_name='rss_generated_books')
    op.drop_index(op.f('ix_rss_generated_books_generation_date'), table_name='rss_generated_books')
    op.drop_index(op.f('ix_rss_generated_books_feed_id'), table_name='rss_generated_books')
    op.drop_table('rss_generated_books')
    op.drop_index(op.f('ix_rss_feeds_id'), table_name='rss_feeds')
    op.drop_table('rss_feeds')
