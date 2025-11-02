from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import logging

from app.models.book import Book, BookDetail, BookListResponse, SearchResult
from app.services.calibre_db import calibre_db
from app.services.cache import cache_service
from app.config import settings

router = APIRouter(prefix="/api/books", tags=["books"])
logger = logging.getLogger(__name__)


@router.get("/", response_model=BookListResponse)
async def get_books(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    sort_by: Optional[str] = Query(None, regex="^(id|title|timestamp|pubdate|last_modified)$"),
    order: Optional[str] = Query(None, regex="^(asc|desc)$"),
    sort_param: Optional[str] = Query(None, regex="^(new|old|abc|zyx|authaz|authza|pubnew|pubold|seriesasc|seriesdesc)$"),
    author_id: Optional[int] = None,
    series_id: Optional[int] = None,
    publisher_id: Optional[int] = None,
    tag_id: Optional[int] = None,
    search_query: Optional[str] = None,
):
    """Get paginated list of books with optional filtering"""
    # Map sort_param to sort_by and order (like original Calibre-Web)
    # Initialize defaults first
    if not sort_by:
        sort_by = "timestamp"
    if not order:
        order = "desc"
    
    if sort_param:
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

    # Temporarily disable cache to debug sorting
    # cached_data = await cache_service.get(cache_key)
    # if cached_data:
    #     return BookListResponse(**cached_data)
    cached_data = None

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

        response = BookListResponse(
            total=total,
            page=page,
            per_page=per_page,
            books=books,
        )

        # Cache the response (use mode='json' to serialize datetime objects)
        await cache_service.set(cache_key, response.model_dump(mode='json'))

        return response
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting books: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{book_id}", response_model=BookDetail)
async def get_book(book_id: int):
    """Get detailed information about a specific book"""
    cache_key = f"book:{book_id}"
    cached_data = await cache_service.get(cache_key)

    if cached_data:
        return BookDetail(**cached_data)

    try:
        book = calibre_db.get_book(book_id)
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

        # Cache the response (use mode='json' to serialize datetime objects)
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
):
    """Search books by title, author, or tags"""
    cache_key = cache_service.cache_key("search", q=q, limit=limit)
    cached_data = await cache_service.get(cache_key)

    if cached_data:
        return SearchResult(**cached_data)

    try:
        books = calibre_db.search_books(q, limit=limit)
        response = SearchResult(
            books=books,
            total=len(books),
            query=q,
        )

        # Cache the response (use mode='json' to serialize datetime objects)
        await cache_service.set(cache_key, response.model_dump(mode='json'))

        return response
    except Exception as e:
        logger.error(f"Error searching books: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/random/", response_model=BookListResponse)
async def get_random_books(
    limit: int = Query(20, ge=1, le=100, description="Number of random books to return"),
):
    """Get random books from the library"""
    # Don't cache random books as they should be different each time
    try:
        books = calibre_db.get_random_books(limit=limit)
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
