import os
import logging
from typing import Optional
from io import BytesIO

# Google Drive
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# S3
import boto3
from botocore.exceptions import ClientError

from app.config import settings

logger = logging.getLogger(__name__)


class GoogleDriveStorage:
    """
    Google Drive integration for storing book files.
    Books are organized in Google Drive folders matching Calibre structure.
    """

    def __init__(self):
        self.service = None
        self.folder_id = settings.google_drive_folder_id

        if settings.use_google_drive and settings.google_drive_credentials_path:
            try:
                credentials = service_account.Credentials.from_service_account_file(
                    settings.google_drive_credentials_path,
                    scopes=[
                        'https://www.googleapis.com/auth/drive.readonly',
                        'https://www.googleapis.com/auth/drive.file'  # For uploads
                    ]
                )
                self.service = build('drive', 'v3', credentials=credentials)
                logger.info("Google Drive storage initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Google Drive: {e}")

    def get_file_stream(self, file_path: str) -> Optional[BytesIO]:
        """
        Get file from Google Drive.
        file_path should match Calibre's structure: "Author/Book Title (123)/book.epub"
        """
        if not self.service:
            return None

        try:
            # Search for file by path
            query = f"'{self.folder_id}' in parents and name contains '{os.path.basename(file_path)}'"
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name, mimeType)',
                pageSize=10
            ).execute()

            files = results.get('files', [])

            if not files:
                logger.warning(f"File not found in Google Drive: {file_path}")
                return None

            # Get the first matching file
            file_id = files[0]['id']

            # Download file
            request = self.service.files().get_media(fileId=file_id)
            file_stream = BytesIO()
            downloader = MediaIoBaseDownload(file_stream, request)

            done = False
            while not done:
                status, done = downloader.next_chunk()

            file_stream.seek(0)
            return file_stream

        except Exception as e:
            logger.error(f"Error downloading from Google Drive: {e}")
            return None

    def file_exists(self, file_path: str) -> bool:
        """Check if file exists in Google Drive"""
        if not self.service:
            return False

        try:
            query = f"'{self.folder_id}' in parents and name contains '{os.path.basename(file_path)}'"
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id)',
                pageSize=1
            ).execute()

            return len(results.get('files', [])) > 0

        except Exception as e:
            logger.error(f"Error checking Google Drive file: {e}")
            return False

    def upload_file(self, file_path: str, file_data: bytes, mime_type: str = None) -> Optional[str]:
        """
        Upload file to Google Drive.
        Returns the file ID if successful, None otherwise.
        Creates folder structure if needed.
        """
        if not self.service:
            return None

        try:
            from googleapiclient.http import MediaIoBaseUpload
            from io import BytesIO
            import os

            # Parse Calibre path: "Author/Book Title (123)/book.epub"
            path_parts = file_path.split(os.sep)
            if len(path_parts) < 2:
                logger.error(f"Invalid file path structure: {file_path}")
                return None

            # Find or create parent folder (Author)
            parent_folder_id = self._get_or_create_folder(
                path_parts[0], 
                self.folder_id
            )

            # Find or create book folder (Book Title (123))
            if len(path_parts) > 2:
                book_folder_id = self._get_or_create_folder(
                    path_parts[1],
                    parent_folder_id
                )
            else:
                book_folder_id = parent_folder_id

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

            media = MediaIoBaseUpload(
                BytesIO(file_data),
                mimetype=mime_type,
                resumable=True
            )

            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()

            logger.info(f"Uploaded file to Google Drive: {file_path} -> {file.get('id')}")
            return file.get('id')

        except Exception as e:
            logger.error(f"Error uploading file to Google Drive: {e}")
            return None

    def _get_or_create_folder(self, folder_name: str, parent_id: str) -> Optional[str]:
        """Get folder ID if exists, or create it"""
        try:
            # Check if folder exists
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


class S3CoverStorage:
    """
    S3 integration for storing book cover images.
    Covers are stored with key: covers/{book_id}.jpg
    """

    def __init__(self):
        self.s3_client = None
        self.bucket_name = settings.s3_bucket_name
        self.prefix = settings.s3_covers_prefix

        if settings.use_s3_covers:
            try:
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=settings.aws_access_key_id,
                    aws_secret_access_key=settings.aws_secret_access_key,
                    region_name=settings.aws_region
                )
                logger.info("S3 cover storage initialized")
            except Exception as e:
                logger.error(f"Failed to initialize S3: {e}")

    def get_cover_url(self, book_id: int, expiration: int = 3600) -> Optional[str]:
        """
        Get presigned URL for cover image.
        Returns None if cover doesn't exist or S3 is not configured.
        """
        if not self.s3_client:
            return None

        key = f"{self.prefix}{book_id}.jpg"

        try:
            # Generate presigned URL (valid for 1 hour by default)
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': key},
                ExpiresIn=expiration
            )
            return url

        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.debug(f"Cover not found in S3: {key}")
            else:
                logger.error(f"Error getting S3 cover URL: {e}")
            return None

    def cover_exists(self, book_id: int) -> bool:
        """Check if cover exists in S3"""
        if not self.s3_client:
            return False

        key = f"{self.prefix}{book_id}.jpg"

        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError:
            return False

    def upload_cover(self, book_id: int, image_data: bytes) -> bool:
        """Upload cover image to S3"""
        if not self.s3_client:
            return False

        key = f"{self.prefix}{book_id}.jpg"

        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=image_data,
                ContentType='image/jpeg',
                CacheControl='public, max-age=31536000'  # 1 year
            )
            logger.info(f"Uploaded cover to S3: {key}")
            return True

        except ClientError as e:
            logger.error(f"Error uploading cover to S3: {e}")
            return False


class StorageService:
    """
    Unified storage service that handles both local and cloud storage.
    Falls back to local storage if cloud storage is not available.
    """

    def __init__(self):
        self.google_drive = GoogleDriveStorage() if settings.use_google_drive else None
        self.s3_covers = S3CoverStorage() if settings.use_s3_covers else None

    def get_book_file_path(self, calibre_path: str, format: str) -> str:
        """
        Get book file path. If Google Drive is enabled, returns path for streaming.
        Otherwise returns local file path.
        """
        if self.google_drive:
            # Book is in Google Drive
            filename = f"{os.path.basename(calibre_path)}.{format.lower()}"
            return os.path.join(calibre_path, filename)
        else:
            # Book is local
            filename = f"{os.path.basename(calibre_path)}.{format.lower()}"
            return os.path.join(settings.calibre_library_path, calibre_path, filename)

    def get_book_stream(self, calibre_path: str, format: str) -> Optional[BytesIO]:
        """Get book file as stream (for Google Drive)"""
        if self.google_drive:
            file_path = self.get_book_file_path(calibre_path, format)
            return self.google_drive.get_file_stream(file_path)
        return None

    def get_book_stream_from_gdrive_id(self, file_id: str) -> Optional[BytesIO]:
        """Get book file as stream from Google Drive file ID"""
        if self.google_drive and self.google_drive.service:
            try:
                from googleapiclient.http import MediaIoBaseDownload
                request = self.google_drive.service.files().get_media(fileId=file_id)
                file_stream = BytesIO()
                downloader = MediaIoBaseDownload(file_stream, request)

                done = False
                while not done:
                    status, done = downloader.next_chunk()

                file_stream.seek(0)
                return file_stream
            except Exception as e:
                logger.error(f"Error downloading from Google Drive (file_id={file_id}): {e}")
                return None
        return None

    def book_file_exists(self, calibre_path: str, format: str) -> bool:
        """Check if book file exists"""
        if self.google_drive:
            file_path = self.get_book_file_path(calibre_path, format)
            return self.google_drive.file_exists(file_path)
        else:
            file_path = self.get_book_file_path(calibre_path, format)
            return os.path.exists(file_path)

    def get_cover_url(self, book_id: int, has_local_cover: bool = False) -> Optional[str]:
        """
        Get cover URL. Tries S3 first, falls back to local.
        Returns None to indicate local cover should be served.
        """
        if self.s3_covers:
            # Try S3 first
            url = self.s3_covers.get_cover_url(book_id)
            if url:
                return url

        # Use local cover if available
        return None  # API will serve from local

    def get_local_cover_path(self, calibre_path: str) -> str:
        """Get local cover file path"""
        return os.path.join(settings.calibre_library_path, calibre_path, "cover.jpg")


# Singleton instance
storage_service = StorageService()
