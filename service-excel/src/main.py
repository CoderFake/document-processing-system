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

app.state.db_pool = None

@app.on_event("startup")
async def startup_event():
    """Sự kiện khi ứng dụng khởi động - Tạo DB pool."""
    try:
        app.state.db_pool = await asyncpg.create_pool(
            dsn=settings.DATABASE_URL,
            min_size=settings.DB_POOL_MIN_SIZE if hasattr(settings, 'DB_POOL_MIN_SIZE') else 1,
            max_size=settings.DB_POOL_MAX_SIZE if hasattr(settings, 'DB_POOL_MAX_SIZE') else 10,
            timeout=settings.DB_TIMEOUT if hasattr(settings, 'DB_TIMEOUT') else 30,
            command_timeout=settings.DB_COMMAND_TIMEOUT if hasattr(settings, 'DB_COMMAND_TIMEOUT') else 5
        )
        print("Connection pool to PostgreSQL started.")
    except Exception as e:
        print(f"Could not connect to PostgreSQL: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Sự kiện khi ứng dụng tắt - Đóng DB pool."""
    if app.state.db_pool:
        await app.state.db_pool.close()
        print("Connection pool to PostgreSQL closed.")

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