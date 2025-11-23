"""SQLAlchemy-based implementation of CalibreDatabase - cleaner and fixes sorting"""
import os
from typing import List, Optional
import logging
from unidecode import unidecode

from sqlalchemy import create_engine, func, or_, and_
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.models.book import Book, Author, Tag, Series, Publisher, BookDetail, Category
from app.services.calibre_db_models import Base, Books, Authors, Tags, Series as SeriesModel, Publishers

logger = logging.getLogger(__name__)


def normalize_text(text: str) -> str:
    """Normalize text by removing diacritics, similar to original Calibre-Web's lcase function"""
    if not text:
        return ""
    try:
        # First lowercase, then unidecode to handle Vietnamese characters like Đ
        normalized = unidecode(text.lower())
        # Handle special Vietnamese characters that unidecode might miss
        # Đ and đ should map to d
        normalized = normalized.replace('đ', 'd')
        return normalized
    except Exception:
        # Fallback: just lowercase and handle Đ manually
        result = text.lower().replace('đ', 'd')
        return result


class CalibreDatabase:
    """Service for reading Calibre's metadata.db using SQLAlchemy ORM"""

    def __init__(self):
        self.db_path = os.path.join(settings.calibre_library_path, "metadata.db")
        if not os.path.exists(self.db_path):
            logger.warning(f"Calibre database not found at {self.db_path}")
            self.engine = None
            self.Session = None
        else:
            # Create SQLAlchemy engine
            # Note: We use a regular sqlite:/// URL without mode=ro because
            # SQLAlchemy doesn't properly support URI parameters in the URL string
            db_url = f"sqlite:///{self.db_path}"

            self.engine = create_engine(
                db_url,
                poolclass=StaticPool,
                connect_args={
                    "check_same_thread": False,
                    "uri": False  # Don't treat the path as a URI
                },
                echo=True  # Enable SQL logging for debugging
            )

            # Register custom SQLite function for text normalization
            # This needs to be done AFTER creating the engine, and only for THIS engine
            from sqlalchemy import event

            @event.listens_for(self.engine, "connect")
            def register_custom_functions(dbapi_conn, connection_record):
                # Only register for SQLite connections
                if hasattr(dbapi_conn, 'create_function'):
                    dbapi_conn.create_function("normalize_text", 1, normalize_text)
                    logger.info("Registered normalize_text custom SQLite function")

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
                return [func.coalesce(Books.sort, Books.title).asc()]
            elif sort_param == "zyx":
                return [func.coalesce(Books.sort, Books.title).desc()]
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
            return [func.coalesce(Books.sort, Books.title).desc() if order == "desc" else func.coalesce(Books.sort, Books.title).asc()]
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

            # Track if we've already joined authors (for sorting optimization)
            authors_joined = False

            # Apply filters
            if author_id:
                query = query.join(Books.authors).filter(Authors.id == author_id)
                authors_joined = True

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

                # For search, we need to left join authors and tags (so books without tags still appear)
                # Use custom normalize_text SQL function for diacritic-insensitive search
                query = query.outerjoin(Books.authors).outerjoin(Books.tags).filter(
                    or_(
                        func.normalize_text(Books.title).like(search_pattern),
                        func.normalize_text(Authors.name).like(search_pattern),
                        func.normalize_text(Tags.name).like(search_pattern)
                    )
                ).distinct()
                authors_joined = True

            # Get sort order (like original Calibre-Web) BEFORE counting
            order_by = self._get_sort_order(sort_param, sort_by, order)

            # Handle author sorting - need to join and group BEFORE counting
            if sort_param in ["authaz", "authza"]:
                if not authors_joined:
                    query = query.join(Books.authors)
                query = query.group_by(Books.id)
            
            # Apply ordering BEFORE counting (for correct total)
            for order_clause in order_by:
                query = query.order_by(order_clause)
            
            # Get total count after applying ordering/filters
            total = query.count()
            
            # Apply pagination
            offset = (page - 1) * per_page
            books_orm = query.limit(per_page).offset(offset).all()
            
            # Debug: Log the query
            logger.error(f"[SQLAlchemy] sort_param={sort_param}, sort_by={sort_by}, order={order}")
            logger.error(f"[SQLAlchemy] Got {len(books_orm)} books, total={total}")
            
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

    def get_books_by_tag_ids(
        self,
        tag_ids: List[int],
        page: int = 1,
        per_page: int = 20,
        sort_param: Optional[str] = "new",
    ) -> tuple[List[Book], int]:
        """Get paginated books that have ANY of the given tag IDs (for category pages)"""
        if not self.Session:
            raise FileNotFoundError(f"Calibre database not found at {self.db_path}")

        if not tag_ids:
            return [], 0

        session = self.Session()
        try:
            # Build query: books with ANY of the given tags
            query = session.query(Books).filter(
                Books.tags.any(Tags.id.in_(tag_ids))
            ).distinct()

            # Apply sort order
            order_by = self._get_sort_order(sort_param, None, None)
            for order_clause in order_by:
                query = query.order_by(order_clause)

            # Get total count
            total = query.count()

            # Apply pagination
            offset = (page - 1) * per_page
            books_orm = query.limit(per_page).offset(offset).all()

            # Convert ORM objects to Pydantic models
            books = []
            for book_orm in books_orm:
                authors = [Author(id=a.id, name=a.name) for a in book_orm.authors]
                tags = [Tag(id=t.id, name=t.name) for t in book_orm.tags]
                series = None
                if book_orm.series_rel:
                    series = Series(id=book_orm.series_rel.id, name=book_orm.series_rel.name)
                publisher = None
                if book_orm.publishers_rel:
                    publisher = Publisher(id=book_orm.publishers_rel.id, name=book_orm.publishers_rel.name)

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
                    file_formats=[],
                )
                books.append(book)

            return books, total

        finally:
            session.close()

    def get_book(self, book_id: int) -> Optional[BookDetail]:
        """Get detailed information about a specific book"""
        if not self.Session:
            raise FileNotFoundError(f"Calibre database not found at {self.db_path}")

        session = self.Session()
        try:
            from app.services.calibre_db_models import Comments, Ratings, Data, Languages, Identifiers

            book_orm = session.query(Books).filter(Books.id == book_id).first()
            if not book_orm:
                return None

            # Get comments
            comments_text = None
            comment = session.query(Comments).filter(Comments.book == book_id).first()
            if comment:
                comments_text = comment.text

            # Get rating
            rating_value = None
            from app.services.calibre_db_models import books_ratings_link
            rating = session.query(Ratings).join(books_ratings_link).filter(books_ratings_link.c.book == book_id).first()
            if rating and rating.rating:
                rating_value = rating.rating / 2.0  # Calibre stores as 0-10

            # Get authors, tags, series, publisher
            authors = [Author(id=a.id, name=a.name) for a in book_orm.authors]
            tags = [Tag(id=t.id, name=t.name) for t in book_orm.tags]
            series = None
            if book_orm.series_rel:
                series = Series(id=book_orm.series_rel.id, name=book_orm.series_rel.name, index=book_orm.series_index)
            publisher = None
            if book_orm.publishers_rel:
                publisher = Publisher(id=book_orm.publishers_rel.id, name=book_orm.publishers_rel.name)

            # Get file formats
            formats = session.query(Data.format).filter(Data.book == book_id).all()
            file_formats = [f.format.upper() for f in formats]

            # Get languages
            from app.services.calibre_db_models import books_languages_link
            lang_rows = session.query(Languages.lang_code).join(books_languages_link).filter(books_languages_link.c.book == book_id).all()
            languages = [lang.lang_code for lang in lang_rows]

            # Get identifiers
            ident_rows = session.query(Identifiers).filter(Identifiers.book == book_id).all()
            identifiers = {i.type: i.val for i in ident_rows}

            book = BookDetail(
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
                comments=comments_text,
                rating=rating_value,
                authors=authors,
                tags=tags,
                series=series,
                publisher=publisher,
                file_formats=file_formats,
                languages=languages,
                identifiers=identifiers,
            )

            return book
        finally:
            session.close()

    def search_books(self, query: str, limit: int = 100) -> List[Book]:
        """Search books by title, author, or tags (diacritic-insensitive)"""
        if not self.Session:
            raise FileNotFoundError(f"Calibre database not found at {self.db_path}")

        session = self.Session()
        try:
            normalized_query = normalize_text(query)
            search_pattern = f"%{normalized_query}%"

            # Build query with left outer joins (so books without tags/authors still appear)
            # Use custom normalize_text SQL function for diacritic-insensitive search
            query_obj = session.query(Books).outerjoin(Books.authors).outerjoin(Books.tags).filter(
                or_(
                    func.normalize_text(Books.title).like(search_pattern),
                    func.normalize_text(Authors.name).like(search_pattern),
                    func.normalize_text(Tags.name).like(search_pattern)
                )
            ).distinct().order_by(Books.timestamp.desc()).limit(limit)

            books_orm = query_obj.all()

            # Convert to Book models
            books = []
            for book_orm in books_orm:
                from app.services.calibre_db_models import Data
                authors = [Author(id=a.id, name=a.name) for a in book_orm.authors]
                tags = [Tag(id=t.id, name=t.name) for t in book_orm.tags]
                series = None
                if book_orm.series_rel:
                    series = Series(id=book_orm.series_rel.id, name=book_orm.series_rel.name)
                publisher = None
                if book_orm.publishers_rel:
                    publisher = Publisher(id=book_orm.publishers_rel.id, name=book_orm.publishers_rel.name)

                formats = session.query(Data.format).filter(Data.book == book_orm.id).all()
                file_formats = [f.format.upper() for f in formats]

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
                    file_formats=file_formats,
                )
                books.append(book)

            return books
        finally:
            session.close()

    def get_all_authors(self) -> List[Author]:
        """Get all authors with book counts"""
        if not self.Session:
            raise FileNotFoundError(f"Calibre database not found at {self.db_path}")

        session = self.Session()
        try:
            results = session.query(
                Authors.id,
                Authors.name,
                func.count(Books.id).label('count')
            ).outerjoin(Books.authors).group_by(Authors.id, Authors.name).order_by(Authors.name).all()

            authors = [Author(id=r.id, name=r.name, count=r.count) for r in results]
            return authors
        finally:
            session.close()

    def get_all_tags(self) -> List[Tag]:
        """Get all tags with book counts"""
        if not self.Session:
            raise FileNotFoundError(f"Calibre database not found at {self.db_path}")

        session = self.Session()
        try:
            results = session.query(
                Tags.id,
                Tags.name,
                func.count(Books.id).label('count')
            ).outerjoin(Books.tags).group_by(Tags.id, Tags.name).order_by(Tags.name).all()

            tags = [Tag(id=r.id, name=r.name, count=r.count) for r in results if r.id is not None]
            return tags
        finally:
            session.close()

    def get_all_series(self) -> List[Series]:
        """Get all series with book counts"""
        if not self.Session:
            raise FileNotFoundError(f"Calibre database not found at {self.db_path}")

        session = self.Session()
        try:
            from app.services.calibre_db_models import Series as SeriesModel
            results = session.query(
                SeriesModel.id,
                SeriesModel.name,
                func.count(Books.id).label('count')
            ).outerjoin(Books.series_rel).group_by(SeriesModel.id, SeriesModel.name).order_by(SeriesModel.name).all()

            series = [Series(id=r.id, name=r.name, count=r.count) for r in results]
            return series
        finally:
            session.close()

    def get_all_publishers(self) -> List[Publisher]:
        """Get all publishers with book counts"""
        if not self.Session:
            raise FileNotFoundError(f"Calibre database not found at {self.db_path}")

        session = self.Session()
        try:
            results = session.query(
                Publishers.id,
                Publishers.name,
                func.count(Books.id).label('count')
            ).outerjoin(Books.publishers_rel).group_by(Publishers.id, Publishers.name).order_by(Publishers.name).all()

            # Filter out NULL publishers (books without publishers)
            publishers = [
                Publisher(id=r.id, name=r.name, count=r.count) 
                for r in results 
                if r.id is not None and r.name is not None
            ]
            return publishers
        finally:
            session.close()

    def get_all_categories(self) -> List[Category]:
        """Get all categories (tags) with book counts, including a 'None' category for books without tags"""
        if not self.Session:
            raise FileNotFoundError(f"Calibre database not found at {self.db_path}")

        session = self.Session()
        try:
            # Get all tags with counts
            results = session.query(
                Tags.id,
                Tags.name,
                func.count(Books.id).label('count')
            ).join(Books.tags).group_by(Tags.id, Tags.name).having(func.count(Books.id) > 0).order_by(Tags.name).all()

            categories = [Category(id=r.id, name=r.name, count=r.count) for r in results]

            # Count books without tags
            no_tag_count = session.query(func.count(Books.id)).filter(~Books.tags.any()).scalar()
            if no_tag_count and no_tag_count > 0:
                categories.append(Category(id=-1, name="None", count=no_tag_count))

            return categories
        finally:
            session.close()

    def get_random_books(self, limit: int = 20) -> List[Book]:
        """Get random books from the library"""
        if not self.Session:
            raise FileNotFoundError(f"Calibre database not found at {self.db_path}")

        session = self.Session()
        try:
            from app.services.calibre_db_models import Data

            # Use func.random() for SQLite
            books_orm = session.query(Books).order_by(func.random()).limit(limit).all()

            books = []
            for book_orm in books_orm:
                authors = [Author(id=a.id, name=a.name) for a in book_orm.authors]
                tags = [Tag(id=t.id, name=t.name) for t in book_orm.tags]
                series = None
                if book_orm.series_rel:
                    series = Series(id=book_orm.series_rel.id, name=book_orm.series_rel.name)
                publisher = None
                if book_orm.publishers_rel:
                    publisher = Publisher(id=book_orm.publishers_rel.id, name=book_orm.publishers_rel.name)

                formats = session.query(Data.format).filter(Data.book == book_orm.id).all()
                file_formats = [f.format.upper() for f in formats]

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
                    file_formats=file_formats,
                )
                books.append(book)

            return books
        finally:
            session.close()

    def get_books_by_ids(self, book_ids: List[int], cloud_formats_map: dict = None) -> List[Book]:
        """Get multiple books by their IDs

        Args:
            book_ids: List of book IDs to fetch
            cloud_formats_map: Optional dict mapping book_id -> list of cloud format strings
        """
        if not self.Session:
            raise FileNotFoundError(f"Calibre database not found at {self.db_path}")

        session = self.Session()
        try:
            books = []
            book_orms = session.query(Books).filter(Books.id.in_(book_ids)).all()

            for book_orm in book_orms:
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

                # Get file formats from Calibre DB
                from app.services.calibre_db_models import Data
                formats = session.query(Data.format, Data.name).filter(Data.book == book_orm.id).all()
                file_formats = [f.format.upper() for f in formats]

                # Add cloud-stored formats if provided
                if cloud_formats_map and book_orm.id in cloud_formats_map:
                    for cloud_format in cloud_formats_map[book_orm.id]:
                        format_upper = cloud_format.upper()
                        if format_upper not in file_formats:
                            file_formats.append(format_upper)

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
                    file_formats=file_formats,
                )
                books.append(book)

            return books
        finally:
            session.close()


# Singleton instance
calibre_db = CalibreDatabase()


# Helper functions for API routes
async def get_book_with_cloud_formats(book_id: int) -> Optional[BookDetail]:
    """Async wrapper for getting a book with cloud format support"""
    from app.database import async_session_maker
    from app.models.upload_tracking import UploadTracking
    from sqlalchemy import select

    # Get book from Calibre DB
    book = calibre_db.get_book(book_id)
    if not book:
        return None

    # Fetch cloud formats for this book
    async with async_session_maker() as db_session:
        result = await db_session.execute(
            select(UploadTracking.file_type).filter(
                UploadTracking.book_id == book_id,
                UploadTracking.file_type != 'cover'
            )
        )
        cloud_formats = [row[0] for row in result.all()]

        # Add cloud formats to the book's file_formats list
        for cloud_format in cloud_formats:
            format_upper = cloud_format.upper()
            if format_upper not in book.file_formats:
                book.file_formats.append(format_upper)

    return book


async def get_books_by_ids(book_ids: List[int]) -> List[Book]:
    """Async wrapper for getting books by IDs with cloud format support"""
    from app.database import async_session_maker
    from app.models.upload_tracking import UploadTracking
    from sqlalchemy import select

    # Fetch cloud formats for all book IDs
    cloud_formats_map = {}
    async with async_session_maker() as db_session:
        result = await db_session.execute(
            select(UploadTracking.book_id, UploadTracking.file_type).filter(
                UploadTracking.book_id.in_(book_ids),
                UploadTracking.file_type != 'cover'
            )
        )
        cloud_formats = result.all()

        # Build map of book_id -> [format1, format2, ...]
        for book_id, file_type in cloud_formats:
            if book_id not in cloud_formats_map:
                cloud_formats_map[book_id] = []
            cloud_formats_map[book_id].append(file_type)

    return calibre_db.get_books_by_ids(book_ids, cloud_formats_map)
