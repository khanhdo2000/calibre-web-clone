from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
import logging
from pydantic import BaseModel

from app.models.upload_tracking import UploadTracking
from app.database import get_db, async_session_maker
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text, literal_column
from datetime import datetime

router = APIRouter(prefix="/api/admin", tags=["admin"])
logger = logging.getLogger(__name__)


class UploadTrackingRecord(BaseModel):
    """Record for bulk upload tracking sync"""
    book_id: int
    book_path: str
    file_type: str
    storage_type: str
    storage_url: str | None = None
    upload_date: datetime | None = None
    file_size: int | None = None
    checksum: str | None = None

    class Config:
        from_attributes = True


class CheckUploadItem(BaseModel):
    """Item to check for existing upload"""
    book_id: int
    file_type: str
    storage_type: str


@router.post("/upload-tracking/bulk")
async def bulk_upsert_upload_tracking(
    records: List[UploadTrackingRecord],
    db: AsyncSession = Depends(get_db)
):
    """
    Bulk upsert upload tracking records from local upload script.
    This endpoint allows the local machine to sync upload tracking to the server.
    """
    try:

        if not records:
            return {"message": "No records to sync", "count": 0}

        # Deduplicate records based on unique constraint (book_id, file_type, storage_type)
        # PostgreSQL doesn't allow duplicate keys in a single INSERT ... ON CONFLICT statement
        # Keep the most recent record when duplicates exist (based on upload_date)
        seen = {}
        duplicate_count = 0
        for record in records:
            key = (record.book_id, record.file_type, record.storage_type)
            if key not in seen:
                seen[key] = record
            else:
                duplicate_count += 1
                existing = seen[key]
                # Keep the record with the most recent upload_date
                if record.upload_date:
                    if not existing.upload_date or record.upload_date > existing.upload_date:
                        seen[key] = record
                # If current record has no date but existing does, keep existing
                # Otherwise keep the current one (both have no date)
        
        if duplicate_count > 0:
            logger.warning(f"Found {duplicate_count} duplicate records in batch, deduplicated to {len(seen)} unique records")

        # Prepare data for upsert from deduplicated records
        values = []
        for record in seen.values():
            values.append({
                'book_id': record.book_id,
                'book_path': record.book_path,
                'file_type': record.file_type,
                'storage_type': record.storage_type,
                'storage_url': record.storage_url,
                'upload_date': record.upload_date or datetime.utcnow(),
                'file_size': record.file_size,
                'checksum': record.checksum,
            })

        # Use PostgreSQL ON CONFLICT for upsert
        from sqlalchemy.dialects.postgresql import insert
        
        insert_stmt = insert(UploadTracking).values(values)
        
        # Use on_conflict_do_update with excluded values
        # Reference excluded columns using literal_column for proper SQL generation
        stmt = insert_stmt.on_conflict_do_update(
            index_elements=['book_id', 'file_type', 'storage_type'],
            set_={
                UploadTracking.storage_url: literal_column('excluded.storage_url'),
                UploadTracking.upload_date: literal_column('excluded.upload_date'),
                UploadTracking.file_size: literal_column('excluded.file_size'),
                UploadTracking.checksum: literal_column('excluded.checksum'),
                UploadTracking.book_path: literal_column('excluded.book_path'),
            }
        )

        await db.execute(stmt)
        await db.commit()

        deduplicated_count = len(seen)
        if deduplicated_count < len(records):
            logger.info(f"Synced {deduplicated_count} upload tracking records (deduplicated from {len(records)} input records)")
        else:
            logger.info(f"Synced {deduplicated_count} upload tracking records")
        return {"message": "Upload tracking synced successfully", "count": deduplicated_count}

    except Exception as e:
        await db.rollback()
        import traceback
        error_traceback = traceback.format_exc()
        logger.error(f"Error syncing upload tracking: {e}")
        logger.error(f"Traceback: {error_traceback}")
        raise HTTPException(status_code=500, detail=f"Failed to sync upload tracking: {str(e)}")


@router.get("/upload-tracking/{book_id}")
async def get_upload_tracking(
    book_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get upload tracking records for a specific book"""
    try:
        result = await db.execute(
            select(UploadTracking).where(UploadTracking.book_id == book_id)
        )
        records = result.scalars().all()
        return records
    except Exception as e:
        logger.error(f"Error getting upload tracking: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/upload-tracking")
async def list_upload_tracking(
    db: AsyncSession = Depends(get_db),
    storage_type: Optional[str] = None,
    file_type: Optional[str] = None,
    limit: int = Query(1000, ge=1, le=10000),
    offset: int = Query(0, ge=0)
):
    """
    List upload tracking records with pagination.
    Can be filtered by storage_type and file_type.
    Returns a list of records with book_id, file_type, storage_type, storage_url.
    """
    try:
        query = select(UploadTracking)
        count_query = select(func.count()).select_from(UploadTracking)
        
        conditions = []
        if storage_type:
            conditions.append(UploadTracking.storage_type == storage_type)
        if file_type:
            conditions.append(UploadTracking.file_type == file_type)
        
        if conditions:
            from sqlalchemy import and_
            where_clause = and_(*conditions)
            query = query.where(where_clause)
            count_query = count_query.where(where_clause)
        
        # Get total count
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Get paginated records
        query = query.limit(limit).offset(offset)
        result = await db.execute(query)
        records = result.scalars().all()
        
        # Return simplified records with pagination info
        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "records": [
                {
                    "book_id": r.book_id,
                    "book_path": r.book_path,
                    "file_type": r.file_type,
                    "storage_type": r.storage_type,
                    "storage_url": r.storage_url,
                }
                for r in records
            ]
        }
    except Exception as e:
        logger.error(f"Error listing upload tracking: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/upload-tracking/check")
async def check_upload_tracking(
    items: List[CheckUploadItem],
    db: AsyncSession = Depends(get_db)
):
    """
    Efficiently check if specific files are already uploaded.
    Accepts a list of {book_id, file_type, storage_type} and returns which ones exist.
    This is more efficient than fetching all records when you only need to check specific files.
    """
    try:
        if not items:
            return {"existing": []}
        
        # Build query to check for all items at once
        from sqlalchemy import or_
        
        conditions = []
        for item in items:
            conditions.append(
                (UploadTracking.book_id == item.book_id) &
                (UploadTracking.file_type == item.file_type) &
                (UploadTracking.storage_type == item.storage_type)
            )
        
        if not conditions:
            return {"existing": []}
        
        query = select(
            UploadTracking.book_id,
            UploadTracking.file_type,
            UploadTracking.storage_type
        ).where(or_(*conditions))
        
        result = await db.execute(query)
        existing_records = result.all()
        
        # Convert to set for fast lookup
        existing_set = {
            (r.book_id, r.file_type, r.storage_type)
            for r in existing_records
        }
        
        # Build response with which items exist
        existing = [
            {
                "book_id": item.book_id,
                "file_type": item.file_type,
                "storage_type": item.storage_type,
            }
            for item in items
            if (item.book_id, item.file_type, item.storage_type) in existing_set
        ]
        
        return {"existing": existing}
    except Exception as e:
        logger.error(f"Error checking upload tracking: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

