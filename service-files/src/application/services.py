import os
import tempfile
import uuid
import zipfile
import pyzipper
import py7zr
import rarfile
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, BinaryIO

from domain.models import ArchiveInfo, ArchiveFormat, FileEntryInfo, ExtractedArchiveInfo, ArchiveProcessingInfo
from domain.exceptions import (
    ArchiveNotFoundException, InvalidFileFormatException, StorageException,
    CompressionException, ExtractionException, UnsupportedFormatException,
    PasswordProtectedException, WrongPasswordException, CrackPasswordException,
    InvalidArchiveException, FileTooLargeException
)
from infrastructure.repository import ArchiveRepository, ProcessingRepository
from infrastructure.minio_client import MinioClient
from infrastructure.rabbitmq_client import RabbitMQClient
from application.dto import (
    CreateArchiveDTO, ExtractArchiveDTO, CompressFilesDTO, AddFilesToArchiveDTO,
    RemoveFilesFromArchiveDTO, EncryptArchiveDTO, DecryptArchiveDTO,
    CrackArchiveDTO, ConvertArchiveDTO
)
from core.config import settings


class ArchiveService:
    def __init__(
        self,
        archive_repo: ArchiveRepository,
        processing_repo: ProcessingRepository,
        minio_client: MinioClient,
        rabbitmq_client: RabbitMQClient
    ):
        self.archive_repo = archive_repo
        self.processing_repo = processing_repo
        self.minio_client = minio_client
        self.rabbitmq_client = rabbitmq_client

    async def create_archive(self, dto: CreateArchiveDTO, content: bytes) -> ArchiveInfo:
        """Tạo tệp nén mới."""
        # Xác định định dạng tệp nén
        archive_format = self._get_archive_format(dto.original_filename)
        
        # Kiểm tra dung lượng
        if len(content) > settings.MAX_UPLOAD_SIZE:
            raise FileTooLargeException(len(content), settings.MAX_UPLOAD_SIZE)
            
        # Lưu tạm tệp để đọc thông tin
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{archive_format.value}") as temp_file:
            temp_path = temp_file.name
            temp_file.write(content)
        
        try:
            # Kiểm tra tệp nén có hợp lệ không
            is_encrypted = False
            try:
                if archive_format == ArchiveFormat.ZIP:
                    with zipfile.ZipFile(temp_path, 'r') as zip_ref:
                        # Kiểm tra mật khẩu
                        for zip_info in zip_ref.infolist():
                            if zip_info.flag_bits & 0x1:
                                is_encrypted = True
                                break
                elif archive_format == ArchiveFormat.RAR:
                    with rarfile.RarFile(temp_path, 'r') as rar_ref:
                        is_encrypted = rar_ref.needs_password()
                elif archive_format == ArchiveFormat.SEVEN_ZIP:
                    with py7zr.SevenZipFile(temp_path, 'r') as sz_ref:
                        is_encrypted = sz_ref.needs_password()
            except Exception as e:
                raise InvalidArchiveException(f"Tệp nén không hợp lệ: {str(e)}")
            
            # Tạo ID duy nhất
            archive_id = str(uuid.uuid4())
            
            # Tạo thông tin tệp nén
            archive_info = ArchiveInfo(
                id=archive_id,
                title=dto.title,
                description=dto.description,
                format=archive_format,
                file_size=len(content),
                original_filename=dto.original_filename,
                storage_path="",  # Được cập nhật sau khi lưu
                is_encrypted=is_encrypted
            )
            
            # Lưu tệp nén
            storage_path = await self.archive_repo.save_archive(archive_id, content)
            archive_info.storage_path = storage_path
            
            # Lưu thông tin tệp nén vào repository
            await self.archive_repo.create_archive(archive_info)
            
            return archive_info
        finally:
            # Xóa tệp tạm
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    async def get_archives(self, skip: int = 0, limit: int = 10, search: Optional[str] = None) -> List[ArchiveInfo]:
        """Lấy danh sách tệp nén."""
        return await self.archive_repo.get_archives(skip, limit, search)

    async def get_archive(self, archive_id: str) -> Tuple[ArchiveInfo, bytes]:
        """Lấy thông tin và nội dung tệp nén."""
        archive_info = await self.archive_repo.get_archive(archive_id)
        if not archive_info:
            raise ArchiveNotFoundException(archive_id)
        
        content = await self.archive_repo.get_archive_content(archive_id)
        return archive_info, content

    async def delete_archive(self, archive_id: str) -> None:
        """Xóa tệp nén."""
        await self.archive_repo.delete_archive(archive_id)

    async def extract_archive(self, dto: ExtractArchiveDTO) -> Dict[str, Any]:
        """Giải nén tệp."""
        # Tạo ID xử lý duy nhất
        processing_id = str(uuid.uuid4())
        
        # Tạo thông tin xử lý
        processing_info = ArchiveProcessingInfo(
            id=processing_id,
            archive_id=dto.archive_id,
            operation_type="extract"
        )
        
        # Lưu thông tin xử lý
        await self.processing_repo.create_processing(processing_info)
        
        # Gửi tác vụ vào queue
        await self.rabbitmq_client.publish_message(
            queue="extract_queue",
            message={
                "processing_id": processing_id,
                "archive_id": dto.archive_id,
                "extract_path": dto.extract_path,
                "password": dto.password,
                "extract_all": dto.extract_all,
                "selected_files": dto.selected_files
            }
        )
        
        return {
            "processing_id": processing_id,
            "status": "processing",
            "message": "Đã bắt đầu giải nén tệp"
        }

    async def compress_files(self, dto: CompressFilesDTO) -> Dict[str, Any]:
        """Nén các tệp."""
        # Tạo ID xử lý duy nhất
        processing_id = str(uuid.uuid4())
        
        # Tạo thông tin xử lý
        processing_info = ArchiveProcessingInfo(
            id=processing_id,
            archive_id="",  # Sẽ được cập nhật sau khi nén xong
            operation_type="compress"
        )
        
        # Lưu thông tin xử lý
        await self.processing_repo.create_processing(processing_info)
        
        # Gửi tác vụ vào queue
        await self.rabbitmq_client.publish_message(
            queue="compress_queue",
            message={
                "processing_id": processing_id,
                "file_ids": dto.file_ids,
                "output_filename": dto.output_filename,
                "archive_format": dto.archive_format,
                "password": dto.password,
                "compression_level": dto.compression_level
            }
        )
        
        return {
            "processing_id": processing_id,
            "status": "processing",
            "message": "Đã bắt đầu nén tệp"
        }

    async def add_files_to_archive(self, dto: AddFilesToArchiveDTO) -> Dict[str, Any]:
        """Thêm tệp vào tệp nén."""
        # Tạo ID xử lý duy nhất
        processing_id = str(uuid.uuid4())
        
        # Tạo thông tin xử lý
        processing_info = ArchiveProcessingInfo(
            id=processing_id,
            archive_id=dto.archive_id,
            operation_type="add_files"
        )
        
        # Lưu thông tin xử lý
        await self.processing_repo.create_processing(processing_info)
        
        # Gửi tác vụ vào queue
        await self.rabbitmq_client.publish_message(
            queue="archive_modify_queue",
            message={
                "processing_id": processing_id,
                "archive_id": dto.archive_id,
                "file_ids": dto.file_ids,
                "password": dto.password,
                "operation": "add"
            }
        )
        
        return {
            "processing_id": processing_id,
            "status": "processing",
            "message": "Đã bắt đầu thêm tệp vào tệp nén"
        }

    async def remove_files_from_archive(self, dto: RemoveFilesFromArchiveDTO) -> Dict[str, Any]:
        """Xóa tệp khỏi tệp nén."""
        # Tạo ID xử lý duy nhất
        processing_id = str(uuid.uuid4())
        
        # Tạo thông tin xử lý
        processing_info = ArchiveProcessingInfo(
            id=processing_id,
            archive_id=dto.archive_id,
            operation_type="remove_files"
        )
        
        # Lưu thông tin xử lý
        await self.processing_repo.create_processing(processing_info)
        
        # Gửi tác vụ vào queue
        await self.rabbitmq_client.publish_message(
            queue="archive_modify_queue",
            message={
                "processing_id": processing_id,
                "archive_id": dto.archive_id,
                "file_paths": dto.file_paths,
                "password": dto.password,
                "operation": "remove"
            }
        )
        
        return {
            "processing_id": processing_id,
            "status": "processing",
            "message": "Đã bắt đầu xóa tệp khỏi tệp nén"
        }

    async def encrypt_archive(self, dto: EncryptArchiveDTO) -> Dict[str, Any]:
        """Mã hóa tệp nén."""
        # Tạo ID xử lý duy nhất
        processing_id = str(uuid.uuid4())
        
        # Tạo thông tin xử lý
        processing_info = ArchiveProcessingInfo(
            id=processing_id,
            archive_id=dto.archive_id,
            operation_type="encrypt"
        )
        
        # Lưu thông tin xử lý
        await self.processing_repo.create_processing(processing_info)
        
        # Gửi tác vụ vào queue
        await self.rabbitmq_client.publish_message(
            queue="archive_security_queue",
            message={
                "processing_id": processing_id,
                "archive_id": dto.archive_id,
                "password": dto.password,
                "operation": "encrypt"
            }
        )
        
        return {
            "processing_id": processing_id,
            "status": "processing",
            "message": "Đã bắt đầu mã hóa tệp nén"
        }

    async def decrypt_archive(self, dto: DecryptArchiveDTO) -> Dict[str, Any]:
        """Giải mã tệp nén."""
        # Tạo ID xử lý duy nhất
        processing_id = str(uuid.uuid4())
        
        # Tạo thông tin xử lý
        processing_info = ArchiveProcessingInfo(
            id=processing_id,
            archive_id=dto.archive_id,
            operation_type="decrypt"
        )
        
        # Lưu thông tin xử lý
        await self.processing_repo.create_processing(processing_info)
        
        # Gửi tác vụ vào queue
        await self.rabbitmq_client.publish_message(
            queue="archive_security_queue",
            message={
                "processing_id": processing_id,
                "archive_id": dto.archive_id,
                "password": dto.password,
                "operation": "decrypt"
            }
        )
        
        return {
            "processing_id": processing_id,
            "status": "processing",
            "message": "Đã bắt đầu giải mã tệp nén"
        }

    async def crack_archive_password(self, dto: CrackArchiveDTO) -> Dict[str, Any]:
        """Crack mật khẩu tệp nén."""
        # Tạo ID xử lý duy nhất
        processing_id = str(uuid.uuid4())
        
        # Tạo thông tin xử lý
        processing_info = ArchiveProcessingInfo(
            id=processing_id,
            archive_id=dto.archive_id,
            operation_type="crack"
        )
        
        # Lưu thông tin xử lý
        await self.processing_repo.create_processing(processing_info)
        
        # Gửi tác vụ vào queue
        await self.rabbitmq_client.publish_message(
            queue="archive_security_queue",
            message={
                "processing_id": processing_id,
                "archive_id": dto.archive_id,
                "max_length": dto.max_length,
                "character_set": dto.character_set,
                "operation": "crack"
            }
        )
        
        return {
            "processing_id": processing_id,
            "status": "processing",
            "message": "Đã bắt đầu crack mật khẩu tệp nén"
        }

    async def convert_archive(self, dto: ConvertArchiveDTO) -> Dict[str, Any]:
        """Chuyển đổi định dạng tệp nén."""
        # Tạo ID xử lý duy nhất
        processing_id = str(uuid.uuid4())
        
        # Tạo thông tin xử lý
        processing_info = ArchiveProcessingInfo(
            id=processing_id,
            archive_id=dto.archive_id,
            operation_type="convert"
        )
        
        # Lưu thông tin xử lý
        await self.processing_repo.create_processing(processing_info)
        
        # Gửi tác vụ vào queue
        await self.rabbitmq_client.publish_message(
            queue="archive_convert_queue",
            message={
                "processing_id": processing_id,
                "archive_id": dto.archive_id,
                "output_format": dto.output_format,
                "password": dto.password
            }
        )
        
        return {
            "processing_id": processing_id,
            "status": "processing",
            "message": "Đã bắt đầu chuyển đổi định dạng tệp nén"
        }

    async def get_processing_status(self, processing_id: str) -> Dict[str, Any]:
        """Lấy trạng thái xử lý."""
        processing_info = await self.processing_repo.get_processing(processing_id)
        if not processing_info:
            return {
                "status": "not_found",
                "message": f"Không tìm thấy thông tin xử lý với ID: {processing_id}"
            }
        
        return {
            "processing_id": processing_info.id,
            "archive_id": processing_info.archive_id,
            "operation_type": processing_info.operation_type,
            "status": processing_info.status,
            "started_at": processing_info.started_at.isoformat(),
            "completed_at": processing_info.completed_at.isoformat() if processing_info.completed_at else None,
            "result": processing_info.result,
            "error": processing_info.error
        }

    def _get_archive_format(self, filename: str) -> ArchiveFormat:
        """Lấy định dạng tệp nén từ tên tệp."""
        lower_filename = filename.lower()
        
        if lower_filename.endswith('.zip'):
            return ArchiveFormat.ZIP
        elif lower_filename.endswith('.rar'):
            return ArchiveFormat.RAR
        elif lower_filename.endswith('.7z'):
            return ArchiveFormat.SEVEN_ZIP
        elif lower_filename.endswith('.tar'):
            return ArchiveFormat.TAR
        elif lower_filename.endswith('.gz') and not lower_filename.endswith('.tar.gz'):
            return ArchiveFormat.GZIP
        elif lower_filename.endswith('.tar.gz') or lower_filename.endswith('.tgz'):
            return ArchiveFormat.TAR_GZIP
        else:
            supported_formats = ", ".join(f.value for f in ArchiveFormat)
            raise UnsupportedFormatException(f"Định dạng không được hỗ trợ. Hỗ trợ: {supported_formats}") 