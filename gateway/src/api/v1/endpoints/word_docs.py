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
word_service = ServiceClient(settings.WORD_SERVICE_URL)


@router.get("/", summary="Lấy danh sách tài liệu Word")
async def get_word_documents(
        skip: int = 0,
        limit: int = 10,
        search: Optional[str] = None
):
    """
    Lấy danh sách tài liệu Word từ hệ thống.
    """
    params = {"skip": skip, "limit": limit}
    if search:
        params["search"] = search

    response = await word_service.get("/documents", params=params)
    return response


@router.post("/upload", summary="Tải lên tài liệu Word mới")
async def upload_word_document(
        file: UploadFile = File(...),
        title: Optional[str] = Form(None),
        description: Optional[str] = Form(None),
        background_tasks: BackgroundTasks = None
):
    """
    Tải lên tài liệu Word mới vào hệ thống.
    """
    # Kiểm tra loại file
    if not file.filename.endswith(('.doc', '.docx')):
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận file .doc hoặc .docx")

    # Upload file
    response = await word_service.upload_file(
        "/documents/upload",
        file=file,
        data={"title": title, "description": description}
    )

    return response


@router.post("/convert/to-pdf", summary="Chuyển đổi tài liệu Word sang PDF")
async def convert_word_to_pdf(
        file: UploadFile = File(...),
        background_tasks: BackgroundTasks = None
):
    """
    Chuyển đổi tài liệu Word sang định dạng PDF.
    """
    # Kiểm tra loại file
    if not file.filename.endswith(('.doc', '.docx')):
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận file .doc hoặc .docx")

    # Gửi yêu cầu chuyển đổi
    response = await word_service.upload_file(
        "/documents/convert/to-pdf",
        file=file
    )

    return response


@router.post("/templates/apply", summary="Áp dụng mẫu tài liệu Word")
async def apply_word_template(
        template_id: str = Form(...),
        data: str = Form(...),
        output_format: str = Form("docx")
):
    """
    Áp dụng mẫu tài liệu Word với dữ liệu được cung cấp.

    - **template_id**: ID của mẫu tài liệu
    - **data**: Dữ liệu JSON cho mẫu (dạng chuỗi JSON)
    - **output_format**: Định dạng đầu ra (docx, pdf)
    """
    # Gửi yêu cầu áp dụng mẫu
    response = await word_service.post(
        "/documents/templates/apply",
        json={
            "template_id": template_id,
            "data": data,
            "output_format": output_format
        }
    )

    return response


@router.post("/watermark", summary="Thêm watermark vào tài liệu Word")
async def add_watermark_to_word(
        file: UploadFile = File(...),
        watermark_text: str = Form(...),
        position: str = Form("center"),
        opacity: float = Form(0.5)
):
    """
    Thêm watermark vào tài liệu Word.

    - **file**: Tài liệu Word cần thêm watermark
    - **watermark_text**: Nội dung watermark
    - **position**: Vị trí của watermark (center, top-left, top-right, bottom-left, bottom-right)
    - **opacity**: Độ mờ của watermark (0.0 - 1.0)
    """
    # Kiểm tra loại file
    if not file.filename.endswith(('.doc', '.docx')):
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận file .doc hoặc .docx")

    # Gửi yêu cầu thêm watermark
    response = await word_service.upload_file(
        "/documents/watermark",
        file=file,
        data={
            "watermark_text": watermark_text,
            "position": position,
            "opacity": str(opacity)
        }
    )

    return response


@router.get("/templates", summary="Lấy danh sách mẫu tài liệu Word")
async def get_word_templates(
        category: Optional[str] = None,
        skip: int = 0,
        limit: int = 10
):
    """
    Lấy danh sách mẫu tài liệu Word từ hệ thống.
    """
    params = {"skip": skip, "limit": limit}
    if category:
        params["category"] = category

    response = await word_service.get("/documents/templates", params=params)
    return response


@router.get("/download/{document_id}", summary="Tải xuống tài liệu Word")
async def download_word_document(document_id: str):
    """
    Tải xuống tài liệu Word theo ID.
    """
    # Gửi yêu cầu tải xuống
    return await word_service.get_file(f"/documents/download/{document_id}")


@router.delete("/{document_id}", summary="Xóa tài liệu Word")
async def delete_word_document(document_id: str):
    """
    Xóa tài liệu Word theo ID.
    """
    response = await word_service.delete(f"/documents/{document_id}")
    return response


@router.post("/batch", summary="Tạo nhiều tài liệu Word từ template")
async def create_batch_word_documents(
        template_id: str = Form(...),
        data_file: UploadFile = File(...),
        output_format: str = Form("docx")
):
    """
    Tạo nhiều tài liệu Word từ một template và tập dữ liệu (CSV, Excel).

    - **template_id**: ID của mẫu tài liệu
    - **data_file**: File dữ liệu CSV hoặc Excel
    - **output_format**: Định dạng đầu ra (docx, pdf, zip)
    """
    # Kiểm tra loại file
    if not data_file.filename.endswith(('.csv', '.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận file .csv, .xlsx hoặc .xls")

    response = await word_service.upload_file(
        "/documents/templates/batch",
        file=data_file,
        data={
            "template_id": template_id,
            "output_format": output_format
        }
    )

    return response