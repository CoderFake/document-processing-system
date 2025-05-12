from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Depends, Query, Path
from fastapi.responses import JSONResponse, StreamingResponse
from typing import List, Optional, Dict, Any
import os
import tempfile
from core.config import settings
from utils.client import ServiceClient
from api.v1.endpoints.auth import get_current_user

router = APIRouter()

files_service = ServiceClient(settings.FILES_SERVICE_URL)


@router.get("/archives", summary="Lấy danh sách tệp nén")
async def get_archives(
    skip: int = 0,
    limit: int = 10,
    search: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Lấy danh sách tệp nén từ hệ thống.
    """
    params = {
        "skip": skip, 
        "limit": limit,
        "user_id": current_user["id"]
    }
    if search:
        params["search"] = search

    response = await files_service.get("/archives", params=params)
    return response


@router.post("/archives/upload", summary="Tải lên tệp nén mới")
async def upload_archive(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Tải lên tệp nén mới vào hệ thống.
    """
    data = {
        "user_id": str(current_user["id"])
    }
    if title:
        data["title"] = title
    if description:
        data["description"] = description

    response = await files_service.upload_file("/archives/upload", file, data)
    return response


@router.post("/compress", summary="Nén nhiều tệp")
async def compress_files(
    file_ids: List[str] = Form(...),
    output_filename: str = Form(...),
    archive_format: str = Form("zip"),
    password: Optional[str] = Form(None),
    compression_level: Optional[int] = Form(6),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Nén nhiều tệp thành một tệp nén.
    """
    data = {
        "file_ids": ",".join(file_ids),
        "output_filename": output_filename,
        "archive_format": archive_format,
        "compression_level": str(compression_level),
        "user_id": str(current_user["id"])
    }
    
    if password:
        data["password"] = password

    response = await files_service.post("/compress", data)
    return response


@router.post("/decompress", summary="Giải nén tệp")
async def decompress_archive(
    archive_id: str = Form(...),
    password: Optional[str] = Form(None),
    extract_all: bool = Form(True),
    file_paths: Optional[List[str]] = Form(None),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Giải nén tệp nén.
    """
    data = {
        "archive_id": archive_id,
        "extract_all": str(extract_all),
        "user_id": str(current_user["id"])
    }
    
    if password:
        data["password"] = password
    
    if file_paths:
        data["file_paths"] = ",".join(file_paths)

    response = await files_service.post("/decompress", data)
    return response


@router.post("/crack", summary="Crack mật khẩu tệp nén")
async def crack_archive_password(
    archive_id: str = Form(...),
    max_length: int = Form(6),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Thử crack mật khẩu tệp nén.
    """
    data = {
        "archive_id": archive_id,
        "max_length": str(max_length),
        "user_id": str(current_user["id"])
    }

    response = await files_service.post("/crack", data)
    return response


@router.get("/archives/download/{archive_id}", summary="Tải xuống tệp nén")
async def download_archive(
    archive_id: str = Path(..., description="ID của tệp nén"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Tải xuống tệp nén theo ID.
    """
    response = await files_service.get_file(f"/archives/download/{archive_id}?user_id={current_user['id']}")
    return response


@router.delete("/archives/{archive_id}", summary="Xóa tệp nén")
async def delete_archive(
    archive_id: str = Path(..., description="ID của tệp nén"),
    permanent: bool = Query(False, description="Xóa vĩnh viễn hay chuyển vào thùng rác"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Xóa tệp nén theo ID.
    """
    response = await files_service.delete(f"/archives/{archive_id}?permanent={permanent}&user_id={current_user['id']}")
    return response


@router.get("/status/compress/{task_id}", summary="Kiểm tra trạng thái nén tệp")
async def get_compress_status(
    task_id: str = Path(..., description="ID của tác vụ nén"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Kiểm tra trạng thái nén tệp.
    """
    response = await files_service.get(f"/status/compress/{task_id}?user_id={current_user['id']}")
    return response


@router.get("/status/decompress/{task_id}", summary="Kiểm tra trạng thái giải nén")
async def get_decompress_status(
    task_id: str = Path(..., description="ID của tác vụ giải nén"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Kiểm tra trạng thái giải nén.
    """
    response = await files_service.get(f"/status/decompress/{task_id}?user_id={current_user['id']}")
    return response


@router.get("/status/crack/{task_id}", summary="Kiểm tra trạng thái crack mật khẩu")
async def get_crack_status(
    task_id: str = Path(..., description="ID của tác vụ crack mật khẩu"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Kiểm tra trạng thái crack mật khẩu.
    """
    response = await files_service.get(f"/status/crack/{task_id}?user_id={current_user['id']}")
    return response 