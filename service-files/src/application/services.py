import os
import tempfile
import uuid
import zipfile
import pyzipper
import py7zr
import rarfile
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, BinaryIO
import shutil
import logging

logger = logging.getLogger(__name__)
from domain.models import ArchiveInfo, ArchiveFormat, FileEntryInfo, ExtractedArchiveInfo, ArchiveProcessingInfo, FileInfo
from domain.exceptions import (
    ArchiveNotFoundException, InvalidFileFormatException, StorageException,
    CompressionException, ExtractionException, UnsupportedFormatException,
    PasswordProtectedException, WrongPasswordException, CrackPasswordException,
    InvalidArchiveException, FileTooLargeException, FileNotFoundException
)
from infrastructure.repository import ArchiveRepository, ProcessingRepository, FileRepository, TrashRepository as GenericTrashRepo, CleanupJobRepository
from infrastructure.minio_client import MinioClient
from infrastructure.rabbitmq_client import RabbitMQClient
from application.dto import (
    CreateArchiveDTO, ExtractArchiveDTO, CompressFilesDTO, AddFilesToArchiveDTO,
    RemoveFilesFromArchiveDTO, EncryptArchiveDTO, DecryptArchiveDTO,
    CrackArchiveDTO, ConvertArchiveDTO, CreateFileDTO, FileFilterDTO, RestoreTrashDTO, CleanupFilesDTO
)
from core.config import settings
from utils.client import ServiceClient


class FileService:
    def __init__(
        self,
        file_repo: FileRepository,
        minio_client: MinioClient,
        rabbitmq_client: RabbitMQClient
    ):
        self.file_repo = file_repo
        self.minio_client = minio_client
        self.rabbitmq_client = rabbitmq_client

    async def create_file(self, dto: CreateFileDTO, content: bytes) -> FileInfo:
        """Tạo tệp mới."""
        if len(content) > settings.MAX_UPLOAD_SIZE:
            raise FileTooLargeException(len(content), settings.MAX_UPLOAD_SIZE)

        file_type = self._get_file_type_from_filename(dto.original_filename)
       
        file_info = FileInfo(
            title=dto.title,
            description=dto.description,
            original_filename=dto.original_filename,
            file_size=len(content),
            file_type=file_type,
            storage_path="",
            doc_metadata=dto.doc_metadata or {}
        )
        
        created_file_info = await self.file_repo.save_file(file_info, content)
        return created_file_info

    async def get_files(
        self, skip: int = 0, limit: int = 10, 
        search: Optional[str] = None, user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Lấy danh sách tệp (document_category='file') dựa trên các tiêu chí lọc.
        Trả về một dictionary với 'items' và 'total_count'.
        """
        if user_id is None:
            logger.warning("User ID is required to list files in FileService.get_files.")
            return {"items": [], "total_count": 0}
        try:
            processed_user_id = user_id
            
            result_dict = await self.file_repo.list_files(
                skip=skip, 
                limit=limit, 
                user_id=processed_user_id, 
                search=search, 
                document_category_filter="file"
            )
            return result_dict
        except StorageException as se:
            logger.error(f"StorageException in FileService.get_files for user {user_id}: {se}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error in FileService.get_files for user {user_id}: {str(e)}", exc_info=True)
            raise StorageException(f"An unexpected error occurred while listing files: {str(e)}")

    async def get_file_content(self, file_db_id: str, user_id: Optional[str] = None) -> Tuple[Optional[FileInfo], Optional[bytes]]:
        """Lấy thông tin và nội dung tệp. Repository sẽ kiểm tra user_id."""
        file_info = await self.file_repo.get_file_info(file_db_id, user_id_check=user_id)
        if not file_info or file_info.doc_metadata.get("document_category", "file") != "file":
            raise FileNotFoundException(file_db_id)
        
        content = await self.file_repo.get_file_content(file_db_id, user_id_check=user_id)
        return file_info, content

    async def update_file(self, file_db_id: str, dto: CreateFileDTO, user_id: str) -> FileInfo:
        """Cập nhật thông tin tệp. Yêu cầu user_id để xác thực."""
        existing_file_info = await self.file_repo.get_file_info(file_db_id, user_id_check=user_id)
        if not existing_file_info or existing_file_info.doc_metadata.get("document_category", "file") != "file":
            raise FileNotFoundException(f"File with id {file_db_id} not found for user {user_id}.")
        
        file_info_to_update = FileInfo(
            id=existing_file_info.id,
            storage_id=existing_file_info.storage_id,
            title=dto.title if dto.title is not None else existing_file_info.title,
            description=dto.description if dto.description is not None else existing_file_info.description,
            file_size=existing_file_info.file_size,
            file_type=self._get_file_type_from_filename(dto.original_filename) if dto.original_filename else existing_file_info.file_type,
            original_filename=dto.original_filename if dto.original_filename else existing_file_info.original_filename,
            storage_path=existing_file_info.storage_path,
            user_id=user_id,
            source_service=existing_file_info.source_service,
            created_at=existing_file_info.created_at,
            doc_metadata=dto.doc_metadata if dto.doc_metadata is not None else existing_file_info.doc_metadata,
            updated_at=datetime.utcnow()
        )
        
        if "document_category" not in file_info_to_update.doc_metadata:
            file_info_to_update.doc_metadata["document_category"] = "file"
        
        return await self.file_repo.update_file_info(file_info_to_update)

    async def delete_file(self, file_db_id: str, user_id: str) -> None:
        """Xóa tệp (category 'file'). Yêu cầu user_id để xác thực."""
        file_info = await self.file_repo.get_file_info(file_db_id, user_id_check=user_id)
        if not file_info or file_info.doc_metadata.get("document_category", "file") != "file":
            raise FileNotFoundException(file_db_id)
        await self.file_repo.delete_file_record(file_db_id, user_id_check=user_id)

    def _get_file_type_from_filename(self, filename: Optional[str]) -> str:
        """Xác định kiểu MIME tệp từ tên tệp."""
        if not filename: return "application/octet-stream"
        import mimetypes
        mime_type, _ = mimetypes.guess_type(filename)
        return mime_type or "application/octet-stream"


class TrashService:
    def __init__(
        self,
        trash_repo: GenericTrashRepo,
        cleanup_repo: CleanupJobRepository,
        file_repo: FileRepository,
        archive_repo: ArchiveRepository,
        minio_client: MinioClient,
        rabbitmq_client: RabbitMQClient
    ):
        self.trash_repo = trash_repo
        self.cleanup_repo = cleanup_repo
        self.file_repo = file_repo
        self.archive_repo = archive_repo
        self.minio_client = minio_client
        self.rabbitmq_client = rabbitmq_client

    async def move_file_to_trash(self, file_db_id: str, user_id: str) -> None:
        """Di chuyển file (từ DB) vào thùng rác (JSON)."""
        await self.file_repo.move_to_trash(file_db_id, user_id)

    async def move_archive_to_trash(self, archive_id: str, user_id: str) -> None:
        """Di chuyển archive (từ JSON/cache) vào thùng rác (JSON của ArchiveRepo)."""
        print(f"Trash functionality for archives (ID: {archive_id}) is not fully DB-integrated yet.")
        pass

    async def restore_file_from_trash(self, trash_item_id: str, user_id: str) -> Optional[FileInfo]:
        """Khôi phục file từ thùng rác (JSON)."""
        return await self.file_repo.restore_from_trash(trash_item_id, user_id)
    
    async def restore_archive_from_trash(self, trash_item_id: str, user_id: str) -> Optional[ArchiveInfo]:
        """Khôi phục archive từ thùng rác (JSON của ArchiveRepo)."""
        print(f"Restore from trash for archives (Item ID: {trash_item_id}) is not fully DB-integrated yet.")
        return None

    async def get_trash_files(self, skip: int = 0, limit: int = 10, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lấy danh sách file trong thùng rác (JSON của FileRepository)."""
        if user_id is None:
            return []
        return await self.file_repo.get_trash_items(skip, limit, user_id)
    
    async def get_trash_archives(self, skip: int = 0, limit: int = 10, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lấy danh sách archives trong thùng rác (JSON của ArchiveRepository)."""
        print(f"Listing trash for archives is not fully DB-integrated yet.")
        return []

    async def permanently_delete_file_from_trash(self, trash_item_id: str, user_id: str) -> None:
        """Xóa vĩnh viễn file khỏi thùng rác (JSON) và MinIO/DB."""
        trash_data = self.file_repo._trash_cache.get(trash_item_id) 
        if not trash_data or (user_id is not None and trash_data.get("user_id") != user_id):
            raise FileNotFoundException(f"Trash item {trash_item_id} not found or permission denied.")

        original_db_id = trash_data.get("original_id")
        storage_path_to_delete = trash_data.get("storage_path")

        if original_db_id:
            try:
                await self.file_repo.delete_file_record(original_db_id, user_id_check=user_id)
            except FileNotFoundException:
                if storage_path_to_delete:
                    try:
                        await self.minio_client.remove_raw_file(storage_path_to_delete)
                    except Exception as e_minio:
                        print(f"Error deleting MinIO object {storage_path_to_delete} for trash item {trash_item_id}: {e_minio}")
            except Exception as e_db:
                print(f"Error deleting DB record {original_db_id} for trash item {trash_item_id}: {e_db}")
        elif storage_path_to_delete:
             try:
                await self.minio_client.remove_raw_file(storage_path_to_delete)
             except Exception as e_minio:
                print(f"Error deleting MinIO object {storage_path_to_delete} (no DB id) for trash item {trash_item_id}: {e_minio}")

        if trash_item_id in self.file_repo._trash_cache:
            del self.file_repo._trash_cache[trash_item_id]
            self.file_repo._save_trash_metadata() 
        else:
            pass

    async def permanently_delete_archive_from_trash(self, trash_item_id: str, user_id: str) -> None:
        """Xóa vĩnh viễn archive khỏi thùng rác (JSON của ArchiveRepo) và MinIO."""
        print(f"Permanent delete from trash for archives (Item ID: {trash_item_id}) is not DB-integrated yet.")
        pass

    async def empty_all_user_trash(self, user_id: str) -> Dict[str, int]:
        """Làm trống toàn bộ thùng rác của user (files và archives)."""
        deleted_files_count = await self.file_repo.empty_trash(user_id)
        deleted_archives_count = 0
        print(f"Empty trash for archives for user {user_id} is not DB-integrated yet.")
        return {"deleted_files": deleted_files_count, "deleted_archives": deleted_archives_count}

    async def cleanup_files_async(self, task_id: str, dto: CleanupFilesDTO):
        await self.cleanup_repo.create_job(task_id, {"days": dto.days, "file_types": dto.file_types, "user_id": dto.user_id})
        print(f"Cleanup job {task_id} created for user {dto.user_id} (days: {dto.days}, types: {dto.file_types}). Actual cleanup logic needs implementation.")
        await asyncio.sleep(2)
        await self.cleanup_repo.update_job(task_id, status="completed", result={"moved_to_trash": 0})

    async def get_cleanup_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        return await self.cleanup_repo.get_job(task_id)


class ArchiveService:
    def __init__(
        self,
        processing_repo: ProcessingRepository,
        minio_client: MinioClient,
        rabbitmq_client: RabbitMQClient,
        file_repo: FileRepository,
        service_client: ServiceClient
    ):
        self.processing_repo = processing_repo
        self.minio_client = minio_client
        self.rabbitmq_client = rabbitmq_client
        self.file_repo = file_repo
        self.service_client = service_client

    async def create_archive(self, dto: CreateArchiveDTO, content: bytes) -> FileInfo:
        """
        Tạo một bản ghi cho tệp nén mới được tải lên.
        Lưu vào DB documents với category='archive' và source_service='files'.
        """
        archive_format_val = self._get_archive_format_from_filename(dto.original_filename)
        if not archive_format_val:
            raise InvalidFileFormatException(f"Unsupported archive format for {dto.original_filename}")
        
        if len(content) > settings.MAX_UPLOAD_SIZE:
            raise FileTooLargeException(len(content), settings.MAX_UPLOAD_SIZE)
            
        archive_as_file_info = FileInfo(
            title=dto.title or os.path.splitext(dto.original_filename)[0],
            description=dto.description or "",
            file_size=len(content),
            file_type=self._get_mimetype_for_archive(archive_format_val.value),
            original_filename=dto.original_filename,
            storage_path="", 
            user_id=dto.user_id,
            source_service="files",
            doc_metadata={
                "document_category": "archive",
                "compression_type": archive_format_val.value,
            }
        )
        
        saved_archive_info = await self.file_repo.save_file(archive_as_file_info, content)
        return saved_archive_info

    async def get_archives(self, skip: int = 0, limit: int = 10, search: Optional[str] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Lấy danh sách tệp nén (document_category='archive') từ bảng documents.
        Trả về một dictionary với 'items' và 'total_count'.
        """
        if user_id is None:
            logger.warning("User ID is required to list archives in ArchiveService.get_archives.")
            return {"items": [], "total_count": 0}
        
        try:
            processed_user_id = user_id
            
            result_dict = await self.file_repo.list_files(
                skip=skip, 
                limit=limit, 
                user_id=processed_user_id, 
                search=search, 
                document_category_filter="archive"
            )
            return result_dict
        except StorageException as se:
            logger.error(f"StorageException in ArchiveService.get_archives for user {user_id}: {se}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error in ArchiveService.get_archives for user {user_id}: {str(e)}", exc_info=True)
            raise StorageException(f"An unexpected error occurred while listing archives: {str(e)}")

    async def get_archive_content(self, archive_db_id: str, user_id: Optional[str] = None) -> Tuple[Optional[FileInfo], Optional[bytes]]:
        """Lấy thông tin và nội dung tệp nén từ DB và MinIO thông qua FileRepository."""
        archive_file_info = await self.file_repo.get_file_info(archive_db_id, user_id_check=user_id)
        
        if not archive_file_info or archive_file_info.doc_metadata.get("document_category") != "archive":
            raise ArchiveNotFoundException(f"Archive with id {archive_db_id} not found or not an archive.")
            
        content = await self.file_repo.get_file_content(archive_db_id, user_id_check=user_id)
        return archive_file_info, content

    async def delete_archive(self, archive_db_id: str, user_id: Optional[str] = None) -> None:
        """Xóa tệp nén (bản ghi trong DB và file trong MinIO) thông qua FileRepository."""
        archive_info = await self.file_repo.get_file_info(archive_db_id, user_id_check=user_id)
        if not archive_info or archive_info.doc_metadata.get("document_category") != "archive":
            raise ArchiveNotFoundException(f"Archive with id {archive_db_id} not found or not an archive for deletion.")
        
        await self.file_repo.delete_file_record(archive_db_id, user_id_check=user_id)

    async def analyze_archive(self, archive_db_id: str, user_id: Optional[str] = None):
        """Phân tích archive (đếm file, etc.) - tác vụ nền.
           Sử dụng FileInfo từ DB.
        """
        print(f"Background task: Analyzing archive {archive_db_id} for user {user_id}...")
        try:
            archive_file_info, content = await self.get_archive_content(archive_db_id, user_id)
            if not archive_file_info or not content:
                print(f"Analyze: Archive {archive_db_id} not found or no content.")
                return

            files_count = 0
            original_archive_filename = archive_file_info.original_filename
            with tempfile.NamedTemporaryFile(delete=True, suffix=os.path.splitext(original_archive_filename)[1]) as tmp_file:
                tmp_file.write(content)
                tmp_file.flush()
                archive_format = self._get_archive_format_from_filename(original_archive_filename)
                if archive_format == ArchiveFormat.ZIP:
                    try:
                        with zipfile.ZipFile(tmp_file.name, 'r') as zf:
                            files_count = len([name for name in zf.namelist() if not zf.getinfo(name).is_dir()])
                    except zipfile.BadZipFile:
                        print(f"Analyze: Bad zip file for archive {archive_db_id}")
                        archive_file_info.doc_metadata["analysis_error"] = "BadZipFile"
                        files_count = -1 
            if "files_count" not in archive_file_info.doc_metadata or archive_file_info.doc_metadata.get("files_count") != files_count:
                archive_file_info.doc_metadata["files_count"] = files_count
            archive_file_info.doc_metadata["files_count_analyzed_at"] = datetime.utcnow().isoformat()
            
            updated_file_info = FileInfo(
                id=archive_file_info.id,
                storage_id=archive_file_info.storage_id,
                title=archive_file_info.title,
                description=archive_file_info.description,
                file_size=archive_file_info.file_size,
                file_type=archive_file_info.file_type,
                original_filename=archive_file_info.original_filename,
                storage_path=archive_file_info.storage_path,
                user_id=archive_file_info.user_id,
                source_service=archive_file_info.source_service,
                created_at=archive_file_info.created_at,
                doc_metadata=archive_file_info.doc_metadata,
                updated_at=datetime.utcnow()
            )
            await self.file_repo.update_file_info(updated_file_info)
            print(f"Analyze: Archive {archive_db_id} DB record updated with files_count: {files_count}")

        except Exception as e:
            print(f"Error analyzing archive {archive_db_id}: {e}")

    async def compress_files(self, dto: CompressFilesDTO) -> FileInfo:
        """
        Nén nhiều file (từ các service khác nhau hoặc service-files) thành một archive mới.
        Archive mới này sẽ được lưu bởi service-files. Thực hiện đồng bộ (async) trong service.
        Hiện tại chỉ hỗ trợ nén ZIP không mật khẩu.
        """
        if not dto.user_id:
            raise ValueError("User ID is required for compressing files.")
        
        user_id = int(dto.user_id)
        
        temp_dir_path: Optional[str] = None
        created_archive_as_file_info: Optional[FileInfo] = None

        try:
            temp_dir_path = tempfile.mkdtemp(prefix="compress_task_", dir=settings.TEMP_DIR)
            files_to_add_to_zip: List[Tuple[str, str]] = []

            for file_db_id_str in dto.file_ids:
                file_info = await self.file_repo.get_file_info(file_db_id_str, user_id_check=user_id)
                if not file_info:
                    print(f"Compress: File ID {file_db_id_str} not found or user {user_id} lacks permission. Skipping.")
                    continue

                file_content: Optional[bytes] = None
                source_service_key = file_info.source_service or "files"

                if source_service_key == "files" or source_service_key == settings.PROJECT_NAME: # files is this service
                    try:
                        file_content = await self.file_repo.get_file_content(file_db_id_str, user_id_check=user_id)
                    except Exception as e_get_local:
                        print(f"Compress: Error getting local file content for {file_db_id_str}: {e_get_local}. Skipping.")
                        continue
                else:
                    service_url = settings.SERVICE_URLS.get(source_service_key)
                    if not service_url:
                        print(f"Compress: Service URL for '{source_service_key}' not found. Skipping file {file_db_id_str}.")
                        continue
                    try:
                        file_content = await self.service_client.download_file_content(
                            base_url=service_url,
                            document_id=file_info.id, 
                            user_id=user_id
                        )
                    except Exception as e_download:
                        print(f"Compress: Error downloading file {file_db_id_str} from '{source_service_key}': {e_download}. Skipping.")
                        continue
                
                if file_content:
                    _, file_ext = os.path.splitext(file_info.original_filename)
                    temp_disk_filename = f"{file_info.id}{file_ext}"
                    temp_file_on_disk_path = os.path.join(temp_dir_path, temp_disk_filename)
                    
                    with open(temp_file_on_disk_path, "wb") as tmp_f:
                        tmp_f.write(file_content)
                    files_to_add_to_zip.append((temp_file_on_disk_path, file_info.original_filename))
                else:
                    print(f"Compress: Content for file {file_db_id_str} is empty. Skipping.")

            if not files_to_add_to_zip:
                raise CompressionException("No files were available to compress.")

            output_base, output_ext = os.path.splitext(dto.output_filename)
            target_compression_type = dto.compression_type.lower()
            if not output_ext or output_ext.lower().lstrip('.') != target_compression_type:
                final_output_filename = f"{output_base or 'archive'}.{target_compression_type}"
            else:
                final_output_filename = dto.output_filename

            compressed_archive_on_disk_path = os.path.join(temp_dir_path, final_output_filename)
            
            if target_compression_type == "zip":
                if dto.password:
                    raise UnsupportedFormatException("Password-protected ZIPs require pyzipper and are best handled by a worker.")
                with zipfile.ZipFile(compressed_archive_on_disk_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=dto.compression_level or 6) as zf:
                    for disk_path, name_in_zip in files_to_add_to_zip:
                        zf.write(disk_path, arcname=name_in_zip)
            else:
                raise UnsupportedFormatException(f"Compression type '{target_compression_type}' is not supported for synchronous compression. Only zip is supported.")

            with open(compressed_archive_on_disk_path, "rb") as f_compressed:
                compressed_content_bytes = f_compressed.read()

            archive_file_info_to_save = FileInfo(
                title=os.path.splitext(final_output_filename)[0],
                description=f"Archive of {len(files_to_add_to_zip)} file(s). IDs: {', '.join(dto.file_ids)}",
                file_size=len(compressed_content_bytes),
                file_type=self._get_mimetype_for_archive(target_compression_type),
                original_filename=final_output_filename,
                storage_path="", 
                user_id=user_id,
                source_service="files",
                doc_metadata={
                    "document_category": "archive",
                    "compression_type": target_compression_type,
                    "original_file_ids": dto.file_ids,
                    "password_protected": bool(dto.password),
                    "compression_level": dto.compression_level
                }
            )
            
            created_archive_as_file_info = await self.file_repo.save_file(archive_file_info_to_save, compressed_content_bytes)
            
            if not created_archive_as_file_info:
                raise StorageException("Failed to save the created archive document.")
            
            return created_archive_as_file_info

        except Exception as e:
            print(f"Compress: Error during compression task for user {user_id}: {e}")
            raise CompressionException(f"Failed to compress files: {str(e)}")
        finally:
            if temp_dir_path and os.path.exists(temp_dir_path):
                try:
                    shutil.rmtree(temp_dir_path)
                except Exception as e_clean:
                    print(f"Compress: Error cleaning up temp directory {temp_dir_path}: {e_clean}")

    async def extract_archive(self, dto: ExtractArchiveDTO) -> Dict[str, Any]:
        """Gửi tác vụ giải nén cho worker qua RabbitMQ."""
        archive_file_info = await self.file_repo.get_file_info(dto.archive_id, user_id_check=dto.user_id)
        if not archive_file_info or archive_file_info.doc_metadata.get("document_category") != "archive":
            raise ArchiveNotFoundException(f"Archive with DB ID {dto.archive_id} not found or not an archive for user {dto.user_id}.")

        processing_id = str(uuid.uuid4())
        await self.processing_repo.create_processing(ArchiveProcessingInfo(
            id=processing_id,
            archive_id=dto.archive_id,
            operation_type="extract",
            user_id=dto.user_id
        ))
        
        message_data = dto.model_dump()

        message_data["user_id"] = dto.user_id
        message_data["storage_path"] = archive_file_info.storage_path
        message_data["original_filename"] = archive_file_info.original_filename
        
        await self.rabbitmq_client.publish_message(
            queue_name=getattr(settings, 'RABBITMQ_EXTRACT_QUEUE', 'extract_queue'), 
            message=message_data
        )
        return {"processing_id": processing_id, "message": "Extraction task submitted."}

    async def crack_archive_password(self, dto: CrackArchiveDTO) -> Dict[str, Any]:
        """Gửi tác vụ crack password cho worker qua RabbitMQ."""
        archive_file_info = await self.file_repo.get_file_info(dto.archive_id, user_id_check=dto.user_id)
        if not archive_file_info or archive_file_info.doc_metadata.get("document_category") != "archive":
            raise ArchiveNotFoundException(f"Archive with DB ID {dto.archive_id} not found or not an archive for user {dto.user_id}.")

        processing_id = str(uuid.uuid4())
        await self.processing_repo.create_processing(ArchiveProcessingInfo(
            id=processing_id,
            archive_id=dto.archive_id,
            operation_type="crack_password",
            user_id=dto.user_id
        ))
        
        message_data = dto.model_dump()
        message_data["user_id"] = dto.user_id
        message_data["storage_path"] = archive_file_info.storage_path
        message_data["original_filename"] = archive_file_info.original_filename
        
        await self.rabbitmq_client.publish_message(
             queue_name=getattr(settings, 'RABBITMQ_CRACK_QUEUE', 'crack_queue'),
             message=message_data
        )
        return {"processing_id": processing_id, "message": "Password cracking task submitted."}

    async def get_processing_status(self, processing_id: str, user_id: Optional[str] = None) -> Optional[ArchiveProcessingInfo]:
        """Lấy trạng thái xử lý, kiểm tra user_id nếu được cung cấp."""
        return await self.processing_repo.get_processing(processing_id, user_id_check=user_id)
    
    async def get_compress_status(self, task_id: str, user_id: Optional[str] = None) -> Optional[ArchiveProcessingInfo]:
        """ 
        Lấy trạng thái nén. Vì compress_files hiện tại là đồng bộ, hàm này có thể không được dùng 
        trừ khi compress_files được chuyển lại cho worker.
        """
       
        print(f"Warning: get_compress_status called for task {task_id}, but compression is synchronous.")
        return None 

    async def get_decompress_status(self, task_id: str, user_id: Optional[str] = None) -> Optional[ArchiveProcessingInfo]:
        """Lấy trạng thái giải nén, kiểm tra user_id."""
        return await self.get_processing_status(task_id, user_id=user_id)

    async def get_crack_status(self, task_id: str, user_id: Optional[str] = None) -> Optional[ArchiveProcessingInfo]:
        """Lấy trạng thái crack password, kiểm tra user_id."""
        return await self.get_processing_status(task_id, user_id=user_id)

    def _get_archive_format_from_filename(self, filename: str) -> Optional[ArchiveFormat]:
        name, ext = os.path.splitext(filename.lower())
        if ext == ".gz" and name.endswith(".tar"):
            return ArchiveFormat.TAR_GZIP
        try:
            return ArchiveFormat(ext.lstrip('.'))
        except ValueError:
            return None
            
    def _get_mimetype_for_archive(self, archive_type: str) -> str:
        mapping = {
            "zip": "application/zip",
            "rar": "application/vnd.rar",
            "7z": "application/x-7z-compressed",
            "tar": "application/x-tar",
            "gz": "application/gzip",
            "tar.gz": "application/gzip"
        }
        return mapping.get(archive_type, "application/octet-stream") 