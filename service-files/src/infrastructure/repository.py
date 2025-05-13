import os
import json
import tempfile
from datetime import datetime
from typing import List, Dict, Any, Optional, BinaryIO

from domain.models import ArchiveInfo, ArchiveProcessingInfo, FileInfo
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


class FileRepository:
    def __init__(self, minio_client: MinioClient):
        self.minio_client = minio_client
        self._files_cache: Dict[str, FileInfo] = {}
        
    async def create_file(self, file_info: FileInfo) -> None:
        """Tạo thông tin tệp mới."""
        self._files_cache[file_info.id] = file_info
        await self._save_file_metadata(file_info)
        
    async def get_file(self, file_id: str, user_id: Optional[int] = None) -> Optional[FileInfo]:
        """Lấy thông tin tệp theo ID."""
        if file_id in self._files_cache:
            file_info = self._files_cache[file_id]
            if user_id is not None and getattr(file_info, 'user_id', None) is not None and file_info.user_id != user_id:
                return None
            return file_info
            
        try:
            metadata_json = await self.minio_client.get_object(
                bucket_name=settings.MINIO_FILES_BUCKET,
                object_name=f"metadata/{file_id}.json"
            )
            
            if not metadata_json:
                return None
                
            metadata = json.loads(metadata_json)
            
            if user_id is not None and metadata.get("user_id") is not None and metadata.get("user_id") != user_id:
                return None
                
            file_info = FileInfo(
                id=metadata["id"],
                title=metadata["title"],
                description=metadata["description"],
                file_size=metadata["file_size"],
                file_type=metadata["file_type"],
                original_filename=metadata["original_filename"],
                storage_path=metadata["storage_path"],
                created_at=datetime.fromisoformat(metadata["created_at"]),
                updated_at=datetime.fromisoformat(metadata["updated_at"]) if metadata.get("updated_at") else None,
                metadata=metadata.get("metadata", {})
            )
            
            self._files_cache[file_id] = file_info
            return file_info
        except Exception as e:
            return None
            
    async def get_file_content(self, file_id: str, user_id: Optional[int] = None) -> bytes:
        """Lấy nội dung tệp theo ID."""
        file_info = await self.get_file(file_id, user_id)
        if not file_info:
            raise FileNotFoundException(file_id)
            
        try:
            content = await self.minio_client.get_object(
                bucket_name=settings.MINIO_FILES_BUCKET,
                object_name=file_info.storage_path
            )
            
            if not content:
                raise StorageException(f"Không thể tải nội dung tệp: {file_id}")
                
            return content
        except Exception as e:
            raise StorageException(f"Lỗi khi tải nội dung tệp: {str(e)}")
            
    async def update_file(self, file_info: FileInfo) -> None:
        """Cập nhật thông tin tệp."""
        file_info.updated_at = datetime.now()
        self._files_cache[file_info.id] = file_info
        await self._save_file_metadata(file_info)
        
    async def delete_file(self, file_id: str, user_id: Optional[int] = None) -> None:
        """Xóa tệp."""
        file_info = await self.get_file(file_id, user_id)
        if not file_info:
            raise FileNotFoundException(file_id)
            
        try:
            await self.minio_client.remove_object(
                bucket_name=settings.MINIO_FILES_BUCKET,
                object_name=file_info.storage_path
            )
            
            await self.minio_client.remove_object(
                bucket_name=settings.MINIO_FILES_BUCKET,
                object_name=f"metadata/{file_id}.json"
            )

            if file_id in self._files_cache:
                del self._files_cache[file_id]
                
        except Exception as e:
            raise StorageException(f"Lỗi khi xóa tệp: {str(e)}")
            
    async def get_files(self, skip: int = 0, limit: int = 10, filter_dto = None, user_id: Optional[int] = None) -> List[FileInfo]:
        """Lấy danh sách tệp."""
        try:
            objects = await self.minio_client.list_objects(
                bucket_name=settings.MINIO_FILES_BUCKET,
                prefix="metadata/",
                recursive=True
            )
            
            files = []
            
            for obj in objects:
                if obj.object_name.endswith(".json"):
                    try:
                        metadata_json = await self.minio_client.get_object(
                            bucket_name=settings.MINIO_FILES_BUCKET,
                            object_name=obj.object_name
                        )
                        
                        if not metadata_json:
                            continue
                            
                        metadata = json.loads(metadata_json)
                        
                        if user_id is not None and metadata.get("user_id") is not None and metadata.get("user_id") != user_id:
                            continue
                            
                        if filter_dto:
                            if filter_dto.search and filter_dto.search.lower() not in metadata["title"].lower():
                                continue
                            if filter_dto.file_type and filter_dto.file_type != metadata["file_type"]:
                                continue
                            if filter_dto.date_from and datetime.fromisoformat(metadata["created_at"]) < datetime.fromisoformat(filter_dto.date_from):
                                continue
                            if filter_dto.date_to and datetime.fromisoformat(metadata["created_at"]) > datetime.fromisoformat(filter_dto.date_to):
                                continue
                        
                        file_info = FileInfo(
                            id=metadata["id"],
                            title=metadata["title"],
                            description=metadata["description"],
                            file_size=metadata["file_size"],
                            file_type=metadata["file_type"],
                            original_filename=metadata["original_filename"],
                            storage_path=metadata["storage_path"],
                            created_at=datetime.fromisoformat(metadata["created_at"]),
                            updated_at=datetime.fromisoformat(metadata["updated_at"]) if metadata.get("updated_at") else None,
                            metadata=metadata.get("metadata", {})
                        )
                        
                        self._files_cache[file_info.id] = file_info
                        files.append(file_info)
                    except:
                        continue
            
            # Sắp xếp theo thứ tự thời gian tạo giảm dần (mới nhất lên đầu)
            files.sort(key=lambda x: x.created_at, reverse=True)
            
            return files[skip:skip+limit]
        except Exception as e:
            raise StorageException(f"Lỗi khi lấy danh sách tệp: {str(e)}")
    
    async def save_file(self, file_id: str, content: bytes) -> str:
        """Lưu nội dung tệp và trả về đường dẫn lưu trữ."""
        try:
            object_name = f"files/{file_id}"
            
            await self.minio_client.put_object(
                bucket_name=settings.MINIO_FILES_BUCKET,
                object_name=object_name,
                data=content
            )
            
            return object_name
        except Exception as e:
            raise StorageException(f"Lỗi khi lưu tệp: {str(e)}")
    
    async def _save_file_metadata(self, file_info: FileInfo) -> None:
        """Lưu metadata của tệp."""
        try:
            metadata = {
                "id": file_info.id,
                "title": file_info.title,
                "description": file_info.description,
                "file_size": file_info.file_size,
                "file_type": file_info.file_type,
                "original_filename": file_info.original_filename,
                "storage_path": file_info.storage_path,
                "created_at": file_info.created_at.isoformat(),
                "updated_at": file_info.updated_at.isoformat() if file_info.updated_at else None,
                "metadata": file_info.metadata
            }
            
            # Thêm user_id nếu có
            if hasattr(file_info, 'user_id') and file_info.user_id is not None:
                metadata["user_id"] = file_info.user_id
                
            await self.minio_client.put_object(
                bucket_name=settings.MINIO_FILES_BUCKET,
                object_name=f"metadata/{file_info.id}.json",
                data=json.dumps(metadata).encode('utf-8')
            )
        except Exception as e:
            raise StorageException(f"Lỗi khi lưu metadata tệp: {str(e)}")
            
    async def move_to_trash(self, file_id: str, user_id: Optional[int] = None) -> None:
        """Di chuyển tệp vào thùng rác."""
        file_info = await self.get_file(file_id, user_id)
        if not file_info:
            raise FileNotFoundException(file_id)
            
        try:
            # Đưa tệp vào thư mục trash
            trash_path = f"trash/{file_info.storage_path.split('/')[-1]}"
            
            content = await self.get_file_content(file_id, user_id)
            
            await self.minio_client.put_object(
                bucket_name=settings.MINIO_FILES_BUCKET,
                object_name=trash_path,
                data=content
            )
            
            # Cập nhật metadata
            metadata = {
                "id": file_info.id,
                "title": file_info.title,
                "description": file_info.description,
                "file_size": file_info.file_size,
                "file_type": file_info.file_type,
                "original_filename": file_info.original_filename,
                "original_path": file_info.storage_path,
                "trash_path": trash_path,
                "deleted_at": datetime.now().isoformat(),
                "created_at": file_info.created_at.isoformat(),
                "updated_at": file_info.updated_at.isoformat() if file_info.updated_at else None,
                "metadata": file_info.metadata
            }
            
            if hasattr(file_info, 'user_id') and file_info.user_id is not None:
                metadata["user_id"] = file_info.user_id
                
            await self.minio_client.put_object(
                bucket_name=settings.MINIO_FILES_BUCKET,
                object_name=f"trash_metadata/{file_info.id}.json",
                data=json.dumps(metadata).encode('utf-8')
            )
            
            # Xóa tệp gốc
            await self.delete_file(file_id, user_id)
            
        except Exception as e:
            raise StorageException(f"Lỗi khi di chuyển tệp vào thùng rác: {str(e)}")
            
    async def restore_from_trash(self, file_id: str, user_id: Optional[int] = None) -> None:
        """Khôi phục tệp từ thùng rác."""
        try:
            # Lấy metadata từ thùng rác
            metadata_json = await self.minio_client.get_object(
                bucket_name=settings.MINIO_FILES_BUCKET,
                object_name=f"trash_metadata/{file_id}.json"
            )
            
            if not metadata_json:
                raise FileNotFoundException(f"Không tìm thấy tệp trong thùng rác: {file_id}")
                
            metadata = json.loads(metadata_json)
            
            if user_id is not None and metadata.get("user_id") is not None and metadata.get("user_id") != user_id:
                raise FileNotFoundException(f"Không tìm thấy tệp trong thùng rác: {file_id}")
                
            # Lấy nội dung từ thùng rác
            content = await self.minio_client.get_object(
                bucket_name=settings.MINIO_FILES_BUCKET,
                object_name=metadata["trash_path"]
            )
            
            if not content:
                raise StorageException(f"Không thể tải nội dung tệp từ thùng rác: {file_id}")
                
            # Khôi phục tệp
            await self.minio_client.put_object(
                bucket_name=settings.MINIO_FILES_BUCKET,
                object_name=metadata["original_path"],
                data=content
            )
            
            # Khôi phục metadata
            file_info = FileInfo(
                id=metadata["id"],
                title=metadata["title"],
                description=metadata["description"],
                file_size=metadata["file_size"],
                file_type=metadata["file_type"],
                original_filename=metadata["original_filename"],
                storage_path=metadata["original_path"],
                created_at=datetime.fromisoformat(metadata["created_at"]),
                updated_at=datetime.now(),
                metadata=metadata.get("metadata", {})
            )
            
            # Thêm user_id nếu có
            if metadata.get("user_id") is not None:
                file_info.user_id = metadata["user_id"]
                
            await self._save_file_metadata(file_info)
            
            # Xóa tệp khỏi thùng rác
            await self.minio_client.remove_object(
                bucket_name=settings.MINIO_FILES_BUCKET,
                object_name=metadata["trash_path"]
            )
            
            await self.minio_client.remove_object(
                bucket_name=settings.MINIO_FILES_BUCKET,
                object_name=f"trash_metadata/{file_id}.json"
            )
            
            self._files_cache[file_id] = file_info
            
        except FileNotFoundException:
            raise
        except Exception as e:
            raise StorageException(f"Lỗi khi khôi phục tệp từ thùng rác: {str(e)}")
            
    async def get_trash_items(self, skip: int = 0, limit: int = 10, user_id: Optional[int] = None) -> List[FileInfo]:
        """Lấy danh sách tệp trong thùng rác."""
        try:
            objects = await self.minio_client.list_objects(
                bucket_name=settings.MINIO_FILES_BUCKET,
                prefix="trash_metadata/",
                recursive=True
            )
            
            trash_items = []
            
            for obj in objects:
                if obj.object_name.endswith(".json"):
                    try:
                        metadata_json = await self.minio_client.get_object(
                            bucket_name=settings.MINIO_FILES_BUCKET,
                            object_name=obj.object_name
                        )
                        
                        if not metadata_json:
                            continue
                            
                        metadata = json.loads(metadata_json)
                        
                        if user_id is not None and metadata.get("user_id") is not None and metadata.get("user_id") != user_id:
                            continue
                            
                        file_info = FileInfo(
                            id=metadata["id"],
                            title=metadata["title"],
                            description=metadata["description"],
                            file_size=metadata["file_size"],
                            file_type=metadata["file_type"],
                            original_filename=metadata["original_filename"],
                            storage_path=metadata["trash_path"],
                            created_at=datetime.fromisoformat(metadata["created_at"]),
                            updated_at=datetime.fromisoformat(metadata["deleted_at"]),
                            metadata={
                                **metadata.get("metadata", {}),
                                "deleted_at": metadata["deleted_at"],
                                "original_path": metadata["original_path"]
                            }
                        )
                        
                        trash_items.append(file_info)
                    except:
                        continue
            
            # Sắp xếp theo thứ tự thời gian xóa giảm dần (mới nhất lên đầu)
            trash_items.sort(key=lambda x: x.updated_at, reverse=True)
            
            return trash_items[skip:skip+limit]
        except Exception as e:
            raise StorageException(f"Lỗi khi lấy danh sách tệp trong thùng rác: {str(e)}")
            
    async def empty_trash(self, user_id: Optional[int] = None) -> int:
        """Làm trống thùng rác."""
        try:
            # Lấy danh sách tệp trong thùng rác
            objects = await self.minio_client.list_objects(
                bucket_name=settings.MINIO_FILES_BUCKET,
                prefix="trash_metadata/",
                recursive=True
            )
            
            trash_files_to_delete = []
            
            for obj in objects:
                if obj.object_name.endswith(".json"):
                    try:
                        metadata_json = await self.minio_client.get_object(
                            bucket_name=settings.MINIO_FILES_BUCKET,
                            object_name=obj.object_name
                        )
                        
                        if not metadata_json:
                            continue
                            
                        metadata = json.loads(metadata_json)
                        
                        if user_id is not None and metadata.get("user_id") is not None and metadata.get("user_id") != user_id:
                            continue
                            
                        trash_files_to_delete.append({
                            "id": metadata["id"],
                            "trash_path": metadata["trash_path"]
                        })
                    except:
                        continue
            
            # Xóa từng tệp
            count = 0
            for file_info in trash_files_to_delete:
                try:
                    # Xóa tệp trong thùng rác
                    await self.minio_client.remove_object(
                        bucket_name=settings.MINIO_FILES_BUCKET,
                        object_name=file_info["trash_path"]
                    )
                    
                    # Xóa metadata
                    await self.minio_client.remove_object(
                        bucket_name=settings.MINIO_FILES_BUCKET,
                        object_name=f"trash_metadata/{file_info['id']}.json"
                    )
                    
                    count += 1
                except:
                    continue
            
            return count
        except Exception as e:
            raise StorageException(f"Lỗi khi làm trống thùng rác: {str(e)}")


class CompressJobRepository:
    def __init__(self):
        self._jobs = {}
        
    async def create_job(self, job_id: str, info: Dict[str, Any]) -> None:
        self._jobs[job_id] = {
            "id": job_id,
            "status": "processing",
            "created_at": datetime.now(),
            "info": info,
            "result": None,
            "error": None
        }
        
    async def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self._jobs.get(job_id)
        
    async def update_job(self, job_id: str, status: str, result: Optional[Dict[str, Any]] = None, error: Optional[str] = None) -> None:
        if job_id in self._jobs:
            self._jobs[job_id].update({
                "status": status,
                "updated_at": datetime.now(),
                "result": result,
                "error": error
            })


class DecompressJobRepository:
    def __init__(self):
        self._jobs = {}
        
    async def create_job(self, job_id: str, info: Dict[str, Any]) -> None:
        self._jobs[job_id] = {
            "id": job_id,
            "status": "processing",
            "created_at": datetime.now(),
            "info": info,
            "result": None,
            "error": None
        }
        
    async def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self._jobs.get(job_id)
        
    async def update_job(self, job_id: str, status: str, result: Optional[Dict[str, Any]] = None, error: Optional[str] = None) -> None:
        if job_id in self._jobs:
            self._jobs[job_id].update({
                "status": status,
                "updated_at": datetime.now(),
                "result": result,
                "error": error
            })


class CrackJobRepository:
    def __init__(self):
        self._jobs = {}
        
    async def create_job(self, job_id: str, info: Dict[str, Any]) -> None:
        self._jobs[job_id] = {
            "id": job_id,
            "status": "processing",
            "created_at": datetime.now(),
            "info": info,
            "result": None,
            "error": None
        }
        
    async def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self._jobs.get(job_id)
        
    async def update_job(self, job_id: str, status: str, result: Optional[Dict[str, Any]] = None, error: Optional[str] = None) -> None:
        if job_id in self._jobs:
            self._jobs[job_id].update({
                "status": status,
                "updated_at": datetime.now(),
                "result": result,
                "error": error
            })


class CleanupJobRepository:
    def __init__(self):
        self._jobs = {}
        
    async def create_job(self, job_id: str, info: Dict[str, Any]) -> None:
        self._jobs[job_id] = {
            "id": job_id,
            "status": "processing",
            "created_at": datetime.now(),
            "info": info,
            "result": None,
            "error": None
        }
        
    async def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self._jobs.get(job_id)
        
    async def update_job(self, job_id: str, status: str, result: Optional[Dict[str, Any]] = None, error: Optional[str] = None) -> None:
        if job_id in self._jobs:
            self._jobs[job_id].update({
                "status": status,
                "updated_at": datetime.now(),
                "result": result,
                "error": error
            })


class TrashRepository:
    def __init__(self):
        self._trash_items = {}
        
    async def add_item(self, item_id: str, item_type: str, item_data: Dict[str, Any]) -> None:
        self._trash_items[item_id] = {
            "id": item_id,
            "type": item_type,
            "data": item_data,
            "deleted_at": datetime.now()
        }
        
    async def get_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        return self._trash_items.get(item_id)
        
    async def get_items(self, skip: int = 0, limit: int = 10) -> List[Dict[str, Any]]:
        items = list(self._trash_items.values())
        items.sort(key=lambda x: x["deleted_at"], reverse=True)
        return items[skip:skip+limit]
        
    async def delete_item(self, item_id: str) -> bool:
        if item_id in self._trash_items:
            del self._trash_items[item_id]
            return True
        return False
        
    async def empty_trash(self) -> int:
        count = len(self._trash_items)
        self._trash_items.clear()
        return count 