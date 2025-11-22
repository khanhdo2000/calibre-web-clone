from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Date
from sqlalchemy.sql import func

from app.database import Base


class RssFeed(Base):
    """RSS feed configuration for daily EPUB generation"""
    __tablename__ = "rss_feeds"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)  # Display name (e.g., "VnExpress")
    url = Column(String(1024), nullable=False, unique=True)  # RSS feed URL
    category = Column(String(100), nullable=True)  # Category/tag for generated books
    max_articles = Column(Integer, default=50)  # Max articles per EPUB
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class RssGeneratedBook(Base):
    """Track generated EPUB files from RSS feeds"""
    __tablename__ = "rss_generated_books"

    id = Column(Integer, primary_key=True, index=True)
    feed_id = Column(Integer, nullable=False, index=True)  # Reference to RssFeed
    title = Column(String(500), nullable=False)  # Generated book title
    filename = Column(String(500), nullable=False, unique=True)  # Local filename
    file_path = Column(String(1024), nullable=False)  # Full path to EPUB
    file_size = Column(Integer, nullable=True)  # File size in bytes
    article_count = Column(Integer, default=0)  # Number of articles included
    generation_date = Column(Date, nullable=False, index=True)  # Date of generation
    calibre_book_id = Column(Integer, nullable=True)  # ID if added to Calibre
    created_at = Column(DateTime(timezone=True), server_default=func.now())
