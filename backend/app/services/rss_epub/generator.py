"""EPUB Generator - creates EPUB files from articles with embedded images"""
import logging
import os
import re
from datetime import date, datetime
from typing import List, Optional, Dict
from ebooklib import epub
from .fetcher import Article

logger = logging.getLogger(__name__)


class EpubGenerator:
    """Generates EPUB files from a list of articles with embedded images"""

    def __init__(self, output_dir: str = "/data/rss-epubs"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate(
        self,
        articles: List[Article],
        title: str,
        author: str = "RSS Feed",
        language: str = "vi",
        cover_image: Optional[bytes] = None
    ) -> Optional[str]:
        """
        Generate an EPUB file from a list of articles.

        Args:
            articles: List of Article objects
            title: Book title
            author: Book author/source name
            language: Language code (default: vi for Vietnamese)
            cover_image: Optional cover image bytes

        Returns:
            Path to the generated EPUB file, or None if failed
        """
        if not articles:
            logger.warning("No articles provided for EPUB generation")
            return None

        try:
            book = epub.EpubBook()

            # Set metadata
            book.set_identifier(f"rss-{self._sanitize_filename(title)}-{date.today().isoformat()}")
            book.set_title(title)
            book.set_language(language)
            book.add_author(author)
            book.add_metadata("DC", "date", date.today().isoformat())

            # Add cover if provided
            if cover_image:
                book.set_cover("cover.jpg", cover_image)

            # Collect all images from all articles
            all_images: Dict[str, bytes] = {}
            for article in articles:
                all_images.update(article.images)

            # Add images to book
            image_items = {}
            for filename, img_data in all_images.items():
                media_type = self._get_media_type(filename)
                img_item = epub.EpubItem(
                    uid=f"image_{filename}",
                    file_name=f"images/{filename}",
                    media_type=media_type,
                    content=img_data
                )
                book.add_item(img_item)
                image_items[filename] = img_item

            logger.info(f"Added {len(image_items)} images to EPUB")

            # Create chapters from articles
            chapters = []
            toc = []

            for idx, article in enumerate(articles, 1):
                chapter = self._create_chapter(article, idx)
                book.add_item(chapter)
                chapters.append(chapter)
                toc.append(chapter)

            # Add Table of Contents
            book.toc = toc

            # Add navigation files
            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())

            # Add CSS
            style = self._get_default_css()
            nav_css = epub.EpubItem(
                uid="style_nav",
                file_name="style/nav.css",
                media_type="text/css",
                content=style
            )
            book.add_item(nav_css)

            # Set spine
            book.spine = ["nav"] + chapters

            # Generate filename
            today = date.today()
            filename = f"{self._sanitize_filename(title)}_{today.strftime('%Y%m%d')}.epub"
            filepath = os.path.join(self.output_dir, filename)

            # Write EPUB file
            epub.write_epub(filepath, book, {})

            file_size = os.path.getsize(filepath)
            logger.info(f"Generated EPUB: {filepath} ({file_size} bytes, {len(articles)} articles, {len(image_items)} images)")

            return filepath

        except Exception as e:
            logger.error(f"Failed to generate EPUB: {e}")
            return None

    def _create_chapter(self, article: Article, index: int) -> epub.EpubHtml:
        """Create an EPUB chapter from an article"""
        # Create HTML content
        published_str = ""
        if article.published:
            published_str = f'<p class="date">{article.published.strftime("%d/%m/%Y %H:%M")}</p>'

        author_str = ""
        if article.author:
            author_str = f'<p class="author">Tác giả: {article.author}</p>'

        source_str = f'<p class="source"><a href="{article.url}">Nguồn gốc</a></p>'

        # Clean content - remove any existing html/body tags
        content = article.content
        content = re.sub(r'<html[^>]*>', '', content, flags=re.IGNORECASE)
        content = re.sub(r'</html>', '', content, flags=re.IGNORECASE)
        content = re.sub(r'<body[^>]*>', '', content, flags=re.IGNORECASE)
        content = re.sub(r'</body>', '', content, flags=re.IGNORECASE)
        content = re.sub(r'<head[^>]*>.*?</head>', '', content, flags=re.IGNORECASE | re.DOTALL)

        html_content = f"""<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>{self._escape_html(article.title)}</title>
    <link rel="stylesheet" type="text/css" href="style/nav.css"/>
</head>
<body>
    <h1>{self._escape_html(article.title)}</h1>
    {published_str}
    {author_str}
    <div class="content">
        {content}
    </div>
    {source_str}
</body>
</html>"""

        chapter = epub.EpubHtml(
            title=article.title,
            file_name=f"chapter_{index:03d}.xhtml",
            lang="vi"
        )
        chapter.content = html_content

        return chapter

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters"""
        return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))

    def _get_media_type(self, filename: str) -> str:
        """Get MIME type for image file"""
        filename_lower = filename.lower()
        if filename_lower.endswith('.png'):
            return 'image/png'
        elif filename_lower.endswith('.gif'):
            return 'image/gif'
        elif filename_lower.endswith('.webp'):
            return 'image/webp'
        elif filename_lower.endswith('.svg'):
            return 'image/svg+xml'
        else:
            return 'image/jpeg'

    def _get_default_css(self) -> str:
        """Return default CSS for the EPUB"""
        return """
body {
    font-family: Georgia, "Times New Roman", serif;
    font-size: 1em;
    line-height: 1.6;
    margin: 1em;
    color: #333;
}
h1 {
    font-size: 1.4em;
    margin-bottom: 0.5em;
    color: #222;
    line-height: 1.3;
}
.date, .author {
    font-size: 0.85em;
    color: #666;
    margin: 0.2em 0;
}
.content {
    margin-top: 1em;
}
.content p {
    text-indent: 1em;
    margin: 0.5em 0;
}
.content img {
    max-width: 100%;
    height: auto;
    display: block;
    margin: 1em auto;
}
.content figure {
    margin: 1em 0;
    text-align: center;
}
.content figcaption {
    font-size: 0.85em;
    color: #666;
    font-style: italic;
    margin-top: 0.5em;
}
.source {
    font-size: 0.8em;
    color: #888;
    margin-top: 2em;
    border-top: 1px solid #ddd;
    padding-top: 0.5em;
}
a {
    color: #0066cc;
    text-decoration: none;
}
blockquote {
    margin: 1em 2em;
    padding-left: 1em;
    border-left: 3px solid #ccc;
    color: #555;
    font-style: italic;
}
"""

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize a string to be used as a filename"""
        # Remove or replace invalid characters
        name = re.sub(r'[<>:"/\\|?*]', '', name)
        # Replace spaces and special chars with underscore
        name = re.sub(r'[\s\-]+', '_', name)
        # Remove non-ASCII for safety
        name = name.encode('ascii', 'ignore').decode('ascii')
        # Limit length
        return name[:100].strip('_')
