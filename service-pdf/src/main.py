from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
from core.config import settings
from api.routes import router as api_router
from infrastructure.database import init_db, async_session_factory


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.PROJECT_VERSION,
    docs_url="/api/v1/pdf/docs",
    redoc_url="/api/v1/pdf/redoc",
    openapi_url="/api/v1/pdf/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS if isinstance(settings.ALLOWED_ORIGINS, list) else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

@app.on_event("startup")
async def startup_event():
    logger.info("Starting up PDF service...")
    await init_db()
    app.state.db_pool = async_session_factory
    logger.info("PDF service started successfully with DB pool initialized.")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down PDF service...")
    logger.info("PDF service shut down gracefully.")

@app.get(settings.API_V1_STR + "/pdf", tags=["Root"])
async def root():
    return {
        "message": f"{settings.PROJECT_NAME} - PDF/PNG Document Service is active",
        "version": settings.PROJECT_VERSION
    }

@app.get(settings.API_V1_STR + "/pdf/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service_name": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION
    }

if __name__ == "__main__":
    logger.info(f"Starting Uvicorn for {settings.PROJECT_NAME} on {settings.HOST}:{settings.PORT}")
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG_MODE,
        workers=settings.WORKERS,
        log_level="info"
    )