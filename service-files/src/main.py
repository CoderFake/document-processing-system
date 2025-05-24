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

# Database engine and session factory
app.state.db_engine = None
app.state.db_session_factory = None

@app.on_event("startup")
async def startup_event():
    """Sự kiện khi ứng dụng khởi động - Tạo DB engine và session factory."""
    try:
        # Create async engine
        app.state.db_engine = create_async_engine(
            settings.DATABASE_URL,
            echo=False,
            pool_size=getattr(settings, 'DB_POOL_MIN_SIZE', 5),
            max_overflow=getattr(settings, 'DB_POOL_MAX_SIZE', 10),
        )
        
        # Create session factory
        app.state.db_session_factory = async_sessionmaker(
            app.state.db_engine,
            expire_on_commit=False
        )
        
        # Create tables
        async with app.state.db_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        print("SQLAlchemy async engine started for service-files.")
    except Exception as e:
        print(f"Could not connect to PostgreSQL for service-files: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Sự kiện khi ứng dụng tắt - Đóng DB engine."""
    if app.state.db_engine:
        await app.state.db_engine.dispose()
        print("SQLAlchemy async engine closed for service-files.")

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
        "message": "Files Compression Service đang hoạt động",
        "version": settings.PROJECT_VERSION
    }

@app.get("/health", tags=["Health"])
async def health_check():
    """Kiểm tra trạng thái hoạt động của service"""
    return {
        "status": "healthy",
        "version": settings.PROJECT_VERSION,
        "service": "files-compression"
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG_MODE,
        workers=settings.WORKERS
    ) 