from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    # Calibre Configuration
    calibre_library_path: str
    watch_calibre_db: bool = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Expand ~ in calibre_library_path
        if self.calibre_library_path and self.calibre_library_path.startswith("~"):
            self.calibre_library_path = os.path.expanduser(self.calibre_library_path)

    # Redis Configuration
    redis_url: str
    cache_ttl: int = 3600

    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    max_search_results: int = 100

    # CORS Configuration
    cors_origins: str
    frontend_url: str = "http://localhost:3003"

    # Authentication
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # PostgreSQL for user data (separate from Calibre's SQLite)
    database_url: str

    # Google Drive Configuration
    use_google_drive: bool = False
    google_drive_credentials_path: Optional[str] = None
    google_drive_folder_id: Optional[str] = None

    # S3 Configuration for covers
    use_s3_covers: bool = False
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = "ap-southeast-1"
    s3_bucket_name: Optional[str] = None
    s3_covers_prefix: str = "covers/"

    # Performance
    enable_auth_cache: bool = True
    auth_cache_ttl: int = 300
    enable_cache: bool = True

    # Email Configuration (for Send to Kindle)
    # AWS SES Configuration
    use_aws_ses: bool = False
    ses_from_email: Optional[str] = None
    ses_from_name: str = "Calibre Web Clone"
    # SMTP Configuration (fallback or alternative)
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_use_tls: bool = True
    smtp_from_email: Optional[str] = None
    smtp_from_name: str = "Calibre Web Clone"

    # RSS to EPUB Configuration
    rss_epub_output_dir: str = "/data/rss-epubs"
    rss_generation_hour: int = 6  # Hour to run daily generation (0-23)
    rss_generation_minute: int = 0  # Minute to run daily generation (0-59)

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    class Config:
        # Don't use env_file when running in Docker - rely on environment variables from docker-compose
        # env_file = ".env"  # Only use this for local development outside Docker
        case_sensitive = False


settings = Settings()
