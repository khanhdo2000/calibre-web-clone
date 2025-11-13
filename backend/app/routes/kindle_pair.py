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
async def get_qr_code(device_key: str):
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
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(pair_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    # Convert to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)

    return Response(content=img_bytes.getvalue(), media_type="image/png")


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
    """
    session_data = await cache_service.get(f"kindle_pair:{device_key}")
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    session = PairingSession.model_validate(session_data)

    # Get book details for selected books
    from app.services.calibre_db import get_books_by_ids
    books = []

    if session.selected_books:
        books = await get_books_by_ids(session.selected_books)

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
