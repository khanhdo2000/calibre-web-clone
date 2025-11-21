from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from app.database import Base


# Association table for categories and tags (from Calibre database)
category_tags = Table(
    'category_tags',
    Base.metadata,
    Column('category_id', Integer, ForeignKey('categories.id', ondelete='CASCADE'), primary_key=True),
    Column('tag_id', Integer, primary_key=True),  # References tags.id from Calibre DB
)


class Category(Base):
    """Category model for grouping tags together"""
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    display_order = Column(Integer, nullable=False, default=0, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# Pydantic models for API

class TagInfo(BaseModel):
    """Tag information for category display"""
    id: int
    name: str

    class Config:
        from_attributes = True


class CategoryBase(BaseModel):
    """Base category schema"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    display_order: Optional[int] = Field(default=0, description="Order for displaying categories")


class CategoryCreate(CategoryBase):
    """Schema for creating a category"""
    tag_ids: List[int] = Field(default_factory=list, description="List of tag IDs to include in this category")


class CategoryUpdate(BaseModel):
    """Schema for updating a category"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    tag_ids: Optional[List[int]] = None
    display_order: Optional[int] = None


class CategoryResponse(CategoryBase):
    """Schema for category response"""
    id: int
    created_at: datetime
    updated_at: datetime
    tags: List[TagInfo] = Field(default_factory=list)
    book_count: Optional[int] = None

    class Config:
        from_attributes = True


class CategoryList(BaseModel):
    """Schema for list of categories"""
    categories: List[CategoryResponse]
    total: int
