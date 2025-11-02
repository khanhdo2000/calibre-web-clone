from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    # Calibre Configuration
    calibre_library_path: str = "/calibre-library"
    watch_calibre_db: bool = True  # Watch for changes from Calibre desktop

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
    database_url: str = "postgresql+asyncpg://calibre:calibre@localhost:5432/calibre_web"

    # Google Drive Configuration
    use_google_drive: bool = False
    google_drive_credentials_path: Optional[str] = None
    google_drive_folder_id: Optional[str] = None

    # S3 Configuration for covers
    use_s3_covers: bool = False
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = "us-east-1"
    s3_bucket_name: Optional[str] = None
    s3_covers_prefix: str = "covers/"

    # Performance
    enable_auth_cache: bool = True
    auth_cache_ttl: int = 300  # 5 minutes

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
