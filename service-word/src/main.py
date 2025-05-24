from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import threading
import logging

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from domain.models import Base

from core.config import settings
from api.routes import router as api_router
from utils.grpc_server import start_grpc_server, GRPCServer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.PROJECT_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

grpc_server_instance = None
app.state.db_engine = None
app.state.db_session_factory = None

@app.on_event("startup")
async def startup_event():
    """
    Hàm được gọi khi ứng dụng khởi động.
    Khởi động gRPC server trong một thread riêng.
    Khởi tạo SQLAlchemy database engine và session factory.
    """
    global grpc_server_instance
    global app
    
    try:
        # Create async engine with asyncpg driver
        app.state.db_engine = create_async_engine(
            settings.DATABASE_URL,
            echo=False,
            pool_size=10,
            max_overflow=20
        )
        
        # Create async session factory
        app.state.db_session_factory = async_sessionmaker(
            app.state.db_engine,
            expire_on_commit=False
        )
        
        logger.info("SQLAlchemy async engine started for service-word.")
    except Exception as e:
        logger.error(f"Không thể tạo SQLAlchemy engine: {e}")

    grpc_host = f"[::]:{settings.GRPC_PORT}"
    
    logger.info(f"Khởi động gRPC server trên {grpc_host}")
    grpc_server_instance = start_grpc_server(host=grpc_host, max_workers=settings.GRPC_WORKERS)
    
    logger.info("Ứng dụng FastAPI và gRPC server đã khởi động")

@app.on_event("shutdown")
async def shutdown_event():
    """
    Hàm được gọi khi ứng dụng shutdown.
    Dừng gRPC server nếu đang chạy.
    Đóng SQLAlchemy database engine.
    """
    global grpc_server_instance
    global app

    if app.state.db_engine:
        try:
            await app.state.db_engine.dispose()
            logger.info("SQLAlchemy database engine đã được đóng.")
        except Exception as e:
            logger.error(f"Lỗi khi đóng SQLAlchemy engine: {e}")
    
    if grpc_server_instance:
        logger.info("Dừng gRPC server")
        grpc_server_instance.stop(grace=5.0)
        logger.info("gRPC server đã dừng")

@app.get("/", tags=["Root"])
async def root():
    """API gốc - dùng để kiểm tra trạng thái hoạt động"""
    return {
        "message": "Word Document Service đang hoạt động",
        "version": settings.PROJECT_VERSION
    }

@app.get("/health", tags=["Health"])
async def health_check():
    """Kiểm tra trạng thái hoạt động của service"""
    return {
        "status": "healthy",
        "version": settings.PROJECT_VERSION,
        "service": "word-document",
        "grpc_running": grpc_server_instance is not None and grpc_server_instance.running
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG_MODE,
        workers=settings.WORKERS
    )