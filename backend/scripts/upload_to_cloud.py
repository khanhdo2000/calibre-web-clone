#!/usr/bin/env python3
"""
Upload script for syncing Calibre library to cloud storage.

This script runs on the local machine where Calibre library is located.
It uploads covers to S3 and book files to Google Drive, then syncs
upload tracking records to the remote server.

Usage:
    python upload_to_cloud.py --all --server-api-url "https://yourserver.com/api" --server-api-key "..."
    python upload_to_cloud.py --covers-only --incremental --server-api-url "..."
    python upload_to_cloud.py --books-only --dry-run
"""

import sys
import os
import argparse
import logging
import hashlib
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import sqlite3
import boto3
from botocore.exceptions import ClientError
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import requests
from PIL import Image
import io

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class LocalCalibreDB:
    """Read Calibre metadata.db from local library"""

    def __init__(self, library_path: str):
        self.library_path = library_path
        self.db_path = os.path.join(library_path, "metadata.db")
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Calibre database not found at {self.db_path}")

    def _get_connection(self):
        """Get connection to local Calibre database"""
        conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        return conn

    def get_all_books(self) -> List[Dict]:
        """Get all books with their file formats"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Get all books
        books_query = "SELECT id, title, path, has_cover FROM books ORDER BY id"
        books = cursor.execute(books_query).fetchall()

        result = []
        for book in books:
            book_id = book["id"]
            # Get file formats
            formats_query = """
                SELECT format FROM data
                WHERE book = ?
            """
            formats = cursor.execute(formats_query, (book_id,)).fetchall()
            file_formats = [row["format"].upper() for row in formats]

            result.append({
                "id": book_id,
                "title": book["title"],
                "path": book["path"],
                "has_cover": bool(book["has_cover"]),
                "file_formats": file_formats,
            })

        conn.close()
        return result


class S3Uploader:
    """Upload covers to S3"""

    def __init__(self, bucket_name: str, prefix: str, aws_access_key: str, aws_secret_key: str, region: str):
        self.bucket_name = bucket_name
        self.prefix = prefix
        try:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key,
                region_name=region
            )
            logger.info("S3 client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize S3: {e}")
            raise

    def create_thumbnail(self, image_path: str, max_size: tuple = (300, 450), quality: int = 85) -> Optional[bytes]:
        """Create a thumbnail version of the cover image"""
        try:
            with Image.open(image_path) as img:
                # Convert to RGB if necessary (handles RGBA, etc.)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Calculate thumbnail size maintaining aspect ratio
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                
                # Save to bytes
                thumb_io = io.BytesIO()
                img.save(thumb_io, format='JPEG', quality=quality, optimize=True)
                thumb_io.seek(0)
                return thumb_io.read()
        except Exception as e:
            logger.error(f"Failed to create thumbnail: {e}")
            return None

    def upload_cover(self, book_id: int, cover_path: str) -> Optional[str]:
        """Upload cover to S3, returns S3 key if successful"""
        if not os.path.exists(cover_path):
            logger.warning(f"Cover not found: {cover_path}")
            return None

        key = f"{self.prefix}{book_id}.jpg"
        try:
            with open(cover_path, 'rb') as f:
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=key,
                    Body=f,
                    ContentType='image/jpeg',
                    CacheControl='public, max-age=31536000'
                )
            logger.info(f"Uploaded cover {book_id} to S3: {key}")
            return key
        except Exception as e:
            logger.error(f"Failed to upload cover {book_id}: {e}")
            return None

    def upload_cover_thumbnail(self, book_id: int, cover_path: str) -> Optional[str]:
        """Upload cover thumbnail to S3, returns S3 key if successful"""
        if not os.path.exists(cover_path):
            logger.warning(f"Cover not found: {cover_path}")
            return None

        # Create thumbnail (300x450 max size, good for book cards)
        thumbnail_data = self.create_thumbnail(cover_path, max_size=(300, 450), quality=85)
        if not thumbnail_data:
            logger.warning(f"Failed to create thumbnail for book {book_id}")
            return None

        thumb_key = f"{self.prefix}thumb/{book_id}.jpg"
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=thumb_key,
                Body=thumbnail_data,
                ContentType='image/jpeg',
                CacheControl='public, max-age=31536000'
            )
            logger.info(f"Uploaded cover thumbnail {book_id} to S3: {thumb_key}")
            return thumb_key
        except Exception as e:
            logger.error(f"Failed to upload cover thumbnail {book_id}: {e}")
            return None

    def get_file_checksum(self, file_path: str) -> str:
        """Calculate MD5 checksum of file"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()


class GoogleDriveUploader:
    """Upload book files to Google Drive"""

    def __init__(self, credentials_path: str, folder_id: str):
        self.folder_id = folder_id
        try:
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path,
                scopes=['https://www.googleapis.com/auth/drive.file']
            )
            self.service = build('drive', 'v3', credentials=credentials)
            logger.info("Google Drive client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Google Drive: {e}")
            raise

    def _get_or_create_folder(self, folder_name: str, parent_id: str) -> Optional[str]:
        """Get folder ID if exists, or create it"""
        try:
            query = f"'{parent_id}' in parents and name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)',
                pageSize=1
            ).execute()

            files = results.get('files', [])
            if files:
                return files[0]['id']

            # Create folder
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent_id]
            }

            folder = self.service.files().create(
                body=folder_metadata,
                fields='id'
            ).execute()

            return folder.get('id')

        except Exception as e:
            logger.error(f"Error getting/creating folder {folder_name}: {e}")
            return None

    def upload_file(self, file_path: str, book_path: str, mime_type: str = None) -> Optional[str]:
        """Upload file to Google Drive, returns file ID if successful"""
        if not os.path.exists(file_path):
            logger.warning(f"File not found: {file_path}")
            return None

        try:
            import os
            # Parse Calibre path: "Author/Book Title (123)/book.epub"
            path_parts = book_path.split(os.sep)
            if len(path_parts) < 2:
                logger.error(f"Invalid book path structure: {book_path}")
                return None

            # Find or create parent folder (Author)
            parent_folder_id = self._get_or_create_folder(
                path_parts[0],
                self.folder_id
            )
            if not parent_folder_id:
                return None

            # Find or create book folder (Book Title (123))
            if len(path_parts) > 2:
                book_folder_id = self._get_or_create_folder(
                    path_parts[1],
                    parent_folder_id
                )
            else:
                book_folder_id = parent_folder_id

            if not book_folder_id:
                return None

            # Get filename
            filename = os.path.basename(file_path)

            # Check if file already exists
            query = f"'{book_folder_id}' in parents and name='{filename}' and trashed=false"
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)',
                pageSize=1
            ).execute()

            files = results.get('files', [])
            if files:
                # File exists, return existing ID
                logger.info(f"File already exists in GDrive: {filename}")
                return files[0]['id']

            # Upload file
            file_metadata = {
                'name': filename,
                'parents': [book_folder_id]
            }

            if mime_type is None:
                # Guess MIME type from extension
                ext = os.path.splitext(filename)[1].lower()
                mime_types = {
                    '.epub': 'application/epub+zip',
                    '.pdf': 'application/pdf',
                    '.mobi': 'application/x-mobipocket-ebook',
                    '.azw3': 'application/vnd.amazon.ebook',
                    '.txt': 'text/plain',
                }
                mime_type = mime_types.get(ext, 'application/octet-stream')

            media = MediaFileUpload(
                file_path,
                mimetype=mime_type,
                resumable=True
            )

            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()

            logger.info(f"Uploaded file to Google Drive: {filename} -> {file.get('id')}")
            return file.get('id')

        except Exception as e:
            logger.error(f"Error uploading file to Google Drive: {e}")
            return None


class UploadTracker:
    """Sync upload tracking records to server"""

    def __init__(self, server_api_url: str, api_key: Optional[str] = None):
        self.server_api_url = server_api_url.rstrip('/')
        self.api_key = api_key
        self.records = []

    def add_record(self, book_id: int, book_path: str, file_type: str, storage_type: str,
                   storage_url: str, file_size: Optional[int] = None, checksum: Optional[str] = None):
        """Add upload record to batch"""
        self.records.append({
            "book_id": book_id,
            "book_path": book_path,
            "file_type": file_type,
            "storage_type": storage_type,
            "storage_url": storage_url,
            "upload_date": datetime.utcnow().isoformat(),
            "file_size": file_size,
            "checksum": checksum,
        })

    def sync_to_server(self, batch_size: int = 100):
        """Sync records to server in batches"""
        if not self.records:
            logger.info("No records to sync")
            return

        total = len(self.records)
        logger.info(f"Syncing {total} upload tracking records to server...")

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        for i in range(0, total, batch_size):
            batch = self.records[i:i + batch_size]
            try:
                response = requests.post(
                    f"{self.server_api_url}/admin/upload-tracking/bulk",
                    json=batch,
                    headers=headers,
                    timeout=30
                )
                response.raise_for_status()
                logger.info(f"Synced batch {i // batch_size + 1}: {len(batch)} records")
            except Exception as e:
                logger.error(f"Failed to sync batch {i // batch_size + 1}: {e}")

        self.records = []  # Clear after sync


def get_existing_uploads(server_api_url: str, api_key: Optional[str] = None) -> Dict[str, bool]:
    """
    Get existing uploads from server to skip already uploaded items.
    Uses pagination to efficiently fetch large numbers of records.
    Returns a dict with keys like 's3:123:cover' or 'gdrive:123:EPUB' mapping to True.
    """
    existing = {}
    try:
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        logger.info("Checking existing uploads from server...")
        
        # Fetch upload tracking records with pagination
        limit = 1000  # Fetch in batches of 1000
        offset = 0
        total_fetched = 0
        
        while True:
            response = requests.get(
                f"{server_api_url}/admin/upload-tracking",
                headers=headers,
                params={"limit": limit, "offset": offset},
                timeout=60
            )
            response.raise_for_status()
            
            data = response.json()
            records = data.get("records", [])
            total = data.get("total", 0)
            
            if not records:
                break
            
            # Build lookup dict
            for record in records:
                book_id = record["book_id"]
                file_type = record["file_type"]
                storage_type = record["storage_type"]
                key = f"{storage_type}:{book_id}:{file_type}"
                existing[key] = True
            
            total_fetched += len(records)
            offset += limit
            
            if total_fetched >= total or len(records) < limit:
                break
        
        logger.info(f"Found {len(existing)} existing upload records on server")
        return existing
        
    except requests.exceptions.RequestException as e:
        logger.warning(f"Could not check existing uploads from server: {e}")
        logger.warning("Continuing without incremental check - files may be uploaded again")
        return existing
    except Exception as e:
        logger.warning(f"Error checking existing uploads: {e}")
        return existing


def check_batch_uploads(
    server_api_url: str,
    items_to_check: List[Dict[str, int]],
    api_key: Optional[str] = None,
    batch_size: int = 100
) -> Dict[str, bool]:
    """
    Efficiently check if specific files are already uploaded using batch API.
    More efficient than fetching all records when you only need to check specific files.
    """
    existing = {}
    try:
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        # Check in batches
        for i in range(0, len(items_to_check), batch_size):
            batch = items_to_check[i:i + batch_size]
            
            response = requests.post(
                f"{server_api_url}/admin/upload-tracking/check",
                json=batch,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            existing_items = result.get("existing", [])
            
            for item in existing_items:
                key = f"{item['storage_type']}:{item['book_id']}:{item['file_type']}"
                existing[key] = True
        
        return existing
        
    except requests.exceptions.RequestException as e:
        logger.warning(f"Could not check batch uploads from server: {e}")
        return existing
    except Exception as e:
        logger.warning(f"Error checking batch uploads: {e}")
        return existing


def main():
    parser = argparse.ArgumentParser(description="Upload Calibre library to cloud storage")
    parser.add_argument("--library-path", required=True, help="Path to local Calibre library")
    parser.add_argument("--covers-only", action="store_true", help="Upload only covers")
    parser.add_argument("--books-only", action="store_true", help="Upload only books")
    parser.add_argument("--all", action="store_true", help="Upload everything")
    parser.add_argument("--incremental", action="store_true", help="Skip already uploaded items")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually upload, just log")
    parser.add_argument("--delete-local", action="store_true", help="Delete local files after successful upload")
    parser.add_argument("--min-size", type=int, default=0, help="Minimum file size in bytes to delete (default: 0, deletes all)")
    parser.add_argument("--min-size-mb", type=float, help="Minimum file size in MB (alternative to --min-size)")
    
    # S3 configuration
    parser.add_argument("--s3-bucket", help="S3 bucket name")
    parser.add_argument("--s3-prefix", default="covers/", help="S3 prefix for covers")
    parser.add_argument("--aws-access-key", help="AWS access key")
    parser.add_argument("--aws-secret-key", help="AWS secret key")
    parser.add_argument("--aws-region", default="us-east-1", help="AWS region")
    
    # Google Drive configuration
    parser.add_argument("--gdrive-credentials", help="Path to Google Drive service account credentials JSON")
    parser.add_argument("--gdrive-folder-id", help="Google Drive folder ID")
    
    # Server sync configuration
    parser.add_argument("--server-api-url", help="Server API URL for syncing upload tracking")
    parser.add_argument("--server-api-key", help="API key for server authentication")
    
    args = parser.parse_args()

    # Validate arguments
    if not args.all and not args.covers_only and not args.books_only:
        parser.error("Must specify --all, --covers-only, or --books-only")

    # Convert min-size-mb to bytes if provided
    min_size_bytes = args.min_size
    if args.min_size_mb:
        min_size_bytes = int(args.min_size_mb * 1024 * 1024)

    if args.dry_run:
        logger.info("DRY RUN MODE - No files will be uploaded")
        if args.delete_local:
            logger.info("DRY RUN MODE - No files will be deleted")
    elif args.delete_local:
        logger.warning(f"DELETE LOCAL MODE ENABLED - Files >= {min_size_bytes} bytes ({min_size_bytes / (1024*1024):.2f} MB) will be deleted after successful upload")
        response = input("Are you sure you want to delete local files? (yes/no): ")
        if response.lower() != "yes":
            logger.info("Aborted. Local files will not be deleted.")
            args.delete_local = False

    # Initialize components
    try:
        calibre_db = LocalCalibreDB(args.library_path)
    except Exception as e:
        logger.error(f"Failed to initialize Calibre DB: {e}")
        return 1

    s3_uploader = None
    if args.covers_only or args.all:
        if not all([args.s3_bucket, args.aws_access_key, args.aws_secret_key]):
            logger.error("S3 configuration required for cover uploads")
            return 1
        try:
            s3_uploader = S3Uploader(
                args.s3_bucket, args.s3_prefix,
                args.aws_access_key, args.aws_secret_key, args.aws_region
            )
        except Exception as e:
            logger.error(f"Failed to initialize S3: {e}")
            return 1

    gdrive_uploader = None
    if args.books_only or args.all:
        if not all([args.gdrive_credentials, args.gdrive_folder_id]):
            logger.error("Google Drive configuration required for book uploads")
            return 1
        try:
            gdrive_uploader = GoogleDriveUploader(args.gdrive_credentials, args.gdrive_folder_id)
        except Exception as e:
            logger.error(f"Failed to initialize Google Drive: {e}")
            return 1

    upload_tracker = None
    if args.server_api_url:
        upload_tracker = UploadTracker(args.server_api_url, args.server_api_key)

    # Get all books first
    logger.info("Reading books from Calibre library...")
    books = calibre_db.get_all_books()
    logger.info(f"Found {len(books)} books")

    # Get existing uploads if incremental (or always if server API is available)
    existing_uploads = {}
    if args.server_api_url:
        # Use batch check API for efficiency when we know what files we need to check
        # This is more efficient than fetching all records
        items_to_check = []
        
        # Build list of items to check
        if args.covers_only or args.all:
            for book in books:
                if book["has_cover"]:
                    items_to_check.append({
                        "book_id": book["id"],
                        "file_type": "cover",
                        "storage_type": "s3"
                    })
                    # Also check for thumbnail
                    items_to_check.append({
                        "book_id": book["id"],
                        "file_type": "cover_thumb",
                        "storage_type": "s3"
                    })
        
        if args.books_only or args.all:
            for book in books:
                for format_ext in book["file_formats"]:
                    items_to_check.append({
                        "book_id": book["id"],
                        "file_type": format_ext,
                        "storage_type": "gdrive"
                    })
        
        if items_to_check:
            logger.info(f"Checking {len(items_to_check)} files against server...")
            existing_uploads = check_batch_uploads(
                args.server_api_url,
                items_to_check,
                args.server_api_key,
                batch_size=100
            )
            logger.info(f"Found {len(existing_uploads)} existing uploads to skip")
        elif args.incremental:
            # Fallback to paginated fetch if no items to check (shouldn't happen)
            logger.info("No files to check, using paginated fetch...")
            existing_uploads = get_existing_uploads(args.server_api_url, args.server_api_key)
    elif args.incremental:
        logger.warning("--incremental specified but --server-api-url not provided. Cannot check existing uploads.")

    # Upload covers
    if (args.covers_only or args.all) and s3_uploader:
        logger.info("Uploading covers to S3...")
        covers_uploaded = 0
        for book in books:
            if not book["has_cover"]:
                continue

            book_id = book["id"]
            cover_key = f"s3:{book_id}:cover"
            thumb_key_check = f"s3:{book_id}:cover_thumb"
            # Skip if both cover and thumbnail are already uploaded
            if cover_key in existing_uploads and thumb_key_check in existing_uploads:
                logger.debug(f"Skipping already uploaded cover and thumbnail: {book_id}")
                continue

            cover_path = os.path.join(args.library_path, book["path"], "cover.jpg")
            if not os.path.exists(cover_path):
                logger.warning(f"Cover file not found: {cover_path}")
                continue

            if args.dry_run:
                logger.info(f"[DRY RUN] Would upload cover: {book_id}")
                covers_uploaded += 1
                continue

            s3_key = s3_uploader.upload_cover(book_id, cover_path)
            if s3_key:
                file_size = os.path.getsize(cover_path)
                
                if upload_tracker:
                    checksum = s3_uploader.get_file_checksum(cover_path)
                    upload_tracker.add_record(
                        book_id=book_id,
                        book_path=book["path"],
                        file_type="cover",
                        storage_type="s3",
                        storage_url=s3_key,
                        file_size=file_size,
                        checksum=checksum,
                    )
                covers_uploaded += 1
                
                # Also upload thumbnail if not already uploaded
                if thumb_key_check not in existing_uploads:
                    thumb_key = s3_uploader.upload_cover_thumbnail(book_id, cover_path)
                    if thumb_key and upload_tracker:
                        upload_tracker.add_record(
                            book_id=book_id,
                            book_path=book["path"],
                            file_type="cover_thumb",
                            storage_type="s3",
                            storage_url=thumb_key,
                            file_size=None,  # Thumbnail size is smaller, optional to track
                            checksum=None,
                        )
                else:
                    logger.debug(f"Thumbnail already uploaded for book {book_id}, skipping")

                # Delete local file if requested and meets size requirement
                if args.delete_local and file_size >= min_size_bytes:
                    if args.dry_run:
                        logger.info(f"[DRY RUN] Would delete local cover: {cover_path} ({file_size} bytes)")
                    else:
                        try:
                            os.remove(cover_path)
                            logger.info(f"Deleted local cover: {cover_path} ({file_size} bytes)")
                        except Exception as e:
                            logger.error(f"Failed to delete local cover {cover_path}: {e}")
                elif args.delete_local and file_size < min_size_bytes:
                    logger.debug(f"Skipping deletion of cover {cover_path} ({file_size} bytes < {min_size_bytes} bytes minimum)")

        logger.info(f"Uploaded {covers_uploaded} covers")

    # Upload book files
    if (args.books_only or args.all) and gdrive_uploader:
        logger.info("Uploading book files to Google Drive...")
        files_uploaded = 0
        for book in books:
            if not book["file_formats"]:
                continue

            book_id = book["id"]
            for format_ext in book["file_formats"]:
                file_key = f"gdrive:{book_id}:{format_ext}"
                if file_key in existing_uploads:
                    logger.debug(f"Skipping already uploaded file: {book_id}.{format_ext}")
                    continue

                file_path = os.path.join(
                    args.library_path,
                    book["path"],
                    f"{os.path.basename(book['path'])}.{format_ext.lower()}"
                )

                if not os.path.exists(file_path):
                    logger.warning(f"File not found: {file_path}")
                    continue

                if args.dry_run:
                    logger.info(f"[DRY RUN] Would upload file: {book_id}.{format_ext}")
                    files_uploaded += 1
                    continue

                gdrive_file_id = gdrive_uploader.upload_file(file_path, book["path"])
                if gdrive_file_id:
                    file_size = os.path.getsize(file_path)
                    
                    if upload_tracker:
                        upload_tracker.add_record(
                            book_id=book_id,
                            book_path=book["path"],
                            file_type=format_ext,
                            storage_type="gdrive",
                            storage_url=gdrive_file_id,
                            file_size=file_size,
                        )
                    files_uploaded += 1

                    # Delete local file if requested and meets size requirement
                    if args.delete_local and file_size >= min_size_bytes:
                        if args.dry_run:
                            logger.info(f"[DRY RUN] Would delete local file: {file_path} ({file_size} bytes)")
                        else:
                            try:
                                os.remove(file_path)
                                logger.info(f"Deleted local file: {file_path} ({file_size} bytes)")
                            except Exception as e:
                                logger.error(f"Failed to delete local file {file_path}: {e}")
                    elif args.delete_local and file_size < min_size_bytes:
                        logger.debug(f"Skipping deletion of file {file_path} ({file_size} bytes < {min_size_bytes} bytes minimum)")

        logger.info(f"Uploaded {files_uploaded} book files")

    # Sync upload tracking to server
    if upload_tracker:
        upload_tracker.sync_to_server()

    logger.info("Upload complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())

