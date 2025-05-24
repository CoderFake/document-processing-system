import os
from pydantic_settings import BaseSettings
from typing import List, Dict, Any, Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "Files Compression Service"
    PROJECT_DESCRIPTION: str = "Dịch vụ xử lý tệp tin nén ZIP, RAR, 7Z và các định dạng khác"
    PROJECT_VERSION: str = "1.0.0"

    HOST: str = "0.0.0.0"
    PORT: int = 10004
    DEBUG_MODE: bool = os.getenv("APP_ENV", "development") == "development"
    WORKERS: int = 1

    ALLOWED_ORIGINS: List[str] = ["*"]

    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/document_processing")
    DEBUG: bool = os.getenv("APP_ENV", "development") == "development"

    # DB Pool Settings
    DB_POOL_MIN_SIZE: int = int(os.getenv("DB_POOL_MIN_SIZE", "1"))
    DB_POOL_MAX_SIZE: int = int(os.getenv("DB_POOL_MAX_SIZE", "10"))
    DB_TIMEOUT: int = int(os.getenv("DB_TIMEOUT", "30"))
    DB_COMMAND_TIMEOUT: int = int(os.getenv("DB_COMMAND_TIMEOUT", "5"))

    RABBITMQ_HOST: str = os.getenv("RABBITMQ_HOST", "rabbitmq")
    RABBITMQ_PORT: int = int(os.getenv("RABBITMQ_PORT", "5672"))
    RABBITMQ_USER: str = os.getenv("RABBITMQ_USER", "admin")
    RABBITMQ_PASS: str = os.getenv("RABBITMQ_PASS", "adminpassword")
    RABBITMQ_VHOST: str = os.getenv("RABBITMQ_VHOST", "/")

    MINIO_HOST: str = os.getenv("MINIO_HOST", "minio")
    MINIO_PORT: int = int(os.getenv("MINIO_PORT", "9000"))
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    MINIO_FILES_BUCKET: str = "files"
    MINIO_RAW_BUCKET: str = "raw-files"
    MINIO_ARCHIVE_BUCKET: str = "archive-files"
    MINIO_EXTRACTED_BUCKET: str = "extracted-files"

    TEMPLATES_DIR: str = "/app/templates"
    TEMP_DIR: str = "/app/temp"

    WORD_SERVICE_URL: str = os.getenv("WORD_SERVICE_URL", "http://service-word:10001")
    PDF_SERVICE_URL: str = os.getenv("PDF_SERVICE_URL", "http://service-pdf:10002")
    EXCEL_SERVICE_URL: str = os.getenv("EXCEL_SERVICE_URL", "http://service-excel:10003")
    FILES_SERVICE_URL: str = os.getenv("FILES_SERVICE_URL", "http://service-files:10004")

    SERVICE_URLS: Dict[str, str] = {}

    DEFAULT_PAGE_SIZE: int = 10
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100MB

    SUPPORTED_ARCHIVE_FORMATS: List[str] = [".zip", ".rar", ".7z", ".tar", ".gz", ".tar.gz"]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

# Initialize SERVICE_URLS after settings object is created
settings.SERVICE_URLS = {
    "word": settings.WORD_SERVICE_URL,
    "pdf": settings.PDF_SERVICE_URL,
    "excel": settings.EXCEL_SERVICE_URL,
    "files": settings.FILES_SERVICE_URL, # For files managed directly by service-files
}

os.makedirs(settings.TEMPLATES_DIR, exist_ok=True)
os.makedirs(settings.TEMP_DIR, exist_ok=True)