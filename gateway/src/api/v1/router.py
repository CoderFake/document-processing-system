from fastapi import APIRouter
from api.v1.endpoints import word_docs, excel_docs, pdf_docs, files_service, auth

api_router = APIRouter()

api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"]
)

api_router.include_router(
    word_docs.router,
    prefix="/word",
    tags=["Word Documents"]
)

api_router.include_router(
    excel_docs.router,
    prefix="/excel",
    tags=["Excel Documents"]
)

api_router.include_router(
    pdf_docs.router,
    prefix="/pdf",
    tags=["PDF Documents"]
)

api_router.include_router(
    files_service.router,
    prefix="/files",
    tags=["Archive Files"]
)