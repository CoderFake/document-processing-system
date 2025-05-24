import os
import json
import tempfile
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, BinaryIO

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update as sqlalchemy_update, delete as sqlalchemy_delete, and_, func

from domain.models import ArchiveInfo, ArchiveProcessingInfo, FileInfo, DBDocument
from domain.exceptions import ArchiveNotFoundException, StorageException, FileNotFoundException
from infrastructure.minio_client import MinioClient
from core.config import settings
import logging

logger = logging.getLogger(__name__)


class ArchiveRepository:
    def __init__(self, minio_client: MinioClient):
        self.minio_client = minio_client
        self._archives_cache: Dict[str, ArchiveInfo] = {}
        
    async def create_archive(self, archive_info: ArchiveInfo) -> None:
        """Tạo thông tin tệp nén mới."""
        self._archives_cache[archive_info.id] = archive_info
        await self._save_archive_metadata(archive_info)
        
    async def get_archive(self, archive_id: str, user_id: Optional[str] = None) -> Optional[ArchiveInfo]:
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
                
            doc_metadata = json.loads(metadata_json)
            
            if user_id is not None and doc_metadata.get("user_id") is not None and doc_metadata.get("user_id") != user_id:
                return None
                
            archive_info = ArchiveInfo(
                id=doc_metadata["id"],
                title=doc_metadata["title"],
                description=doc_metadata["description"],
                file_size=doc_metadata["file_size"],
                original_filename=doc_metadata["original_filename"],
                storage_path=doc_metadata["storage_path"],
                user_id=doc_metadata.get("user_id"),
                created_at=datetime.fromisoformat(doc_metadata["created_at"]),
                updated_at=datetime.fromisoformat(doc_metadata["updated_at"]) if doc_metadata.get("updated_at") else None,
                doc_metadata=doc_metadata.get("doc_metadata", {}),
                compression_type=doc_metadata.get("compression_type", doc_metadata.get("format")),
                file_type=doc_metadata.get("file_type", "application/octet-stream")
            )
            
            self._archives_cache[archive_id] = archive_info
            return archive_info
        except Exception as e:
            return None
            
    async def get_archive_content(self, archive_id: str, user_id: Optional[str] = None) -> bytes:
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
        
    async def delete_archive(self, archive_id: str, user_id: Optional[str] = None) -> None:
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
            
    async def get_archives(self, skip: int = 0, limit: int = 10, search: Optional[str] = None, user_id: Optional[str] = None) -> List[ArchiveInfo]:
        """Lấy danh sách tệp nén."""
        try:
            objects = await self.minio_client.list_objects(
                bucket_name=settings.MINIO_ARCHIVE_BUCKET,
                prefix="metadata/",
                recursive=True
            )
            
            archives = []
            
            for obj in objects:
                try:
                    metadata_json = await self.minio_client.download_file(obj.object_name)
                    doc_metadata = json.loads(metadata_json)
                    
                    metadata_user_id = doc_metadata.get("user_id")
                    if user_id is not None and metadata_user_id != user_id:
                        continue
                    
                    if search and search.lower() not in doc_metadata["title"].lower():
                        continue
                    
                    archive_info = ArchiveInfo(
                        id=doc_metadata["id"],
                        title=doc_metadata["title"],
                        description=doc_metadata["description"],
                        file_size=doc_metadata["file_size"],
                        original_filename=doc_metadata["original_filename"],
                        storage_path=doc_metadata["storage_path"],
                        user_id=doc_metadata.get("user_id"),
                        created_at=datetime.fromisoformat(doc_metadata["created_at"]),
                        updated_at=datetime.fromisoformat(doc_metadata["updated_at"]) if doc_metadata.get("updated_at") else None,
                        doc_metadata=doc_metadata.get("doc_metadata", {}),
                        compression_type=doc_metadata.get("compression_type", doc_metadata.get("format")),
                        file_type=doc_metadata.get("file_type", "application/octet-stream")
                    )
                    archives.append(archive_info)
                except Exception as e:
                    print(f"Lỗi khi xử lý doc_metadata archive {obj.object_name}: {str(e)}")
                    continue
            
            archives.sort(key=lambda x: x.created_at, reverse=True)
            
            return archives[skip:skip+limit]
        except Exception as e:
            raise StorageException(f"Lỗi khi lấy danh sách tệp nén: {str(e)}")
    
    async def save_archive(self, archive_id: str, content: bytes, filename: str) -> str:
        """Lưu nội dung tệp nén và trả về đường dẫn lưu trữ."""
        try:
            object_name = f"archives/{archive_id}/{filename}"
            
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
            doc_metadata = {
                "id": archive_info.id,
                "title": archive_info.title,
                "description": archive_info.description,
                "format": archive_info.compression_type,
                "file_size": archive_info.file_size,
                "original_filename": archive_info.original_filename,
                "storage_path": archive_info.storage_path,
                "is_encrypted": archive_info.doc_metadata.get("is_encrypted", False),
                "user_id": archive_info.user_id,
                "created_at": archive_info.created_at.isoformat(),
                "updated_at": archive_info.updated_at.isoformat() if archive_info.updated_at else None,
                "doc_metadata": archive_info.doc_metadata,
                "compression_type": archive_info.compression_type,
                "file_type": archive_info.file_type,
                "files_count": archive_info.files_count
            }
            
            await self.minio_client.put_object(
                bucket_name=settings.MINIO_ARCHIVE_BUCKET,
                object_name=f"metadata/{archive_info.id}.json",
                data=json.dumps(doc_metadata).encode('utf-8')
            )
        except Exception as e:
            raise StorageException(f"Lỗi khi lưu metadata tệp nén: {str(e)}")


class ProcessingRepository:
    def __init__(self, minio_client: MinioClient):
        self.minio_client = minio_client
        self._processing_cache: Dict[str, ArchiveProcessingInfo] = {}
        
    async def create_processing(self, processing_info: ArchiveProcessingInfo) -> None:
        """Tạo thông tin xử lý mới và lưu metadata."""
        await self._save_processing_metadata(processing_info)
        
    async def get_processing(self, processing_id: str, user_id_check: Optional[str] = None) -> Optional[ArchiveProcessingInfo]:
        """Lấy thông tin xử lý theo ID, có kiểm tra user_id nếu được cung cấp."""
        try:
            metadata_json_bytes = await self.minio_client.get_object(
                bucket_name=settings.MINIO_ARCHIVE_BUCKET,
                object_name=f"processing/{processing_id}.json"
            )
            
            if not metadata_json_bytes:
                return None
                
            metadata = json.loads(metadata_json_bytes.decode('utf-8'))
            
            if user_id_check is not None:
                processing_user_id = metadata.get("user_id")
                if processing_user_id is not None and processing_user_id != user_id_check:
                    print(f"User {user_id_check} tried to access processing info {processing_id} owned by user {processing_user_id}")
                return None
                
            if metadata.get('started_at') and isinstance(metadata['started_at'], str):
                metadata['started_at'] = datetime.fromisoformat(metadata['started_at'])
            if metadata.get('completed_at') and isinstance(metadata['completed_at'], str):
                metadata['completed_at'] = datetime.fromisoformat(metadata['completed_at'])

            processing_info = ArchiveProcessingInfo(**metadata)
            return processing_info
        except Exception as e:
            print(f"Error getting processing info {processing_id}: {e}")
            return None
            
    async def update_processing(self, processing_info: ArchiveProcessingInfo) -> None:
        """Cập nhật thông tin xử lý và lưu metadata."""
        if not processing_info.completed_at:
            processing_info.completed_at = datetime.utcnow()
        await self._save_processing_metadata(processing_info)
        
    async def delete_processing(self, processing_id: str, user_id: Optional[str] = None) -> None:
        """Xóa thông tin xử lý."""
        try:
            await self.minio_client.remove_object(
                bucket_name=settings.MINIO_ARCHIVE_BUCKET,
                object_name=f"processing/{processing_id}.json"
            )
        except Exception as e:
            print(f"Error deleting processing metadata {processing_id}: {e}")
            
    async def _save_processing_metadata(self, processing_info: ArchiveProcessingInfo) -> None:
        """Lưu metadata của thông tin xử lý, bao gồm user_id."""
        try:
            processing_data = {
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
                data=json.dumps(processing_data).encode('utf-8')
            )
        except Exception as e:
            print(f"Error saving processing metadata for {processing_info.id}: {e}")
            raise StorageException(f"Lỗi khi lưu metadata processing: {str(e)}")


class FileRepository:
    def __init__(self, minio_client: MinioClient, db_session_factory):
        self.minio_client = minio_client
        self.async_session_factory = db_session_factory
        self.trash_metadata_file = os.path.join(settings.TEMP_DIR, "files_trash_metadata.json")
        self._trash_cache: Dict[str, Any] = {}
        self._load_trash_metadata()

    async def save_file(self, file_info: FileInfo, content: bytes) -> FileInfo:
        """
        Lưu file mới vào MinIO và metadata vào PostgreSQL.
        FileInfo đầu vào có thể chưa có id, storage_id, storage_path, created_at, updated_at.
        Chúng sẽ được tạo/cập nhật và trả về trong FileInfo mới.
        """
        async with self.async_session_factory() as session:
            async with session.begin():
                try:
                    storage_id_val = str(uuid.uuid4())
                    document_category = file_info.doc_metadata.get("document_category", "file")
                    
                    original_filename = file_info.original_filename
                    if not original_filename:
                        base_name = file_info.title.replace(" ", "_") if file_info.title else storage_id_val
                        import mimetypes
                        ext = mimetypes.guess_extension(file_info.file_type) or ".dat"
                        original_filename = f"{base_name}{ext}"
                    
                    storage_path_val = f"{document_category}/{storage_id_val}/{original_filename}"

                    bucket_to_use = settings.MINIO_FILES_BUCKET
                    if document_category == "archive":
                        bucket_to_use = settings.MINIO_ARCHIVE_BUCKET

                    await self.minio_client.put_object(
                        bucket_name=bucket_to_use,
                        object_name=storage_path_val,
                        data=content,
                        content_type=file_info.file_type
                    )

                    file_size = len(content)
                    user_id_to_save = file_info.user_id
                    if user_id_to_save is None:
                        raise StorageException("user_id is required to save the file.")

                    doc_meta = file_info.doc_metadata.copy() if file_info.doc_metadata else {}
                    doc_meta.pop("document_category", None) 
                    metadata_json = json.dumps(doc_meta) if doc_meta else None

                    created_at_val = datetime.utcnow()
                    updated_at_val = created_at_val
                    source_service_val = file_info.source_service or "files"

                    # Create DBDocument instance using SQLAlchemy ORM
                    db_document = DBDocument(
                        storage_id=storage_id_val,
                        document_category=document_category,
                        title=file_info.title,
                        description=file_info.description,
                        file_size=file_size,
                        storage_path=storage_path_val,
                        original_filename=original_filename,
                        doc_metadata=metadata_json,
                        created_at=created_at_val,
                        updated_at=updated_at_val,
                        user_id=user_id_to_save,
                        file_type=file_info.file_type,
                        source_service=source_service_val
                    )
                    
                    # Add to session and commit
                    session.add(db_document)
                    await session.flush()
                    await session.refresh(db_document)
                    
                    return FileInfo(
                        id=str(db_document.id), 
                        storage_id=storage_id_val,
                        title=file_info.title,
                        description=file_info.description,
                        file_size=file_size,
                        file_type=file_info.file_type,
                        original_filename=original_filename,
                        storage_path=storage_path_val,
                        user_id=user_id_to_save,
                        created_at=db_document.created_at,
                        updated_at=db_document.updated_at,
                        doc_metadata=doc_meta,
                        source_service=source_service_val
                    )
                except Exception as e:
                    logger.error(f"Lỗi khi lưu file: {e}", exc_info=True)
                    raise StorageException(f"Không thể lưu file: {str(e)}")

    async def get_file_info(self, file_db_id: str, user_id_check: Optional[str] = None) -> Optional[FileInfo]:
        """
        Lấy thông tin file từ PostgreSQL theo ID trong bảng documents.
        Hàm này giờ sẽ lấy file thuộc bất kỳ document_category nào, không chỉ 'file'.
        """
        async with self.async_session_factory() as session:
            try:
                db_id_int = int(file_db_id)
                
                # Build query using SQLAlchemy ORM
                query = select(DBDocument).where(DBDocument.id == db_id_int)
                
                if user_id_check is not None:
                    query = query.where(DBDocument.user_id == user_id_check)
                
                result = await session.execute(query)
                record = result.scalar_one_or_none()

                if not record:
                    return None

                loaded_metadata = {}
                if record.doc_metadata:
                    try:
                        loaded_metadata = json.loads(record.doc_metadata)
                    except json.JSONDecodeError: 
                        pass 

                return FileInfo(
                    id=str(record.id),
                    storage_id=str(record.storage_id),
                    title=record.title,
                    description=record.description,
                    file_size=record.file_size,
                    file_type=record.file_type or 'application/octet-stream',
                    original_filename=record.original_filename,
                    storage_path=record.storage_path,
                    user_id=str(record.user_id),
                    created_at=record.created_at,
                    updated_at=record.updated_at,
                    doc_metadata=loaded_metadata,
                    source_service=record.source_service or 'files'
                )
            except ValueError:
                return None
            except Exception as e:
                logger.error(f"Lỗi khi lấy thông tin file {file_db_id}: {e}", exc_info=True)
                return None

    async def get_file_content(self, file_db_id: str, user_id_check: Optional[str] = None) -> bytes:
        """
        Lấy nội dung file từ MinIO sau khi lấy thông tin từ PostgreSQL.
        """
        file_info = await self.get_file_info(file_db_id, user_id_check=user_id_check)
        if not file_info or not file_info.storage_path:
            raise FileNotFoundException(file_db_id)
            
        try:
            content = await self.minio_client.get_raw_file(file_info.storage_path)
            if not content:
                raise StorageException(f"Không thể tải nội dung file: {file_db_id} từ {file_info.storage_path}")
            return content
        except Exception as e:
            raise StorageException(f"Lỗi khi tải nội dung file {file_db_id}: {str(e)}")

    async def update_file_info(self, file_info_to_update: FileInfo) -> FileInfo:
        """
        Cập nhật thông tin file trong PostgreSQL. Không cập nhật content ở đây.
        FileInfo đầu vào phải có id (từ DB) và user_id.
        """
        async with self.async_session_factory() as session:
            async with session.begin():
                try:
                    db_id_int = int(file_info_to_update.id)
                    user_id_owner = file_info_to_update.user_id
                    if user_id_owner is None:
                        raise StorageException("user_id is required to update file info.")

                    updated_at_val = datetime.utcnow()
                    metadata_json = json.dumps(file_info_to_update.doc_metadata) if file_info_to_update.doc_metadata else None
                    
                    # Build update query using SQLAlchemy ORM
                    query = (
                        sqlalchemy_update(DBDocument)
                        .where(and_(
                            DBDocument.id == db_id_int,
                            DBDocument.document_category == 'file',
                            DBDocument.user_id == user_id_owner
                        ))
                        .values(
                            title=file_info_to_update.title,
                            description=file_info_to_update.description,
                            doc_metadata=metadata_json,
                            original_filename=file_info_to_update.original_filename,
                            file_type=file_info_to_update.file_type,
                            updated_at=updated_at_val
                        )
                        .returning(DBDocument)
                    )
                    
                    result = await session.execute(query)
                    record = result.scalar_one_or_none()

                    if not record:
                        raise FileNotFoundException(f"File with id {file_info_to_update.id} not found for user {user_id_owner} or not a 'file' category.")
                    
                    loaded_metadata = {}
                    if record.doc_metadata:
                        try: 
                            loaded_metadata = json.loads(record.doc_metadata)
                        except: 
                            pass
                    
                    return FileInfo(
                        id=str(record.id),
                        storage_id=str(record.storage_id),
                        title=record.title,
                        description=record.description,
                        file_size=record.file_size,
                        file_type=record.file_type or 'application/octet-stream',
                        original_filename=record.original_filename,
                        storage_path=record.storage_path,
                        user_id=str(record.user_id),
                        created_at=record.created_at,
                        updated_at=record.updated_at,
                        doc_metadata=loaded_metadata,
                        source_service=record.source_service or 'files'
                    )
                except ValueError:
                    raise FileNotFoundException(file_info_to_update.id)
                except FileNotFoundException:
                    raise
                except Exception as e:
                    logger.error(f"Lỗi khi cập nhật file {file_info_to_update.id}: {e}", exc_info=True)
                    raise StorageException(f"Không thể cập nhật thông tin file {file_info_to_update.id}: {str(e)}")

    async def delete_file_record(self, file_db_id: str, user_id_check: Optional[str] = None) -> None:
        """
        Xóa record file khỏi PostgreSQL và file khỏi MinIO.
        """
        async with self.async_session_factory() as session:
            async with session.begin():
                try:
                    db_id_int = int(file_db_id)
                    
                    # Get file info first using SQLAlchemy ORM
                    query = select(DBDocument.storage_path, DBDocument.user_id).where(
                        and_(
                            DBDocument.id == db_id_int,
                            DBDocument.document_category == 'file'
                        )
                    )
                    
                    result = await session.execute(query)
                    record = result.first()

                    if not record:
                        raise FileNotFoundException(file_db_id)
                    
                    if user_id_check is not None and str(record.user_id) != user_id_check:
                        raise FileNotFoundException(f"File {file_db_id} not found for user {user_id_check} or permission denied.")

                    storage_path_to_delete = record.storage_path

                    # Delete using SQLAlchemy ORM
                    delete_query = sqlalchemy_delete(DBDocument).where(
                        and_(
                            DBDocument.id == db_id_int,
                            DBDocument.document_category == 'file'
                        )
                    )
                    
                    delete_result = await session.execute(delete_query)

                    if delete_result.rowcount == 0:
                        raise FileNotFoundException(file_db_id) 

                    if storage_path_to_delete:
                        await self.minio_client.remove_raw_file(storage_path_to_delete) 
                except ValueError:
                    raise FileNotFoundException(file_db_id)
                except FileNotFoundException:
                    raise
                except Exception as e:
                    logger.error(f"Lỗi khi xóa file {file_db_id}: {e}", exc_info=True)
                    raise StorageException(f"Không thể xóa file {file_db_id}: {str(e)}")

    async def list_files(
        self, 
        skip: int = 0, 
        limit: int = 10, 
        user_id: Optional[str] = None, 
        search: Optional[str] = None,
        document_category_filter: Optional[str] = None,
        source_service_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Lấy danh sách file từ PostgreSQL, lọc theo user_id, tùy chọn document_category và source_service.
        Nếu document_category_filter là None, sẽ không lọc theo category.
        Nếu source_service_filter có giá trị, sẽ lọc thêm theo source_service.
        Trả về một dictionary chứa danh sách 'items' (FileInfo) và 'total_count' (int).
        """
        if user_id is None:
            return {"items": [], "total_count": 0}

        async with self.async_session_factory() as session:
            try:
                # Build query using SQLAlchemy ORM
                query = select(DBDocument).where(DBDocument.user_id == user_id)
                
                if document_category_filter is not None:
                    query = query.where(DBDocument.document_category == document_category_filter)
                
                if source_service_filter is not None:
                    query = query.where(DBDocument.source_service == source_service_filter)

                if search:
                    search_term = f"%{search.lower()}%"
                    query = query.where(
                        (func.lower(DBDocument.title).like(search_term)) |
                        (func.lower(DBDocument.description).like(search_term)) |
                        (func.lower(DBDocument.original_filename).like(search_term))
                    )

                # Count query
                count_query = select(func.count()).select_from(query.subquery())
                count_result = await session.execute(count_query)
                total_count = count_result.scalar() or 0

                # List query with pagination
                list_query = query.order_by(DBDocument.created_at.desc()).offset(skip).limit(limit)
                result = await session.execute(list_query)
                records = result.scalars().all()

                files_list = []
                for record in records:
                    loaded_metadata = {}
                    if record.doc_metadata:
                        try: 
                            loaded_metadata = json.loads(record.doc_metadata)
                        except json.JSONDecodeError: 
                            pass 

                    files_list.append(FileInfo(
                        id=str(record.id),
                        storage_id=str(record.storage_id),
                        title=record.title,
                        description=record.description,
                        file_size=record.file_size,
                        file_type=record.file_type or 'application/octet-stream',
                        original_filename=record.original_filename,
                        storage_path=record.storage_path,
                        user_id=str(record.user_id),
                        created_at=record.created_at,
                        updated_at=record.updated_at,
                        doc_metadata=loaded_metadata,
                        source_service=record.source_service or 'files'
                    ))
                return {"items": files_list, "total_count": total_count}
            except Exception as e:
                logger.error(f"DB Error in list_files: {e}", exc_info=True)
                raise StorageException(f"Không thể lấy danh sách file từ DB: {str(e)}")

    def _load_trash_metadata(self) -> None:
        try:
            if os.path.exists(self.trash_metadata_file):
                with open(self.trash_metadata_file, "r") as f:
                    self._trash_cache = json.load(f)
        except Exception:
            self._trash_cache = {}

    def _save_trash_metadata(self) -> None:
        try:
            os.makedirs(os.path.dirname(self.trash_metadata_file), exist_ok=True)
            with open(self.trash_metadata_file, "w") as f:
                json.dump(self._trash_cache, f, default=str)
        except Exception as e:
            logger.error(f"Error saving trash metadata: {e}")

    async def move_to_trash(self, file_id: str, user_id: Optional[str] = None) -> None:
        file_info = await self.get_file_info(file_id, user_id_check=user_id)
        if not file_info:
            raise FileNotFoundException(file_id)

        trash_item_id = str(uuid.uuid4())
        self._trash_cache[trash_item_id] = {
            "original_id": file_info.id,
            "storage_id": file_info.storage_id,
            "title": file_info.title,
            "description": file_info.description,
            "file_size": file_info.file_size,
            "file_type": file_info.file_type,
            "original_filename": file_info.original_filename,
            "storage_path": file_info.storage_path,
            "user_id": file_info.user_id,
            "doc_metadata": file_info.doc_metadata,
            "deleted_at": datetime.utcnow().isoformat(),
            "original_created_at": file_info.created_at.isoformat(),
        }
        self._save_trash_metadata()

    async def restore_from_trash(self, trash_item_id: str, user_id: Optional[str] = None) -> Optional[FileInfo]:
        if trash_item_id not in self._trash_cache:
            return None
        
        trash_data = self._trash_cache[trash_item_id]
        if user_id is not None and trash_data.get("user_id") != user_id:
            return None

        original_file_id = trash_data.get("original_id")
        
        del self._trash_cache[trash_item_id]
        self._save_trash_metadata()

        return FileInfo(
            id=original_file_id,
            storage_id=trash_data["storage_id"],
            title=trash_data["title"],
            description=trash_data["description"],
            file_size=trash_data["file_size"],
            file_type=trash_data["file_type"],
            original_filename=trash_data["original_filename"],
            storage_path=trash_data["storage_path"],
            user_id=trash_data["user_id"],
            created_at=datetime.fromisoformat(trash_data["original_created_at"]),
            updated_at=None,
            doc_metadata=trash_data["doc_metadata"]
        )

    async def get_trash_items(self, skip: int = 0, limit: int = 10, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        self._load_trash_metadata()
        filtered_items = []
        for item_id, item_data in self._trash_cache.items():
            if user_id is None or item_data.get("user_id") == user_id:
                item_data["trash_item_id"] = item_id
                filtered_items.append(item_data)
        
        filtered_items.sort(key=lambda x: x.get("deleted_at", ""), reverse=True)
        return filtered_items[skip:skip+limit]

    async def empty_trash(self, user_id: Optional[str] = None) -> int:
        self._load_trash_metadata()
        items_to_remove = []
        for item_id, item_data in self._trash_cache.items():
            if user_id is None or item_data.get("user_id") == user_id:
                items_to_remove.append(item_id)
                storage_path = item_data.get("storage_path")
                if storage_path:
                    try:
                        await self.minio_client.remove_raw_file(storage_path)
                    except Exception as e:
                        logger.error(f"Error deleting file from MinIO {storage_path}: {e}")
        
        for item_id in items_to_remove:
            del self._trash_cache[item_id]
        
        self._save_trash_metadata()
        return len(items_to_remove)


class CompressJobRepository:
    def __init__(self):
        self._jobs: Dict[str, Dict[str, Any]] = {}
        
    async def create_job(self, job_id: str, info: Dict[str, Any]) -> None:
        self._jobs[job_id] = {
            "id": job_id,
            "status": "processing",
            "created_at": datetime.utcnow().isoformat(),
            "info": info
        }
        
    async def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self._jobs.get(job_id)
        
    async def update_job(self, job_id: str, status: str, result: Optional[Dict[str, Any]] = None, error: Optional[str] = None) -> None:
        if job_id in self._jobs:
            self._jobs[job_id]["status"] = status
            self._jobs[job_id]["updated_at"] = datetime.utcnow().isoformat()
            if result: self._jobs[job_id]["result"] = result
            if error: self._jobs[job_id]["error"] = error


class DecompressJobRepository:
    def __init__(self):
        self._jobs: Dict[str, Dict[str, Any]] = {}
        
    async def create_job(self, job_id: str, info: Dict[str, Any]) -> None:
        self._jobs[job_id] = {
            "id": job_id,
            "status": "processing",
            "created_at": datetime.utcnow().isoformat(),
            "info": info
        }
        
    async def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self._jobs.get(job_id)
        
    async def update_job(self, job_id: str, status: str, result: Optional[Dict[str, Any]] = None, error: Optional[str] = None) -> None:
        if job_id in self._jobs:
            self._jobs[job_id]["status"] = status
            self._jobs[job_id]["updated_at"] = datetime.utcnow().isoformat()
            if result: self._jobs[job_id]["result"] = result
            if error: self._jobs[job_id]["error"] = error


class CrackJobRepository:
    def __init__(self):
        self._jobs: Dict[str, Dict[str, Any]] = {}
        
    async def create_job(self, job_id: str, info: Dict[str, Any]) -> None:
        self._jobs[job_id] = {
            "id": job_id,
            "status": "processing",
            "created_at": datetime.utcnow().isoformat(),
            "info": info
        }
        
    async def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self._jobs.get(job_id)
        
    async def update_job(self, job_id: str, status: str, result: Optional[Dict[str, Any]] = None, error: Optional[str] = None) -> None:
        if job_id in self._jobs:
            self._jobs[job_id]["status"] = status
            self._jobs[job_id]["updated_at"] = datetime.utcnow().isoformat()
            if result: self._jobs[job_id]["result"] = result
            if error: self._jobs[job_id]["error"] = error


class CleanupJobRepository:
    def __init__(self):
        self._jobs: Dict[str, Dict[str, Any]] = {}
        
    async def create_job(self, job_id: str, info: Dict[str, Any]) -> None:
        self._jobs[job_id] = {
            "id": job_id,
            "status": "processing",
            "created_at": datetime.utcnow().isoformat(),
            "info": info
        }
        
    async def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self._jobs.get(job_id)
        
    async def update_job(self, job_id: str, status: str, result: Optional[Dict[str, Any]] = None, error: Optional[str] = None) -> None:
        if job_id in self._jobs:
            self._jobs[job_id]["status"] = status
            self._jobs[job_id]["updated_at"] = datetime.utcnow().isoformat()
            if result: self._jobs[job_id]["result"] = result
            if error: self._jobs[job_id]["error"] = error


class TrashRepository:
    def __init__(self):
        self._items: Dict[str, Dict[str, Any]] = {}
        
    async def add_item(self, item_id: str, item_type: str, item_data: Dict[str, Any]) -> None:
        self._items[item_id] = {
            "item_id": item_id,
            "item_type": item_type,
            "data": item_data,
            "deleted_at": datetime.utcnow().isoformat()
        }
        
    async def get_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        return self._items.get(item_id)
        
    async def get_items(self, skip: int = 0, limit: int = 10) -> List[Dict[str, Any]]:
        all_items = list(self._items.values())
        all_items.sort(key=lambda x: x["deleted_at"], reverse=True)
        return all_items[skip : skip + limit]
        
    async def delete_item(self, item_id: str) -> bool:
        if item_id in self._items:
            del self._items[item_id]
            return True
        return False
        
    async def empty_trash(self) -> int:
        count = len(self._items)
        self._items.clear()
        return count 