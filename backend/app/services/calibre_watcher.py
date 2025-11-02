import os
import logging
import asyncio
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from typing import Callable, Optional

from app.config import settings
from app.services.cache import cache_service

logger = logging.getLogger(__name__)


class CalibreDBWatcher(FileSystemEventHandler):
    """
    Watch Calibre's metadata.db for changes from Calibre desktop.

    When Calibre desktop modifies the database:
    1. SQLite creates a -wal (write-ahead log) and -shm (shared memory) file
    2. On commit, these are merged back to metadata.db
    3. We detect changes and invalidate cache

    This ensures the web interface shows fresh data when books are added/modified
    via Calibre desktop without needing to restart the server.
    """

    def __init__(self, on_change_callback: Optional[Callable] = None):
        self.db_path = os.path.join(settings.calibre_library_path, "metadata.db")
        self.on_change_callback = on_change_callback
        self._debounce_task = None
        self._debounce_delay = 2  # Wait 2 seconds after last change

    def on_modified(self, event):
        """Called when metadata.db or related files are modified"""
        if event.is_directory:
            return

        # Monitor metadata.db and its WAL files
        if any(name in event.src_path for name in ["metadata.db", "metadata.db-wal", "metadata.db-shm"]):
            logger.info(f"Detected change in Calibre database: {event.src_path}")
            self._schedule_cache_invalidation()

    def _schedule_cache_invalidation(self):
        """Debounce cache invalidation to avoid excessive clearing during imports"""
        if self._debounce_task:
            self._debounce_task.cancel()

        self._debounce_task = asyncio.create_task(self._invalidate_cache_after_delay())

    async def _invalidate_cache_after_delay(self):
        """Wait for changes to settle, then invalidate cache"""
        try:
            await asyncio.sleep(self._debounce_delay)
            await self._invalidate_cache()

            if self.on_change_callback:
                await self.on_change_callback()

        except asyncio.CancelledError:
            pass  # Task was cancelled by a new change
        except Exception as e:
            logger.error(f"Error invalidating cache: {e}")

    async def _invalidate_cache(self):
        """Clear all book-related cache entries"""
        logger.info("Invalidating cache due to Calibre database changes")

        patterns = [
            "books:*",
            "book:*",
            "search:*",
            "metadata:*",
        ]

        for pattern in patterns:
            await cache_service.delete_pattern(pattern)

        logger.info("Cache invalidated successfully")


class CalibreWatcherService:
    """Service to manage the file watcher"""

    def __init__(self):
        self.observer: Optional[Observer] = None
        self.watcher: Optional[CalibreDBWatcher] = None

    def start(self, on_change_callback: Optional[Callable] = None):
        """Start watching the Calibre library directory"""
        if not settings.watch_calibre_db:
            logger.info("Calibre DB watching disabled")
            return

        if not os.path.exists(settings.calibre_library_path):
            logger.warning(f"Calibre library path not found: {settings.calibre_library_path}")
            return

        try:
            self.watcher = CalibreDBWatcher(on_change_callback)
            self.observer = Observer()
            self.observer.schedule(
                self.watcher,
                settings.calibre_library_path,
                recursive=False
            )
            self.observer.start()
            logger.info(f"Started watching Calibre database at {settings.calibre_library_path}")

        except Exception as e:
            logger.error(f"Failed to start Calibre watcher: {e}")

    def stop(self):
        """Stop watching"""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            logger.info("Stopped Calibre database watcher")


# Singleton instance
calibre_watcher = CalibreWatcherService()
