from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from domain.models import Base

from core.config import settings
from api.routes import router as api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.PROJECT_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.state.db_engine = None
app.state.db_session_factory = None

@app.on_event("startup")
async def startup_event():
    """Sự kiện khi ứng dụng khởi động - Tạo SQLAlchemy engine và session factory."""
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
        
        print("SQLAlchemy async engine started for service-excel.")
    except Exception as e:
        print(f"Could not create SQLAlchemy engine: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Sự kiện khi ứng dụng tắt - Đóng SQLAlchemy engine."""
    if app.state.db_engine:
        await app.state.db_engine.dispose()
        print("SQLAlchemy database engine closed.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

@app.get("/", tags=["Root"])
async def root():
    """API gốc - dùng để kiểm tra trạng thái hoạt động"""
    return {
        "message": "Excel Document Service đang hoạt động",
        "version": settings.PROJECT_VERSION
    }

@app.get("/health", tags=["Health"])
async def health_check():
    """Kiểm tra trạng thái hoạt động của service"""
    return {
        "status": "healthy",
        "version": settings.PROJECT_VERSION,
        "service": "excel-document"
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG_MODE,
        workers=settings.WORKERS
    )