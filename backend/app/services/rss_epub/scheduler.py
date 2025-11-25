"""RSS Scheduler - handles daily EPUB generation"""
import logging
import os
import subprocess
from datetime import date
from typing import List, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rss_feed import RssFeed, RssGeneratedBook
from app.database import async_session_maker
from .fetcher import RssFetcher
from .generator import EpubGenerator

logger = logging.getLogger(__name__)


class RssScheduler:
    """Manages scheduled RSS-to-EPUB generation"""

    def __init__(
        self,
        output_dir: str = "/data/rss-epubs",
        calibre_library_path: Optional[str] = None
    ):
        self.output_dir = output_dir
        self.calibre_library_path = calibre_library_path
        self.scheduler = AsyncIOScheduler()
        self.fetcher = RssFetcher()
        self.generator = EpubGenerator(output_dir=output_dir)

    def start(self, hour: int = 6, minute: int = 0):
        """
        Start the scheduler for daily generation.

        Args:
            hour: Hour to run (0-23), default 6 AM
            minute: Minute to run (0-59), default 0
        """
        trigger = CronTrigger(hour=hour, minute=minute)
        self.scheduler.add_job(
            self._scheduled_generation_wrapper,
            trigger,
            id="rss_daily_generation",
            replace_existing=True
        )
        self.scheduler.start()
        logger.info(f"RSS scheduler started - will run daily at {hour:02d}:{minute:02d}")

    def stop(self):
        """Stop the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("RSS scheduler stopped")

    async def _scheduled_generation_wrapper(self):
        """
        Wrapper for scheduled generation that creates its own database session.
        This is needed because APScheduler can't inject dependencies.
        """
        async with async_session_maker() as db:
            try:
                await self._generate_all_feeds(db)
            except Exception as e:
                logger.error(f"Error in scheduled RSS generation: {e}")
            finally:
                await db.close()

    async def generate_now(self, db: AsyncSession) -> List[str]:
        """
        Manually trigger generation for all enabled feeds.

        Returns:
            List of generated EPUB file paths
        """
        return await self._generate_all_feeds(db)

    async def generate_feed(
        self,
        db: AsyncSession,
        feed: RssFeed
    ) -> Optional[str]:
        """
        Generate EPUB for a single feed.

        Returns:
            Path to generated EPUB or None
        """
        logger.info(f"Generating EPUB for feed: {feed.name}")

        # Fetch articles
        articles = self.fetcher.fetch_feed(feed.url, max_articles=feed.max_articles or 20)

        if not articles:
            logger.warning(f"No articles found for feed: {feed.name}")
            return None

        # Generate title with date
        today = date.today()
        title = f"{feed.name} - {today.strftime('%d/%m/%Y')}"

        # Generate EPUB
        filepath = self.generator.generate(
            articles=articles,
            title=title,
            author=feed.name
        )

        if filepath:
            # Record in database
            filename = os.path.basename(filepath)
            file_size = os.path.getsize(filepath)

            # Convert to MOBI
            mobi_path = self._convert_to_mobi(filepath)
            mobi_filename = None
            mobi_file_size = None

            if mobi_path and os.path.exists(mobi_path):
                mobi_filename = os.path.basename(mobi_path)
                mobi_file_size = os.path.getsize(mobi_path)
                logger.info(f"MOBI conversion successful: {mobi_filename}")

            # Delete existing record with same filename if exists
            await db.execute(
                delete(RssGeneratedBook).where(RssGeneratedBook.filename == filename)
            )

            generated_book = RssGeneratedBook(
                feed_id=feed.id,
                title=title,
                filename=filename,
                file_path=filepath,
                file_size=file_size,
                mobi_filename=mobi_filename,
                mobi_file_path=mobi_path,
                mobi_file_size=mobi_file_size,
                article_count=len(articles),
                generation_date=today
            )
            db.add(generated_book)

            # Optionally add to Calibre
            calibre_id = self._add_to_calibre(filepath, feed.category)
            if calibre_id:
                generated_book.calibre_book_id = calibre_id

            await db.commit()
            logger.info(f"Generated and recorded: {filename}" + (f" + {mobi_filename}" if mobi_filename else ""))

        return filepath

    async def _generate_all_feeds(self, db: AsyncSession) -> List[str]:
        """Generate EPUBs for all enabled feeds"""
        logger.info("Starting daily RSS-to-EPUB generation")

        # Get all enabled feeds
        result = await db.execute(
            select(RssFeed).where(RssFeed.enabled == True)
        )
        feeds = result.scalars().all()

        if not feeds:
            logger.info("No enabled feeds found")
            return []

        generated_files = []

        for feed in feeds:
            try:
                filepath = await self.generate_feed(db, feed)
                if filepath:
                    generated_files.append(filepath)
            except Exception as e:
                logger.error(f"Error generating EPUB for feed {feed.name}: {e}")
                continue

        logger.info(f"Daily generation complete: {len(generated_files)} EPUBs created")
        return generated_files

    def _convert_to_mobi(self, epub_path: str) -> Optional[str]:
        """
        Convert EPUB to MOBI using Calibre's ebook-convert.

        Args:
            epub_path: Path to EPUB file

        Returns:
            Path to generated MOBI file or None if conversion failed
        """
        try:
            mobi_path = epub_path.replace('.epub', '.mobi')

            logger.info(f"Converting {epub_path} to MOBI...")

            cmd = ["ebook-convert", epub_path, mobi_path]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )

            if result.returncode == 0 and os.path.exists(mobi_path):
                logger.info(f"Successfully converted to MOBI: {mobi_path}")
                return mobi_path
            else:
                logger.error(f"ebook-convert failed: {result.stderr}")
                return None

        except subprocess.TimeoutExpired:
            logger.error("ebook-convert timed out")
        except Exception as e:
            logger.error(f"Failed to convert to MOBI: {e}")

        return None

    def _add_to_calibre(self, epub_path: str, category: Optional[str] = None) -> Optional[int]:
        """
        Add EPUB to Calibre library using calibredb CLI.

        Returns:
            Calibre book ID if successful, None otherwise
        """
        if not self.calibre_library_path:
            return None

        try:
            cmd = [
                "calibredb", "add",
                "--library-path", self.calibre_library_path,
                epub_path
            ]

            if category:
                cmd.extend(["--tags", category])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                # Parse book ID from output
                # Output format: "Added book ids: X"
                output = result.stdout
                if "Added book ids:" in output:
                    book_id = int(output.split("Added book ids:")[-1].strip())
                    logger.info(f"Added to Calibre with ID: {book_id}")
                    return book_id

        except subprocess.TimeoutExpired:
            logger.error("Calibre add command timed out")
        except Exception as e:
            logger.error(f"Failed to add to Calibre: {e}")

        return None


# Global scheduler instance
rss_scheduler: Optional[RssScheduler] = None


def get_rss_scheduler() -> Optional[RssScheduler]:
    """Get the global RSS scheduler instance"""
    return rss_scheduler


def init_rss_scheduler(
    output_dir: str = "/data/rss-epubs",
    calibre_library_path: Optional[str] = None,
    auto_start: bool = True,
    hour: int = 6,
    minute: int = 0
) -> RssScheduler:
    """
    Initialize the global RSS scheduler.

    Args:
        output_dir: Directory to store generated EPUBs
        calibre_library_path: Path to Calibre library (optional)
        auto_start: Whether to start the scheduler immediately
        hour: Hour to run daily generation (0-23)
        minute: Minute to run daily generation (0-59)

    Returns:
        Initialized RssScheduler instance
    """
    global rss_scheduler

    rss_scheduler = RssScheduler(
        output_dir=output_dir,
        calibre_library_path=calibre_library_path
    )

    if auto_start:
        rss_scheduler.start(hour=hour, minute=minute)

    return rss_scheduler
