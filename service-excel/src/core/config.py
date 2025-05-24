import os
from pydantic_settings import BaseSettings
from typing import List, Dict, Any, Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "Excel Document Service"
    PROJECT_DESCRIPTION: str = "Dịch vụ xử lý tài liệu Excel"
    PROJECT_VERSION: str = "1.0.0"

    HOST: str = "0.0.0.0"
    PORT: int = 10002
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
    
    # RabbitMQ Task Settings
    RABBITMQ_EXCHANGE_TASKS: str = os.getenv("RABBITMQ_EXCHANGE_TASKS", "tasks_exchange")
    RABBITMQ_ROUTING_KEY_EXCEL_MERGE: str = os.getenv("RABBITMQ_ROUTING_KEY_EXCEL_MERGE", "excel.tasks.merge")
    RABBITMQ_ROUTING_KEY_EXCEL_TO_PDF: str = os.getenv("RABBITMQ_ROUTING_KEY_EXCEL_TO_PDF", "excel.tasks.convert.pdf")
    RABBITMQ_ROUTING_KEY_EXCEL_TO_WORD: str = os.getenv("RABBITMQ_ROUTING_KEY_EXCEL_TO_WORD", "excel.tasks.convert.word")

    MINIO_HOST: str = os.getenv("MINIO_HOST", "minio")
    MINIO_PORT: int = int(os.getenv("MINIO_PORT", "9000"))
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    MINIO_EXCEL_BUCKET: str = "excel-documents"
    MINIO_TEMPLATES_BUCKET: str = "excel-templates"

    TEMPLATES_DIR: str = "/app/templates"
    TEMP_DIR: str = "/app/temp"

    DEFAULT_PAGE_SIZE: int = 10
    MAX_UPLOAD_SIZE: int = 20 * 1024 * 1024  

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

os.makedirs(settings.TEMPLATES_DIR, exist_ok=True)
os.makedirs(settings.TEMP_DIR, exist_ok=True)