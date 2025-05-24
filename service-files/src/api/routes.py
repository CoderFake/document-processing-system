from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Depends, Query, Path, status, Request
from fastapi.responses import JSONResponse, FileResponse
from typing import List, Optional, Dict, Any
import os
import tempfile
import shutil
from datetime import datetime
import uuid
from fastapi.security import APIKeyHeader
import logging

from domain.models import FileInfo
from application.dto import (
    CreateFileDTO, CreateArchiveDTO, CompressFilesDTO, DecompressArchiveDTO, 
    CrackArchivePasswordDTO, CleanupFilesDTO, RestoreTrashDTO, ExtractArchiveDTO
)
from application.services import FileService, ArchiveService, TrashService
from infrastructure.repository import FileRepository, ProcessingRepository, CleanupJobRepository, TrashRepository, ArchiveRepository
from infrastructure.minio_client import MinioClient
from infrastructure.rabbitmq_client import RabbitMQClient
from domain.exceptions import FileNotFoundException, ArchiveNotFoundException, PasswordProtectedException, WrongPasswordException, StorageException
from core.config import settings
from utils.client import ServiceClient

logger = logging.getLogger(__name__)

API_KEY_HEADER = APIKeyHeader(name="X-User-ID", auto_error=False)

async def get_current_user_id(request: Request, x_user_id: Optional[str] = Depends(API_KEY_HEADER)) -> str:
    user_id_from_query = request.query_params.get("user_id_dev")
    user_id_from_form: Optional[str] = None
    try:
        form_data = await request.form()
        user_id_from_form = form_data.get("user_id_dev")
    except Exception:
        pass

    if x_user_id:
        try:
            # Validate UUID format
            import uuid
            uuid.UUID(x_user_id)
            return x_user_id
        except ValueError:
            logger.warning(f"Invalid X-User-ID header: {x_user_id}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid User ID in header")
    elif user_id_from_query:
        logger.warning(f"DEV MODE: Using user_id_dev from query params: {user_id_from_query}")
        try:
            import uuid
            uuid.UUID(user_id_from_query)
            return user_id_from_query
        except ValueError: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user_id_dev in query")
    elif user_id_from_form:
        logger.warning(f"DEV MODE: Using user_id_dev from form data: {user_id_from_form}")
        try:
            import uuid
            uuid.UUID(user_id_from_form)
            return user_id_from_form
        except ValueError: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user_id_dev in form")
    
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID not found in request")


router = APIRouter()


def get_file_service(request: Request):
    minio_client = MinioClient()
    rabbitmq_client = RabbitMQClient()
    db_pool = request.app.state.db_pool
    if not db_pool:
        logger.error("DB connection pool is not available for FileService.")
        raise HTTPException(status_code=503, detail="Database connection pool is not available.")
    file_repo = FileRepository(minio_client, db_pool)
    return FileService(file_repo, minio_client, rabbitmq_client)


def get_archive_service(request: Request):
    minio_client = MinioClient()
    rabbitmq_client = RabbitMQClient()
    processing_repo = ProcessingRepository(minio_client)
    
    db_pool = request.app.state.db_pool
    if not db_pool:
        logger.error("DB connection pool is not available for ArchiveService.")
        raise HTTPException(status_code=503, detail="Database connection pool is not available for ArchiveService.")
        
    file_repo = FileRepository(minio_client, db_pool)
    service_client = ServiceClient()
    
    return ArchiveService(
        processing_repo=processing_repo, 
        minio_client=minio_client, 
        rabbitmq_client=rabbitmq_client, 
        file_repo=file_repo,
        service_client=service_client
    )


def get_trash_service(request: Request):
    minio_client = MinioClient()
    rabbitmq_client = RabbitMQClient()
    trash_repo = TrashRepository()
    cleanup_repo = CleanupJobRepository()
    
    db_pool = request.app.state.db_pool
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database connection pool is not available for TrashService.")
    file_repo = FileRepository(minio_client, db_pool)
    archive_repo = ArchiveRepository(minio_client)
    return TrashService(trash_repo, cleanup_repo, file_repo, archive_repo, minio_client, rabbitmq_client)


@router.get("/files", summary="Lấy danh sách tệp")
async def get_files(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    current_user_id: str = Depends(get_current_user_id),
    file_service: FileService = Depends(get_file_service)
):
    """
    Lấy danh sách tệp (document_category='file') của người dùng hiện tại.
    Trả về danh sách các mục và tổng số lượng.
    """
    try:
       
        result = await file_service.get_files(skip, limit, search, current_user_id)
        return result
    except StorageException as se:
        logger.error(f"API: StorageException getting files for user {current_user_id}: {se}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(se))
    except Exception as e:
        logger.error(f"API: Error getting files for user {current_user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not retrieve files.")


@router.post("/files/upload", summary="Tải lên tệp mới")
async def upload_file(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    current_user_id: str = Depends(get_current_user_id),
    background_tasks: BackgroundTasks = None,
    file_service: FileService = Depends(get_file_service)
):
    """
    Tải lên tệp mới (document_category='file') cho người dùng hiện tại.
    """
    try:
        file_dto = CreateFileDTO(
            title=title or os.path.splitext(file.filename)[0],
            description=description or "",
            original_filename=file.filename,
            user_id=current_user_id
        )

        content = await file.read()
        file_info = await file_service.create_file(file_dto, content)

        return file_info
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error uploading file for user {current_user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Could not upload file: {str(e)}")


@router.get("/archives", summary="Lấy danh sách tệp nén")
async def get_archives(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    current_user_id: str = Depends(get_current_user_id),
    archive_service: ArchiveService = Depends(get_archive_service)
):
    """
    Lấy danh sách tệp nén (document_category='archive') của người dùng hiện tại.
    Trả về danh sách các mục và tổng số lượng.
    """
    try:
        result = await archive_service.get_archives(skip, limit, search, current_user_id)
        return result
    except StorageException as se:
        logger.error(f"API: StorageException getting archives for user {current_user_id}: {se}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(se))
    except Exception as e:
        logger.error(f"API: Error getting archives for user {current_user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not retrieve archives.")


@router.post("/archives/upload", summary="Tải lên tệp nén mới")
async def upload_archive(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    current_user_id: str = Depends(get_current_user_id),
    background_tasks: BackgroundTasks = None,
    archive_service: ArchiveService = Depends(get_archive_service)
):
    """
    Tải lên tệp nén mới (document_category='archive') cho người dùng hiện tại.
    """
    try:
        archive_dto = CreateArchiveDTO(
            title=title or os.path.splitext(file.filename)[0],
            description=description or "",
            original_filename=file.filename,
            user_id=current_user_id
        )

        content = await file.read()
        archive_file_info = await archive_service.create_archive(archive_dto, content)

        if background_tasks and archive_file_info.id:
            background_tasks.add_task(
                archive_service.analyze_archive,
                archive_db_id=archive_file_info.id, 
                user_id=current_user_id
            )
        return archive_file_info
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error uploading archive for user {current_user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Could not upload archive: {str(e)}")


@router.post("/compress", summary="Nén nhiều tệp")
async def compress_files_endpoint(
    file_ids: List[str] = Form(...),
    output_filename: str = Form(...),
    compression_type: str = Form("zip"),
    password: Optional[str] = Form(None),
    compression_level: Optional[int] = Form(settings.DEFAULT_COMPRESSION_LEVEL if hasattr(settings, 'DEFAULT_COMPRESSION_LEVEL') else 6),
    current_user_id: str = Depends(get_current_user_id),
    archive_service: ArchiveService = Depends(get_archive_service)
):
    """
    Nén nhiều tệp được chỉ định bởi file_ids (ID từ bảng documents) thành một archive mới.
    Thực hiện đồng bộ.
    """
    try:
        compress_dto = CompressFilesDTO(
            file_ids=file_ids,
            output_filename=output_filename,
            compression_type=compression_type,
            password=password,
            compression_level=compression_level,
            user_id=current_user_id
        )

        created_archive_file_info = await archive_service.compress_files(compress_dto)
  
        return created_archive_file_info
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error compressing files for user {current_user_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi nén tệp: {str(e)}"
        )


@router.post("/decompress", summary="Giải nén tệp")
async def decompress_archive(
    archive_id: str = Form(...),
    password: Optional[str] = Form(None),
    extract_all: bool = Form(True),
    file_paths: Optional[List[str]] = Form(None),
    current_user_id: str = Depends(get_current_user_id),
    archive_service: ArchiveService = Depends(get_archive_service)
):
    """
    Gửi yêu cầu giải nén tệp cho người dùng hiện tại. Tác vụ chạy nền.
    `file_paths`: Danh sách các file/folder cụ thể cần giải nén trong archive. Nếu `None` hoặc rỗng và `extract_all` là True, giải nén tất cả.
    """
    try:
        parsed_file_paths = []
        if file_paths:
            if isinstance(file_paths, list):
                parsed_file_paths = file_paths
            elif isinstance(file_paths, str):
                parsed_file_paths = [p.strip() for p in file_paths.split(',') if p.strip()]

        dto = ExtractArchiveDTO(
            archive_id=archive_id,
            password=password,
            extract_all=extract_all,
            file_paths=parsed_file_paths if parsed_file_paths else [],
            user_id=current_user_id
        )
        result = await archive_service.extract_archive(dto)
        return result
    except ArchiveNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error submitting decompress task for archive {archive_id}, user {current_user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Could not submit decompress task: {str(e)}")


@router.post("/crack", summary="Crack mật khẩu tệp nén")
async def crack_archive_password(
    archive_id: str = Form(...),
    max_length: int = Form(settings.DEFAULT_CRACK_MAX_LENGTH if hasattr(settings, 'DEFAULT_CRACK_MAX_LENGTH') else 6),
    current_user_id: str = Depends(get_current_user_id),
    archive_service: ArchiveService = Depends(get_archive_service)
):
    """
    Gửi yêu cầu crack mật khẩu tệp nén cho người dùng hiện tại. Tác vụ chạy nền.
    """
    try:
        dto = CrackArchivePasswordDTO(
            archive_id=archive_id,
            max_length=max_length,
            user_id=current_user_id,
        )
        result = await archive_service.crack_archive_password(dto)
        return result
    except ArchiveNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error submitting crack task for archive {archive_id}, user {current_user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Could not submit crack task: {str(e)}")


@router.post("/cleanup", summary="Dọn dẹp tệp cũ (chuyển vào thùng rác)")
async def cleanup_files_endpoint(
    days: int = Form(settings.DEFAULT_CLEANUP_DAYS if hasattr(settings, 'DEFAULT_CLEANUP_DAYS') else 30),
    file_types: Optional[List[str]] = Form(None),
    current_user_id: str = Depends(get_current_user_id),
    trash_service: TrashService = Depends(get_trash_service)
):
    """
    Gửi yêu cầu dọn dẹp tệp cũ (chuyển vào thùng rác) cho người dùng hiện tại.
    Tác vụ chạy nền.
    `file_types`: danh sách các kiểu file (MIME type hoặc extension) cần dọn, nếu None là tất cả.
    """
    try:
        parsed_file_types = []
        if file_types:
            if isinstance(file_types, list):
                parsed_file_types = file_types
            elif isinstance(file_types, str):
                 parsed_file_types = [ft.strip() for ft in file_types.split(',') if ft.strip()]

        dto = CleanupFilesDTO(
            days=days,
            file_types=parsed_file_types if parsed_file_types else None,
            user_id=current_user_id
        )
        task_id = str(uuid.uuid4())

        await trash_service.cleanup_files_async(task_id, dto)
        return {"task_id": task_id, "message": "Cleanup task submitted."}
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error submitting cleanup task for user {current_user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Could not submit cleanup task: {str(e)}")


@router.get("/trash", summary="Lấy danh sách mục trong thùng rác")
async def get_trash_items_endpoint(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    item_type: Optional[str] = Query(None, description="Lọc theo loại: 'file' hoặc 'archive'. Mặc định cả hai."),
    current_user_id: str = Depends(get_current_user_id),
    trash_service: TrashService = Depends(get_trash_service)
):
    """
    Lấy danh sách các mục (file và/hoặc archive) trong thùng rác của người dùng hiện tại.
    Thùng rác hiện tại dựa trên JSON cache trong FileRepository/ArchiveRepository.
    """
    try:
        items = []
     
        if item_type is None or item_type == "file":
            file_trash_items = await trash_service.get_trash_files(skip, limit, current_user_id)
            for item in file_trash_items:
                item['item_type'] = 'file' 
            items.extend(file_trash_items)
        
        if item_type is None or item_type == "archive":
           
            pass

        
        return {"items": items, "total": len(items)}
    except Exception as e:
        logger.error(f"Error getting trash items for user {current_user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not retrieve trash items.")


@router.post("/restore", summary="Khôi phục mục từ thùng rác")
async def restore_trash_items_endpoint(
    
    trash_item_id: str = Form(...),
    item_type: str = Form(..., description="Loại mục cần khôi phục: 'file' hoặc 'archive'"),
    current_user_id: str = Depends(get_current_user_id),
    trash_service: TrashService = Depends(get_trash_service)
):
    """
    Khôi phục một mục (file hoặc archive) từ thùng rác của người dùng hiện tại.
    `trash_item_id` là ID của mục trong thùng rác (từ FileRepository._trash_cache).
    """
    try:
        restored_item_info = None
        if item_type == "file":
            restored_item_info = await trash_service.restore_file_from_trash(trash_item_id, current_user_id)
        elif item_type == "archive":
            logger.warning(f"Restore archive from trash (item: {trash_item_id}) is not fully implemented.")
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Restoring archives from trash is not yet fully supported.")
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid item_type. Must be 'file' or 'archive'.")

        if not restored_item_info:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Trash item {trash_item_id} (type: {item_type}) not found or could not be restored for user {current_user_id}.")
        
        return {"message": f"{item_type.capitalize()} restored successfully.", "restored_item": restored_item_info}
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error restoring trash item {trash_item_id} (type: {item_type}) for user {current_user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Could not restore item from trash: {str(e)}")


@router.delete("/trash/{trash_item_id}", summary="Xóa vĩnh viễn mục trong thùng rác")
async def delete_trash_item_permanently_endpoint(
    trash_item_id: str = Path(..., description="ID của mục trong thùng rác"),
    item_type: str = Query(..., description="Loại mục cần xóa: 'file' hoặc 'archive'"), 
    current_user_id: str = Depends(get_current_user_id),
    trash_service: TrashService = Depends(get_trash_service)
):
    """
    Xóa vĩnh viễn một mục (file hoặc archive) khỏi thùng rác của người dùng hiện tại.
    """
    try:
        if item_type == "file":
            await trash_service.permanently_delete_file_from_trash(trash_item_id, current_user_id)
        elif item_type == "archive":
            logger.warning(f"Permanent delete archive from trash (item: {trash_item_id}) is not fully implemented.")
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Permanent delete for archives from trash is not yet fully supported.")
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid item_type. Must be 'file' or 'archive'.")
        
        return JSONResponse(content={"message": f"Trash item {trash_item_id} (type: {item_type}) permanently deleted."}, status_code=status.HTTP_200_OK)
    except FileNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error permanently deleting trash item {trash_item_id} (type: {item_type}) for user {current_user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Could not permanently delete trash item: {str(e)}")


@router.post("/trash/empty", summary="Làm trống thùng rác")
async def empty_trash_endpoint(
    current_user_id: str = Depends(get_current_user_id),
    trash_service: TrashService = Depends(get_trash_service)
):
    """
    Làm trống toàn bộ thùng rác (files và archives) của người dùng hiện tại.
    Lưu ý: phần archive của empty_trash chưa được DB-integrated hoàn toàn trong service.
    """
    try:
        result = await trash_service.empty_all_user_trash(current_user_id)
        return result 
    except Exception as e:
        logger.error(f"Error emptying trash for user {current_user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Could not empty trash: {str(e)}")


@router.get("/status/compress/{task_id}", summary="Kiểm tra trạng thái nén tệp")
async def get_compress_status_endpoint(
    task_id: str = Path(..., description="ID của tác vụ nén (hiện không dùng vì nén đồng bộ)"),
    current_user_id: str = Depends(get_current_user_id),
    archive_service: ArchiveService = Depends(get_archive_service)
):
    """
    Kiểm tra trạng thái của một tác vụ nén. 
    LƯU Ý: API nén hiện tại là đồng bộ và không trả về task_id theo dõi được qua endpoint này.
    Endpoint này được giữ lại cho tương thích nếu nén chuyển sang bất đồng bộ.
    """
  
    logger.warning(f"get_compress_status_endpoint for task {task_id} called, but compression is synchronous. This endpoint may not be useful.")
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=f"Status check for compress task {task_id} is not applicable for synchronous compression.")


@router.get("/status/decompress/{task_id}", summary="Kiểm tra trạng thái giải nén")
async def get_decompress_status_endpoint(
    task_id: str = Path(..., description="ID của tác vụ giải nén (processing_id)"),
    current_user_id: str = Depends(get_current_user_id),
    archive_service: ArchiveService = Depends(get_archive_service)
):
    """
    Kiểm tra trạng thái của một tác vụ giải nén, yêu cầu user_id để xác thực.
    `task_id` là `processing_id` trả về khi submit task.
    """
    try:
        processing_info = await archive_service.get_decompress_status(task_id, current_user_id)
        if not processing_info:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Decompress task with ID {task_id} not found or access denied for user {current_user_id}.")
        return processing_info
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error getting decompress status for task {task_id}, user {current_user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Could not get decompress task status: {str(e)}")


@router.get("/status/crack/{task_id}", summary="Kiểm tra trạng thái crack mật khẩu")
async def get_crack_status_endpoint(
    task_id: str = Path(..., description="ID của tác vụ crack mật khẩu (processing_id)"),
    current_user_id: str = Depends(get_current_user_id),
    archive_service: ArchiveService = Depends(get_archive_service)
):
    """
    Kiểm tra trạng thái của một tác vụ crack mật khẩu, yêu cầu user_id để xác thực.
    `task_id` là `processing_id` trả về khi submit task.
    """
    try:
        processing_info = await archive_service.get_crack_status(task_id, current_user_id)
        if not processing_info:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Crack task with ID {task_id} not found or access denied for user {current_user_id}.")
        return processing_info
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error getting crack status for task {task_id}, user {current_user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Could not get crack task status: {str(e)}")


@router.get("/status/cleanup/{task_id}", summary="Kiểm tra trạng thái dọn dẹp")
async def get_cleanup_status_endpoint(
    task_id: str = Path(..., description="ID của tác vụ dọn dẹp"),
    current_user_id: str = Depends(get_current_user_id), # Thêm user_id để trash_service có thể kiểm tra nếu cần
    trash_service: TrashService = Depends(get_trash_service)
):
    """
    Kiểm tra trạng thái của một tác vụ dọn dẹp.
    TrashService.get_cleanup_status hiện không kiểm tra user_id, nhưng API nên có để nhất quán.
    """
    try:
        # TrashService.get_cleanup_status không có user_id, nhưng ta có thể thêm vào nếu cần
        # job_info = await trash_service.get_cleanup_status(task_id, user_id=current_user_id) # Nếu service hỗ trợ
        job_info = await trash_service.get_cleanup_status(task_id)
        if not job_info:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Cleanup task with ID {task_id} not found.")
        
        # Kiểm tra user_id của job nếu có trong job_info
        job_user_id = job_info.get("info", {}).get("user_id")
        if job_user_id is not None and job_user_id != current_user_id:
            logger.warning(f"User {current_user_id} attempting to access cleanup job {task_id} of user {job_user_id}")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Access denied to cleanup job {task_id}.")
            
        return job_info
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error getting cleanup status for task {task_id}, user {current_user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Could not get cleanup task status: {str(e)}")


@router.get("/debug/minio-status", summary="Kiểm tra trạng thái MinIO (admin)")
async def check_minio_status(
    archive_service: ArchiveService = Depends(get_archive_service)
):
    """
    Kiểm tra kết nối và trạng thái của MinIO.
    Endpoint này có thể cần được bảo vệ bằng quyền admin.
    """
    try:
       
        buckets = await archive_service.minio_client.list_buckets() # list_buckets là async
        bucket_names = [bucket.name for bucket in buckets]
        return {
            "status": "ok", 
            "message": "MinIO connection successful.",
            "buckets_found": bucket_names,
            "configured_buckets": {
                "files": settings.MINIO_FILES_BUCKET,
                "archives": settings.MINIO_ARCHIVE_BUCKET
            }
        }
    except Exception as e:
        logger.error(f"MinIO status check failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"MinIO connection failed: {str(e)}")


@router.get("/all-documents", summary="Lấy tất cả tài liệu của người dùng từ bảng documents")
async def get_all_user_documents(
    current_user_id: str = Depends(get_current_user_id),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = Query(None),
    source_service_filter: Optional[str] = Query(None, description="Lọc theo service gốc, ví dụ: files, word, pdf, excel"),
    file_repo: FileRepository = Depends(lambda request: FileRepository(MinioClient(), request.app.state.db_pool))
):
    """
    Lấy tất cả các loại tài liệu thuộc về người dùng hiện tại.
    """
    try:
        result_dict = await file_repo.list_files(
            skip=skip, 
            limit=limit, 
            user_id=current_user_id, 
            search=search,
            document_category_filter=None, 
            source_service_filter=source_service_filter 
        )
        return result_dict
    except StorageException as se:
        logger.error(f"API: StorageException in get_all_user_documents for user {current_user_id}: {se}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(se))
    except Exception as e:
        logger.error(f"API: Error getting all documents for user {current_user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not retrieve all documents.")


@router.get("/documents/{category}", summary="Lấy tài liệu theo loại cụ thể từ bảng documents")
async def get_documents_by_category(
    category: str = Path(..., description="Loại tài liệu: files, archive, word, pdf, excel"),
    current_user_id: str = Depends(get_current_user_id),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    search: Optional[str] = Query(None),
    source_service_filter: Optional[str] = Query(None, description="Lọc theo service gốc nếu cần"),
    file_repo: FileRepository = Depends(lambda request: FileRepository(MinioClient(), request.app.state.db_pool))
):
    """
    Lấy danh sách tài liệu thuộc một `document_category` cụ thể.
    """
    try:
        valid_categories = ["files", "archive", "word", "pdf", "excel"]
        if category.lower() not in valid_categories:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid document category. Allowed: {valid_categories}")

        result_dict = await file_repo.list_files(
            skip=skip, 
            limit=limit, 
            user_id=current_user_id, 
            search=search,
            document_category_filter=category.lower(),
            source_service_filter=source_service_filter
        )
        return result_dict
    except StorageException as se:
        logger.error(f"API: StorageException in get_documents_by_category '{category}' for user {current_user_id}: {se}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(se))
    except Exception as e:
        logger.error(f"API: Error getting documents for category {category}, user {current_user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Could not retrieve documents for category {category}.")



@router.post("/compress-all-by-category", summary="Nén tất cả tài liệu của người dùng theo category(ies)")
async def compress_all_user_documents_by_category(

    current_user_id: str = Depends(get_current_user_id),
    output_filename: str = Form(..., description="Tên file nén kết quả (ví dụ: my_documents.zip)"),
    categories: List[str] = Form(..., description="List các document_category cần nén (ví dụ: [\"pdf\", \"word\"])"),
    compression_type: str = Form("zip", description="Loại nén (zip)"),
    password: Optional[str] = Form(None, description="Mật khẩu bảo vệ file nén (nếu hỗ trợ)"),

    file_repo: FileRepository = Depends(lambda r: FileRepository(MinioClient(), r.app.state.db_pool)),
    archive_service: ArchiveService = Depends(get_archive_service)
):
    """
    Tạo một file nén chứa tất cả tài liệu của người dùng thuộc các `categories` được chỉ định.
    Lấy ID các tài liệu này từ bảng `documents`, sau đó gọi `ArchiveService.compress_files`.
    """
    try:
        file_ids_to_compress = []
        valid_doc_categories = ["files", "archive", "word", "pdf", "excel"]
        
        for cat in categories:
            if cat.lower() not in valid_doc_categories:
                logger.warning(f"Invalid category '{cat}' in compress-all request for user {current_user_id}. Skipping.")
                continue
            MAX_FILES_FOR_COMPRESS_ALL = 500 # Ví dụ
            
            docs_in_cat = await file_repo.list_files(
                user_id=current_user_id,
                document_category_filter=cat.lower(),
                limit=MAX_FILES_FOR_COMPRESS_ALL
            )
            for doc_info in docs_in_cat:
                if doc_info.id:
                     file_ids_to_compress.append(doc_info.id)
            
            if len(file_ids_to_compress) >= MAX_FILES_FOR_COMPRESS_ALL:
                logger.warning(f"Reached max files ({MAX_FILES_FOR_COMPRESS_ALL}) for compress-all operation for user {current_user_id}. Some files might be excluded.")
                break

        if not file_ids_to_compress:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No files found for the specified categories to compress.")

        unique_file_ids = sorted(list(set(file_ids_to_compress)))
        
        if len(unique_file_ids) > MAX_FILES_FOR_COMPRESS_ALL: 
             unique_file_ids = unique_file_ids[:MAX_FILES_FOR_COMPRESS_ALL]
             logger.warning(f"Total unique files for compression for user {current_user_id} capped at {MAX_FILES_FOR_COMPRESS_ALL}.")

        compress_dto = CompressFilesDTO(
            file_ids=unique_file_ids,
            output_filename=output_filename,
            compression_type=compression_type,
            password=password,
            user_id=current_user_id,
        )

        created_archive_file_info = await archive_service.compress_files(compress_dto)
        return created_archive_file_info

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error in compress-all-by-category for user {current_user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Could not compress all documents by category: {str(e)}")
