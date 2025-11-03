from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse, StreamingResponse, RedirectResponse
import os
import logging
from pathlib import Path

from app.config import settings
from app.services.calibre_db import calibre_db
from app.services.storage import storage_service
from app.database import get_db
from app.models.upload_tracking import UploadTracking
from app.routes.books import build_s3_cover_url
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

router = APIRouter(prefix="/api/files", tags=["files"])
logger = logging.getLogger(__name__)


@router.get("/cover/{book_id}")
async def get_cover(book_id: int, db: AsyncSession = Depends(get_db)):
    """Get book cover image - supports S3 and local storage"""
    try:
        book = calibre_db.get_book(book_id)
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

        if not book.has_cover:
            raise HTTPException(status_code=404, detail="Cover not found")

        # Check upload tracking for S3 cover
        result = await db.execute(
            select(UploadTracking).where(
                UploadTracking.book_id == book_id,
                UploadTracking.file_type == "cover",
                UploadTracking.storage_type == "s3"
            )
        )
        upload_record = result.scalar_one_or_none()

        if upload_record and upload_record.storage_url:
            # Serve from S3 using public URL (no credentials needed)
            if settings.s3_bucket_name:
                s3_url = build_s3_cover_url(
                    upload_record.storage_url,
                    settings.s3_bucket_name,
                    settings.aws_region
                )
                return RedirectResponse(url=s3_url)

        # Fall back to local storage
        cover_path = storage_service.get_local_cover_path(book.path)

        if not os.path.exists(cover_path):
            raise HTTPException(status_code=404, detail="Cover file not found")

        return FileResponse(
            cover_path,
            media_type="image/jpeg",
            headers={"Cache-Control": "public, max-age=31536000"}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting cover for book {book_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/download/{book_id}/{format}")
async def download_book(book_id: int, format: str, db: AsyncSession = Depends(get_db)):
    """Download book in specified format - supports Google Drive and local storage"""
    try:
        book = calibre_db.get_book(book_id)
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

        format_upper = format.upper()
        if format_upper not in book.file_formats:
            raise HTTPException(
                status_code=404,
                detail=f"Format {format_upper} not available for this book"
            )

        # Determine media type
        media_types = {
            "EPUB": "application/epub+zip",
            "PDF": "application/pdf",
            "MOBI": "application/x-mobipocket-ebook",
            "AZW3": "application/vnd.amazon.ebook",
            "TXT": "text/plain",
        }
        media_type = media_types.get(format_upper, "application/octet-stream")
        filename = f"{book.title}.{format.lower()}"

        # Check upload tracking for Google Drive file
        result = await db.execute(
            select(UploadTracking).where(
                UploadTracking.book_id == book_id,
                UploadTracking.file_type == format_upper,
                UploadTracking.storage_type == "gdrive"
            )
        )
        upload_record = result.scalar_one_or_none()

        if upload_record and upload_record.storage_url:
            # Serve from Google Drive using file ID
            book_stream = storage_service.get_book_stream_from_gdrive_id(upload_record.storage_url)
            if book_stream:
                return StreamingResponse(
                    book_stream,
                    media_type=media_type,
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'}
                )

        # Fall back to checking Google Drive by path (legacy)
        book_stream = storage_service.get_book_stream(book.path, format)
        if book_stream:
            return StreamingResponse(
                book_stream,
                media_type=media_type,
                headers={"Content-Disposition": f'attachment; filename="{filename}"'}
            )

        # Use local file
        book_path = storage_service.get_book_file_path(book.path, format)

        if not os.path.exists(book_path):
            raise HTTPException(status_code=404, detail="Book file not found")

        return FileResponse(
            book_path,
            media_type=media_type,
            filename=filename,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading book {book_id} in format {format}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/read/{book_id}/{format}")
async def read_book(book_id: int, format: str, db: AsyncSession = Depends(get_db)):
    """Stream book file for reading (inline, not download) - supports Google Drive and local storage"""
    try:
        book = calibre_db.get_book(book_id)
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

        format_upper = format.upper()
        if format_upper not in book.file_formats:
            raise HTTPException(
                status_code=404,
                detail=f"Format {format_upper} not available for this book"
            )

        media_types = {
            "EPUB": "application/epub+zip",
            "PDF": "application/pdf",
            "TXT": "text/plain",
        }
        media_type = media_types.get(format_upper, "application/octet-stream")

        # Check upload tracking for Google Drive file
        result = await db.execute(
            select(UploadTracking).where(
                UploadTracking.book_id == book_id,
                UploadTracking.file_type == format_upper,
                UploadTracking.storage_type == "gdrive"
            )
        )
        upload_record = result.scalar_one_or_none()

        if upload_record and upload_record.storage_url:
            # Stream from Google Drive using file ID
            book_stream = storage_service.get_book_stream_from_gdrive_id(upload_record.storage_url)
            if book_stream:
                return StreamingResponse(
                    book_stream,
                    media_type=media_type,
                    headers={"Content-Disposition": "inline"}
                )

        # Fall back to checking Google Drive by path (legacy)
        book_stream = storage_service.get_book_stream(book.path, format)
        if book_stream:
            return StreamingResponse(
                book_stream,
                media_type=media_type,
                headers={"Content-Disposition": "inline"}
            )

        # Use local file
        book_path = storage_service.get_book_file_path(book.path, format)

        if not os.path.exists(book_path):
            raise HTTPException(status_code=404, detail="Book file not found")

        return FileResponse(
            book_path,
            media_type=media_type,
            headers={"Content-Disposition": "inline"}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading book {book_id} in format {format}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
