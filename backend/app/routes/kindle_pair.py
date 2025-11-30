from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
import secrets
import qrcode
import io
import json
from datetime import datetime, timedelta

from app.services.cache import cache_service

router = APIRouter(prefix="/api/kindle-pair", tags=["Kindle Pairing"])

# Session expires after 30 minutes
SESSION_EXPIRY = 30 * 60


class PairingSession(BaseModel):
    device_key: str
    created_at: str
    selected_books: list[int] = []


class ConnectRequest(BaseModel):
    device_key: str


class SelectBooksRequest(BaseModel):
    device_key: str
    book_ids: list[int]


@router.post("/create-session")
async def create_pairing_session():
    """
    Create a new device pairing session for Kindle.
    Returns a unique device key that can be displayed as QR code.
    """
    # Generate a unique 6-character alphanumeric key
    device_key = secrets.token_urlsafe(6)[:6].upper()

    # Ensure uniqueness
    while await cache_service.get(f"kindle_pair:{device_key}"):
        device_key = secrets.token_urlsafe(6)[:6].upper()

    # Store session in Redis
    session = PairingSession(
        device_key=device_key,
        created_at=datetime.utcnow().isoformat(),
        selected_books=[]
    )

    await cache_service.set(
        f"kindle_pair:{device_key}",
        session.model_dump(),
        ttl=SESSION_EXPIRY
    )

    return {
        "device_key": device_key,
        "expires_in": SESSION_EXPIRY,
        "pair_url": f"{get_base_url()}/pair?key={device_key}"
    }


@router.get("/qr-code/{device_key}")
async def get_qr_code(device_key: str, fmt: str | None = None):
    """
    Generate QR code for the pairing URL.
    """
    # Check if session exists
    session_data = await cache_service.get(f"kindle_pair:{device_key}")
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    # Generate QR code
    pair_url = f"{get_base_url()}/pair?key={device_key}"
    qr = qrcode.QRCode(
        version=1,  # Smallest version - auto-upgrades if data doesn't fit
        error_correction=qrcode.constants.ERROR_CORRECT_L,  # Lowest error correction for simpler code
        box_size=10,  # Reduced from 15 - smaller boxes = smaller image
        border=2,  # Reduced from 4 - thinner border
    )
    qr.add_data(pair_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    # Kindle Paperwhite 3 and older models struggle with PNG rendering.
    # Default to GIF for maximum compatibility but keep PNG as opt-in (?fmt=png).
    image_format = "PNG" if (fmt and fmt.lower() == "png") else "GIF"
    media_type = "image/png" if image_format == "PNG" else "image/gif"

    if image_format == "GIF":
        # Convert to palette mode (256 colors) for GIF
        # Use black and white palette for smallest file size
        img = img.convert("P", palette=1, colors=2)
    else:
        img = img.convert("RGB")

    img_bytes = io.BytesIO()
    # Optimize for smallest file size
    img.save(img_bytes, format=image_format, optimize=True)
    img_bytes.seek(0)

    return Response(content=img_bytes.getvalue(), media_type=media_type)


@router.post("/connect")
async def connect_device(request: ConnectRequest):
    """
    Connect a phone/PC to a Kindle session using device key.
    """
    session_data = await cache_service.get(f"kindle_pair:{request.device_key}")
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    session = PairingSession.model_validate(session_data)

    return {
        "success": True,
        "device_key": request.device_key,
        "selected_books": session.selected_books
    }


@router.post("/select-books")
async def select_books(request: SelectBooksRequest):
    """
    Select books from phone/PC to display on Kindle.
    """
    session_data = await cache_service.get(f"kindle_pair:{request.device_key}")
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    session = PairingSession.model_validate(session_data)
    session.selected_books = request.book_ids

    # Update session in Redis
    await cache_service.set(
        f"kindle_pair:{request.device_key}",
        session.model_dump(),
        ttl=SESSION_EXPIRY
    )

    return {
        "success": True,
        "selected_count": len(request.book_ids)
    }


@router.get("/check-books/{device_key}")
async def check_selected_books(device_key: str):
    """
    Check which books have been selected (called from Kindle).
    Handles both regular books (positive IDs) and RSS books (negative IDs).
    """
    session_data = await cache_service.get(f"kindle_pair:{device_key}")
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    session = PairingSession.model_validate(session_data)

    books = []

    if session.selected_books:
        # Separate regular books and RSS books
        regular_book_ids = [bid for bid in session.selected_books if bid > 0]
        rss_book_ids = [-bid for bid in session.selected_books if bid < 0]

        # Get regular books from Calibre
        if regular_book_ids:
            from app.services.calibre_db import get_books_by_ids
            books.extend(await get_books_by_ids(regular_book_ids))

        # Get RSS books
        if rss_book_ids:
            from sqlalchemy import select
            from app.database import async_session_maker
            from app.models.rss_feed import RssGeneratedBook

            async with async_session_maker() as db:
                result = await db.execute(
                    select(RssGeneratedBook).where(RssGeneratedBook.id.in_(rss_book_ids))
                )
                rss_books = result.scalars().all()

                # Convert RSS books to the same format as regular books
                for rss_book in rss_books:
                    books.append({
                        "id": -rss_book.id,  # Use negative ID to identify as RSS
                        "title": rss_book.title,
                        "authors": [{"name": "RSS Feed"}],
                        "path": f"/api/rss/books/{rss_book.id}/download",
                        "file_formats": ["MOBI" if rss_book.mobi_filename else "EPUB"],
                        "is_rss": True
                    })

    return {
        "device_key": device_key,
        "books": books
    }


@router.delete("/session/{device_key}")
async def delete_session(device_key: str):
    """
    Delete a pairing session.
    """
    # Check if session exists before deleting
    session_exists = await cache_service.get(f"kindle_pair:{device_key}")
    if not session_exists:
        raise HTTPException(status_code=404, detail="Session not found")

    await cache_service.delete(f"kindle_pair:{device_key}")
    return {"success": True}


def get_base_url() -> str:
    """
    Get the base URL for the application.
    In production, this should come from environment variables.
    """
    import os
    return os.getenv("FRONTEND_URL", "http://localhost:3003")
