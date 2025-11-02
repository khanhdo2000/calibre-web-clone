from sqlalchemy import Column, Integer, String, DateTime, BigInteger, UniqueConstraint
from datetime import datetime
from app.database import Base


class UploadTracking(Base):
    """Track which book files and covers have been uploaded to cloud storage"""
    __tablename__ = "upload_tracking"
    
    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, nullable=False, index=True)
    book_path = Column(String, nullable=False)
    file_type = Column(String, nullable=False)  # 'cover' or format like 'EPUB', 'PDF'
    storage_type = Column(String, nullable=False)  # 's3' or 'gdrive'
    storage_url = Column(String, nullable=True)  # S3 key or GDrive file ID
    upload_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    file_size = Column(BigInteger, nullable=True)
    checksum = Column(String, nullable=True)  # MD5 or SHA256 for verification
    
    __table_args__ = (
        UniqueConstraint('book_id', 'file_type', 'storage_type', name='uq_book_file_storage'),
    )

