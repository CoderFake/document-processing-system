from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Query
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from typing import List, Optional, Dict, Any
import logging
from core.config import settings
from utils.client import ServiceClient
from api.v1.endpoints.auth import get_current_user

router = APIRouter(prefix="/excel", tags=["Excel Documents"])
excel_service = ServiceClient(settings.EXCEL_SERVICE_URL)
logger = logging.getLogger(__name__)

@router.get("/", summary="Lấy danh sách tài liệu Excel")
async def get_excel_documents(
        skip: int = 0,
        limit: int = 10,
        search: Optional[str] = None,
        current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Lấy danh sách tài liệu Excel từ hệ thống.
    """
    headers = {"X-User-ID": str(current_user["id"])}
    params = {"skip": skip, "limit": limit}
    if search:
        params["search"] = search

    response = await excel_service.get("/documents", params=params, headers=headers)
    return response


@router.post("/upload", summary="Tải lên tài liệu Excel mới")
async def upload_excel_document(
        file: UploadFile = File(...),
        title: Optional[str] = Form(None),
        description: Optional[str] = Form(None),
        current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Tải lên tài liệu Excel mới vào hệ thống.
    """
    if not file.filename.endswith(('.xls', '.xlsx')):
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận file .xls hoặc .xlsx")

    headers = {"X-User-ID": str(current_user["id"])}
    data_payload = {}
    if title:
        data_payload["title"] = title
    if description:
        data_payload["description"] = description

    response = await excel_service.upload_file(
        "/documents/upload",
        file=file,
        data=data_payload,
        headers=headers
    )
    return response


@router.post("/convert/to-pdf", summary="Chuyển đổi tài liệu Excel sang PDF")
async def convert_excel_to_pdf(
        file: UploadFile = File(...),
        current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Chuyển đổi tài liệu Excel sang định dạng PDF.
    """
    if not file.filename.endswith(('.xls', '.xlsx')):
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận file .xls hoặc .xlsx")

    headers = {"X-User-ID": str(current_user["id"])}
    response = await excel_service.upload_file(
        "/documents/convert/to-pdf",
        file=file,
        data={},
        headers=headers
    )
    return response


@router.post("/convert/to-word", summary="Chuyển đổi tài liệu Excel sang Word")
async def convert_excel_to_word(
        file: UploadFile = File(...),
        current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Chuyển đổi tài liệu Excel sang định dạng Word.
    """
    if not file.filename.endswith(('.xls', '.xlsx')):
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận file .xls hoặc .xlsx")
    
    headers = {"X-User-ID": str(current_user["id"])}
    response = await excel_service.upload_file(
        "/documents/convert/to-word",
        file=file,
        data={},
        headers=headers
    )
    return response


@router.post("/merge", summary="Gộp nhiều file Excel thành một")
async def merge_excel_files(
        files: List[UploadFile] = File(...),
        output_filename: str = Form(...),
        current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Gộp nhiều file Excel thành một file duy nhất.

    - **files**: Danh sách các file Excel cần gộp
    - **output_filename**: Tên file kết quả
    """
    for file_item in files:
        if not file_item.filename.endswith(('.xls', '.xlsx')):
            raise HTTPException(status_code=400, detail=f"File {file_item.filename} không phải là file Excel (.xls, .xlsx)")

    headers = {"X-User-ID": str(current_user["id"])}
    data_payload = {
        "output_filename": output_filename,
    }
    response = await excel_service.upload_files(
        "/documents/merge",
        files=files,
        data=data_payload,
        headers=headers
    )
    return response


@router.get("/templates", summary="Lấy danh sách mẫu tài liệu Excel")
async def get_excel_templates(
        category: Optional[str] = None,
        skip: int = 0,
        limit: int = 10,
        current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Lấy danh sách mẫu tài liệu Excel từ hệ thống.
    """
    headers = {"X-User-ID": str(current_user["id"])}
    params = {"skip": skip, "limit": limit}
    if category:
        params["category"] = category

    response = await excel_service.get("/documents/templates", params=params, headers=headers)
    return response


@router.post("/templates/apply", summary="Áp dụng mẫu tài liệu Excel")
async def apply_excel_template(
        template_id: str = Form(...),
        data: str = Form(...),
        output_format: str = Form("xlsx"),
        current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Áp dụng mẫu tài liệu Excel với dữ liệu được cung cấp.

    - **template_id**: ID của mẫu tài liệu
    - **data**: Dữ liệu JSON cho mẫu (dạng chuỗi JSON)
    - **output_format**: Định dạng đầu ra (xlsx, pdf)
    """
    headers = {"X-User-ID": str(current_user["id"])}
    json_payload = {
        "template_id": template_id,
        "data": data,
        "output_format": output_format,
    }
    response = await excel_service.post(
        "/documents/templates/apply",
        json_data=json_payload,
        headers=headers
    )
    return response


@router.get("/download/{document_id}", summary="Tải xuống tài liệu Excel")
async def download_excel_document(
    document_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Tải xuống tài liệu Excel theo ID.
    """
    headers = {"X-User-ID": str(current_user["id"])}
    response = await excel_service.get_file(f"/documents/download/{document_id}", headers=headers)
    return response


@router.delete("/{document_id}", summary="Xóa tài liệu Excel")
async def delete_excel_document(
    document_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Xóa tài liệu Excel theo ID.
    """
    headers = {"X-User-ID": str(current_user["id"])}
    response = await excel_service.delete(f"/documents/{document_id}", headers=headers)
    return response