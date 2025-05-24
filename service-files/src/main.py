from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncpg
from core.config import settings
from api.routes import router as api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.PROJECT_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Database pool state
app.state.db_pool = None

@app.on_event("startup")
async def startup_event():
    """Sự kiện khi ứng dụng khởi động - Tạo DB pool."""
    try:
        # Các giá trị DB_POOL_... nên được thêm vào Settings nếu chưa có
        app.state.db_pool = await asyncpg.create_pool(
            dsn=settings.DATABASE_URL,
            min_size=getattr(settings, 'DB_POOL_MIN_SIZE', 1),
            max_size=getattr(settings, 'DB_POOL_MAX_SIZE', 10),
            timeout=getattr(settings, 'DB_TIMEOUT', 30),
            command_timeout=getattr(settings, 'DB_COMMAND_TIMEOUT', 5)
        )
        print("Connection pool to PostgreSQL started for service-files.")
    except Exception as e:
        print(f"Could not connect to PostgreSQL for service-files: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Sự kiện khi ứng dụng tắt - Đóng DB pool."""
    if app.state.db_pool:
        await app.state.db_pool.close()
        print("Connection pool to PostgreSQL closed for service-files.")

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