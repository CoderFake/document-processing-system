from fastapi import APIRouter, HTTPException, status
import httpx
from core.config import settings
import asyncio

health_router = APIRouter()


@health_router.get("/", summary="Kiểm tra trạng thái hệ thống")
async def health_check():
    service_urls = {
        "word_service": f"{settings.WORD_SERVICE_URL}/health",
        "excel_service": f"{settings.EXCEL_SERVICE_URL}/health",
        "pdf_service": f"{settings.PDF_SERVICE_URL}/health",
        "files_service": f"{settings.FILES_SERVICE_URL}/health",
        "user_service": f"{settings.USER_SERVICE_URL}/health"
    }

    services_health = {}

    async with httpx.AsyncClient(timeout=5.0) as client:
        for service_name, url in service_urls.items():
            try:
                response = await client.get(url)
                services_health[service_name] = {
                    "status": "up" if response.status_code == 200 else "down",
                    "details": response.json() if response.status_code == 200 else {"error": "Service unreachable"}
                }
            except Exception as e:
                services_health[service_name] = {
                    "status": "down",
                    "details": {"error": str(e)}
                }

    all_up = all(service["status"] == "up" for service in services_health.values())

    return {
        "status": "healthy" if all_up else "degraded",
        "gateway": {
            "status": "up",
            "version": settings.PROJECT_VERSION
        },
        "services": services_health
    }