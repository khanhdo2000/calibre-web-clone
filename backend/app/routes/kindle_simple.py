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
            overflow: hidden;
        }}
        .book-info {{
            overflow: hidden;
            margin-right: 90px;
        }}
        .book-item .download-btn {{
            float: right;
            margin-left: 10px;
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
            padding: 12px 20px;
            text-decoration: none;
            border-radius: 4px;
            font-size: 16px;
            white-space: nowrap;
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
        .refresh-btn {{
            display: inline-block;
            background: #059669;
            color: white;
            padding: 8px 16px;
            text-decoration: none;
            border-radius: 4px;
            font-size: 13px;
            margin: 10px 5px;
            border: none;
            cursor: pointer;
        }}
        .refresh-btn:hover {{
            background: #047857;
        }}
        .refresh-btn:active {{
            background: #065f46;
        }}
    </style>
</head>
<body>
    <h1>"{quote}"</h1>

    <div class="section">
        <div style="overflow: hidden;">
            <div style="float: right; text-align: center; margin-left: 15px;">
                <div style="color: #666; font-size: 11px; margin-bottom: 3px;">Quét QR:</div>
                <img src="{qr_code_url}" alt="QR Code" width="100" height="100" style="border: 2px solid #ddd; border-radius: 4px;">
            </div>
            <div style="overflow: hidden;">
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
        </div>
    </div>

    <div class="section">
        <h2 style="margin-bottom: 10px; font-size: 18px;">Sách đã chọn <span id="bookCount"></span></h2>
        <div style="background: #f0fdf4; border: 1px solid #86efac; border-radius: 4px; padding: 8px; margin-bottom: 10px; font-size: 11px; color: #166534;">
            ✓ Tự động chọn định dạng tốt nhất cho thiết bị của bạn
        </div>
        <div id="booksList" class="loading">
            Chưa chọn sách nào.<br>
            Chọn sách từ thiết bị đã ghép nối để tải về đây.
        </div>
    </div>

    <div class="refresh-note">
        <button onclick="manualRefresh(); return false;" class="refresh-btn">🔄 Làm mới ngay</button><br>
        Trang tự động làm mới sau 5 giây • Phiên hết hạn sau 30 phút
    </div>

    <script>
        // Use current page's protocol to ensure HTTPS when accessed via HTTPS
        var PROTOCOL = window.location.protocol;
        var HOST = window.location.host;
        var DEVICE_KEY = '{device_key}';
        var CHECK_URL = PROTOCOL + '//' + HOST + '/api/kindle-pair/check-books/' + DEVICE_KEY;
        var API_BASE = PROTOCOL + '//' + HOST + '/api';
        var pollInterval = null;
        var lastCheckTime = Date.now();

        // Persist device key in localStorage (with try-catch for older browsers)
        try {{
            var STORAGE_KEY = 'kindle_device_key';
            var storedKey = localStorage.getItem(STORAGE_KEY);
            var urlParams = new URLSearchParams(window.location.search);
            var keyParam = urlParams.get('key');

            // If we have a new key and it's different from stored, save it
            if (DEVICE_KEY && DEVICE_KEY !== storedKey) {{
                localStorage.setItem(STORAGE_KEY, DEVICE_KEY);
            }}

            // Show status if using stored key
            if (keyParam && keyParam === storedKey) {{
                var statusEl = document.getElementById('keyStatus');
                if (statusEl) {{
                    statusEl.style.display = 'block';
                }}
            }}

            // If no key in URL but we have a stored key, redirect to use it
            if (!keyParam && storedKey && storedKey !== DEVICE_KEY) {{
                window.location.href = window.location.pathname + '?key=' + storedKey;
            }}
        }} catch (e) {{
            // localStorage not available, continue without it
        }}

        function resetDevice() {{
            try {{
                localStorage.removeItem('kindle_device_key');
            }} catch (e) {{
                // Ignore errors
            }}
            // Redirect to get a new key
            window.location.href = window.location.pathname;
        }}

        function formatAuthors(authors) {{
            if (!authors || !authors.length) return 'Unknown';
            var names = [];
            for (var i = 0; i < authors.length; i++) {{
                names.push(authors[i].name || 'Unknown');
            }}
            return names.join(', ');
        }}

        // Detect if this is a Kindle browser
        function isKindle() {{
            var ua = navigator.userAgent.toLowerCase();
            return ua.indexOf('kindle') !== -1 || ua.indexOf('silk') !== -1;
        }}

        function getDownloadUrl(bookId, formats) {{
            var format = null;

            if (isKindle()) {{
                // Kindle browser only supports MOBI, PRC, AZW, and AZW3
                var preferred = ['MOBI', 'PRC', 'AZW3', 'AZW'];
                for (var i = 0; i < preferred.length; i++) {{
                    if (formats.indexOf(preferred[i]) !== -1) {{
                        format = preferred[i];
                        break;
                    }}
                }}
            }} else {{
                // Non-Kindle browsers: prefer EPUB, then MOBI/PRC
                var preferred = ['EPUB', 'MOBI', 'PRC', 'AZW3', 'AZW', 'PDF'];
                for (var i = 0; i < preferred.length; i++) {{
                    if (formats.indexOf(preferred[i]) !== -1) {{
                        format = preferred[i];
                        break;
                    }}
                }}
            }}

            if (!format) return null;

            // RSS books have negative IDs - use RSS download endpoint
            if (bookId < 0) {{
                var rssBookId = Math.abs(bookId);
                return {{
                    url: API_BASE + '/rss/books/' + rssBookId + '/download?format=' + format.toLowerCase(),
                    format: format
                }};
            }}

            // Regular books use the files download endpoint
            return {{
                url: API_BASE + '/files/download/' + bookId + '/' + format.toLowerCase(),
                format: format
            }};
        }}

        // Compatible HTTP request function (works with older browsers)
        function makeRequest(url, callback) {{
            // Try fetch first (modern browsers)
            if (window.fetch) {{
                fetch(url)
                    .then(function(response) {{
                        if (!response.ok) {{
                            callback(null, response.status);
                            return;
                        }}
                        return response.json();
                    }})
                    .then(function(data) {{
                        callback(data, null);
                    }})
                    .catch(function(err) {{
                        callback(null, err);
                    }});
                return;
            }}

            // Fallback to XMLHttpRequest (older browsers)
            var xhr = new XMLHttpRequest();
            xhr.onreadystatechange = function() {{
                if (xhr.readyState === 4) {{
                    if (xhr.status === 200) {{
                        try {{
                            var data = JSON.parse(xhr.responseText);
                            callback(data, null);
                        }} catch (e) {{
                            callback(null, 'Parse error');
                        }}
                    }} else if (xhr.status === 404) {{
                        callback(null, 404);
                    }} else {{
                        callback(null, xhr.status);
                    }}
                }}
            }};
            xhr.onerror = function() {{
                callback(null, 'Network error');
            }};
            xhr.open('GET', url, true);
            xhr.timeout = 10000; // 10 second timeout
            xhr.ontimeout = function() {{
                callback(null, 'Timeout');
            }};
            xhr.send();
        }}

        function checkBooks() {{
            lastCheckTime = Date.now();
            makeRequest(CHECK_URL, function(data, error) {{
                var countEl = document.getElementById('bookCount');
                var listEl = document.getElementById('booksList');

                if (error) {{
                    if (error === 404) {{
                        listEl.innerHTML =
                            '<div style="color: red;">' +
                            'Phiên đã hết hạn. ' +
                            '<a href="#" onclick="resetDevice(); return false;" style="color: blue; text-decoration: underline;">Tạo mã mới</a>' +
                            '</div>';
                        // Stop polling if session expired
                        if (pollInterval) {{
                            clearInterval(pollInterval);
                            pollInterval = null;
                        }}
                    }} else {{
                        // Show error but keep polling
                        listEl.innerHTML = '<div style="color: #999; font-size: 12px;">Đang kết nối... (Lỗi: ' + error + ')</div>';
                    }}
                    return;
                }}

                if (!data || !data.books) {{
                    return;
                }}

                var books = data.books || [];

                if (books.length === 0) {{
                    if (countEl) countEl.textContent = '';
                    listEl.className = 'loading';
                    listEl.innerHTML = 'Chưa chọn sách nào.<br>Chọn sách từ thiết bị đã ghép nối để tải về đây.';
                }} else {{
                    if (countEl) countEl.textContent = '(' + books.length + ')';
                    listEl.className = 'books-list';

                    var html = '';
                    var supportedBooks = [];

                    // Filter books to only show those with supported formats
                    for (var i = 0; i < books.length; i++) {{
                        var book = books[i];
                        var downloadInfo = getDownloadUrl(book.id, book.file_formats);
                        if (downloadInfo) {{
                            supportedBooks.push({{book: book, downloadInfo: downloadInfo}});
                        }}
                    }}

                    if (supportedBooks.length === 0) {{
                        listEl.className = 'loading';
                        listEl.innerHTML = 'Không có sách tương thích.<br>Vui lòng chọn sách khác.';
                    }} else {{
                        for (var i = 0; i < supportedBooks.length; i++) {{
                            var item = supportedBooks[i];
                            var book = item.book;
                            var downloadInfo = item.downloadInfo;

                            html += '<div class="book-item">' +
                                '<a href="' + downloadInfo.url + '" class="download-btn" download>Tải về</a>' +
                                '<div class="book-info">' +
                                '<div class="book-title">' + (book.title || 'Untitled') + '</div>' +
                                '<div class="book-author">' + formatAuthors(book.authors) + '</div>' +
                                '<div class="book-formats">Định dạng: ' + downloadInfo.format + '</div>' +
                                '</div>' +
                                '</div>';
                        }}
                        listEl.innerHTML = html;
                    }}
                }}
            }});
        }}

        // Check immediately
        checkBooks();

        // Then check every 5 seconds (with fallback mechanism)
        pollInterval = setInterval(function() {{
            // Check if page is still active (prevent issues with background tabs)
            var timeSinceLastCheck = Date.now() - lastCheckTime;
            if (timeSinceLastCheck > 30000) {{
                // If more than 30 seconds since last check, something might be wrong
                // Try to restart polling
                if (pollInterval) {{
                    clearInterval(pollInterval);
                }}
                pollInterval = setInterval(checkBooks, 5000);
            }}
            checkBooks();
        }}, 5000);

        // Add manual refresh button handler
        function manualRefresh() {{
            checkBooks();
        }}

        // Add meta refresh as ultimate fallback (refreshes page every 60 seconds)
        // This ensures the page updates even if JavaScript fails
        setTimeout(function() {{
            var metaRefresh = document.createElement('meta');
            metaRefresh.httpEquiv = 'refresh';
            metaRefresh.content = '60';
            document.getElementsByTagName('head')[0].appendChild(metaRefresh);
        }}, 5000); // Add after 5 seconds to let JS polling work first
    </script>
</body>
</html>
    """

    return HTMLResponse(content=html_content)
