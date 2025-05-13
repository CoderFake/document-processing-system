from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from core.config import settings
from api.v1.router import api_router
from api.health import health_router

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

app.include_router(health_router, prefix="/health", tags=["Health Check"])
app.include_router(api_router, prefix="/api/v1")

@app.get("/", tags=["Root"])
async def root():
    """API gốc - dùng để kiểm tra trạng thái hoạt động"""
    return {
        "message": "Hệ thống xử lý tài liệu - Gateway API đang hoạt động",
        "version": settings.PROJECT_VERSION,
        "services": {
            "word": f"{settings.WORD_SERVICE_URL}",
            "excel": f"{settings.EXCEL_SERVICE_URL}",
            "pdf": f"{settings.PDF_SERVICE_URL}",
            "files": f"{settings.FILES_SERVICE_URL}",
            "user": f"{settings.USER_SERVICE_URL}"
        }
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG_MODE,
        workers=settings.WORKERS
    )