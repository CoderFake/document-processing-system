from fastapi import APIRouter
from api.v1.endpoints import word_docs, excel_docs, pdf_docs, files_service, auth, dashboard

api_router = APIRouter()

api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"]
)

api_router.include_router(
    dashboard.router,
    tags=["Dashboard"]
)

# Thêm router cho User Service để định tuyến tới các endpoint trong service-user
api_router.include_router(
    auth.router,
    prefix="/user",
    tags=["User Service"]
)

# Không thêm route trực tiếp nữa - các route này sẽ sử dụng qua prefix "/files"
# từ router files_service được đăng ký ở cuối file

api_router.include_router(
    word_docs.router,
    prefix="/word",
    tags=["Word Documents"]
)

api_router.include_router(
    excel_docs.router,
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