"""RSS Feed Fetcher - parses RSS feeds and extracts full article content with images"""
import io
import logging
import re
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict
from urllib.parse import urljoin, urlparse
import feedparser
import httpx
from readability import Document
from PIL import Image

logger = logging.getLogger(__name__)


@dataclass
class Article:
    """Represents a single article from an RSS feed"""
    title: str
    url: str
    content: str  # Full HTML content
    author: Optional[str] = None
    published: Optional[datetime] = None
    summary: Optional[str] = None
    images: Dict[str, bytes] = field(default_factory=dict)  # url -> image bytes


class RssFetcher:
    """Fetches and parses RSS feeds, extracting full article content with images"""

    def __init__(
        self,
        timeout: int = 30,
        download_images: bool = True,
        max_image_width: int = 800,
        jpeg_quality: int = 75
    ):
        self.timeout = timeout
        self.download_images = download_images
        self.max_image_width = max_image_width
        self.jpeg_quality = jpeg_quality
        self.client = httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
        )

    def fetch_feed(self, feed_url: str, max_articles: int = 50) -> List[Article]:
        """
        Fetch RSS feed and extract articles with full content and images.

        Args:
            feed_url: URL of the RSS feed
            max_articles: Maximum number of articles to fetch (default: 50)

        Returns:
            List of Article objects
        """
        try:
            logger.info(f"Fetching RSS feed: {feed_url}")
            feed = feedparser.parse(feed_url)

            if feed.bozo and not feed.entries:
                logger.error(f"Failed to parse feed {feed_url}: {feed.bozo_exception}")
                return []

            articles = []
            for entry in feed.entries[:max_articles]:
                try:
                    article = self._process_entry(entry)
                    if article:
                        articles.append(article)
                except Exception as e:
                    logger.warning(f"Failed to process entry '{entry.get('title', 'Unknown')}': {e}")
                    continue

            logger.info(f"Fetched {len(articles)} articles from {feed_url}")
            return articles

        except Exception as e:
            logger.error(f"Error fetching feed {feed_url}: {e}")
            return []

    def _process_entry(self, entry: dict) -> Optional[Article]:
        """Process a single feed entry and extract full content"""
        title = entry.get("title", "Untitled")
        url = entry.get("link", "")

        if not url:
            return None

        # Extract thumbnail from RSS feed first
        thumbnail_url = self._extract_thumbnail(entry)

        # Try to get content from feed first
        content = ""
        if "content" in entry and entry["content"]:
            content = entry["content"][0].get("value", "")
        elif "summary" in entry:
            content = entry.get("summary", "")

        # If content is too short, fetch full article
        if len(content) < 500:
            full_content = self._fetch_full_article(url)
            if full_content:
                content = full_content

        # Download images from content
        images = {}
        if self.download_images and content:
            content, images = self._process_images(content, url)

        # Add thumbnail image if we have one and it's not already in content
        if thumbnail_url and self.download_images:
            thumb_data = self._download_image(thumbnail_url)
            if thumb_data:
                url_hash = hashlib.md5(thumbnail_url.encode()).hexdigest()[:12]
                ext = self._get_image_extension(thumbnail_url)
                thumb_filename = f"thumb_{url_hash}{ext}"
                images[thumb_filename] = thumb_data
                # Prepend thumbnail to content if not already present
                if thumb_filename not in content and thumbnail_url not in content:
                    content = f'<figure><img src="images/{thumb_filename}" alt="{title}"/></figure>\n{content}'
                    logger.debug(f"Added thumbnail: {thumb_filename}")

        # Parse published date
        published = None
        if "published_parsed" in entry and entry["published_parsed"]:
            try:
                published = datetime(*entry["published_parsed"][:6])
            except:
                pass
        elif "updated_parsed" in entry and entry["updated_parsed"]:
            try:
                published = datetime(*entry["updated_parsed"][:6])
            except:
                pass

        # Get author
        author = entry.get("author", None)
        if not author and "authors" in entry and entry["authors"]:
            author = entry["authors"][0].get("name", None)

        return Article(
            title=title,
            url=url,
            content=content,
            author=author,
            published=published,
            summary=entry.get("summary", "")[:500] if entry.get("summary") else None,
            images=images
        )

    def _extract_thumbnail(self, entry: dict) -> Optional[str]:
        """Extract thumbnail image URL from RSS feed entry"""
        # Try media:thumbnail (common in RSS 2.0 with media namespace)
        if "media_thumbnail" in entry and entry["media_thumbnail"]:
            thumbnails = entry["media_thumbnail"]
            if isinstance(thumbnails, list) and thumbnails:
                # Get the largest thumbnail
                best = max(thumbnails, key=lambda x: int(x.get("width", 0) or 0))
                if "url" in best:
                    return best["url"]

        # Try media:content
        if "media_content" in entry and entry["media_content"]:
            for media in entry["media_content"]:
                if media.get("medium") == "image" or "image" in media.get("type", ""):
                    return media.get("url")

        # Try enclosures (common for images in RSS)
        if "enclosures" in entry and entry["enclosures"]:
            for enc in entry["enclosures"]:
                if enc.get("type", "").startswith("image/"):
                    return enc.get("href") or enc.get("url")

        # Try to extract from summary/content HTML
        summary = entry.get("summary", "") or ""
        if "<img" in summary:
            match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', summary, re.IGNORECASE)
            if match:
                return match.group(1)

        # Try links with image type
        if "links" in entry:
            for link in entry["links"]:
                if link.get("type", "").startswith("image/"):
                    return link.get("href")

        return None

    def _fetch_full_article(self, url: str) -> Optional[str]:
        """Fetch and extract full article content using readability"""
        try:
            response = self.client.get(url)
            response.raise_for_status()

            doc = Document(response.text)
            content = doc.summary()

            if content:
                return content

        except Exception as e:
            logger.debug(f"Could not fetch full article from {url}: {e}")

        return None

    def _process_images(self, content: str, base_url: str) -> tuple[str, Dict[str, bytes]]:
        """
        Download images from content and replace URLs with local references.

        Returns:
            Tuple of (modified content, dict of image_filename -> image_bytes)
        """
        images = {}

        # Find all image URLs in content
        img_pattern = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.IGNORECASE)
        matches = img_pattern.findall(content)

        for img_url in matches:
            try:
                # Make absolute URL
                absolute_url = urljoin(base_url, img_url)

                # Generate filename from URL hash
                url_hash = hashlib.md5(absolute_url.encode()).hexdigest()[:12]
                ext = self._get_image_extension(absolute_url)
                filename = f"img_{url_hash}{ext}"

                # Download image
                img_data = self._download_image(absolute_url)
                if img_data:
                    images[filename] = img_data
                    # Replace URL in content with local reference
                    content = content.replace(img_url, f"images/{filename}")
                    logger.debug(f"Downloaded image: {filename}")

            except Exception as e:
                logger.debug(f"Failed to download image {img_url}: {e}")
                continue

        return content, images

    def _download_image(self, url: str) -> Optional[bytes]:
        """Download an image, resize and compress it"""
        try:
            response = self.client.get(url, timeout=15)
            response.raise_for_status()

            content_type = response.headers.get("content-type", "")
            if "image" in content_type or self._is_image_url(url):
                # Limit original image size to 5MB
                if len(response.content) > 5 * 1024 * 1024:
                    return None

                # Compress image
                return self._compress_image(response.content)

        except Exception as e:
            logger.debug(f"Failed to download image {url}: {e}")

        return None

    def _compress_image(self, image_data: bytes) -> Optional[bytes]:
        """Resize and compress image to reduce file size"""
        try:
            img = Image.open(io.BytesIO(image_data))

            # Convert to RGB if necessary (for PNG with transparency, etc.)
            if img.mode in ('RGBA', 'P', 'LA'):
                # Create white background for transparent images
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            # Resize if wider than max width
            if img.width > self.max_image_width:
                ratio = self.max_image_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((self.max_image_width, new_height), Image.Resampling.LANCZOS)

            # Save as JPEG with compression
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=self.jpeg_quality, optimize=True)
            compressed = output.getvalue()

            logger.debug(f"Compressed image: {len(image_data)} -> {len(compressed)} bytes")
            return compressed

        except Exception as e:
            logger.debug(f"Failed to compress image: {e}")
            # Return original if compression fails
            return image_data

    def _get_image_extension(self, url: str) -> str:
        """Get image extension from URL"""
        parsed = urlparse(url)
        path = parsed.path.lower()

        if '.png' in path:
            return '.png'
        elif '.gif' in path:
            return '.gif'
        elif '.webp' in path:
            return '.webp'
        elif '.svg' in path:
            return '.svg'
        else:
            return '.jpg'

    def _is_image_url(self, url: str) -> bool:
        """Check if URL likely points to an image"""
        image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg')
        return any(url.lower().endswith(ext) for ext in image_extensions)

    def close(self):
        """Close the HTTP client"""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
