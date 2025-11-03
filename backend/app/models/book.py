from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class Author(BaseModel):
    id: int
    name: str
    count: Optional[int] = None


class Tag(BaseModel):
    id: int
    name: str
    count: Optional[int] = None


class Series(BaseModel):
    id: int
    name: str
    index: Optional[float] = None
    count: Optional[int] = None


class Publisher(BaseModel):
    id: int
    name: str
    count: Optional[int] = None


class Category(BaseModel):
    """Category model for displaying tags as categories with book counts"""
    id: int
    name: str
    count: int = 0


class Book(BaseModel):
    id: int
    title: str
    authors: List[Author] = []
    tags: List[Tag] = []
    series: Optional[Series] = None
    publisher: Optional[Publisher] = None
    pubdate: Optional[datetime] = None
    timestamp: Optional[datetime] = None
    last_modified: Optional[datetime] = None
    path: str
    has_cover: bool = False
    cover_url: Optional[str] = None  # S3 URL if cover is uploaded to S3 (full-size)
    cover_thumb_url: Optional[str] = None  # S3 URL for thumbnail (optimized for list view)
    uuid: Optional[str] = None
    isbn: Optional[str] = None
    lccn: Optional[str] = None
    rating: Optional[float] = None
    file_formats: List[str] = []
    file_size: Optional[int] = None
    comments: Optional[str] = None

    class Config:
        from_attributes = True


class BookDetail(Book):
    """Extended book information with full metadata"""
    languages: List[str] = []
    identifiers: dict = {}


class BookListResponse(BaseModel):
    total: int
    page: int
    per_page: int
    books: List[Book]


class SearchResult(BaseModel):
    books: List[Book]
    total: int
    query: str
