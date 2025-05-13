import os
from pydantic_settings import BaseSettings
from typing import List, Dict, Any


class Settings(BaseSettings):
    PROJECT_NAME: str = "Document Processing Gateway API"
    PROJECT_DESCRIPTION: str = "API Gateway cho hệ thống xử lý tài liệu đa định dạng"
    PROJECT_VERSION: str = "1.0.0"

    HOST: str = "0.0.0.0"
    PORT: int = 10000
    DEBUG_MODE: bool = os.getenv("APP_ENV", "development") == "development"
    WORKERS: int = 4

    ALLOWED_ORIGINS: List[str] = ["*"]

    WORD_SERVICE_URL: str = os.getenv("WORD_SERVICE_URL", "http://service-word:10001")
    EXCEL_SERVICE_URL: str = os.getenv("EXCEL_SERVICE_URL", "http://service-excel:10002")
    PDF_SERVICE_URL: str = os.getenv("PDF_SERVICE_URL", "http://service-pdf:10003")
    FILES_SERVICE_URL: str = os.getenv("FILES_SERVICE_URL", "http://service-files:10004")
    USER_SERVICE_URL: str = os.getenv("USER_SERVICE_URL", "http://service-user:10005")

    RABBITMQ_HOST: str = os.getenv("RABBITMQ_HOST", "rabbitmq")
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = os.getenv("RABBITMQ_USER", "admin")
    RABBITMQ_PASS: str = os.getenv("RABBITMQ_PASS", "adminpassword")
    RABBITMQ_VHOST: str = os.getenv("RABBITMQ_VHOST", "/")

    MINIO_HOST: str = os.getenv("MINIO_HOST", "minio")
    MINIO_PORT: int = 9000
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")

    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "your_jwt_secret_key")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()