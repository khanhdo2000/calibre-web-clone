from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, List, Dict
import logging

from app.models.book import Book, BookDetail, BookListResponse, SearchResult
from app.services.calibre_db import calibre_db, get_book_with_cloud_formats
from app.services.cache import cache_service
from app.config import settings
from app.database import get_db
from app.models.upload_tracking import UploadTracking
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

router = APIRouter(prefix="/api/books", tags=["books"])
logger = logging.getLogger(__name__)


def build_s3_cover_url(storage_url: str, bucket: str, region: str) -> str:
    """Build S3 public URL for cover image"""
    # Format: https://s3.{region}.amazonaws.com/{bucket}/{storage_url}
    # Example: https://s3.ap-southeast-1.amazonaws.com/cdn.mnd.vn/covers/11.jpg
    return f"https://s3.{region}.amazonaws.com/{bucket}/{storage_url}"


async def get_cover_urls_map(
    db: AsyncSession,
    book_ids: List[int],
    bucket: Optional[str] = None,
    region: str = "ap-southeast-1",
    use_thumbnail: bool = False
) -> Dict[int, str]:
    """Get S3 cover URLs for a list of book IDs
    
    Args:
        db: Database session
        book_ids: List of book IDs to fetch
        bucket: S3 bucket name
        region: AWS region
        use_thumbnail: If True, fetch thumbnails; if False, fetch full-size covers
    """
    if not book_ids or not bucket:
        return {}
    
    try:
        file_type = "cover_thumb" if use_thumbnail else "cover"
        result = await db.execute(
            select(UploadTracking.book_id, UploadTracking.storage_url).where(
                and_(
                    UploadTracking.book_id.in_(book_ids),
                    UploadTracking.file_type == file_type,
                    UploadTracking.storage_type == "s3"
                )
            )
        )
        records = result.all()
        
        # Build map: book_id -> S3 URL
        cover_urls = {}
        for book_id, storage_url in records:
            if storage_url:
                cover_urls[book_id] = build_s3_cover_url(storage_url, bucket, region)
        
        # Fallback: if thumbnail not found but full-size exists, use full-size
        if use_thumbnail and len(cover_urls) < len(book_ids):
            full_size_result = await db.execute(
                select(UploadTracking.book_id, UploadTracking.storage_url).where(
                    and_(
                        UploadTracking.book_id.in_([bid for bid in book_ids if bid not in cover_urls]),
                        UploadTracking.file_type == "cover",
                        UploadTracking.storage_type == "s3"
                    )
                )
            )
            full_size_records = full_size_result.all()
            for book_id, storage_url in full_size_records:
                if storage_url:
                    cover_urls[book_id] = build_s3_cover_url(storage_url, bucket, region)
        
        return cover_urls
    except Exception as e:
        logger.error(f"Error getting cover URLs: {e}")
        return {}


@router.get("/", response_model=BookListResponse)
async def get_books(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    sort_by: Optional[str] = Query(None, regex="^(id|title|timestamp|pubdate|last_modified)$"),
    order: Optional[str] = Query(None, regex="^(asc|desc)$"),
    sort_param: Optional[str] = Query(None, regex="^(new|old|abc|zyx|authaz|authza|pubnew|pubold|seriesasc|seriesdesc|stored)$"),
    author_id: Optional[int] = None,
    series_id: Optional[int] = None,
    publisher_id: Optional[int] = None,
    tag_id: Optional[int] = None,
    search_query: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get paginated list of books with optional filtering"""
    # Map sort_param to sort_by and order (like original Calibre-Web)
    # Initialize defaults first
    if not sort_by:
        sort_by = "timestamp"
    if not order:
        order = "desc"
    
    if sort_param:
        if sort_param == "stored":
            # "stored" defaults to "new" (timestamp desc) like original Calibre-Web
            sort_param = "new"
        if sort_param == "new":
            sort_by = "timestamp"
            order = "desc"
        elif sort_param == "old":
            sort_by = "timestamp"
            order = "asc"
        elif sort_param == "abc":
            sort_by = "title"
            order = "asc"
        elif sort_param == "zyx":
            sort_by = "title"
            order = "desc"
        elif sort_param == "pubnew":
            sort_by = "pubdate"
            order = "desc"
        elif sort_param == "pubold":
            sort_by = "pubdate"
            order = "asc"
        elif sort_param == "seriesasc":
            sort_by = "series_index"
            order = "asc"
        elif sort_param == "seriesdesc":
            sort_by = "series_index"
            order = "desc"
        # authaz and authza need special handling in calibre_db - sort_by stays None
        elif sort_param in ["authaz", "authza"]:
            sort_by = None  # Explicitly set to None for author sorting

    # Try cache first
    cached_data = None
    if settings.enable_cache:
        cache_key = cache_service.cache_key(
            "books",
            page=page,
            per_page=per_page,
            sort_by=sort_by,
            order=order,
            sort_param=sort_param,
            author_id=author_id,
            series_id=series_id,
            publisher_id=publisher_id,
            tag_id=tag_id,
            search_query=search_query,
        )
        cached_data = await cache_service.get(cache_key)
        if cached_data:
            return BookListResponse(**cached_data)
    else:
        cache_key = None

    try:
        books, total = calibre_db.get_books(
            page=page,
            per_page=per_page,
            sort_by=sort_by,
            order=order,
            sort_param=sort_param,
            author_id=author_id,
            series_id=series_id,
            publisher_id=publisher_id,
            tag_id=tag_id,
            search_query=search_query,
        )

        # Get S3 cover URLs for books that have covers
        # For list view, prefer thumbnails for better performance
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
            # Update books with cover URLs (prefer thumbnails, fallback to full-size)
            for book in books:
                if book.id in thumb_urls_map:
                    book.cover_thumb_url = thumb_urls_map[book.id]
                    book.cover_url = full_size_urls_map.get(book.id)  # Also set full-size if available
                elif book.id in full_size_urls_map:
                    book.cover_url = full_size_urls_map[book.id]
                    # Use full-size as thumbnail if thumbnail doesn't exist
                    book.cover_thumb_url = full_size_urls_map[book.id]

        response = BookListResponse(
            total=total,
            page=page,
            per_page=per_page,
            books=books,
        )

        # Cache the response if caching is enabled (use mode='json' to serialize datetime objects)
        if settings.enable_cache and cache_key:
            await cache_service.set(cache_key, response.model_dump(mode='json'))

        return response
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting books: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{book_id}", response_model=BookDetail)
async def get_book(book_id: int, db: AsyncSession = Depends(get_db)):
    """Get detailed information about a specific book"""
    cache_key = f"book:{book_id}"
    cached_data = None

    if settings.enable_cache:
        cached_data = await cache_service.get(cache_key)
        if cached_data:
            return BookDetail(**cached_data)

    try:
        # Get book with cloud-stored formats included
        book = await get_book_with_cloud_formats(book_id)
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

        # Get S3 cover URL if cover exists and is uploaded to S3
        # For detail page, use full-size covers (not thumbnails)
        if book.has_cover and settings.s3_bucket_name:
            full_size_urls_map = await get_cover_urls_map(
                db,
                [book_id],
                bucket=settings.s3_bucket_name,
                region=settings.aws_region,
                use_thumbnail=False
            )
            thumb_urls_map = await get_cover_urls_map(
                db,
                [book_id],
                bucket=settings.s3_bucket_name,
                region=settings.aws_region,
                use_thumbnail=True
            )
            if book_id in full_size_urls_map:
                book.cover_url = full_size_urls_map[book_id]
            if book_id in thumb_urls_map:
                book.cover_thumb_url = thumb_urls_map[book_id]
            elif book_id in full_size_urls_map:
                # Use full-size as thumbnail fallback
                book.cover_thumb_url = full_size_urls_map[book_id]

        # Cache the response if caching is enabled (use mode='json' to serialize datetime objects)
        if settings.enable_cache:
            await cache_service.set(cache_key, book.model_dump(mode='json'))

        return book
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting book {book_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/search/", response_model=SearchResult)
async def search_books(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(50, ge=1, le=settings.max_search_results),
    db: AsyncSession = Depends(get_db),
):
    """Search books by title, author, or tags"""
    cached_data = None
    cache_key = None
    
    if settings.enable_cache:
        cache_key = cache_service.cache_key("search", q=q, limit=limit)
        cached_data = await cache_service.get(cache_key)
        if cached_data:
            return SearchResult(**cached_data)

    try:
        books = calibre_db.search_books(q, limit=limit)
        
        # Get S3 cover URLs for books that have covers
        # For search results, prefer thumbnails for better performance
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
            # Update books with cover URLs (prefer thumbnails, fallback to full-size)
            for book in books:
                if book.id in thumb_urls_map:
                    book.cover_thumb_url = thumb_urls_map[book.id]
                    book.cover_url = full_size_urls_map.get(book.id)  # Also set full-size if available
                elif book.id in full_size_urls_map:
                    book.cover_url = full_size_urls_map[book.id]
                    # Use full-size as thumbnail if thumbnail doesn't exist
                    book.cover_thumb_url = full_size_urls_map[book.id]
        
        response = SearchResult(
            books=books,
            total=len(books),
            query=q,
        )

        # Cache the response if caching is enabled (use mode='json' to serialize datetime objects)
        if settings.enable_cache and cache_key:
            await cache_service.set(cache_key, response.model_dump(mode='json'))

        return response
    except Exception as e:
        logger.error(f"Error searching books: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/random/", response_model=BookListResponse)
async def get_random_books(
    limit: int = Query(20, ge=1, le=100, description="Number of random books to return"),
    db: AsyncSession = Depends(get_db),
):
    """Get random books from the library"""
    # Don't cache random books as they should be different each time
    try:
        books = calibre_db.get_random_books(limit=limit)
        
        # Get S3 cover URLs for books that have covers
        # For random books list, prefer thumbnails for better performance
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
            # Update books with cover URLs (prefer thumbnails, fallback to full-size)
            for book in books:
                if book.id in thumb_urls_map:
                    book.cover_thumb_url = thumb_urls_map[book.id]
                    book.cover_url = full_size_urls_map.get(book.id)  # Also set full-size if available
                elif book.id in full_size_urls_map:
                    book.cover_url = full_size_urls_map[book.id]
                    # Use full-size as thumbnail if thumbnail doesn't exist
                    book.cover_thumb_url = full_size_urls_map[book.id]
        
        response = BookListResponse(
            total=len(books),
            page=1,
            per_page=limit,
            books=books,
        )
        return response
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting random books: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
