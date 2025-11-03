from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    # Calibre Configuration
    calibre_library_path: str = "~/calibre-web"  # Default to ~/calibre-web, can be overridden via env
    watch_calibre_db: bool = True  # Watch for changes from Calibre desktop
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Expand ~ in calibre_library_path
        if self.calibre_library_path and self.calibre_library_path.startswith("~"):
            self.calibre_library_path = os.path.expanduser(self.calibre_library_path)

    # Redis Configuration
    redis_url: str = "redis://localhost:6379"
    cache_ttl: int = 3600

    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    max_search_results: int = 100

    # CORS Configuration
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    # Authentication
    secret_key: str = "your-secret-key-change-this-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # PostgreSQL for user data (separate from Calibre's SQLite)
    database_url: str = "postgresql+asyncpg://calibre:ZBuJqsMtI2gKE0gosZuohPmLphaSawnJuX7QFMfEkFh1JH6GJoonre3AbLbwOrAu@31.97.70.110:5432/calibre_web"

    # Google Drive Configuration
    use_google_drive: bool = False
    google_drive_credentials_path: Optional[str] = None
    google_drive_folder_id: Optional[str] = None

    # S3 Configuration for covers
    use_s3_covers: bool = True  # Enable S3 covers by default
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = "ap-southeast-1"  # Default to ap-southeast-1
    s3_bucket_name: Optional[str] = "cdn.mnd.vn"  # Default S3 bucket
    s3_covers_prefix: str = "covers/"

    # Performance
    enable_auth_cache: bool = True
    auth_cache_ttl: int = 300  # 5 minutes
    enable_cache: bool = True  # Enable/disable Redis caching for dev/prod

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
