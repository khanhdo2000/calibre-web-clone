import sqlite3
import os
from typing import List, Optional, Dict, Any
from pathlib import Path
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
            # Create SQLAlchemy engine with read-only mode
            # Use StaticPool for SQLite connection pooling
            db_url = f"sqlite:///{self.db_path}?mode=ro&uri=true"
            self.engine = create_engine(
                db_url,
                poolclass=StaticPool,
                connect_args={"check_same_thread": False},
                echo=False
            )
            # Create session factory
            self.Session = scoped_session(sessionmaker(bind=self.engine))

    def _get_connection(self):
        """Get a read-only connection to the Calibre database"""
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Calibre database not found at {self.db_path}")

        conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        
        # Register custom lower function (like original Calibre-Web) for diacritic-insensitive search
        # This replaces SQLite's built-in lower() with our normalize_text function
        def sql_lower(text):
            if text is None:
                return ""
            return normalize_text(str(text))
        
        # Register normalize function as well (for explicit use)
        def sql_normalize(text):
            if text is None:
                return ""
            return normalize_text(str(text))
        
        try:
            conn.create_function("lower", 1, sql_lower)
            conn.create_function("normalize", 1, sql_normalize)
        except sqlite3.OperationalError:
            # Function might already exist, ignore
            pass
        
        return conn

    def get_books(
        self,
        page: int = 1,
        per_page: int = 20,
        sort_by: str = "timestamp",
        order: str = "desc",
        sort_param: Optional[str] = None,
        author_id: Optional[int] = None,
        series_id: Optional[int] = None,
        publisher_id: Optional[int] = None,
        tag_id: Optional[int] = None,
        search_query: Optional[str] = None,
    ) -> tuple[List[Book], int]:
        """Get paginated list of books with optional filtering"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Build WHERE clause
        where_clauses = []
        params = []

        if author_id:
            where_clauses.append("EXISTS (SELECT 1 FROM books_authors_link WHERE book = books.id AND author = ?)")
            params.append(author_id)
        if series_id:
            where_clauses.append("EXISTS (SELECT 1 FROM books_series_link WHERE book = books.id AND series = ?)")
            params.append(series_id)
        if publisher_id:
            where_clauses.append("EXISTS (SELECT 1 FROM books_publishers_link WHERE book = books.id AND publisher = ?)")
            params.append(publisher_id)
        if tag_id:
            if tag_id == -1:
                # Special case: books without tags
                where_clauses.append("NOT EXISTS (SELECT 1 FROM books_tags_link WHERE book = books.id)")
            else:
                where_clauses.append("EXISTS (SELECT 1 FROM books_tags_link WHERE book = books.id AND tag = ?)")
                params.append(tag_id)
        
        # Search query - searches across title, authors, and tags (diacritic-insensitive)
        # Use lower() function which is registered to use normalize_text (like original)
        if search_query:
            # Normalize the search term to remove diacritics
            normalized_search = normalize_text(search_query)
            search_term = f"%{normalized_search}%"
            logger.debug(f"Search query: '{search_query}' -> normalized: '{normalized_search}' -> pattern: '{search_term}'")
            where_clauses.append(
                "(lower(books.title) LIKE ? OR EXISTS (SELECT 1 FROM books_authors_link "
                "JOIN authors ON books_authors_link.author = authors.id "
                "WHERE books_authors_link.book = books.id AND lower(authors.name) LIKE ?) "
                "OR EXISTS (SELECT 1 FROM books_tags_link "
                "JOIN tags ON books_tags_link.tag = tags.id "
                "WHERE books_tags_link.book = books.id AND lower(tags.name) LIKE ?))"
            )
            params.extend([search_term, search_term, search_term])

        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        # Count total - need to handle search differently for counting
        if search_query:
            # For search, we need to use the same JOIN structure as the main query
            count_query = f"""
                SELECT COUNT(DISTINCT books.id) as total 
                FROM books
                LEFT JOIN books_authors_link ON books.id = books_authors_link.book
                LEFT JOIN authors ON books_authors_link.author = authors.id
                LEFT JOIN books_tags_link ON books.id = books_tags_link.book
                LEFT JOIN tags ON books_tags_link.tag = tags.id
                {where_clause}
            """
        else:
            count_query = f"SELECT COUNT(*) as total FROM books {where_clause}"
        total = cursor.execute(count_query, params).fetchone()["total"]

        # Get books
        offset = (page - 1) * per_page
        valid_sort_fields = ["id", "title", "timestamp", "pubdate", "last_modified", "series_index"]
        
        # Ensure order is not None (it might be None from query params)
        if order is None:
            order = "desc"
            logger.warning(f"[FIX] order was None, defaulting to 'desc'. sort_param={sort_param}, sort_by={sort_by}")
        
        sort_order = "DESC" if order and order.lower() == "desc" else "ASC"
        logger.error(f"[FIX] order={order}, sort_order={sort_order}, sort_by={sort_by}")

        # Handle special sorting cases
        order_by_clause = ""
        needs_group_by = False
        needs_author_join = False
        needs_series_join = False
        
        # Debug logging - use print to ensure it shows up
        print(f"[CALIBRE_DB] Sort params: sort_param={sort_param}, sort_by={sort_by}, order={order}")
        logger.info(f"[CALIBRE_DB] Sort params: sort_param={sort_param}, sort_by={sort_by}, order={order}")
        
        if sort_param == "authaz" or sort_param == "authza":
            # Sort by author (need to join authors table)
            # We always need JOINs for sorting by author, even if filters exist
            author_order = "ASC" if sort_param == "authaz" else "DESC"
            needs_group_by = True
            if not search_query:
                # Need to add JOIN for author sorting (search_query already has JOINs)
                needs_author_join = True
            order_by_clause = f"ORDER BY MIN(authors.name) {author_order}, books.title ASC"
        elif sort_by and sort_by in valid_sort_fields:
            if sort_by == "series_index":
                # Need to join series_link table
                needs_series_join = True
                order_by_clause = f"ORDER BY books.series_index {sort_order}"
            else:
                # Normal field sorting (title, timestamp, pubdate, etc.)
                order_by_clause = f"ORDER BY books.{sort_by} {sort_order}"
                logger.error(f"[DEBUG] Built ORDER BY for normal sort: {order_by_clause} (sort_by={sort_by}, sort_order={sort_order})")
        else:
            # Default fallback
            logger.warning(f"No valid sort found, using default. sort_param={sort_param}, sort_by={sort_by}")
            order_by_clause = "ORDER BY books.timestamp DESC"

        # Build GROUP BY clause if needed
        group_by_clause = ""
        if needs_group_by or (sort_param in ["authaz", "authza"]):
            group_by_clause = "GROUP BY books.id"
        elif search_query:
            # DISTINCT is used instead of GROUP BY for search queries
            pass
        
        # Build JOIN clauses
        join_clauses = []
        if search_query:
            # Search already includes all necessary JOINs in the main query
            pass
        else:
            if needs_author_join:
                join_clauses.append("LEFT JOIN books_authors_link ON books.id = books_authors_link.book")
                join_clauses.append("LEFT JOIN authors ON books_authors_link.author = authors.id")
            if needs_series_join and "books_series_link" not in str(join_clauses):
                join_clauses.append("LEFT JOIN books_series_link ON books.id = books_series_link.book")
        
        join_clause = " ".join(join_clauses) if join_clauses else ""

        if search_query:
            # Ensure order_by_clause is set
            if not order_by_clause or not order_by_clause.strip():
                order_by_clause = "ORDER BY books.timestamp DESC"
            
            query = f"""
                SELECT DISTINCT
                    books.id,
                    books.title,
                    books.path,
                    books.has_cover,
                    books.uuid,
                    books.isbn,
                    books.lccn,
                    books.pubdate,
                    books.timestamp,
                    books.last_modified
                FROM books
                LEFT JOIN books_authors_link ON books.id = books_authors_link.book
                LEFT JOIN authors ON books_authors_link.author = authors.id
                LEFT JOIN books_tags_link ON books.id = books_tags_link.book
                LEFT JOIN tags ON books_tags_link.tag = tags.id
                {where_clause}
                {group_by_clause}
                {order_by_clause}
                LIMIT ? OFFSET ?
            """
            # Verify ORDER BY is in the query
            if "ORDER BY" not in query.upper():
                logger.error(f"[CRITICAL] ORDER BY missing in search query!")
                query = query.replace("LIMIT", "ORDER BY books.timestamp DESC LIMIT")
        else:
            # Build the query - always use FROM books, then JOINs, then WHERE
            # CRITICAL: Ensure ORDER BY is always included and properly formatted
            if not order_by_clause or not order_by_clause.strip():
                logger.error(f"[FATAL] order_by_clause is EMPTY! sort_param={sort_param}, sort_by={sort_by}, order={order}")
                order_by_clause = "ORDER BY books.timestamp DESC"
            
            # Build query with proper SQL syntax - simple and clear, ONE TIME ONLY
            query = "SELECT books.id, books.title, books.path, books.has_cover, books.uuid, books.isbn, books.lccn, books.pubdate, books.timestamp, books.last_modified FROM books"
            if join_clause:
                query += " " + join_clause.strip()
            if where_clause and where_clause.strip():
                query += " " + where_clause.strip()
            if group_by_clause and group_by_clause.strip():
                query += " " + group_by_clause.strip()
            # ALWAYS add ORDER BY - this is critical for sorting!
            # Verify order_by_clause is not empty before adding
            if not order_by_clause or not order_by_clause.strip():
                raise ValueError(f"order_by_clause is EMPTY when trying to add to query! sort_param={sort_param}, sort_by={sort_by}, order={order}")
            
            query += " " + order_by_clause.strip()
            query += " LIMIT ? OFFSET ?"
            
            # Final verification - if ORDER BY is missing, something is very wrong
            if "ORDER BY" not in query.upper():
                raise ValueError(f"ORDER BY missing from final query! Query: {query}")
        params.extend([per_page, offset])

        # Debug: log the query - print full details
        logger.error(f"[DEBUG] ============ BOOKS QUERY DEBUG ============")
        logger.error(f"[DEBUG] sort_param={sort_param}")
        logger.error(f"[DEBUG] sort_by={sort_by}")
        logger.error(f"[DEBUG] order={order}")
        logger.error(f"[DEBUG] sort_order={sort_order}")
        logger.error(f"[DEBUG] order_by_clause='{order_by_clause}'")
        logger.error(f"[DEBUG] where_clause='{where_clause}'")
        logger.error(f"[DEBUG] join_clause='{join_clause}'")
        logger.error(f"[DEBUG] Full Query:\n{query}")
        logger.error(f"[DEBUG] Query has ORDER BY: {'ORDER BY' in query.upper()}")
        logger.error(f"[DEBUG] Query length: {len(query)}")
        logger.error(f"[DEBUG] ============================================")

        # Final safety check - ensure ORDER BY is in query
        if "ORDER BY" not in query.upper():
            logger.error(f"CRITICAL: ORDER BY missing from query! sort_param={sort_param}, sort_by={sort_by}")
            query = query.replace("LIMIT", "ORDER BY books.timestamp DESC LIMIT")
        
        # Log to a file to ensure we see it
        try:
            with open("/tmp/calibre_query.log", "a") as f:
                f.write(f"\n=== QUERY DEBUG ===\n")
                f.write(f"sort_param={sort_param}, sort_by={sort_by}, order={order}\n")
                f.write(f"order_by_clause='{order_by_clause}'\n")
                f.write(f"Query: {query}\n")
                f.write(f"Has ORDER BY: {'ORDER BY' in query.upper()}\n")
                f.write(f"==================\n")
        except:
            pass
        
        # CRITICAL: Write query to file for inspection - use absolute path
        import os
        debug_file = "/tmp/calibre_query_debug.txt"
        try:
            with open(debug_file, "a") as f:
                f.write("\n" + "="*80 + "\n")
                f.write(f"sort_param={sort_param}\n")
                f.write(f"sort_by={sort_by}\n")
                f.write(f"order={order}\n")
                f.write(f"sort_order={sort_order}\n")
                f.write(f"order_by_clause={order_by_clause}\n")
                f.write(f"search_query={search_query}\n")
                f.write(f"\nQUERY:\n{query}\n")
                f.write(f"\nHas ORDER BY: {'ORDER BY' in query.upper()}\n")
                f.write(f"Params: {params}\n")
                f.write("="*80 + "\n")
                os.fsync(f.fileno())  # Force write to disk
        except Exception as e:
            # Write error to stderr
            import sys
            print(f"Failed to write debug file: {e}", file=sys.stderr, flush=True)
        
        # CRITICAL DEBUG: Log the actual query being executed
        import sys
        print("\n" + "="*80, file=sys.stderr, flush=True)
        print(f"FINAL QUERY BEING EXECUTED:", file=sys.stderr, flush=True)
        print(f"sort_param={sort_param}, sort_by={sort_by}, order={order}", file=sys.stderr, flush=True)
        print(f"order_by_clause={order_by_clause}", file=sys.stderr, flush=True)
        print(f"Query: {query}", file=sys.stderr, flush=True)
        print(f"Has ORDER BY: {'ORDER BY' in query.upper()}", file=sys.stderr, flush=True)
        print(f"ORDER BY position: {query.upper().find('ORDER BY')}", file=sys.stderr, flush=True)
        print("="*80 + "\n", file=sys.stderr, flush=True)
        
        try:
            rows = cursor.execute(query, params).fetchall()
            print(f"Query executed. Got {len(rows)} rows.", file=sys.stderr, flush=True)
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            logger.error(f"Query was: {query[:500]}")
            raise
        
        books = []

        for row in rows:
            book_id = row["id"]
            book = Book(
                id=book_id,
                title=row["title"],
                path=row["path"],
                has_cover=bool(row["has_cover"]),
                uuid=row["uuid"],
                isbn=row["isbn"],
                lccn=row["lccn"],
                pubdate=row["pubdate"],
                timestamp=row["timestamp"],
                last_modified=row["last_modified"],
                authors=self._get_authors(cursor, book_id),
                tags=self._get_tags(cursor, book_id),
                series=self._get_series(cursor, book_id),
                publisher=self._get_publisher(cursor, book_id),
                file_formats=self._get_formats(cursor, book_id),
            )
            books.append(book)

        conn.close()
        return books, total

    def get_book(self, book_id: int) -> Optional[BookDetail]:
        """Get detailed information about a specific book"""
        conn = self._get_connection()
        cursor = conn.cursor()

        query = """
            SELECT
                books.*,
                (SELECT text FROM comments WHERE book = books.id) as comments,
                (SELECT rating FROM ratings WHERE id IN (SELECT rating FROM books_ratings_link WHERE book = books.id)) as rating
            FROM books
            WHERE books.id = ?
        """
        row = cursor.execute(query, (book_id,)).fetchone()

        if not row:
            conn.close()
            return None

        book = BookDetail(
            id=row["id"],
            title=row["title"],
            path=row["path"],
            has_cover=bool(row["has_cover"]),
            uuid=row["uuid"],
            isbn=row["isbn"],
            lccn=row["lccn"],
            pubdate=row["pubdate"],
            timestamp=row["timestamp"],
            last_modified=row["last_modified"],
            comments=row["comments"],
            rating=row["rating"] / 2.0 if row["rating"] else None,  # Calibre stores rating as 0-10
            authors=self._get_authors(cursor, book_id),
            tags=self._get_tags(cursor, book_id),
            series=self._get_series(cursor, book_id),
            publisher=self._get_publisher(cursor, book_id),
            file_formats=self._get_formats(cursor, book_id),
            languages=self._get_languages(cursor, book_id),
            identifiers=self._get_identifiers(cursor, book_id),
        )

        conn.close()
        return book

    def search_books(self, query: str, limit: int = 100) -> List[Book]:
        """Search books by title, author, or tags (diacritic-insensitive)"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Normalize the search term to remove diacritics
        normalized_query = normalize_text(query)
        search_query = f"%{normalized_query}%"
        sql = """
            SELECT DISTINCT books.id, books.title, books.path, books.has_cover,
                   books.uuid, books.isbn, books.lccn, books.pubdate,
                   books.timestamp, books.last_modified
            FROM books
            LEFT JOIN books_authors_link ON books.id = books_authors_link.book
            LEFT JOIN authors ON books_authors_link.author = authors.id
            LEFT JOIN books_tags_link ON books.id = books_tags_link.book
            LEFT JOIN tags ON books_tags_link.tag = tags.id
            WHERE lower(books.title) LIKE ?
               OR lower(authors.name) LIKE ?
               OR lower(tags.name) LIKE ?
            ORDER BY books.timestamp DESC
            LIMIT ?
        """

        rows = cursor.execute(sql, (search_query, search_query, search_query, limit)).fetchall()
        books = []

        for row in rows:
            book_id = row["id"]
            book = Book(
                id=book_id,
                title=row["title"],
                path=row["path"],
                has_cover=bool(row["has_cover"]),
                uuid=row["uuid"],
                isbn=row["isbn"],
                lccn=row["lccn"],
                pubdate=row["pubdate"],
                timestamp=row["timestamp"],
                last_modified=row["last_modified"],
                authors=self._get_authors(cursor, book_id),
                tags=self._get_tags(cursor, book_id),
                series=self._get_series(cursor, book_id),
                publisher=self._get_publisher(cursor, book_id),
                file_formats=self._get_formats(cursor, book_id),
            )
            books.append(book)

        conn.close()
        return books

    def _get_authors(self, cursor, book_id: int) -> List[Author]:
        """Get authors for a book"""
        query = """
            SELECT authors.id, authors.name
            FROM authors
            JOIN books_authors_link ON authors.id = books_authors_link.author
            WHERE books_authors_link.book = ?
            ORDER BY authors.name
        """
        rows = cursor.execute(query, (book_id,)).fetchall()
        return [Author(id=row["id"], name=row["name"]) for row in rows]

    def _get_tags(self, cursor, book_id: int) -> List[Tag]:
        """Get tags for a book"""
        query = """
            SELECT tags.id, tags.name
            FROM tags
            JOIN books_tags_link ON tags.id = books_tags_link.tag
            WHERE books_tags_link.book = ?
            ORDER BY tags.name
        """
        rows = cursor.execute(query, (book_id,)).fetchall()
        return [Tag(id=row["id"], name=row["name"]) for row in rows]

    def _get_series(self, cursor, book_id: int) -> Optional[Series]:
        """Get series for a book"""
        query = """
            SELECT series.id, series.name, books.series_index
            FROM series
            JOIN books_series_link ON series.id = books_series_link.series
            JOIN books ON books.id = books_series_link.book
            WHERE books_series_link.book = ?
        """
        row = cursor.execute(query, (book_id,)).fetchone()
        if row:
            return Series(id=row["id"], name=row["name"], index=row["series_index"])
        return None

    def _get_publisher(self, cursor, book_id: int) -> Optional[Publisher]:
        """Get publisher for a book"""
        query = """
            SELECT publishers.id, publishers.name
            FROM publishers
            JOIN books_publishers_link ON publishers.id = books_publishers_link.publisher
            WHERE books_publishers_link.book = ?
        """
        row = cursor.execute(query, (book_id,)).fetchone()
        if row:
            return Publisher(id=row["id"], name=row["name"])
        return None

    def _get_formats(self, cursor, book_id: int) -> List[str]:
        """Get available file formats for a book"""
        query = "SELECT format FROM data WHERE book = ?"
        rows = cursor.execute(query, (book_id,)).fetchall()
        return [row["format"].upper() for row in rows]

    def _get_languages(self, cursor, book_id: int) -> List[str]:
        """Get languages for a book"""
        query = """
            SELECT languages.lang_code
            FROM languages
            JOIN books_languages_link ON languages.id = books_languages_link.lang_code
            WHERE books_languages_link.book = ?
        """
        rows = cursor.execute(query, (book_id,)).fetchall()
        return [row["lang_code"] for row in rows]

    def _get_identifiers(self, cursor, book_id: int) -> Dict[str, str]:
        """Get identifiers (ISBN, Amazon, Goodreads, etc.) for a book"""
        query = "SELECT type, val FROM identifiers WHERE book = ?"
        rows = cursor.execute(query, (book_id,)).fetchall()
        return {row["type"]: row["val"] for row in rows}

    def get_all_authors(self) -> List[Author]:
        """Get all authors with book counts"""
        conn = self._get_connection()
        cursor = conn.cursor()
        query = """
            SELECT authors.id, authors.name, COUNT(books_authors_link.book) as count
            FROM authors
            LEFT JOIN books_authors_link ON authors.id = books_authors_link.author
            GROUP BY authors.id, authors.name
            ORDER BY authors.name
        """
        rows = cursor.execute(query).fetchall()
        authors = [Author(id=row["id"], name=row["name"], count=row["count"]) for row in rows]
        conn.close()
        return authors

    def get_all_tags(self) -> List[Tag]:
        """Get all tags with book counts"""
        conn = self._get_connection()
        cursor = conn.cursor()
        query = """
            SELECT tags.id, tags.name, COUNT(books_tags_link.book) as count
            FROM tags
            LEFT JOIN books_tags_link ON tags.id = books_tags_link.tag
            GROUP BY tags.id, tags.name
            ORDER BY tags.name
        """
        rows = cursor.execute(query).fetchall()
        tags = [Tag(id=row["id"], name=row["name"], count=row["count"]) for row in rows]
        conn.close()
        return tags

    def get_all_series(self) -> List[Series]:
        """Get all series"""
        conn = self._get_connection()
        cursor = conn.cursor()
        query = "SELECT id, name FROM series ORDER BY name"
        rows = cursor.execute(query).fetchall()
        series = [Series(id=row["id"], name=row["name"]) for row in rows]
        conn.close()
        return series

    def get_all_publishers(self) -> List[Publisher]:
        """Get all publishers with book counts"""
        conn = self._get_connection()
        cursor = conn.cursor()
        query = """
            SELECT publishers.id, publishers.name, COUNT(books_publishers_link.book) as count
            FROM publishers
            LEFT JOIN books_publishers_link ON publishers.id = books_publishers_link.publisher
            GROUP BY publishers.id, publishers.name
            ORDER BY publishers.name
        """
        rows = cursor.execute(query).fetchall()
        publishers = [Publisher(id=row["id"], name=row["name"], count=row["count"]) for row in rows]
        conn.close()
        return publishers

    def get_all_categories(self) -> List[Category]:
        """Get all categories (tags) with book counts, including a 'None' category for books without tags"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Get all tags with counts
        query = """
            SELECT tags.id, tags.name, COUNT(books_tags_link.book) as count
            FROM tags
            LEFT JOIN books_tags_link ON tags.id = books_tags_link.tag
            GROUP BY tags.id, tags.name
            HAVING count > 0
            ORDER BY tags.name
        """
        rows = cursor.execute(query).fetchall()
        categories = [Category(id=row["id"], name=row["name"], count=row["count"]) for row in rows]
        
        # Count books without tags
        no_tag_query = """
            SELECT COUNT(*) as count
            FROM books
            WHERE books.id NOT IN (SELECT DISTINCT book FROM books_tags_link)
        """
        no_tag_row = cursor.execute(no_tag_query).fetchone()
        if no_tag_row and no_tag_row["count"] > 0:
            categories.append(Category(id=-1, name="None", count=no_tag_row["count"]))
        
        conn.close()
        return categories

    def get_random_books(self, limit: int = 20) -> List[Book]:
        """Get random books from the library"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Use RANDOM() for SQLite to get random books
        # Similar to original's func.randomblob(2) ordering
        query = """
            SELECT
                books.id,
                books.title,
                books.path,
                books.has_cover,
                books.uuid,
                books.isbn,
                books.lccn,
                books.pubdate,
                books.timestamp,
                books.last_modified
            FROM books
            ORDER BY RANDOM()
            LIMIT ?
        """
        
        rows = cursor.execute(query, (limit,)).fetchall()
        books = []
        
        for row in rows:
            book_id = row["id"]
            book = Book(
                id=book_id,
                title=row["title"],
                path=row["path"],
                has_cover=bool(row["has_cover"]),
                uuid=row["uuid"],
                isbn=row["isbn"],
                lccn=row["lccn"],
                pubdate=row["pubdate"],
                timestamp=row["timestamp"],
                last_modified=row["last_modified"],
                authors=self._get_authors(cursor, book_id),
                tags=self._get_tags(cursor, book_id),
                series=self._get_series(cursor, book_id),
                publisher=self._get_publisher(cursor, book_id),
                file_formats=self._get_formats(cursor, book_id),
            )
            books.append(book)
        
        conn.close()
        return books


# Singleton instance
calibre_db = CalibreDatabase()
