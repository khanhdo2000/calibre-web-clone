"""RSS Feeds API routes"""
import os
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.rss_feed import RssFeed, RssGeneratedBook
from app.services.rss_epub import RssFetcher, EpubGenerator
from app.services.rss_epub.scheduler import get_rss_scheduler

router = APIRouter(prefix="/api/rss", tags=["RSS Feeds"])


# Pydantic schemas
class RssFeedCreate(BaseModel):
    name: str
    url: HttpUrl
    category: Optional[str] = None
    max_articles: int = 20
    enabled: bool = True


class RssFeedUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[HttpUrl] = None
    category: Optional[str] = None
    max_articles: Optional[int] = None
    enabled: Optional[bool] = None


class RssFeedResponse(BaseModel):
    id: int
    name: str
    url: str
    category: Optional[str]
    max_articles: int
    enabled: bool

    class Config:
        from_attributes = True


class RssGeneratedBookResponse(BaseModel):
    id: int
    feed_id: int
    title: str
    filename: str
    file_size: Optional[int]
    article_count: int
    generation_date: date
    calibre_book_id: Optional[int]

    class Config:
        from_attributes = True


class GenerateResponse(BaseModel):
    success: bool
    files_generated: int
    files: List[str]


# Routes
@router.get("/feeds", response_model=List[RssFeedResponse])
async def list_feeds(
    enabled_only: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """List all configured RSS feeds"""
    query = select(RssFeed)
    if enabled_only:
        query = query.where(RssFeed.enabled == True)
    query = query.order_by(RssFeed.name)

    result = await db.execute(query)
    return result.scalars().all()


@router.post("/feeds", response_model=RssFeedResponse)
async def create_feed(
    feed: RssFeedCreate,
    db: AsyncSession = Depends(get_db)
):
    """Add a new RSS feed"""
    # Check if URL already exists
    existing = await db.execute(
        select(RssFeed).where(RssFeed.url == str(feed.url))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Feed URL already exists")

    new_feed = RssFeed(
        name=feed.name,
        url=str(feed.url),
        category=feed.category,
        max_articles=feed.max_articles,
        enabled=feed.enabled
    )
    db.add(new_feed)
    await db.commit()
    await db.refresh(new_feed)

    return new_feed


@router.get("/feeds/{feed_id}", response_model=RssFeedResponse)
async def get_feed(
    feed_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific RSS feed"""
    result = await db.execute(
        select(RssFeed).where(RssFeed.id == feed_id)
    )
    feed = result.scalar_one_or_none()
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")
    return feed


@router.put("/feeds/{feed_id}", response_model=RssFeedResponse)
async def update_feed(
    feed_id: int,
    updates: RssFeedUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update an RSS feed"""
    result = await db.execute(
        select(RssFeed).where(RssFeed.id == feed_id)
    )
    feed = result.scalar_one_or_none()
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")

    update_data = updates.model_dump(exclude_unset=True)
    if "url" in update_data:
        update_data["url"] = str(update_data["url"])

    for key, value in update_data.items():
        setattr(feed, key, value)

    await db.commit()
    await db.refresh(feed)
    return feed


@router.delete("/feeds/{feed_id}")
async def delete_feed(
    feed_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete an RSS feed"""
    result = await db.execute(
        select(RssFeed).where(RssFeed.id == feed_id)
    )
    feed = result.scalar_one_or_none()
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")

    await db.execute(delete(RssFeed).where(RssFeed.id == feed_id))
    await db.commit()

    return {"success": True, "message": f"Feed '{feed.name}' deleted"}


@router.post("/generate", response_model=GenerateResponse)
async def generate_all(
    db: AsyncSession = Depends(get_db)
):
    """Manually trigger EPUB generation for all enabled feeds"""
    scheduler = get_rss_scheduler()
    if not scheduler:
        raise HTTPException(
            status_code=503,
            detail="RSS scheduler not initialized"
        )

    files = await scheduler.generate_now(db)
    return GenerateResponse(
        success=True,
        files_generated=len(files),
        files=files
    )


@router.post("/generate/{feed_id}", response_model=GenerateResponse)
async def generate_single(
    feed_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Generate EPUB for a specific feed"""
    result = await db.execute(
        select(RssFeed).where(RssFeed.id == feed_id)
    )
    feed = result.scalar_one_or_none()
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")

    scheduler = get_rss_scheduler()
    if not scheduler:
        raise HTTPException(
            status_code=503,
            detail="RSS scheduler not initialized"
        )

    filepath = await scheduler.generate_feed(db, feed)
    files = [filepath] if filepath else []

    return GenerateResponse(
        success=bool(filepath),
        files_generated=len(files),
        files=files
    )


@router.get("/books", response_model=List[RssGeneratedBookResponse])
async def list_generated_books(
    feed_id: Optional[int] = None,
    limit: int = Query(50, le=100),
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """List generated EPUB books"""
    query = select(RssGeneratedBook)

    if feed_id:
        query = query.where(RssGeneratedBook.feed_id == feed_id)

    query = query.order_by(RssGeneratedBook.generation_date.desc())
    query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/books/{book_id}/download")
async def download_book(
    book_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Download a generated EPUB book"""
    result = await db.execute(
        select(RssGeneratedBook).where(RssGeneratedBook.id == book_id)
    )
    book = result.scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    if not os.path.exists(book.file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    return FileResponse(
        path=book.file_path,
        filename=book.filename,
        media_type="application/epub+zip"
    )


@router.delete("/books/{book_id}")
async def delete_book(
    book_id: int,
    delete_file: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """Delete a generated book record and optionally the file"""
    result = await db.execute(
        select(RssGeneratedBook).where(RssGeneratedBook.id == book_id)
    )
    book = result.scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Delete file if requested
    if delete_file and os.path.exists(book.file_path):
        try:
            os.remove(book.file_path)
        except OSError as e:
            # Log but don't fail
            pass

    await db.execute(delete(RssGeneratedBook).where(RssGeneratedBook.id == book_id))
    await db.commit()

    return {"success": True, "message": f"Book '{book.title}' deleted"}


@router.get("/preview/{feed_id}")
async def preview_feed(
    feed_id: int,
    max_articles: int = Query(5, le=20),
    db: AsyncSession = Depends(get_db)
):
    """Preview articles from a feed without generating EPUB"""
    result = await db.execute(
        select(RssFeed).where(RssFeed.id == feed_id)
    )
    feed = result.scalar_one_or_none()
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")

    fetcher = RssFetcher()
    try:
        articles = fetcher.fetch_feed(feed.url, max_articles=max_articles)
        return {
            "feed_name": feed.name,
            "feed_url": feed.url,
            "article_count": len(articles),
            "articles": [
                {
                    "title": a.title,
                    "url": a.url,
                    "author": a.author,
                    "published": a.published.isoformat() if a.published else None,
                    "summary": a.summary
                }
                for a in articles
            ]
        }
    finally:
        fetcher.close()
