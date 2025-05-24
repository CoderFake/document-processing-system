import os
from pydantic_settings import BaseSettings
from typing import List, Dict, Any, Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "User Management Service"
    PROJECT_DESCRIPTION: str = "Dịch vụ quản lý người dùng và phân quyền"
    PROJECT_VERSION: str = "1.0.0"

    HOST: str = "0.0.0.0"
    PORT: int = 10005
    DEBUG: bool = os.getenv("APP_ENV", "development") == "development"
    WORKERS: int = 1

    API_V1_STR: str = "/api/v1"
    CORS_ORIGINS: List[str] = ["*"]

    # Database settings
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/users")
    
    # JWT settings
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "secret_key_for_jwt_please_change_in_production")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # RabbitMQ settings
    RABBITMQ_HOST: str = os.getenv("RABBITMQ_HOST", "rabbitmq")
    RABBITMQ_PORT: int = int(os.getenv("RABBITMQ_PORT", "5672"))
    RABBITMQ_USER: str = os.getenv("RABBITMQ_USER", "admin")
    RABBITMQ_PASS: str = os.getenv("RABBITMQ_PASS", "adminpassword")
    RABBITMQ_VHOST: str = os.getenv("RABBITMQ_VHOST", "/")

    # MinIO settings
    MINIO_HOST: str = os.getenv("MINIO_HOST", "minio")
    MINIO_PORT: int = int(os.getenv("MINIO_PORT", "9000"))
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    MINIO_USER_BUCKET: str = "user-profiles"
    
    # Service URLs
    PDF_SERVICE_URL: str = os.getenv("PDF_SERVICE_URL", "http://service-pdf:10003")
    WORD_SERVICE_URL: str = os.getenv("WORD_SERVICE_URL", "http://service-word:10001")
    EXCEL_SERVICE_URL: str = os.getenv("EXCEL_SERVICE_URL", "http://service-excel:10002")
    FILES_SERVICE_URL: str = os.getenv("FILES_SERVICE_URL", "http://service-files:10004")

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

os.makedirs(os.path.join(os.path.dirname(__file__), "../../logs"), exist_ok=True) 