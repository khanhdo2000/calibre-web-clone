"""SQLAlchemy models for Calibre database"""
from sqlalchemy import create_engine, Column, Integer, String, TIMESTAMP, Table, ForeignKey
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, scoped_session
from sqlalchemy.pool import StaticPool
from datetime import datetime, timezone

Base = declarative_base()

# Association tables
books_authors_link = Table(
    'books_authors_link', Base.metadata,
    Column('book', Integer, ForeignKey('books.id'), primary_key=True),
    Column('author', Integer, ForeignKey('authors.id'), primary_key=True)
)

books_tags_link = Table(
    'books_tags_link', Base.metadata,
    Column('book', Integer, ForeignKey('books.id'), primary_key=True),
    Column('tag', Integer, ForeignKey('tags.id'), primary_key=True)
)

books_series_link = Table(
    'books_series_link', Base.metadata,
    Column('book', Integer, ForeignKey('books.id'), primary_key=True),
    Column('series', Integer, ForeignKey('series.id'), primary_key=True)
)

books_publishers_link = Table(
    'books_publishers_link', Base.metadata,
    Column('book', Integer, ForeignKey('books.id'), primary_key=True),
    Column('publisher', Integer, ForeignKey('publishers.id'), primary_key=True)
)

books_ratings_link = Table(
    'books_ratings_link', Base.metadata,
    Column('book', Integer, ForeignKey('books.id'), primary_key=True),
    Column('rating', Integer, ForeignKey('ratings.id'), primary_key=True)
)

books_languages_link = Table(
    'books_languages_link', Base.metadata,
    Column('book', Integer, ForeignKey('books.id'), primary_key=True),
    Column('lang_code', Integer, ForeignKey('languages.id'), primary_key=True)
)


class Authors(Base):
    __tablename__ = 'authors'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(collation='NOCASE'))
    sort = Column(String(collation='NOCASE'))
    link = Column(String, default="")


class Tags(Base):
    __tablename__ = 'tags'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(collation='NOCASE'))


class Series(Base):
    __tablename__ = 'series'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(collation='NOCASE'))
    sort = Column(String(collation='NOCASE'))


class Publishers(Base):
    __tablename__ = 'publishers'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(collation='NOCASE'))
    sort = Column(String(collation='NOCASE'))


class Comments(Base):
    __tablename__ = 'comments'
    
    id = Column(Integer, primary_key=True)
    book = Column(Integer, ForeignKey('books.id'), nullable=False, unique=True)
    text = Column(String(collation='NOCASE'), nullable=False)


class Ratings(Base):
    __tablename__ = 'ratings'
    
    id = Column(Integer, primary_key=True)
    rating = Column(Integer)


class Languages(Base):
    __tablename__ = 'languages'
    
    id = Column(Integer, primary_key=True)
    lang_code = Column(String(collation='NOCASE'), nullable=False, unique=True)


class Identifiers(Base):
    __tablename__ = 'identifiers'
    
    id = Column(Integer, primary_key=True)
    type = Column(String(collation='NOCASE'), nullable=False, default="isbn")
    val = Column(String(collation='NOCASE'), nullable=False)
    book = Column(Integer, ForeignKey('books.id'), nullable=False)


class Data(Base):
    __tablename__ = 'data'
    
    id = Column(Integer, primary_key=True)
    book = Column(Integer, ForeignKey('books.id'), nullable=False)
    format = Column(String(collation='NOCASE'), nullable=False)
    uncompressed_size = Column(Integer, nullable=False)
    name = Column(String, nullable=False)


class Books(Base):
    __tablename__ = 'books'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(collation='NOCASE'), nullable=False, default='Unknown')
    sort = Column(String(collation='NOCASE'))
    author_sort = Column(String(collation='NOCASE'))
    timestamp = Column(TIMESTAMP, default=lambda: datetime.now(timezone.utc))
    pubdate = Column(TIMESTAMP)
    series_index = Column(String, nullable=False, default="1.0")
    last_modified = Column(TIMESTAMP, default=lambda: datetime.now(timezone.utc))
    path = Column(String, default="", nullable=False)
    has_cover = Column(Integer, default=0)
    uuid = Column(String)
    isbn = Column(String(collation='NOCASE'), default="")
    lccn = Column(String, default="")
    
    # Relationships
    authors = relationship(Authors, secondary=books_authors_link, backref='books')
    tags = relationship(Tags, secondary=books_tags_link, backref='books', order_by="Tags.name")
    series_rel = relationship(Series, secondary=books_series_link, backref='books', uselist=False)
    publishers_rel = relationship(Publishers, secondary=books_publishers_link, backref='books', uselist=False)
    ratings_rel = relationship(Ratings, secondary=books_ratings_link, backref='books')
    languages_rel = relationship(Languages, secondary=books_languages_link, backref='books')

