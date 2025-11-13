from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from app.services.cache import cache_service
from app.routes.kindle_pair import PairingSession, SESSION_EXPIRY
import secrets
import os
import random

router = APIRouter(prefix="/kindle", tags=["Kindle"])

MOTIVATIONAL_QUOTES = [
    # Book-related quotes
    "A reader lives a thousand lives before he dies.",
    "Books are a uniquely portable magic.",
    "Reading is dreaming with open eyes.",
    "The more that you read, the more things you will know.",
    "A room without books is like a body without a soul.",
    "Reading is to the mind what exercise is to the body.",

    # General motivational quotes
    "The only way to do great work is to love what you do.",
    "Believe you can and you're halfway there.",
    "Success is not final, failure is not fatal: it is the courage to continue that counts.",
    "The future belongs to those who believe in the beauty of their dreams.",
    "Don't watch the clock; do what it does. Keep going.",
    "The best time to plant a tree was 20 years ago. The second best time is now.",
    "Everything you've ever wanted is on the other side of fear.",
    "Happiness is not something ready made. It comes from your own actions.",
    "The only impossible journey is the one you never begin.",
    "Life is 10% what happens to you and 90% how you react to it.",
    "What lies behind us and what lies before us are tiny matters compared to what lies within us.",
    "The way to get started is to quit talking and begin doing.",
    "Don't let yesterday take up too much of today.",
    "You learn more from failure than from success. Don't let it stop you.",
    "It's not whether you get knocked down, it's whether you get up.",
    "We may encounter many defeats but we must not be defeated.",
    "Knowing is not enough; we must apply. Wishing is not enough; we must do.",
    "The secret of getting ahead is getting started.",
    "Dream big and dare to fail.",
    "Act as if what you do makes a difference. It does.",
]


@router.get("/", response_class=HTMLResponse)
async def kindle_page(request: Request, key: str = None):
    """
    Simple HTML-only Kindle page without React/JS frameworks.
    Works better with Kindle's limited browser.
    Supports ?key=XXXXX parameter to reuse existing device key.
    """
    device_key = None

    # Try to reuse existing key from URL parameter
    if key:
        key = key.upper()
        existing_session = await cache_service.get(f"kindle_pair:{key}")
        if existing_session:
            device_key = key
            # Refresh the TTL
            await cache_service.set(
                f"kindle_pair:{device_key}",
                existing_session,
                ttl=SESSION_EXPIRY
            )

    # Generate a new key if needed
    if not device_key:
        device_key = secrets.token_urlsafe(6)[:6].upper()

        # Ensure uniqueness
        while await cache_service.get(f"kindle_pair:{device_key}"):
            device_key = secrets.token_urlsafe(6)[:6].upper()

        # Store session in Redis
        from datetime import datetime
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

    # Get base URL - use the same protocol as the incoming request
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3003")

    # Use the request's scheme (http or https) for API URLs
    scheme = request.url.scheme
    host = request.url.netloc
    api_base = f"{scheme}://{host}"

    pair_url = f"{frontend_url}/pair?key={device_key}"
    qr_code_url = f"{api_base}/api/kindle-pair/qr-code/{device_key}"
    check_url = f"{api_base}/api/kindle-pair/check-books/{device_key}"

    # Get random motivational quote
    quote = random.choice(MOTIVATIONAL_QUOTES)

    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kindle Book Transfer</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: Arial, sans-serif;
            background: white;
            padding: 20px;
            max-width: 800px;
            margin: 0 auto;
        }}
        h1 {{
            text-align: center;
            margin-bottom: 20px;
            font-size: 18px;
            color: #666;
            font-style: italic;
            font-weight: normal;
        }}
        .section {{
            border: 2px solid #ccc;
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 15px;
        }}
        .device-key {{
            font-size: 32px;
            font-weight: bold;
            color: #2563eb;
            font-family: monospace;
            letter-spacing: 4px;
            margin: 3px 0;
        }}
        .instruction {{
            text-align: center;
            color: #666;
            margin-bottom: 20px;
        }}
        .qr-code {{
            text-align: center;
            padding-top: 20px;
            border-top: 1px solid #ddd;
        }}
        .qr-code img {{
            border: 2px solid #ddd;
            border-radius: 4px;
        }}
        .books-list {{
            margin-top: 10px;
        }}
        .book-item {{
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 8px;
            margin-bottom: 6px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .book-info {{
            flex: 1;
            min-width: 0;
        }}
        .book-title {{
            font-size: 14px;
            font-weight: bold;
            margin-bottom: 2px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .book-author {{
            color: #666;
            font-size: 12px;
            margin-bottom: 0;
        }}
        .book-formats {{
            font-size: 10px;
            color: #999;
        }}
        .download-btn {{
            display: inline-block;
            background: #2563eb;
            color: white;
            padding: 6px 12px;
            text-decoration: none;
            border-radius: 4px;
            font-size: 13px;
            white-space: nowrap;
            flex-shrink: 0;
        }}
        .loading {{
            text-align: center;
            color: #666;
            padding: 40px;
        }}
        .refresh-note {{
            text-align: center;
            color: #999;
            font-size: 12px;
            margin-top: 20px;
        }}
    </style>
</head>
<body>
    <h1>"{quote}"</h1>

    <div class="section">
        <div style="display: flex; align-items: center; gap: 15px;">
            <div style="flex: 1;">
                <h2 style="margin: 0 0 8px 0; font-size: 18px;">Ghép nối thiết bị</h2>
                <div style="color: #666; font-size: 12px; margin-bottom: 3px;">Mã thiết bị:</div>
                <div class="device-key" id="deviceKey">{device_key}</div>
                <div id="keyStatus" style="color: #059669; font-size: 10px; margin-top: 3px; display: none;">
                    ✓ Đang dùng mã đã lưu
                </div>
                <div style="color: #666; font-size: 11px; margin-top: 5px;">
                    Nhập tại: <strong>{frontend_url}/pair</strong>
                </div>
            </div>
            <div style="text-align: center; flex-shrink: 0;">
                <div style="color: #666; font-size: 11px; margin-bottom: 3px;">Quét QR:</div>
                <img src="{qr_code_url}" alt="QR Code" width="100" height="100" style="border: 2px solid #ddd; border-radius: 4px;">
            </div>
        </div>
    </div>

    <div class="section">
        <h2 style="margin-bottom: 10px; font-size: 18px;">Sách đã chọn <span id="bookCount"></span></h2>
        <div id="booksList" class="loading">
            Chưa chọn sách nào.<br>
            Chọn sách từ thiết bị đã ghép nối để tải về đây.
        </div>
    </div>

    <div class="refresh-note">
        Trang tự động làm mới sau 10 giây • Phiên hết hạn sau 30 phút
    </div>

    <script>
        // Use current page's protocol to ensure HTTPS when accessed via HTTPS
        const PROTOCOL = window.location.protocol;
        const HOST = window.location.host;
        const DEVICE_KEY = '{device_key}';
        const CHECK_URL = PROTOCOL + '//' + HOST + '/api/kindle-pair/check-books/' + DEVICE_KEY;
        const API_BASE = PROTOCOL + '//' + HOST + '/api';

        console.log('Protocol:', PROTOCOL);
        console.log('Host:', HOST);
        console.log('API_BASE:', API_BASE);
        console.log('CHECK_URL:', CHECK_URL);

        // Persist device key in localStorage
        try {{
            const STORAGE_KEY = 'kindle_device_key';
            const storedKey = localStorage.getItem(STORAGE_KEY);
            const urlParams = new URLSearchParams(window.location.search);
            const keyParam = urlParams.get('key');

            // If we have a new key and it's different from stored, save it
            if (DEVICE_KEY && DEVICE_KEY !== storedKey) {{
                localStorage.setItem(STORAGE_KEY, DEVICE_KEY);
                console.log('Saved device key to localStorage:', DEVICE_KEY);
            }}

            // Show status if using stored key
            if (keyParam && keyParam === storedKey) {{
                const statusEl = document.getElementById('keyStatus');
                if (statusEl) {{
                    statusEl.style.display = 'block';
                }}
            }}

            // If no key in URL but we have a stored key, redirect to use it
            if (!keyParam && storedKey && storedKey !== DEVICE_KEY) {{
                console.log('Redirecting to use stored key:', storedKey);
                window.location.href = window.location.pathname + '?key=' + storedKey;
            }}
        }} catch (e) {{
            console.error('localStorage not available:', e);
        }}

        function resetDevice() {{
            try {{
                localStorage.removeItem('kindle_device_key');
                console.log('Cleared stored device key');
            }} catch (e) {{
                console.error('Error clearing localStorage:', e);
            }}
            // Redirect to get a new key
            window.location.href = window.location.pathname;
        }}

        function formatAuthors(authors) {{
            return authors.map(a => a.name).join(', ');
        }}

        function getDownloadUrl(bookId, formats) {{
            const preferred = ['MOBI', 'AZW3', 'AZW', 'EPUB', 'PDF'];
            const format = preferred.find(f => formats.includes(f)) || formats[0];
            if (!format) return null;
            return API_BASE + '/files/book/' + bookId + '/' + format.toLowerCase();
        }}

        async function checkBooks() {{
            try {{
                const response = await fetch(CHECK_URL);
                if (!response.ok) {{
                    if (response.status === 404) {{
                        document.getElementById('booksList').innerHTML =
                            '<div style="color: red;">' +
                            'Phiên đã hết hạn. ' +
                            '<a href="#" onclick="resetDevice(); return false;" style="color: blue; text-decoration: underline;">Tạo mã mới</a>' +
                            '</div>';
                        return;
                    }}
                    throw new Error('Failed to check books');
                }}

                const data = await response.json();
                const books = data.books || [];

                const countEl = document.getElementById('bookCount');
                const listEl = document.getElementById('booksList');

                if (books.length === 0) {{
                    countEl.textContent = '';
                    listEl.className = 'loading';
                    listEl.innerHTML = 'Chưa chọn sách nào.<br>Chọn sách từ thiết bị đã ghép nối để tải về đây.';
                }} else {{
                    countEl.textContent = '(' + books.length + ')';
                    listEl.className = 'books-list';

                    listEl.innerHTML = books.map(book => {{
                        const downloadUrl = getDownloadUrl(book.id, book.file_formats);
                        const downloadBtn = downloadUrl ?
                            '<a href="' + downloadUrl + '" class="download-btn" download>Tải về</a>' : '';

                        return '<div class="book-item">' +
                            '<div class="book-info">' +
                            '<div class="book-title">' + book.title + '</div>' +
                            '<div class="book-author">' + formatAuthors(book.authors) + '</div>' +
                            '<div class="book-formats">Định dạng: ' + book.file_formats.join(', ') + '</div>' +
                            '</div>' +
                            downloadBtn +
                            '</div>';
                    }}).join('');
                }}
            }} catch (err) {{
                console.error('Error checking books:', err);
            }}
        }}

        // Check immediately
        checkBooks();

        // Then check every 10 seconds
        setInterval(checkBooks, 10000);
    </script>
</body>
</html>
    """

    return HTMLResponse(content=html_content)
