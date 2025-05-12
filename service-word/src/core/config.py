import os
from pydantic_settings import BaseSettings
from typing import List, Dict, Any, Optional


class Settings(BaseSettings):
    # Thông tin ứng dụng
    PROJECT_NAME: str = "Word Document Service"
    PROJECT_DESCRIPTION: str = "Dịch vụ xử lý tài liệu Word/DOCX"
    PROJECT_VERSION: str = "1.0.0"

    # Cấu hình API
    HOST: str = "0.0.0.0"
    PORT: int = 6001
    DEBUG_MODE: bool = os.getenv("APP_ENV", "development") == "development"
    WORKERS: int = 1

    # Cấu hình CORS
    ALLOWED_ORIGINS: List[str] = ["*"]

    # Cấu hình RabbitMQ
    RABBITMQ_HOST: str = os.getenv("RABBITMQ_HOST", "rabbitmq")
    RABBITMQ_PORT: int = int(os.getenv("RABBITMQ_PORT", "5672"))
    RABBITMQ_USER: str = os.getenv("RABBITMQ_USER", "admin")
    RABBITMQ_PASS: str = os.getenv("RABBITMQ_PASS", "adminpassword")
    RABBITMQ_VHOST: str = os.getenv("RABBITMQ_VHOST", "/")

    # Cấu hình MinIO
    MINIO_HOST: str = os.getenv("MINIO_HOST", "minio")
    MINIO_PORT: int = int(os.getenv("MINIO_PORT", "9000"))
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    MINIO_WORD_BUCKET: str = "word-documents"
    MINIO_TEMPLATES_BUCKET: str = "word-templates"

    # Cấu hình thư mục
    TEMPLATES_DIR: str = "/app/templates"
    TEMP_DIR: str = "/app/temp"

    # Các cấu hình khác
    DEFAULT_PAGE_SIZE: int = 10
    MAX_UPLOAD_SIZE: int = 20 * 1024 * 1024  # 20MB

    class Config:
        env_file = ".env"
        case_sensitive = True


# Singleton instance
settings = Settings()

# Đảm bảo thư mục tồn tại
os.makedirs(settings.TEMPLATES_DIR, exist_ok=True)
os.makedirs(settings.TEMP_DIR, exist_ok=True)