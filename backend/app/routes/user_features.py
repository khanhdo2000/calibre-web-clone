from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models.user import User, Favorite, ReadingProgress, ReadingList, ReadingListItem
from app.models.book import Book
from app.routes.auth import get_current_user
from app.services.calibre_db import calibre_db
from app.routes.books import get_cover_urls_map
from app.config import settings

router = APIRouter(prefix="/api/user", tags=["user-features"])


# Pydantic models
class FavoriteResponse(BaseModel):
    id: int
    book_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class ReadingProgressResponse(BaseModel):
    id: int
    book_id: int
    progress: int
    current_location: Optional[str]
    last_read: datetime

    class Config:
        from_attributes = True


class ReadingProgressUpdate(BaseModel):
    progress: int
    current_location: Optional[str] = None


class ReadingListResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_at: datetime
    book_count: int = 0

    class Config:
        from_attributes = True


class ReadingListCreate(BaseModel):
    name: str
    description: Optional[str] = None


class ReadingListItemResponse(BaseModel):
    id: int
    book_id: int
    order: int

    class Config:
        from_attributes = True


# Favorites
@router.get("/favorites", response_model=List[FavoriteResponse])
async def get_favorites(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's favorite books"""
    result = await db.execute(
        select(Favorite)
        .where(Favorite.user_id == current_user.id)
        .order_by(Favorite.created_at.desc())
    )
    favorites = result.scalars().all()
    return favorites


@router.post("/favorites/{book_id}", response_model=FavoriteResponse)
async def add_favorite(
    book_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add a book to favorites"""
    # Check if already favorited
    result = await db.execute(
        select(Favorite).where(
            Favorite.user_id == current_user.id,
            Favorite.book_id == book_id
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        return existing

    # Add to favorites
    favorite = Favorite(user_id=current_user.id, book_id=book_id)
    db.add(favorite)
    await db.commit()
    await db.refresh(favorite)

    return favorite


@router.delete("/favorites/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_favorite(
    book_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove a book from favorites"""
    await db.execute(
        delete(Favorite).where(
            Favorite.user_id == current_user.id,
            Favorite.book_id == book_id
        )
    )
    await db.commit()


@router.get("/favorites/books", response_model=List[Book])
async def get_favorites_with_books(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's favorite books with full book data - optimized single call"""
    # Get favorite book IDs
    result = await db.execute(
        select(Favorite.book_id)
        .where(Favorite.user_id == current_user.id)
        .order_by(Favorite.created_at.desc())
    )
    book_ids = [row[0] for row in result.all()]

    if not book_ids:
        return []

    # Fetch all books at once
    books = []
    for book_id in book_ids:
        try:
            book = calibre_db.get_book(book_id)
            if book:
                books.append(book)
        except Exception:
            # Skip books that can't be loaded
            continue

    # Get S3 cover URLs for books that have covers
    book_ids_with_covers = [book.id for book in books if book.has_cover]
    if book_ids_with_covers and settings.s3_bucket_name:
        # Get thumbnails for list view
        thumb_urls_map = await get_cover_urls_map(
            db,
            book_ids_with_covers,
            bucket=settings.s3_bucket_name,
            region=settings.aws_region,
            use_thumbnail=True
        )
        # Get full-size covers as fallback
        full_size_urls_map = await get_cover_urls_map(
            db,
            book_ids_with_covers,
            bucket=settings.s3_bucket_name,
            region=settings.aws_region,
            use_thumbnail=False
        )

        # Assign cover URLs to books
        for book in books:
            if book.has_cover:
                book.cover_thumb_url = thumb_urls_map.get(book.id)
                book.cover_url = full_size_urls_map.get(book.id)

    return books


# Reading Progress
@router.get("/progress", response_model=List[ReadingProgressResponse])
async def get_all_progress(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all reading progress for user"""
    result = await db.execute(
        select(ReadingProgress)
        .where(ReadingProgress.user_id == current_user.id)
        .order_by(ReadingProgress.last_read.desc())
    )
    progress_list = result.scalars().all()
    return progress_list


@router.get("/progress/{book_id}", response_model=Optional[ReadingProgressResponse])
async def get_progress(
    book_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get reading progress for a specific book"""
    result = await db.execute(
        select(ReadingProgress).where(
            ReadingProgress.user_id == current_user.id,
            ReadingProgress.book_id == book_id
        )
    )
    progress = result.scalar_one_or_none()
    return progress


@router.put("/progress/{book_id}", response_model=ReadingProgressResponse)
async def update_progress(
    book_id: int,
    progress_data: ReadingProgressUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update reading progress for a book"""
    # Get existing progress
    result = await db.execute(
        select(ReadingProgress).where(
            ReadingProgress.user_id == current_user.id,
            ReadingProgress.book_id == book_id
        )
    )
    progress = result.scalar_one_or_none()

    if progress:
        # Update existing
        progress.progress = progress_data.progress
        progress.current_location = progress_data.current_location
        progress.last_read = datetime.utcnow()
    else:
        # Create new
        progress = ReadingProgress(
            user_id=current_user.id,
            book_id=book_id,
            progress=progress_data.progress,
            current_location=progress_data.current_location
        )
        db.add(progress)

    await db.commit()
    await db.refresh(progress)

    return progress


# Reading Lists
@router.get("/reading-lists", response_model=List[ReadingListResponse])
async def get_reading_lists(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all reading lists for user"""
    result = await db.execute(
        select(ReadingList)
        .where(ReadingList.user_id == current_user.id)
        .order_by(ReadingList.created_at.desc())
    )
    lists = result.scalars().all()

    # Add book count to each list
    response = []
    for reading_list in lists:
        count_result = await db.execute(
            select(ReadingListItem).where(ReadingListItem.reading_list_id == reading_list.id)
        )
        count = len(count_result.scalars().all())

        response.append(
            ReadingListResponse(
                id=reading_list.id,
                name=reading_list.name,
                description=reading_list.description,
                created_at=reading_list.created_at,
                book_count=count
            )
        )

    return response


@router.post("/reading-lists", response_model=ReadingListResponse)
async def create_reading_list(
    list_data: ReadingListCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new reading list"""
    reading_list = ReadingList(
        user_id=current_user.id,
        name=list_data.name,
        description=list_data.description
    )
    db.add(reading_list)
    await db.commit()
    await db.refresh(reading_list)

    return ReadingListResponse(
        id=reading_list.id,
        name=reading_list.name,
        description=reading_list.description,
        created_at=reading_list.created_at,
        book_count=0
    )


@router.delete("/reading-lists/{list_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reading_list(
    list_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a reading list"""
    result = await db.execute(
        select(ReadingList).where(
            ReadingList.id == list_id,
            ReadingList.user_id == current_user.id
        )
    )
    reading_list = result.scalar_one_or_none()

    if not reading_list:
        raise HTTPException(status_code=404, detail="Reading list not found")

    await db.delete(reading_list)
    await db.commit()


@router.get("/reading-lists/{list_id}/books", response_model=List[ReadingListItemResponse])
async def get_reading_list_books(
    list_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all books in a reading list"""
    # Verify ownership
    result = await db.execute(
        select(ReadingList).where(
            ReadingList.id == list_id,
            ReadingList.user_id == current_user.id
        )
    )
    reading_list = result.scalar_one_or_none()

    if not reading_list:
        raise HTTPException(status_code=404, detail="Reading list not found")

    # Get items
    result = await db.execute(
        select(ReadingListItem)
        .where(ReadingListItem.reading_list_id == list_id)
        .order_by(ReadingListItem.order)
    )
    items = result.scalars().all()

    return items


@router.post("/reading-lists/{list_id}/books/{book_id}", response_model=ReadingListItemResponse)
async def add_book_to_reading_list(
    list_id: int,
    book_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add a book to a reading list"""
    # Verify ownership
    result = await db.execute(
        select(ReadingList).where(
            ReadingList.id == list_id,
            ReadingList.user_id == current_user.id
        )
    )
    reading_list = result.scalar_one_or_none()

    if not reading_list:
        raise HTTPException(status_code=404, detail="Reading list not found")

    # Check if book already in list
    result = await db.execute(
        select(ReadingListItem).where(
            ReadingListItem.reading_list_id == list_id,
            ReadingListItem.book_id == book_id
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        return existing

    # Get next order number
    result = await db.execute(
        select(ReadingListItem)
        .where(ReadingListItem.reading_list_id == list_id)
        .order_by(ReadingListItem.order.desc())
    )
    last_item = result.scalar_one_or_none()
    next_order = (last_item.order + 1) if last_item else 0

    # Add book
    item = ReadingListItem(
        reading_list_id=list_id,
        book_id=book_id,
        order=next_order
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)

    return item


@router.delete("/reading-lists/{list_id}/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_book_from_reading_list(
    list_id: int,
    book_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove a book from a reading list"""
    # Verify ownership
    result = await db.execute(
        select(ReadingList).where(
            ReadingList.id == list_id,
            ReadingList.user_id == current_user.id
        )
    )
    reading_list = result.scalar_one_or_none()

    if not reading_list:
        raise HTTPException(status_code=404, detail="Reading list not found")

    # Remove book
    await db.execute(
        delete(ReadingListItem).where(
            ReadingListItem.reading_list_id == list_id,
            ReadingListItem.book_id == book_id
        )
    )
    await db.commit()
