from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Depends, Query, Path
from fastapi.responses import JSONResponse, FileResponse
from typing import List, Optional, Dict, Any
import os
import tempfile
import shutil
from datetime import datetime
import uuid

from domain.models import FileInfo, ArchiveInfo
from application.dto import CreateFileDTO, CreateArchiveDTO, CompressFilesDTO, DecompressArchiveDTO, CrackArchivePasswordDTO, CleanupFilesDTO, RestoreTrashDTO
from application.services import FileService, ArchiveService, TrashService
from infrastructure.repository import FileRepository, ArchiveRepository, CompressJobRepository, DecompressJobRepository, CrackJobRepository, CleanupJobRepository, TrashRepository
from infrastructure.minio_client import MinioClient
from infrastructure.rabbitmq_client import RabbitMQClient
from domain.exceptions import FileNotFoundException, ArchiveNotFoundException, PasswordProtectedException, WrongPasswordException

router = APIRouter()


def get_file_service():
    minio_client = MinioClient()
    rabbitmq_client = RabbitMQClient()
    file_repo = FileRepository(minio_client)
    return FileService(file_repo, minio_client, rabbitmq_client)


def get_archive_service():
    minio_client = MinioClient()
    rabbitmq_client = RabbitMQClient()
    archive_repo = ArchiveRepository(minio_client)
    compress_repo = CompressJobRepository()
    decompress_repo = DecompressJobRepository()
    crack_repo = CrackJobRepository()
    file_repo = FileRepository(minio_client)
    return ArchiveService(archive_repo, compress_repo, decompress_repo, crack_repo, file_repo, minio_client, rabbitmq_client)


def get_trash_service():
    minio_client = MinioClient()
    rabbitmq_client = RabbitMQClient()
    trash_repo = TrashRepository()
    cleanup_repo = CleanupJobRepository()
    file_repo = FileRepository(minio_client)
    archive_repo = ArchiveRepository(minio_client)
    return TrashService(trash_repo, cleanup_repo, file_repo, archive_repo, minio_client, rabbitmq_client)


@router.get("/files", summary="Lấy danh sách tệp")
async def get_files(
    skip: int = 0,
    limit: int = 10,
    search: Optional[str] = None,
    file_service: FileService = Depends(get_file_service)
):
    """
    Lấy danh sách tệp từ hệ thống.
    """
    try:
        files = await file_service.get_files(skip, limit, search)
        return {"items": files, "total": len(files)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/files/upload", summary="Tải lên tệp mới")
async def upload_file(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    background_tasks: BackgroundTasks = None,
    file_service: FileService = Depends(get_file_service)
):
    """
    Tải lên tệp mới vào hệ thống.
    """
    try:
        file_dto = CreateFileDTO(
            title=title or os.path.splitext(file.filename)[0],
            description=description or "",
            original_filename=file.filename
        )

        content = await file.read()

        file_info = await file_service.create_file(file_dto, content)

        return {
            "id": file_info.id,
            "title": file_info.title,
            "description": file_info.description,
            "created_at": file_info.created_at.isoformat(),
            "file_size": file_info.file_size,
            "file_type": file_info.file_type,
            "original_filename": file_info.original_filename
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/archives", summary="Lấy danh sách tệp nén")
async def get_archives(
    skip: int = 0,
    limit: int = 10,
    search: Optional[str] = None,
    archive_service: ArchiveService = Depends(get_archive_service)
):
    """
    Lấy danh sách tệp nén từ hệ thống.
    """
    try:
        archives = await archive_service.get_archives(skip, limit, search)
        return {"items": archives, "total": len(archives)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/archives/upload", summary="Tải lên tệp nén mới")
async def upload_archive(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    background_tasks: BackgroundTasks = None,
    archive_service: ArchiveService = Depends(get_archive_service)
):
    """
    Tải lên tệp nén mới vào hệ thống.
    """
    try:
        if not file.filename.endswith(('.zip', '.7z', '.rar')):
            raise HTTPException(status_code=400, detail="Chỉ chấp nhận file .zip, .7z hoặc .rar")

        compression_type = os.path.splitext(file.filename)[1][1:]

        archive_dto = CreateArchiveDTO(
            title=title or os.path.splitext(file.filename)[0],
            description=description or "",
            original_filename=file.filename,
            compression_type=compression_type
        )

        content = await file.read()

        archive_info = await archive_service.create_archive(archive_dto, content)

        if background_tasks:
            background_tasks.add_task(
                archive_service.analyze_archive,
                archive_info.id
            )

        return {
            "id": archive_info.id,
            "title": archive_info.title,
            "description": archive_info.description,
            "created_at": archive_info.created_at.isoformat(),
            "file_size": archive_info.file_size,
            "file_type": archive_info.file_type,
            "compression_type": archive_info.compression_type,
            "is_encrypted": archive_info.is_encrypted,
            "original_filename": archive_info.original_filename
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compress", summary="Nén nhiều tệp")
async def compress_files(
    file_ids: List[str] = Form(...),
    output_filename: str = Form(...),
    compression_type: str = Form("zip"),
    password: Optional[str] = Form(None),
    background_tasks: BackgroundTasks = None,
    archive_service: ArchiveService = Depends(get_archive_service)
):
    """
    Nén nhiều tệp thành một tệp nén.
    """
    try:
        compress_dto = CompressFilesDTO(
            file_ids=file_ids,
            output_filename=output_filename,
            compression_type=compression_type,
            password=password
        )

        task_id = str(uuid.uuid4())

        if background_tasks:
            background_tasks.add_task(
                archive_service.compress_files_async,
                task_id,
                compress_dto
            )

        return {
            "status": "processing",
            "message": "Yêu cầu nén tệp đã được gửi đi",
            "task_id": task_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/decompress", summary="Giải nén tệp")
async def decompress_archive(
    archive_id: str = Form(...),
    password: Optional[str] = Form(None),
    extract_all: bool = Form(True),
    file_paths: Optional[List[str]] = Form(None),
    background_tasks: BackgroundTasks = None,
    archive_service: ArchiveService = Depends(get_archive_service)
):
    """
    Giải nén tệp nén.
    """
    try:
        decompress_dto = DecompressArchiveDTO(
            archive_id=archive_id,
            password=password,
            extract_all=extract_all,
            file_paths=file_paths
        )

        task_id = str(uuid.uuid4())

        if background_tasks:
            background_tasks.add_task(
                archive_service.decompress_archive_async,
                task_id,
                decompress_dto
            )

        return {
            "status": "processing",
            "message": "Yêu cầu giải nén tệp đã được gửi đi",
            "task_id": task_id
        }
    except ArchiveNotFoundException:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy tệp nén với ID: {archive_id}")
    except PasswordProtectedException:
        raise HTTPException(status_code=400, detail="Tệp nén được bảo vệ bằng mật khẩu. Vui lòng cung cấp mật khẩu.")
    except WrongPasswordException:
        raise HTTPException(status_code=400, detail="Mật khẩu không đúng.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/crack", summary="Crack mật khẩu tệp nén")
async def crack_archive_password(
    archive_id: str = Form(...),
    max_length: int = Form(6),
    background_tasks: BackgroundTasks = None,
    archive_service: ArchiveService = Depends(get_archive_service)
):
    """
    Thử crack mật khẩu tệp nén.
    """
    try:
        crack_dto = CrackArchivePasswordDTO(
            archive_id=archive_id,
            max_length=max_length
        )

        task_id = str(uuid.uuid4())

        if background_tasks:
            background_tasks.add_task(
                archive_service.crack_archive_password_async,
                task_id,
                crack_dto
            )

        return {
            "status": "processing",
            "message": "Yêu cầu crack mật khẩu đã được gửi đi",
            "task_id": task_id
        }
    except ArchiveNotFoundException:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy tệp nén với ID: {archive_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cleanup", summary="Dọn dẹp tệp cũ")
async def cleanup_files(
    days: int = Form(30),
    file_types: Optional[List[str]] = Form(None),
    background_tasks: BackgroundTasks = None,
    trash_service: TrashService = Depends(get_trash_service)
):
    """
    Dọn dẹp tệp cũ và chuyển vào thùng rác.
    """
    try:
        cleanup_dto = CleanupFilesDTO(
            days=days,
            file_types=file_types
        )

        task_id = str(uuid.uuid4())

        if background_tasks:
            background_tasks.add_task(
                trash_service.cleanup_files_async,
                task_id,
                cleanup_dto
            )

        return {
            "status": "processing",
            "message": "Yêu cầu dọn dẹp tệp đã được gửi đi",
            "task_id": task_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trash", summary="Lấy danh sách tệp trong thùng rác")
async def get_trash_files(
    skip: int = 0,
    limit: int = 10,
    trash_service: TrashService = Depends(get_trash_service)
):
    """
    Lấy danh sách tệp trong thùng rác.
    """
    try:
        trash_files = await trash_service.get_trash_files(skip, limit)
        return {"items": trash_files, "total": len(trash_files)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/restore", summary="Khôi phục tệp từ thùng rác")
async def restore_trash_files(
    trash_ids: List[str] = Form(...),
    trash_service: TrashService = Depends(get_trash_service)
):
    """
    Khôi phục tệp từ thùng rác.
    """
    try:
        restore_dto = RestoreTrashDTO(
            trash_ids=trash_ids
        )

        result = await trash_service.restore_files(restore_dto)

        return {
            "status": "success",
            "message": f"Đã khôi phục {result['restored_count']} tệp",
            "restored_files": result["restored_files"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/trash/{trash_id}", summary="Xóa vĩnh viễn tệp trong thùng rác")
async def delete_trash_file(
    trash_id: str = Path(..., description="ID của tệp trong thùng rác"),
    trash_service: TrashService = Depends(get_trash_service)
):
    """
    Xóa vĩnh viễn tệp trong thùng rác.
    """
    try:
        await trash_service.delete_trash_file(trash_id)
        return {
            "status": "success",
            "message": "Tệp đã được xóa vĩnh viễn"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/download/{file_id}", summary="Tải xuống tệp")
async def download_file(
    file_id: str = Path(..., description="ID của tệp"),
    file_service: FileService = Depends(get_file_service)
):
    """
    Tải xuống tệp theo ID.
    """
    try:
        file_info, file_content = await file_service.get_file(file_id)

        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file_info.original_filename}") as temp:
            temp.write(file_content)
            temp_path = temp.name

        return FileResponse(
            path=temp_path,
            filename=file_info.original_filename,
            media_type=file_info.file_type,
            background=BackgroundTasks().add_task(lambda: os.unlink(temp_path))
        )
    except FileNotFoundException:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy tệp với ID: {file_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/archives/download/{archive_id}", summary="Tải xuống tệp nén")
async def download_archive(
    archive_id: str = Path(..., description="ID của tệp nén"),
    archive_service: ArchiveService = Depends(get_archive_service)
):
    """
    Tải xuống tệp nén theo ID.
    """
    try:
        archive_info, archive_content = await archive_service.get_archive(archive_id)

        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{archive_info.original_filename}") as temp:
            temp.write(archive_content)
            temp_path = temp.name

        return FileResponse(
            path=temp_path,
            filename=archive_info.original_filename,
            media_type=archive_info.file_type,
            background=BackgroundTasks().add_task(lambda: os.unlink(temp_path))
        )
    except ArchiveNotFoundException:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy tệp nén với ID: {archive_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/files/{file_id}", summary="Xóa tệp")
async def delete_file(
    file_id: str = Path(..., description="ID của tệp"),
    permanent: bool = Query(False, description="Xóa vĩnh viễn hay chuyển vào thùng rác"),
    file_service: FileService = Depends(get_file_service),
    trash_service: TrashService = Depends(get_trash_service)
):
    """
    Xóa tệp theo ID.
    """
    try:
        if permanent:
            await file_service.delete_file(file_id)
        else:
            await trash_service.move_to_trash(file_id, "file")

        return {
            "status": "success",
            "message": f"Tệp đã được {'xóa vĩnh viễn' if permanent else 'chuyển vào thùng rác'}"
        }
    except FileNotFoundException:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy tệp với ID: {file_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/archives/{archive_id}", summary="Xóa tệp nén")
async def delete_archive(
    archive_id: str = Path(..., description="ID của tệp nén"),
    permanent: bool = Query(False, description="Xóa vĩnh viễn hay chuyển vào thùng rác"),
    archive_service: ArchiveService = Depends(get_archive_service),
    trash_service: TrashService = Depends(get_trash_service)
):
    """
    Xóa tệp nén theo ID.
    """
    try:
        if permanent:
            await archive_service.delete_archive(archive_id)
        else:
            await trash_service.move_to_trash(archive_id, "archive")

        return {
            "status": "success",
            "message": f"Tệp nén đã được {'xóa vĩnh viễn' if permanent else 'chuyển vào thùng rác'}"
        }
    except ArchiveNotFoundException:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy tệp nén với ID: {archive_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/compress/{task_id}", summary="Kiểm tra trạng thái nén tệp")
async def get_compress_status(
    task_id: str = Path(..., description="ID của tác vụ nén"),
    archive_service: ArchiveService = Depends(get_archive_service)
):
    """
    Kiểm tra trạng thái nén tệp.
    """
    try:
        status = await archive_service.get_compress_status(task_id)
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/decompress/{task_id}", summary="Kiểm tra trạng thái giải nén")
async def get_decompress_status(
    task_id: str = Path(..., description="ID của tác vụ giải nén"),
    archive_service: ArchiveService = Depends(get_archive_service)
):
    """
    Kiểm tra trạng thái giải nén.
    """
    try:
        status = await archive_service.get_decompress_status(task_id)
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/crack/{task_id}", summary="Kiểm tra trạng thái crack mật khẩu")
async def get_crack_status(
    task_id: str = Path(..., description="ID của tác vụ crack mật khẩu"),
    archive_service: ArchiveService = Depends(get_archive_service)
):
    """
    Kiểm tra trạng thái crack mật khẩu.
    """
    try:
        status = await archive_service.get_crack_status(task_id)
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/cleanup/{task_id}", summary="Kiểm tra trạng thái dọn dẹp")
async def get_cleanup_status(
    task_id: str = Path(..., description="ID của tác vụ dọn dẹp"),
    trash_service: TrashService = Depends(get_trash_service)
):
    """
    Kiểm tra trạng thái dọn dẹp.
    """
    try:
        status = await trash_service.get_cleanup_status(task_id)
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))