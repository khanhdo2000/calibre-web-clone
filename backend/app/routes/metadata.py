from fastapi import APIRouter, HTTPException
from typing import List
import logging

from app.models.book import Author, Series, Publisher, Category as Tag
from app.services.calibre_db import calibre_db
from app.services.cache import cache_service

router = APIRouter(prefix="/api/metadata", tags=["metadata"])
logger = logging.getLogger(__name__)


@router.get("/authors", response_model=List[Author])
async def get_authors():
    """Get all authors"""
    cache_key = "metadata:authors"
    cached_data = await cache_service.get(cache_key)

    if cached_data:
        return [Author(**author) for author in cached_data]

    try:
        authors = calibre_db.get_all_authors()
        await cache_service.set(cache_key, [author.model_dump(mode='json') for author in authors])
        return authors
    except Exception as e:
        logger.error(f"Error getting authors: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/series", response_model=List[Series])
async def get_series():
    """Get all series"""
    cache_key = "metadata:series"
    cached_data = await cache_service.get(cache_key)

    if cached_data:
        return [Series(**s) for s in cached_data]

    try:
        series = calibre_db.get_all_series()
        await cache_service.set(cache_key, [s.model_dump(mode='json') for s in series])
        return series
    except Exception as e:
        logger.error(f"Error getting series: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/publishers", response_model=List[Publisher])
async def get_publishers():
    """Get all publishers"""
    cache_key = "metadata:publishers"
    cached_data = await cache_service.get(cache_key)

    if cached_data:
        return [Publisher(**p) for p in cached_data]

    try:
        publishers = calibre_db.get_all_publishers()
        await cache_service.set(cache_key, [p.model_dump(mode='json') for p in publishers])
        return publishers
    except Exception as e:
        logger.error(f"Error getting publishers: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/tags", response_model=List[Tag])
async def get_tags():
    """Get all tags with book counts"""
    cache_key = "metadata:tags"
    cached_data = await cache_service.get(cache_key)

    if cached_data:
        return [Tag(**tag) for tag in cached_data]

    try:
        tags = calibre_db.get_all_categories()
        await cache_service.set(cache_key, [tag.model_dump(mode='json') for tag in tags])
        return tags
    except Exception as e:
        logger.error(f"Error getting tags: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
