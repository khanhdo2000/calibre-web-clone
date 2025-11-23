from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from typing import Optional
import logging
import os
import tempfile

from app.database import get_db
from app.models.user import User
from app.routes.auth import get_current_user
from app.services.email import email_service
from app.services.calibre_db import calibre_db
from app.services.storage import storage_service
from app.services.auth import auth_service
from app.config import settings

router = APIRouter(prefix="/api/kindle-email", tags=["kindle-email"])
logger = logging.getLogger(__name__)


class SendToKindleRequest(BaseModel):
    book_id: int
    kindle_email: Optional[EmailStr] = None  # Override user's default Kindle email


class SendToKindleResponse(BaseModel):
    success: bool
    message: str
    kindle_email: str


class KindleEmailUpdate(BaseModel):
    kindle_email: Optional[EmailStr] = None


@router.post("/send", response_model=SendToKindleResponse)
async def send_to_kindle(
    request: SendToKindleRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Send a book to Kindle via email (EPUB format only).
    
    Requires:
    - Email service to be configured in settings
    - User to have a Kindle email set, or provide one in the request
    - Book file to be available in EPUB format
    """
    # Check if email service is configured
    if not email_service.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Email service is not configured. Please contact administrator."
        )

    # Determine Kindle email to use
    kindle_email = request.kindle_email or current_user.kindle_email
    if not kindle_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kindle email not set. Please set your Kindle email in settings or provide it in the request."
        )

    # Validate Kindle email format
    if not email_service.is_kindle_email(kindle_email):
        logger.warning(f"Email {kindle_email} does not appear to be a Kindle email address")

    # Get book information
    try:
        book = calibre_db.get_book(request.book_id)
        if not book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Book not found"
            )
    except Exception as e:
        logger.error(f"Error getting book {request.book_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving book information"
        )

    # Only EPUB format is supported for Send to Kindle
    format_upper = "EPUB"
    
    # Check if EPUB format is available
    if format_upper not in book.file_formats:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"EPUB format not available for this book. Available formats: {', '.join(book.file_formats)}"
        )

    # Get book file path
    book_path = None
    temp_file = None
    
    try:
        # Try to get file from local storage first
        book_path = storage_service.get_book_file_path(book.path, format_upper)
        
        if not os.path.exists(book_path):
            # Fallback: scan the book directory
            book_dir = os.path.join(settings.calibre_library_path, book.path)
            if os.path.isdir(book_dir):
                target_ext = f".{format_upper.lower()}"
                candidates = [
                    os.path.join(book_dir, name)
                    for name in os.listdir(book_dir)
                    if os.path.splitext(name)[1].lower() == target_ext
                ]
                if candidates:
                    book_path = candidates[0]

        # If still not found, try to stream from Google Drive and save to temp file
        if not book_path or not os.path.exists(book_path):
            # Check if file is in Google Drive
            from app.models.upload_tracking import UploadTracking
            result = await db.execute(
                select(UploadTracking).where(
                    UploadTracking.book_id == request.book_id,
                    UploadTracking.file_type == format_upper,
                    UploadTracking.storage_type == "gdrive"
                )
            )
            upload_record = result.scalar_one_or_none()
            
            if upload_record and upload_record.storage_url:
                # Download from Google Drive to temp file
                book_stream = storage_service.get_book_stream_from_gdrive_id(upload_record.storage_url)
                if book_stream:
                    # Create temp file
                    temp_file = tempfile.NamedTemporaryFile(
                        delete=False,
                        suffix=f".{format_upper.lower()}",
                        prefix=f"kindle_{request.book_id}_"
                    )
                    temp_file.write(book_stream.read())
                    temp_file.close()
                    book_path = temp_file.name
                else:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Book file in format {format_upper} not found"
                    )
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Book file in format {format_upper} not found"
                )

        # Send to Kindle
        success = await email_service.send_to_kindle(
            to_email=kindle_email,
            book_path=book_path,
            book_title=book.title,
            format=format_upper
        )

        if success:
            return SendToKindleResponse(
                success=True,
                message=f"Book '{book.title}' sent successfully to {kindle_email}",
                kindle_email=kindle_email
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send book to Kindle. Please check email service configuration."
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending book to Kindle: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error sending book to Kindle: {str(e)}"
        )
    finally:
        # Clean up temp file if created
        if temp_file and os.path.exists(temp_file.name):
            try:
                os.unlink(temp_file.name)
            except Exception as e:
                logger.warning(f"Failed to delete temp file {temp_file.name}: {e}")


@router.get("/settings", response_model=KindleEmailUpdate)
async def get_kindle_email_settings(
    current_user: User = Depends(get_current_user)
):
    """Get user's Kindle email settings"""
    return KindleEmailUpdate(kindle_email=current_user.kindle_email)


@router.put("/settings", response_model=KindleEmailUpdate)
async def update_kindle_email_settings(
    settings_data: KindleEmailUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user's Kindle email address"""
    # Fetch user from current session (current_user might be from cache)
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    user.kindle_email = settings_data.kindle_email
    await db.commit()
    await db.refresh(user)

    # Invalidate user cache so next request gets updated data
    await auth_service.invalidate_user_cache(user.id)

    return KindleEmailUpdate(kindle_email=user.kindle_email)


@router.get("/status")
async def get_email_service_status():
    """Check if email service is configured and ready"""
    status_info = {
        "configured": email_service.is_configured(),
        "service_type": "AWS SES" if email_service.use_aws_ses else "SMTP"
    }
    
    if email_service.use_aws_ses:
        status_info["from_email"] = email_service.ses_from_email
    else:
        status_info["smtp_host"] = email_service.smtp_host
    
    return status_info

