from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional

from app.database import Base


class User(Base):
    """User model for authentication and personalization"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=True)  # Optional, can be derived from email
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    kindle_email = Column(String, nullable=True)  # User's Kindle email address
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    email_verified = Column(Boolean, default=False)  # Email verification status
    verification_token = Column(String, nullable=True)  # Token for email verification
    verification_token_expires = Column(DateTime(timezone=True), nullable=True)  # Token expiration
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    favorites = relationship("Favorite", back_populates="user", cascade="all, delete-orphan")
    reading_progress = relationship("ReadingProgress", back_populates="user", cascade="all, delete-orphan")
    reading_lists = relationship("ReadingList", back_populates="user", cascade="all, delete-orphan")


class Favorite(Base):
    """User's favorite books"""
    __tablename__ = "favorites"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    book_id = Column(Integer, nullable=False, index=True)  # Calibre book ID
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="favorites")

    # Unique constraint: one favorite per user per book
    __table_args__ = (
        {"schema": None},
    )


class ReadingProgress(Base):
    """Track reading progress for each book"""
    __tablename__ = "reading_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    book_id = Column(Integer, nullable=False, index=True)  # Calibre book ID
    progress = Column(Integer, default=0)  # Percentage (0-100)
    current_location = Column(String)  # EPUB CFI or page number
    last_read = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="reading_progress")


class ReadingList(Base):
    """User's custom reading lists"""
    __tablename__ = "reading_lists"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="reading_lists")
    items = relationship("ReadingListItem", back_populates="reading_list", cascade="all, delete-orphan")


class ReadingListItem(Base):
    """Items in a reading list"""
    __tablename__ = "reading_list_items"

    id = Column(Integer, primary_key=True, index=True)
    reading_list_id = Column(Integer, ForeignKey("reading_lists.id"), nullable=False)
    book_id = Column(Integer, nullable=False)  # Calibre book ID
    order = Column(Integer, default=0)
    added_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    reading_list = relationship("ReadingList", back_populates="items")
