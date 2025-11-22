from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse, StreamingResponse, RedirectResponse
from urllib.parse import quote
from unidecode import unidecode
import re
import os
import logging
from pathlib import Path
import httpx

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

        # Check if format exists in Calibre metadata or in cloud storage (PostgreSQL)
        result = await db.execute(
            select(UploadTracking.file_type).where(
                UploadTracking.book_id == book_id,
                UploadTracking.file_type == format_upper,
                UploadTracking.storage_type == "gdrive"
            )
        )
        cloud_format = result.scalar_one_or_none()

        if format_upper not in book.file_formats and not cloud_format:
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
        # Build a safe Content-Disposition
        if format_upper == "MOBI":
            # For MOBI, produce a strict ASCII filename: letters, numbers, dashes and underscores only
            base_name = unidecode(book.title)
            base_name = re.sub(r"[^A-Za-z0-9\-_.]+", "_", base_name)  # replace non-allowed with underscores
            base_name = re.sub(r"_+", "_", base_name).strip("._-") or "book"
            filename = f"{base_name}.{format.lower()}"
            cd_header = f"attachment; filename=\"{filename}\""
        else:
            filename = f"{book.title}.{format.lower()}"
            ascii_fallback = filename.encode('ascii', 'ignore').decode('ascii') or f"book.{format.lower()}"
            cd_header = f"attachment; filename=\"{ascii_fallback}\"; filename*=UTF-8''{quote(filename)}"

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
                    headers={"Content-Disposition": cd_header}
                )

        # Fall back to checking Google Drive by path (legacy)
        book_stream = storage_service.get_book_stream(book.path, format)
        if book_stream:
            return StreamingResponse(
                book_stream,
                media_type=media_type,
                headers={"Content-Disposition": f'attachment; filename="{filename}"'}
            )

        # Use local file (with fallback scan if canonical name is missing)
        book_path = storage_service.get_book_file_path(book.path, format)
        if not os.path.exists(book_path):
            # Fallback: scan the book directory for any matching extension
            book_dir = os.path.join(settings.calibre_library_path, book.path)
            if not os.path.isdir(book_dir):
                raise HTTPException(status_code=404, detail="Book file not found")
            target_ext = f".{format.lower()}"
            candidates = [
                os.path.join(book_dir, name)
                for name in os.listdir(book_dir)
                if os.path.splitext(name)[1].lower() == target_ext
            ]
            if not candidates:
                raise HTTPException(status_code=404, detail="Book file not found")
            # pick first candidate
            book_path = candidates[0]

        return FileResponse(
            book_path,
            media_type=media_type,
            headers={"Content-Disposition": cd_header}
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

        # Check if format exists in Calibre metadata or in cloud storage (PostgreSQL)
        result = await db.execute(
            select(UploadTracking.file_type).where(
                UploadTracking.book_id == book_id,
                UploadTracking.file_type == format_upper,
                UploadTracking.storage_type == "gdrive"
            )
        )
        cloud_format = result.scalar_one_or_none()

        if format_upper not in book.file_formats and not cloud_format:
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
        # RFC 5987/ASCII header for inline
        if format_upper == "MOBI":
            base_name = unidecode(book.title)
            base_name = re.sub(r"[^A-Za-z0-9\-_.]+", "_", base_name)
            base_name = re.sub(r"_+", "_", base_name).strip("._-") or "book"
            filename = f"{base_name}.{format.lower()}"
            cd_inline = f"inline; filename=\"{filename}\""
        else:
            filename = f"{book.title}.{format.lower()}"
            ascii_fallback = filename.encode('ascii', 'ignore').decode('ascii') or f"book.{format.lower()}"
            cd_inline = f"inline; filename=\"{ascii_fallback}\"; filename*=UTF-8''{quote(filename)}"

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
            file_id = upload_record.storage_url
            book_stream = storage_service.get_book_stream_from_gdrive_id(file_id)
            if book_stream:
                return StreamingResponse(
                    book_stream,
                    media_type=media_type,
                    headers={"Content-Disposition": cd_inline}
                )
            else:
                # If streaming via API fails, fetch from Google Drive public URL and proxy it
                # This avoids CORS issues that would occur with a redirect
                logger.warning(
                    f"Failed to stream Google Drive file {file_id} for book {book_id}, "
                    f"format {format_upper}. Proxying from public URL."
                )
                public_url = f"https://drive.google.com/uc?id={file_id}&export=download"
                
                async def generate():
                    try:
                        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                            async with client.stream("GET", public_url) as response:
                                # Check status before starting to yield
                                if response.status_code != 200:
                                    error_msg = (
                                        f"Failed to fetch from Google Drive public URL: "
                                        f"{response.status_code} for file {file_id}"
                                    )
                                    logger.error(error_msg)
                                    # Read error response body if available
                                    try:
                                        error_body = await response.aread()
                                        logger.debug(f"Google Drive error response: {error_body}")
                                    except:
                                        pass
                                    raise HTTPException(
                                        status_code=response.status_code,
                                        detail=error_msg
                                    )
                                # Stream the file content
                                async for chunk in response.aiter_bytes():
                                    yield chunk
                    except HTTPException:
                        raise
                    except Exception as e:
                        logger.error(f"Error proxying Google Drive file {file_id}: {e}")
                        raise HTTPException(
                            status_code=500,
                            detail=f"Failed to proxy file from Google Drive: {str(e)}"
                        )
                
                return StreamingResponse(
                    generate(),
                    media_type=media_type,
                    headers={"Content-Disposition": cd_inline}
                )

        # Fall back to checking Google Drive by path (legacy)
        book_stream = storage_service.get_book_stream(book.path, format)
        if book_stream:
            return StreamingResponse(
                book_stream,
                media_type=media_type,
                headers={"Content-Disposition": cd_inline}
            )

        # Use local file (with fallback scan if canonical name is missing)
        book_path = storage_service.get_book_file_path(book.path, format)
        if not os.path.exists(book_path):
            book_dir = os.path.join(settings.calibre_library_path, book.path)
            if not os.path.isdir(book_dir):
                raise HTTPException(status_code=404, detail="Book file not found")
            target_ext = f".{format.lower()}"
            candidates = [
                os.path.join(book_dir, name)
                for name in os.listdir(book_dir)
                if os.path.splitext(name)[1].lower() == target_ext
            ]
            if not candidates:
                raise HTTPException(status_code=404, detail="Book file not found")
            book_path = candidates[0]

        return FileResponse(
            book_path,
            media_type=media_type,
            headers={"Content-Disposition": cd_inline}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading book {book_id} in format {format}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/book/{book_id}/{format}")
async def get_book_redirect(book_id: int, format: str, db: AsyncSession = Depends(get_db)):
    """Redirect to Google Drive download link if available, otherwise serve from local storage.

    This endpoint checks if the book is stored in Google Drive and redirects to the public download URL.
    If not found in Google Drive, it falls back to downloading from local storage.
    """
    try:
        book = calibre_db.get_book(book_id)
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

        format_upper = format.upper()

        # Check if format exists in Calibre metadata or in cloud storage (PostgreSQL)
        result_check = await db.execute(
            select(UploadTracking.file_type).where(
                UploadTracking.book_id == book_id,
                UploadTracking.file_type == format_upper,
                UploadTracking.storage_type == "gdrive"
            )
        )
        cloud_format = result_check.scalar_one_or_none()

        if format_upper not in book.file_formats and not cloud_format:
            raise HTTPException(status_code=404, detail=f"Format {format_upper} not available for this book")

        # Check if file is in Google Drive
        result = await db.execute(
            select(UploadTracking).where(
                UploadTracking.book_id == book_id,
                UploadTracking.file_type == format_upper,
                UploadTracking.storage_type == "gdrive"
            )
        )
        upload_record = result.scalar_one_or_none()

        if upload_record and upload_record.storage_url:
            # Redirect to Google Drive download link
            file_id = upload_record.storage_url
            public_url = f"https://drive.google.com/uc?id={file_id}&export=download"
            return RedirectResponse(url=public_url)

        # Fall back to local download endpoint
        from fastapi import Request
        return RedirectResponse(url=f"/api/files/download/{book_id}/{format}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting book redirect for book {book_id} format {format}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/gdrive-link/{book_id}/{format}")
async def gdrive_direct_link(book_id: int, format: str, db: AsyncSession = Depends(get_db)):
    """Redirect to the public Google Drive download URL if tracked.

    This provides a right-clickable direct link: https://drive.google.com/uc?id=<FILE_ID>&export=download
    """
    try:
        book = calibre_db.get_book(book_id)
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

        format_upper = format.upper()

        # Check if format exists in Calibre metadata or in cloud storage (PostgreSQL)
        result_check = await db.execute(
            select(UploadTracking.file_type).where(
                UploadTracking.book_id == book_id,
                UploadTracking.file_type == format_upper,
                UploadTracking.storage_type == "gdrive"
            )
        )
        cloud_format = result_check.scalar_one_or_none()

        if format_upper not in book.file_formats and not cloud_format:
            raise HTTPException(status_code=404, detail=f"Format {format_upper} not available for this book")

        result = await db.execute(
            select(UploadTracking).where(
                UploadTracking.book_id == book_id,
                UploadTracking.file_type == format_upper,
                UploadTracking.storage_type == "gdrive"
            )
        )
        upload_record = result.scalar_one_or_none()

        if not upload_record or not upload_record.storage_url:
            raise HTTPException(status_code=404, detail="Google Drive link not found")

        file_id = upload_record.storage_url
        public_url = f"https://drive.google.com/uc?id={file_id}&export=download"
        return RedirectResponse(url=public_url)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting Google Drive link for book {book_id} format {format}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
