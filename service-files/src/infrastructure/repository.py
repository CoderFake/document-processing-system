import os
import json
import tempfile
from datetime import datetime
from typing import List, Dict, Any, Optional, BinaryIO

from domain.models import ArchiveInfo, ArchiveProcessingInfo
from domain.exceptions import ArchiveNotFoundException, StorageException
from infrastructure.minio_client import MinioClient
from core.config import settings


class ArchiveRepository:
    def __init__(self, minio_client: MinioClient):
        self.minio_client = minio_client
        self._archives_cache: Dict[str, ArchiveInfo] = {}
        
    async def create_archive(self, archive_info: ArchiveInfo) -> None:
        """Tạo thông tin tệp nén mới."""
        self._archives_cache[archive_info.id] = archive_info
        await self._save_archive_metadata(archive_info)
        
    async def get_archive(self, archive_id: str, user_id: Optional[int] = None) -> Optional[ArchiveInfo]:
        """Lấy thông tin tệp nén theo ID."""
        if archive_id in self._archives_cache:
            archive_info = self._archives_cache[archive_id]
            if user_id is not None and archive_info.user_id is not None and archive_info.user_id != user_id:
                return None
            return archive_info
            
        try:
            metadata_json = await self.minio_client.get_object(
                bucket_name=settings.MINIO_ARCHIVE_BUCKET,
                object_name=f"metadata/{archive_id}.json"
            )
            
            if not metadata_json:
                return None
                
            metadata = json.loads(metadata_json)
            
            if user_id is not None and metadata.get("user_id") is not None and metadata.get("user_id") != user_id:
                return None
                
            archive_info = ArchiveInfo(
                id=metadata["id"],
                title=metadata["title"],
                description=metadata["description"],
                format=metadata["format"],
                file_size=metadata["file_size"],
                original_filename=metadata["original_filename"],
                storage_path=metadata["storage_path"],
                is_encrypted=metadata["is_encrypted"],
                user_id=metadata.get("user_id"),
                created_at=datetime.fromisoformat(metadata["created_at"]),
                updated_at=datetime.fromisoformat(metadata["updated_at"]) if metadata.get("updated_at") else None,
                metadata=metadata.get("metadata", {})
            )
            
            self._archives_cache[archive_id] = archive_info
            return archive_info
        except Exception as e:
            return None
            
    async def get_archive_content(self, archive_id: str, user_id: Optional[int] = None) -> bytes:
        """Lấy nội dung tệp nén theo ID."""
        archive_info = await self.get_archive(archive_id, user_id)
        if not archive_info:
            raise ArchiveNotFoundException(archive_id)
            
        try:
            content = await self.minio_client.get_object(
                bucket_name=settings.MINIO_ARCHIVE_BUCKET,
                object_name=archive_info.storage_path
            )
            
            if not content:
                raise StorageException(f"Không thể tải nội dung tệp nén: {archive_id}")
                
            return content
        except Exception as e:
            raise StorageException(f"Lỗi khi tải nội dung tệp nén: {str(e)}")
            
    async def update_archive(self, archive_info: ArchiveInfo) -> None:
        """Cập nhật thông tin tệp nén."""
        archive_info.updated_at = datetime.now()
        self._archives_cache[archive_info.id] = archive_info
        await self._save_archive_metadata(archive_info)
        
    async def delete_archive(self, archive_id: str, user_id: Optional[int] = None) -> None:
        """Xóa tệp nén."""
        archive_info = await self.get_archive(archive_id, user_id)
        if not archive_info:
            raise ArchiveNotFoundException(archive_id)
            
        try:
            await self.minio_client.remove_object(
                bucket_name=settings.MINIO_ARCHIVE_BUCKET,
                object_name=archive_info.storage_path
            )
            
            await self.minio_client.remove_object(
                bucket_name=settings.MINIO_ARCHIVE_BUCKET,
                object_name=f"metadata/{archive_id}.json"
            )

            if archive_id in self._archives_cache:
                del self._archives_cache[archive_id]
                
        except Exception as e:
            raise StorageException(f"Lỗi khi xóa tệp nén: {str(e)}")
            
    async def get_archives(self, skip: int = 0, limit: int = 10, search: Optional[str] = None, user_id: Optional[int] = None) -> List[ArchiveInfo]:
        """Lấy danh sách tệp nén."""
        try:
            objects = await self.minio_client.list_objects(
                bucket_name=settings.MINIO_ARCHIVE_BUCKET,
                prefix="metadata/",
                recursive=True
            )
            
            archives = []
            
            for obj in objects:
                if obj.object_name.endswith(".json"):
                    try:
                        metadata_json = await self.minio_client.get_object(
                            bucket_name=settings.MINIO_ARCHIVE_BUCKET,
                            object_name=obj.object_name
                        )
                        
                        if not metadata_json:
                            continue
                            
                        metadata = json.loads(metadata_json)
                        
                        if user_id is not None and metadata.get("user_id") is not None and metadata.get("user_id") != user_id:
                            continue
                            
                        if search and search.lower() not in metadata["title"].lower():
                            continue
                            
                        archive_info = ArchiveInfo(
                            id=metadata["id"],
                            title=metadata["title"],
                            description=metadata["description"],
                            format=metadata["format"],
                            file_size=metadata["file_size"],
                            original_filename=metadata["original_filename"],
                            storage_path=metadata["storage_path"],
                            is_encrypted=metadata["is_encrypted"],
                            user_id=metadata.get("user_id"),
                            created_at=datetime.fromisoformat(metadata["created_at"]),
                            updated_at=datetime.fromisoformat(metadata["updated_at"]) if metadata.get("updated_at") else None,
                            metadata=metadata.get("metadata", {})
                        )
                        
                        self._archives_cache[archive_info.id] = archive_info
                        archives.append(archive_info)
                    except:
                        continue
            
            archives.sort(key=lambda x: x.created_at, reverse=True)
            
            return archives[skip:skip+limit]
        except Exception as e:
            raise StorageException(f"Lỗi khi lấy danh sách tệp nén: {str(e)}")
    
    async def save_archive(self, archive_id: str, content: bytes) -> str:
        """Lưu nội dung tệp nén và trả về đường dẫn lưu trữ."""
        try:
            object_name = f"archives/{archive_id}"
            
            await self.minio_client.put_object(
                bucket_name=settings.MINIO_ARCHIVE_BUCKET,
                object_name=object_name,
                data=content
            )
            
            return object_name
        except Exception as e:
            raise StorageException(f"Lỗi khi lưu tệp nén: {str(e)}")
    
    async def _save_archive_metadata(self, archive_info: ArchiveInfo) -> None:
        """Lưu metadata của tệp nén."""
        try:
            metadata = {
                "id": archive_info.id,
                "title": archive_info.title,
                "description": archive_info.description,
                "format": archive_info.format.value,
                "file_size": archive_info.file_size,
                "original_filename": archive_info.original_filename,
                "storage_path": archive_info.storage_path,
                "is_encrypted": archive_info.is_encrypted,
                "user_id": archive_info.user_id,
                "created_at": archive_info.created_at.isoformat(),
                "updated_at": archive_info.updated_at.isoformat() if archive_info.updated_at else None,
                "metadata": archive_info.metadata
            }
            
            await self.minio_client.put_object(
                bucket_name=settings.MINIO_ARCHIVE_BUCKET,
                object_name=f"metadata/{archive_info.id}.json",
                data=json.dumps(metadata).encode('utf-8')
            )
        except Exception as e:
            raise StorageException(f"Lỗi khi lưu metadata tệp nén: {str(e)}")


class ProcessingRepository:
    def __init__(self, minio_client: MinioClient):
        self.minio_client = minio_client
        self._processing_cache: Dict[str, ArchiveProcessingInfo] = {}
        
    async def create_processing(self, processing_info: ArchiveProcessingInfo) -> None:
        """Tạo thông tin xử lý mới."""
        self._processing_cache[processing_info.id] = processing_info
        await self._save_processing_metadata(processing_info)
        
    async def get_processing(self, processing_id: str, user_id: Optional[int] = None) -> Optional[ArchiveProcessingInfo]:
        """Lấy thông tin xử lý theo ID."""
        if processing_id in self._processing_cache:
            processing_info = self._processing_cache[processing_id]
            if user_id is not None and processing_info.user_id is not None and processing_info.user_id != user_id:
                return None
            return processing_info
            
        try:
            metadata_json = await self.minio_client.get_object(
                bucket_name=settings.MINIO_ARCHIVE_BUCKET,
                object_name=f"processing/{processing_id}.json"
            )
            
            if not metadata_json:
                return None
                
            metadata = json.loads(metadata_json)
            
            if user_id is not None and metadata.get("user_id") is not None and metadata.get("user_id") != user_id:
                return None
                
            processing_info = ArchiveProcessingInfo(
                id=metadata["id"],
                archive_id=metadata["archive_id"],
                operation_type=metadata["operation_type"],
                status=metadata["status"],
                user_id=metadata.get("user_id"),
                started_at=datetime.fromisoformat(metadata["started_at"]),
                completed_at=datetime.fromisoformat(metadata["completed_at"]) if metadata.get("completed_at") else None,
                result=metadata.get("result"),
                error=metadata.get("error")
            )
            
            self._processing_cache[processing_id] = processing_info
            return processing_info
        except Exception as e:
            return None
            
    async def update_processing(self, processing_info: ArchiveProcessingInfo) -> None:
        """Cập nhật thông tin xử lý."""
        self._processing_cache[processing_info.id] = processing_info
        await self._save_processing_metadata(processing_info)
        
    async def delete_processing(self, processing_id: str, user_id: Optional[int] = None) -> None:
        """Xóa thông tin xử lý."""
        processing_info = await self.get_processing(processing_id, user_id)
        if not processing_info:
            return
            
        try:
            await self.minio_client.remove_object(
                bucket_name=settings.MINIO_ARCHIVE_BUCKET,
                object_name=f"processing/{processing_id}.json"
            )
            
            if processing_id in self._processing_cache:
                del self._processing_cache[processing_id]
                
        except Exception as e:
            pass
            
    async def _save_processing_metadata(self, processing_info: ArchiveProcessingInfo) -> None:
        """Lưu metadata của thông tin xử lý."""
        try:
            metadata = {
                "id": processing_info.id,
                "archive_id": processing_info.archive_id,
                "operation_type": processing_info.operation_type,
                "status": processing_info.status,
                "user_id": processing_info.user_id,
                "started_at": processing_info.started_at.isoformat(),
                "completed_at": processing_info.completed_at.isoformat() if processing_info.completed_at else None,
                "result": processing_info.result,
                "error": processing_info.error
            }
            
            await self.minio_client.put_object(
                bucket_name=settings.MINIO_ARCHIVE_BUCKET,
                object_name=f"processing/{processing_info.id}.json",
                data=json.dumps(metadata).encode('utf-8')
            )
        except Exception as e:
            pass 