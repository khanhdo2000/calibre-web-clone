"""SQLAlchemy-based implementation of CalibreDatabase - cleaner and fixes sorting"""
import os
from typing import List, Optional
import logging

from sqlalchemy import create_engine, func, or_, and_
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.models.book import Book, Author, Tag, Series, Publisher, BookDetail, Category
from app.services.calibre_db_models import Base, Books, Authors, Tags, Series as SeriesModel, Publishers
from app.services.calibre_db import normalize_text

logger = logging.getLogger(__name__)


class CalibreDatabase:
    """Service for reading Calibre's metadata.db using SQLAlchemy ORM"""

    def __init__(self):
        self.db_path = os.path.join(settings.calibre_library_path, "metadata.db")
        if not os.path.exists(self.db_path):
            logger.warning(f"Calibre database not found at {self.db_path}")
            self.engine = None
            self.Session = None
        else:
            # Create SQLAlchemy engine with read-only mode
            db_url = f"sqlite:///{self.db_path}?mode=ro&uri=true"
            self.engine = create_engine(
                db_url,
                poolclass=StaticPool,
                connect_args={"check_same_thread": False},
                echo=False
            )
            # Create session factory
            self.Session = scoped_session(sessionmaker(bind=self.engine))

    def _get_sort_order(self, sort_param: Optional[str], sort_by: Optional[str], order: Optional[str]) -> List:
        """Get SQLAlchemy order_by clause based on sort parameters (like original Calibre-Web)"""
        # Default to newest first
        if sort_param:
            if sort_param == "new":
                return [Books.timestamp.desc()]
            elif sort_param == "old":
                return [Books.timestamp.asc()]
            elif sort_param == "abc":
                return [Books.sort.asc() if Books.sort is not None else Books.title.asc()]
            elif sort_param == "zyx":
                return [Books.sort.desc() if Books.sort is not None else Books.title.desc()]
            elif sort_param == "pubnew":
                return [Books.pubdate.desc()]
            elif sort_param == "pubold":
                return [Books.pubdate.asc()]
            elif sort_param == "seriesasc":
                return [Books.series_index.asc()]
            elif sort_param == "seriesdesc":
                return [Books.series_index.desc()]
            elif sort_param == "authaz":
                # Sort by author (use MIN to get first author when multiple)
                return [func.min(Authors.name).asc(), Books.title.asc()]
            elif sort_param == "authza":
                return [func.min(Authors.name).desc(), Books.title.desc()]
        
        # Fallback to sort_by/order
        if sort_by == "timestamp":
            return [Books.timestamp.desc() if order == "desc" else Books.timestamp.asc()]
        elif sort_by == "title":
            return [Books.sort.desc() if order == "desc" else Books.sort.asc()] if Books.sort else [Books.title.desc() if order == "desc" else Books.title.asc()]
        elif sort_by == "pubdate":
            return [Books.pubdate.desc() if order == "desc" else Books.pubdate.asc()]
        elif sort_by == "series_index":
            return [Books.series_index.desc() if order == "desc" else Books.series_index.asc()]
        
        # Default
        return [Books.timestamp.desc()]

    def get_books(
        self,
        page: int = 1,
        per_page: int = 20,
        sort_by: Optional[str] = None,
        order: Optional[str] = None,
        sort_param: Optional[str] = None,
        author_id: Optional[int] = None,
        series_id: Optional[int] = None,
        publisher_id: Optional[int] = None,
        tag_id: Optional[int] = None,
        search_query: Optional[str] = None,
    ) -> tuple[List[Book], int]:
        """Get paginated list of books with optional filtering using SQLAlchemy ORM"""
        if not self.Session:
            raise FileNotFoundError(f"Calibre database not found at {self.db_path}")
        
        session = self.Session()
        try:
            # Build base query
            query = session.query(Books)
            
            # Apply filters
            if author_id:
                query = query.join(Books.authors).filter(Authors.id == author_id)
            
            if series_id:
                query = query.join(Books.series_rel).filter(SeriesModel.id == series_id)
            
            if publisher_id:
                query = query.join(Books.publishers_rel).filter(Publishers.id == publisher_id)
            
            if tag_id:
                if tag_id == -1:
                    # Special case: books without tags
                    query = query.filter(~Books.tags.any())
                else:
                    query = query.filter(Books.tags.any(Tags.id == tag_id))
            
            # Search query - searches across title, authors, and tags
            if search_query:
                normalized_search = normalize_text(search_query)
                search_pattern = f"%{normalized_search}%"
                
                # For search, we need to join authors and tags
                query = query.join(Books.authors).join(Books.tags).filter(
                    or_(
                        func.lower(Books.title).like(search_pattern),
                        func.lower(Authors.name).like(search_pattern),
                        func.lower(Tags.name).like(search_pattern)
                    )
                ).distinct()
            
            # Get total count before applying ordering
            total = query.count()
            
            # Get sort order (like original Calibre-Web)
            order_by = self._get_sort_order(sort_param, sort_by, order)
            
            # Handle author sorting - need to join and group
            if sort_param in ["authaz", "authza"]:
                query = query.join(Books.authors).group_by(Books.id)
            
            # Apply ordering
            for order_clause in order_by:
                query = query.order_by(order_clause)
            
            # Apply pagination
            offset = (page - 1) * per_page
            books_orm = query.limit(per_page).offset(offset).all()
            
            # Convert ORM objects to Pydantic models
            books = []
            for book_orm in books_orm:
                # Get authors
                authors = [Author(id=a.id, name=a.name) for a in book_orm.authors]
                
                # Get tags
                tags = [Tag(id=t.id, name=t.name) for t in book_orm.tags]
                
                # Get series
                series = None
                if book_orm.series_rel:
                    series = Series(id=book_orm.series_rel.id, name=book_orm.series_rel.name)
                
                # Get publisher
                publisher = None
                if book_orm.publishers_rel:
                    publisher = Publisher(id=book_orm.publishers_rel.id, name=book_orm.publishers_rel.name)
                
                # Create Book model
                book = Book(
                    id=book_orm.id,
                    title=book_orm.title or "Unknown",
                    path=book_orm.path or "",
                    has_cover=bool(book_orm.has_cover),
                    uuid=book_orm.uuid,
                    isbn=book_orm.isbn or "",
                    lccn=book_orm.lccn or "",
                    pubdate=book_orm.pubdate,
                    timestamp=book_orm.timestamp,
                    last_modified=book_orm.last_modified,
                    authors=authors,
                    tags=tags,
                    series=series,
                    publisher=publisher,
                    file_formats=[],  # Will need to query separately if needed
                )
                books.append(book)
            
            return books, total
            
        finally:
            session.close()

