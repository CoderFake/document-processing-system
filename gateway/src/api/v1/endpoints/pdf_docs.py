from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Query
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from typing import List, Optional, Dict, Any
import logging
from core.config import settings
from utils.client import ServiceClient
from api.v1.endpoints.auth import get_current_user

router = APIRouter()
pdf_service = ServiceClient(settings.PDF_SERVICE_URL)
logger = logging.getLogger(__name__)

@router.get("/", summary="Lấy danh sách tài liệu PDF")
async def get_pdf_documents(
        skip: int = 0,
        limit: int = 10,
        search: Optional[str] = None,
        current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Lấy danh sách tài liệu PDF từ hệ thống.
    """
    headers = {"X-User-ID": str(current_user["id"])}
    params = {"skip": skip, "limit": limit}
    if search:
        params["search"] = search

    response = await pdf_service.get("/documents", params=params, headers=headers)
    return response

@router.post("/upload", summary="Tải lên tài liệu PDF mới")
async def upload_pdf_document(
        file: UploadFile = File(...),
        title: Optional[str] = Form(None),
        description: Optional[str] = Form(None),
        current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Tải lên tài liệu PDF mới vào hệ thống.
    """

    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận file .pdf")

    headers = {"X-User-ID": str(current_user["id"])}
    data_payload = {}
    if title:
        data_payload["title"] = title
    if description:
        data_payload["description"] = description

    response = await pdf_service.upload_file(
        "/documents/upload",
        file=file,
        data=data_payload,
        headers=headers
    )

    return response

@router.post("/convert/to-word", summary="Chuyển đổi tài liệu PDF sang Word")
async def convert_pdf_to_word(
        file: UploadFile = File(...),
        current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Chuyển đổi tài liệu PDF sang định dạng Word.
    """

    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận file .pdf")

    headers = {"X-User-ID": str(current_user["id"])}
    response = await pdf_service.upload_file(
        "/documents/convert/to-word",
        file=file,
        data={},
        headers=headers
    )

    return response

@router.post("/encrypt", summary="Mã hóa tài liệu PDF")
async def encrypt_pdf(
        file: UploadFile = File(...),
        password: str = Form(...),
        current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Mã hóa tài liệu PDF với mật khẩu.

    - **file**: Tài liệu PDF cần mã hóa
    - **password**: Mật khẩu để bảo vệ tài liệu
    """

    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận file .pdf")

    headers = {"X-User-ID": str(current_user["id"])}
    data_payload = {
        "password": password,
    }
    response = await pdf_service.upload_file(
        "/documents/encrypt",
        file=file,
        data=data_payload,
        headers=headers
    )

    return response

@router.post("/decrypt", summary="Giải mã tài liệu PDF")
async def decrypt_pdf(
        file: UploadFile = File(...),
        password: str = Form(...),
        current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Giải mã tài liệu PDF có bảo vệ.

    - **file**: Tài liệu PDF cần giải mã
    - **password**: Mật khẩu bảo vệ tài liệu
    """

    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận file .pdf")

    headers = {"X-User-ID": str(current_user["id"])}
    data_payload = {
        "password": password,
    }
    response = await pdf_service.upload_file(
        "/documents/decrypt",
        file=file,
        data=data_payload,
        headers=headers
    )

    return response

@router.post("/crack", summary="Crack mật khẩu tài liệu PDF (Brute-force)")
async def crack_pdf_password(
        file: UploadFile = File(...),
        current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Thử crack mật khẩu tài liệu PDF sử dụng phương pháp brute-force.

    - **file**: Tài liệu PDF cần crack mật khẩu
    """

    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận file .pdf")

    headers = {"X-User-ID": str(current_user["id"])}
    response = await pdf_service.upload_file(
        "/documents/crack",
        file=file,
        data={},
        headers=headers
    )

    return response

@router.post("/watermark", summary="Thêm watermark vào tài liệu PDF")
async def add_watermark_to_pdf(
        file: UploadFile = File(...),
        watermark_text: str = Form(...),
        position: str = Form("center"),
        opacity: float = Form(0.5),
        current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Thêm watermark vào tài liệu PDF.

    - **file**: Tài liệu PDF cần thêm watermark
    - **watermark_text**: Nội dung watermark
    - **position**: Vị trí của watermark (center, top-left, top-right, bottom-left, bottom-right)
    - **opacity**: Độ mờ của watermark (0.0 - 1.0)
    """

    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận file .pdf")

    headers = {"X-User-ID": str(current_user["id"])}
    data_payload = {
        "watermark_text": watermark_text,
        "position": position,
        "opacity": str(opacity),
    }
    response = await pdf_service.upload_file(
        "/documents/watermark",
        file=file,
        data=data_payload,
        headers=headers
    )

    return response

@router.post("/sign", summary="Chèn chữ ký vào tài liệu PDF")
async def add_signature_to_pdf(
        file: UploadFile = File(...),
        signature_file: Optional[UploadFile] = File(None),
        signature_position: str = Form("bottom-right"),
        page_number: int = Form(-1),
        current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Thêm chữ ký hình ảnh vào tài liệu PDF.

    - **file**: Tài liệu PDF cần thêm chữ ký
    - **signature_file**: File hình ảnh chữ ký (PNG, JPG)
    - **signature_position**: Vị trí của chữ ký (bottom-right, bottom-left, top-right, top-left, custom)
    - **page_number**: Số trang cần thêm chữ ký (-1 cho trang cuối cùng, 0 cho tất cả các trang, 1-indexed cho trang cụ thể)
    """

    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận file PDF")

    if signature_file and not signature_file.filename.endswith(('.png', '.jpg', '.jpeg')):
        raise HTTPException(status_code=400, detail="Chữ ký chỉ chấp nhận file PNG hoặc JPG")

    headers = {"X-User-ID": str(current_user["id"])}
    data_payload = {
        "signature_position": signature_position,
        "page_number": str(page_number),
    }
    files_payload = {"file": file}
    if signature_file:
        files_payload["signature_file"] = signature_file

    response = await pdf_service.upload_files(
        "/documents/sign",
        files=files_payload,
        data=data_payload,
        headers=headers
    )

    return response

@router.post("/merge", summary="Gộp nhiều file PDF thành một")
async def merge_pdf_files(
        files: List[UploadFile] = File(...),
        output_filename: str = Form(...),
        current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Gộp nhiều file PDF thành một file duy nhất.

    - **files**: Danh sách các file PDF cần gộp
    - **output_filename**: Tên file kết quả (tùy chọn, service có thể tự sinh nếu không có)
    """

    for file_item in files:
        if not file_item.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail=f"File {file_item.filename} không phải là file PDF")

    headers = {"X-User-ID": str(current_user["id"])}
    data_payload = {
        "output_filename": output_filename,
    }
    response = await pdf_service.upload_files(
        "/documents/merge",
        files=files,
        data=data_payload,
        headers=headers
    )

    return response

@router.get("/download/{document_id}", summary="Tải xuống tài liệu PDF")
async def download_pdf_document(
    document_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Tải xuống tài liệu PDF theo ID.
    """
    headers = {"X-User-ID": str(current_user["id"])}
    response = await pdf_service.get_file(f"/documents/download/{document_id}", headers=headers)
    return response

@router.delete("/{document_id}", summary="Xóa tài liệu PDF")
async def delete_pdf_document(
    document_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Xóa tài liệu PDF theo ID.
    """
    headers = {"X-User-ID": str(current_user["id"])}
    response = await pdf_service.delete(f"/documents/{document_id}", headers=headers)
    return response