from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Depends, Query
from fastapi.responses import JSONResponse, FileResponse
import httpx
from typing import List, Optional, Dict, Any
import os
import tempfile
import shutil
from core.config import settings
from utils.client import ServiceClient

router = APIRouter()
excel_service = ServiceClient(settings.EXCEL_SERVICE_URL)


@router.get("/", summary="Lấy danh sách tài liệu Excel")
async def get_excel_documents(
        skip: int = 0,
        limit: int = 10,
        search: Optional[str] = None
):
    """
    Lấy danh sách tài liệu Excel từ hệ thống.
    """
    params = {"skip": skip, "limit": limit}
    if search:
        params["search"] = search

    response = await excel_service.get("/documents", params=params)
    return response


@router.post("/upload", summary="Tải lên tài liệu Excel mới")
async def upload_excel_document(
        file: UploadFile = File(...),
        title: Optional[str] = Form(None),
        description: Optional[str] = Form(None),
        background_tasks: BackgroundTasks = None
):
    """
    Tải lên tài liệu Excel mới vào hệ thống.
    """
    if not file.filename.endswith(('.xls', '.xlsx')):
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận file .xls hoặc .xlsx")

    response = await excel_service.upload_file(
        "/documents/upload",
        file=file,
        data={"title": title, "description": description}
    )

    return response


@router.post("/convert/to-pdf", summary="Chuyển đổi tài liệu Excel sang PDF")
async def convert_excel_to_pdf(
        file: UploadFile = File(...),
        background_tasks: BackgroundTasks = None
):
    """
    Chuyển đổi tài liệu Excel sang định dạng PDF.
    """
    if not file.filename.endswith(('.xls', '.xlsx')):
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận file .xls hoặc .xlsx")

    response = await excel_service.upload_file(
        "/documents/convert/to-pdf",
        file=file
    )

    return response


@router.post("/convert/to-word", summary="Chuyển đổi tài liệu Excel sang Word")
async def convert_excel_to_word(
        file: UploadFile = File(...),
        background_tasks: BackgroundTasks = None
):
    """
    Chuyển đổi tài liệu Excel sang định dạng Word.
    """
    if not file.filename.endswith(('.xls', '.xlsx')):
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận file .xls hoặc .xlsx")
    response = await excel_service.upload_file(
        "/documents/convert/to-word",
        file=file
    )

    return response


@router.post("/merge", summary="Gộp nhiều file Excel thành một")
async def merge_excel_files(
        files: List[UploadFile] = File(...),
        output_filename: str = Form(...),
        background_tasks: BackgroundTasks = None
):
    """
    Gộp nhiều file Excel thành một file duy nhất.

    - **files**: Danh sách các file Excel cần gộp
    - **output_filename**: Tên file kết quả
    """
    for file in files:
        if not file.filename.endswith(('.xls', '.xlsx')):
            raise HTTPException(status_code=400, detail=f"File {file.filename} không phải là file Excel (.xls, .xlsx)")

    response = await excel_service.upload_files(
        "/documents/merge",
        files=files,
        data={"output_filename": output_filename}
    )

    return response


@router.get("/templates", summary="Lấy danh sách mẫu tài liệu Excel")
async def get_excel_templates(
        category: Optional[str] = None,
        skip: int = 0,
        limit: int = 10
):
    """
    Lấy danh sách mẫu tài liệu Excel từ hệ thống.
    """
    params = {"skip": skip, "limit": limit}
    if category:
        params["category"] = category

    response = await excel_service.get("/documents/templates", params=params)
    return response


@router.post("/templates/apply", summary="Áp dụng mẫu tài liệu Excel")
async def apply_excel_template(
        template_id: str = Form(...),
        data: str = Form(...),
        output_format: str = Form("xlsx")
):
    """
    Áp dụng mẫu tài liệu Excel với dữ liệu được cung cấp.

    - **template_id**: ID của mẫu tài liệu
    - **data**: Dữ liệu JSON cho mẫu (dạng chuỗi JSON)
    - **output_format**: Định dạng đầu ra (xlsx, pdf)
    """
    response = await excel_service.post(
        "/documents/templates/apply",
        json={
            "template_id": template_id,
            "data": data,
            "output_format": output_format
        }
    )

    return response


@router.get("/download/{document_id}", summary="Tải xuống tài liệu Excel")
async def download_excel_document(document_id: str):
    """
    Tải xuống tài liệu Excel theo ID.
    """
    return await excel_service.get_file(f"/documents/download/{document_id}")


@router.delete("/{document_id}", summary="Xóa tài liệu Excel")
async def delete_excel_document(document_id: str):
    """
    Xóa tài liệu Excel theo ID.
    """
    response = await excel_service.delete(f"/documents/{document_id}")
    return response