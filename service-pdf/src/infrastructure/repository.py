import os
import json
import uuid
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update as sqlalchemy_update, delete as sqlalchemy_delete, and_, func, text
from sqlalchemy.orm import sessionmaker

from domain.models import PDFDocumentInfo, PNGDocumentInfo, StampInfo, PDFProcessingInfo, MergeInfo, DBDocument
from domain.exceptions import (
    DocumentNotFoundException, ImageNotFoundException, StampNotFoundException,
    StorageException, PDFPasswordProtectedException, WrongPasswordException
)
from infrastructure.minio_client import MinioClient
from core.config import settings
import logging

logger = logging.getLogger(__name__)

class PDFDocumentRepository:
    """
    Repository để làm việc với tài liệu PDF sử dụng bảng documents chung
    """

    def __init__(self, minio_client: MinioClient, db_session_factory):
        self.minio_client = minio_client
        self.async_session_factory = db_session_factory

    async def save(self, document_info: PDFDocumentInfo, content: bytes, user_id: str) -> PDFDocumentInfo:
        """
        Lưu tài liệu PDF vào MinIO và metadata vào database
        """
        async with self.async_session_factory() as session:
            async with session.begin():
                try:
                    # Validate user_id
                    if not user_id:
                        raise StorageException("user_id is required to save the document.")
                    
                    try:
                        uuid.UUID(user_id)
                    except ValueError:
                        raise StorageException("user_id must be a valid UUID format.")
                    
                    # Setup document info
                    doc_id = str(uuid.uuid4())
                    storage_id = str(uuid.uuid4())
                    document_info.id = doc_id
                    document_info.storage_id = storage_id
                    document_info.user_id = user_id
                    document_info.document_category = "pdf"
                    
                    # Create storage path
                    object_name = f"pdf/{storage_id}/{document_info.original_filename}"
                    document_info.storage_path = object_name
                    
                    # Upload to MinIO
                    await self.minio_client.upload_pdf_document(
                        content=content,
                        filename=document_info.original_filename,
                        object_name_override=object_name
                    )
                    
                    # Update file info
                    document_info.file_size = len(content)
                    document_info.file_type = "application/pdf"
                    
                    # Set timestamps
                    now = datetime.now()
                    document_info.created_at = document_info.created_at or now
                    document_info.updated_at = document_info.updated_at or now
                    
                    # Prepare metadata
                    metadata_json = json.dumps(document_info.metadata) if document_info.metadata else None
                    
                    # Create DBDocument instance using SQLAlchemy ORM
                    db_document = DBDocument(
                        id=doc_id,
                        storage_id=storage_id,
                        document_category="pdf",
                        title=document_info.title,
                        description=document_info.description,
                        file_size=document_info.file_size,
                        file_type=document_info.file_type,
                        storage_path=object_name,
                        original_filename=document_info.original_filename,
                        doc_metadata=metadata_json,
                        created_at=document_info.created_at,
                        updated_at=document_info.updated_at,
                        user_id=user_id,
                        page_count=document_info.page_count,
                        is_encrypted=document_info.is_encrypted,
                        version=document_info.version or 1,
                        checksum=document_info.checksum
                    )
                    
                    # Add to session and commit
                    session.add(db_document)
                    await session.flush()
                    await session.refresh(db_document)
                    
                    # Update document_info with saved data
                    document_info.id = str(db_document.id)
                    document_info.created_at = db_document.created_at
                    document_info.updated_at = db_document.updated_at
                    
                    return document_info
                    
                except Exception as e:
                    logger.error(f"Lỗi khi lưu tài liệu PDF: {e}", exc_info=True)
                    raise StorageException(f"Không thể lưu tài liệu PDF: {str(e)}")

    async def get(self, document_id: str, user_id_check: Optional[str] = None) -> Tuple[Optional[PDFDocumentInfo], Optional[bytes]]:
        """
        Lấy tài liệu PDF từ database và MinIO
        """
        async with self.async_session_factory() as session:
            try:
                # Build query using SQLAlchemy ORM
                query = select(DBDocument).where(
                    (DBDocument.id == document_id) & 
                    (DBDocument.document_category == "pdf")
                )
                
                if user_id_check:
                    query = query.where(DBDocument.user_id == user_id_check)
                
                result = await session.execute(query)
                record = result.scalar_one_or_none()
                
                if not record:
                    return None, None
                
                # Parse metadata
                metadata = {}
                if record.doc_metadata:
                    try:
                        metadata = json.loads(record.doc_metadata)
                    except json.JSONDecodeError:
                        metadata = {}
                
                doc_data = {
                    'id': str(record.id),
                    'storage_id': str(record.storage_id),
                    'title': record.title,
                    'description': record.description,
                    'created_at': record.created_at,
                    'updated_at': record.updated_at,
                    'file_size': record.file_size,
                    'page_count': record.page_count,
                    'is_encrypted': record.is_encrypted,
                    'storage_path': record.storage_path,
                    'original_filename': record.original_filename,
                    'metadata': metadata,
                    'user_id': str(record.user_id),
                    'file_type': record.file_type,
                    'document_category': record.document_category,
                    'version': record.version,
                    'checksum': record.checksum
                }
                
                document_info = PDFDocumentInfo(**doc_data)
                
                # Download from MinIO
                try:
                    content = await self.minio_client.download_pdf_document(document_info.storage_path)
                    return document_info, content
                except Exception as minio_e:
                    logger.error(f"Lỗi MinIO khi tải {document_info.storage_path}: {minio_e}")
                    raise StorageException(f"Không thể tải nội dung tài liệu: {str(minio_e)}")
                    
            except Exception as e:
                logger.error(f"Lỗi khi lấy tài liệu PDF {document_id}: {e}", exc_info=True)
                return None, None

    async def list(self, skip: int = 0, limit: int = 10, search: Optional[str] = None, user_id: Optional[str] = None) -> Tuple[List[PDFDocumentInfo], int]:
        """
        Lấy danh sách tài liệu PDF
        """
        async with self.async_session_factory() as session:
            try:
                query = select(DBDocument).where(DBDocument.document_category == "pdf")
                
                if user_id:
                    query = query.where(DBDocument.user_id == user_id)
                
                if search:
                    search_term = f"%{search.lower()}%"
                    query = query.where(
                        (func.lower(DBDocument.title).like(search_term)) |
                        (func.lower(DBDocument.description).like(search_term))
                    )
                
                count_query = select(func.count()).select_from(query.subquery())
                count_result = await session.execute(count_query)
                total_count = count_result.scalar() or 0
                
                list_query = query.order_by(DBDocument.created_at.desc()).offset(skip).limit(limit)
                result = await session.execute(list_query)
                records = result.scalars().all()
                
                documents = []
                for record in records:
                    metadata = {}
                    if record.doc_metadata:
                        try:
                            metadata = json.loads(record.doc_metadata)
                        except json.JSONDecodeError:
                            metadata = {}
                    
                    doc_data = {
                        'id': str(record.id),
                        'storage_id': str(record.storage_id),
                        'title': record.title,
                        'description': record.description,
                        'created_at': record.created_at,
                        'updated_at': record.updated_at,
                        'file_size': record.file_size,
                        'page_count': record.page_count,
                        'is_encrypted': record.is_encrypted,
                        'storage_path': record.storage_path,
                        'original_filename': record.original_filename,
                        'metadata': metadata,
                        'user_id': str(record.user_id),
                        'file_type': record.file_type,
                        'document_category': record.document_category,
                        'version': record.version,
                        'checksum': record.checksum
                    }
                    
                    documents.append(PDFDocumentInfo(**doc_data))
                
                return documents, total_count
                
            except Exception as e:
                logger.error(f"Lỗi khi lấy danh sách tài liệu PDF: {e}", exc_info=True)
                return [], 0

    async def update(self, document_info: PDFDocumentInfo, user_id_check: Optional[str] = None) -> PDFDocumentInfo:
        """
        Cập nhật thông tin tài liệu PDF
        """
        async with self.async_session_factory() as session:
            async with session.begin():
                try:
                    if not document_info.id:
                        raise ValueError("Document ID is required for update.")
                    
                    # Update timestamp
                    document_info.updated_at = datetime.now()
                    metadata_json = json.dumps(document_info.metadata) if document_info.metadata else None
                    
                    # Build query using SQLAlchemy ORM
                    query = select(DBDocument).where(
                        (DBDocument.id == document_info.id) & 
                        (DBDocument.document_category == "pdf")
                    )
                    
                    if user_id_check:
                        query = query.where(DBDocument.user_id == user_id_check)
                    
                    result = await session.execute(query)
                    db_document = result.scalar_one_or_none()
                    
                    if not db_document:
                        raise DocumentNotFoundException(f"Tài liệu PDF {document_info.id} không tìm thấy hoặc không có quyền cập nhật.")
                    
                    # Update fields
                    db_document.title = document_info.title
                    db_document.description = document_info.description
                    db_document.doc_metadata = metadata_json
                    db_document.updated_at = document_info.updated_at
                    db_document.page_count = document_info.page_count
                    db_document.is_encrypted = document_info.is_encrypted
                    
                    await session.flush()
                    await session.refresh(db_document)
                    
                    # Convert back to PDFDocumentInfo
                    metadata = {}
                    if db_document.doc_metadata:
                        try:
                            metadata = json.loads(db_document.doc_metadata)
                        except json.JSONDecodeError:
                            metadata = {}
                    
                    doc_data = {
                        'id': str(db_document.id),
                        'storage_id': str(db_document.storage_id),
                        'title': db_document.title,
                        'description': db_document.description,
                        'created_at': db_document.created_at,
                        'updated_at': db_document.updated_at,
                        'file_size': db_document.file_size,
                        'page_count': db_document.page_count,
                        'is_encrypted': db_document.is_encrypted,
                        'storage_path': db_document.storage_path,
                        'original_filename': db_document.original_filename,
                        'metadata': metadata,
                        'user_id': str(db_document.user_id),
                        'file_type': db_document.file_type,
                        'document_category': db_document.document_category,
                        'version': db_document.version,
                        'checksum': db_document.checksum
                    }
                    
                    return PDFDocumentInfo(**doc_data)
                    
                except DocumentNotFoundException:
                    raise
                except Exception as e:
                    logger.error(f"Lỗi khi cập nhật tài liệu PDF {document_info.id}: {e}", exc_info=True)
                    raise StorageException(f"Không thể cập nhật tài liệu PDF: {str(e)}")

    async def delete(self, document_id: str, user_id_check: Optional[str] = None) -> None:
        """
        Xóa tài liệu PDF
        """
        async with self.async_session_factory() as session:
            async with session.begin():
                try:
                    # Get document info using SQLAlchemy ORM
                    query = select(DBDocument).where(
                        (DBDocument.id == document_id) & 
                        (DBDocument.document_category == "pdf")
                    )
                    
                    if user_id_check:
                        query = query.where(DBDocument.user_id == user_id_check)
                    
                    result = await session.execute(query)
                    db_document = result.scalar_one_or_none()
                    
                    if not db_document:
                        raise DocumentNotFoundException(f"Tài liệu PDF {document_id} không tìm thấy hoặc không có quyền xóa.")
                    
                    storage_path = db_document.storage_path
                    
                    # Delete from database
                    await session.delete(db_document)
                    await session.flush()
                    
                    # Delete from MinIO
                    if storage_path:
                        try:
                            await self.minio_client.delete_pdf_document(storage_path)
                        except Exception as minio_e:
                            logger.error(f"Lỗi khi xóa file từ MinIO {storage_path}: {minio_e}")
                    
                except DocumentNotFoundException:
                    raise
                except Exception as e:
                    logger.error(f"Lỗi khi xóa tài liệu PDF {document_id}: {e}", exc_info=True)
                    raise StorageException(f"Không thể xóa tài liệu PDF: {str(e)}")

class PNGDocumentRepository:
    """
    Repository để làm việc với tài liệu PNG sử dụng bảng documents chung
    """

    def __init__(self, minio_client: MinioClient, db_session_factory):
        self.minio_client = minio_client
        self.async_session_factory = db_session_factory

    async def save(self, document_info: PNGDocumentInfo, content: bytes, user_id: str) -> PNGDocumentInfo:
        """
        Lưu tài liệu PNG vào MinIO và metadata vào database
        """
        async with self.async_session_factory() as session:
            async with session.begin():
                try:
                    # Validate user_id
                    if not user_id:
                        raise StorageException("user_id is required to save the document.")
                    
                    try:
                        uuid.UUID(user_id)
                    except ValueError:
                        raise StorageException("user_id must be a valid UUID format.")
                    
                    # Setup document info
                    doc_id = str(uuid.uuid4())
                    storage_id = str(uuid.uuid4())
                    document_info.id = doc_id
                    document_info.storage_id = storage_id
                    document_info.user_id = user_id
                    document_info.document_category = "png"
                    
                    # Create storage path
                    object_name = f"png/{storage_id}/{document_info.original_filename}"
                    document_info.storage_path = object_name
                    
                    # Upload to MinIO
                    await self.minio_client.upload_png_document(
                        content=content,
                        filename=document_info.original_filename
                    )
                    
                    # Update file info
                    document_info.file_size = len(content)
                    document_info.file_type = "image/png"
                    
                    # Set timestamps
                    now = datetime.now()
                    document_info.created_at = document_info.created_at or now
                    document_info.updated_at = document_info.updated_at or now
                    
                    # Prepare metadata
                    metadata_json = json.dumps(document_info.metadata) if document_info.metadata else None
                    
                    # Create DBDocument instance using SQLAlchemy ORM
                    db_document = DBDocument(
                        id=doc_id,
                        storage_id=storage_id,
                        document_category="png",
                        title=document_info.title,
                        description=document_info.description,
                        file_size=document_info.file_size,
                        file_type=document_info.file_type,
                        storage_path=object_name,
                        original_filename=document_info.original_filename,
                        doc_metadata=metadata_json,
                        created_at=document_info.created_at,
                        updated_at=document_info.updated_at,
                        user_id=user_id,
                        version=document_info.version or 1,
                        checksum=document_info.checksum
                    )
                    
                    # Add to session and commit
                    session.add(db_document)
                    await session.flush()
                    await session.refresh(db_document)
                    
                    # Update document_info with saved data
                    document_info.id = str(db_document.id)
                    document_info.created_at = db_document.created_at
                    document_info.updated_at = db_document.updated_at
                    
                    return document_info
                    
                except Exception as e:
                    logger.error(f"Lỗi khi lưu tài liệu PNG: {e}", exc_info=True)
                    raise StorageException(f"Không thể lưu tài liệu PNG: {str(e)}")

    async def get(self, document_id: str, user_id_check: Optional[str] = None) -> Tuple[Optional[PNGDocumentInfo], Optional[bytes]]:
        """
        Lấy tài liệu PNG từ database và MinIO
        """
        async with self.async_session_factory() as session:
            try:
                # Build query using SQLAlchemy ORM
                query = select(DBDocument).where(
                    (DBDocument.id == document_id) & 
                    (DBDocument.document_category == "png")
                )
                
                if user_id_check:
                    query = query.where(DBDocument.user_id == user_id_check)
                
                result = await session.execute(query)
                record = result.scalar_one_or_none()
                
                if not record:
                    return None, None
                
                # Parse metadata
                metadata = {}
                if record.doc_metadata:
                    try:
                        metadata = json.loads(record.doc_metadata)
                    except json.JSONDecodeError:
                        metadata = {}
                
                # Create PNGDocumentInfo
                doc_data = {
                    'id': str(record.id),
                    'storage_id': str(record.storage_id),
                    'title': record.title,
                    'description': record.description,
                    'created_at': record.created_at,
                    'updated_at': record.updated_at,
                    'file_size': record.file_size,
                    'storage_path': record.storage_path,
                    'original_filename': record.original_filename,
                    'metadata': metadata,
                    'user_id': str(record.user_id),
                    'file_type': record.file_type,
                    'document_category': record.document_category,
                    'version': record.version,
                    'checksum': record.checksum
                }
                
                document_info = PNGDocumentInfo(**doc_data)
                
                # Download from MinIO
                try:
                    content = await self.minio_client.download_png_document(document_info.storage_path)
                    return document_info, content
                except Exception as minio_e:
                    logger.error(f"Lỗi MinIO khi tải {document_info.storage_path}: {minio_e}")
                    raise StorageException(f"Không thể tải nội dung tài liệu: {str(minio_e)}")
                    
            except Exception as e:
                logger.error(f"Lỗi khi lấy tài liệu PNG {document_id}: {e}", exc_info=True)
                return None, None

class StampRepository:
    """
    Repository để làm việc với mẫu dấu
    """

    def __init__(self, minio_client: MinioClient):
        self.minio_client = minio_client
        self.stamps_metadata_file = os.path.join(settings.TEMP_DIR, "stamps_metadata.json")
        self.stamps: Dict[str, StampInfo] = {}
        self._load_metadata()

    def _load_metadata(self) -> None:
        """
        Tải metadata của mẫu dấu từ file
        """
        try:
            if os.path.exists(self.stamps_metadata_file):
                with open(self.stamps_metadata_file, "r") as f:
                    data = json.load(f)
                    for stamp_id, stamp_data in data.items():
                        # Convert datetime strings back to datetime objects
                        if stamp_data.get('created_at') and isinstance(stamp_data['created_at'], str):
                            stamp_data['created_at'] = datetime.fromisoformat(stamp_data['created_at'])
                        if stamp_data.get('updated_at') and isinstance(stamp_data['updated_at'], str):
                            stamp_data['updated_at'] = datetime.fromisoformat(stamp_data['updated_at'])
                        
                        self.stamps[stamp_id] = StampInfo(**stamp_data)
        except Exception as e:
            logger.error(f"Lỗi khi tải metadata stamps: {e}", exc_info=True)
            self._save_metadata()

    def _save_metadata(self) -> None:
        """
        Lưu metadata của mẫu dấu vào file
        """
        try:
            os.makedirs(settings.TEMP_DIR, exist_ok=True)
            
            serializable_data = {}
            for stamp_id, stamp in self.stamps.items():
                stamp_dict = stamp.dict()
                # Convert datetime to ISO format
                if stamp_dict.get('created_at'):
                    stamp_dict['created_at'] = stamp_dict['created_at'].isoformat()
                if stamp_dict.get('updated_at'):
                    stamp_dict['updated_at'] = stamp_dict['updated_at'].isoformat()
                
                serializable_data[stamp_id] = stamp_dict
            
            with open(self.stamps_metadata_file, "w") as f:
                json.dump(serializable_data, f, indent=4)
        except Exception as e:
            logger.error(f"Lỗi khi lưu metadata stamps: {e}", exc_info=True)
            raise StorageException(f"Không thể lưu metadata mẫu dấu: {str(e)}")

    async def save(self, stamp_info: StampInfo, content: bytes) -> StampInfo:
        """
        Lưu mẫu dấu mới
        """
        try:
            minio_object_name = f"stamps/{stamp_info.id}/{stamp_info.original_filename}"
            stamp_info.storage_path = minio_object_name
            
            await self.minio_client.upload_stamp(
                content=content,
                filename=stamp_info.original_filename
            )

            stamp_info.file_size = len(content)
            stamp_info.created_at = stamp_info.created_at or datetime.now()
            stamp_info.updated_at = stamp_info.updated_at or datetime.now()
            
            self.stamps[stamp_info.id] = stamp_info
            self._save_metadata()
            return stamp_info
        except Exception as e:
            logger.error(f"Lỗi khi lưu mẫu dấu: {e}", exc_info=True)
            raise StorageException(f"Không thể lưu mẫu dấu: {str(e)}")

    async def get(self, stamp_id: str) -> Tuple[StampInfo, bytes]:
        """
        Lấy thông tin và nội dung mẫu dấu
        """
        try:
            if stamp_id not in self.stamps:
                raise StampNotFoundException(stamp_id)
            
            stamp_info = self.stamps[stamp_id]
            content = await self.minio_client.download_stamp(stamp_info.storage_path)
            return stamp_info, content
        except StampNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Lỗi khi lấy mẫu dấu {stamp_id}: {e}", exc_info=True)
            raise StorageException(f"Không thể lấy mẫu dấu {stamp_id}: {str(e)}")

    async def list(self, skip: int = 0, limit: int = 10) -> List[StampInfo]:
        """
        Lấy danh sách mẫu dấu
        """
        try:
            self._load_metadata()
            stamps_list = list(self.stamps.values())
            sorted_stamps = sorted(
                stamps_list,
                key=lambda x: (x.name.lower() if x.name else '', x.created_at),
                reverse=False 
            )
            return sorted_stamps[skip:skip + limit]
        except Exception as e:
            logger.error(f"Lỗi khi lấy danh sách mẫu dấu: {e}", exc_info=True)
            raise StorageException(f"Không thể lấy danh sách mẫu dấu: {str(e)}")

class PDFProcessingRepository:
    """
    Repository để làm việc với thông tin xử lý PDF
    """
    
    def __init__(self):
        self.processing_metadata_file = os.path.join(settings.TEMP_DIR, "pdf_processing_metadata.json")
        self.processings: Dict[str, PDFProcessingInfo] = {}
        self._load_metadata()

    def _load_metadata(self) -> None:
        try:
            if os.path.exists(self.processing_metadata_file):
                with open(self.processing_metadata_file, "r") as f:
                    data = json.load(f)
                    for processing_id, processing_data in data.items():
                        # Convert datetime strings
                        if processing_data.get('created_at') and isinstance(processing_data['created_at'], str):
                            processing_data['created_at'] = datetime.fromisoformat(processing_data['created_at'])
                        if processing_data.get('completed_at') and isinstance(processing_data['completed_at'], str):
                            processing_data['completed_at'] = datetime.fromisoformat(processing_data['completed_at'])
                        
                        self.processings[processing_id] = PDFProcessingInfo(**processing_data)
        except Exception as e:
            logger.error(f"Lỗi khi tải metadata processing: {e}", exc_info=True)
            self._save_metadata()

    def _save_metadata(self) -> None:
        try:
            os.makedirs(settings.TEMP_DIR, exist_ok=True)
            
            serializable_data = {}
            for pid, p in self.processings.items():
                p_dict = p.dict()
                # Convert datetime to ISO format
                if p_dict.get('created_at'):
                    p_dict['created_at'] = p_dict['created_at'].isoformat()
                if p_dict.get('completed_at'):
                    p_dict['completed_at'] = p_dict['completed_at'].isoformat()
                
                serializable_data[pid] = p_dict
            
            with open(self.processing_metadata_file, "w") as f:
                json.dump(serializable_data, f, indent=4)
        except Exception as e:
            logger.error(f"Lỗi khi lưu metadata processing: {e}", exc_info=True)
            raise StorageException(f"Không thể lưu metadata xử lý PDF: {str(e)}")

    async def save(self, processing_info: PDFProcessingInfo) -> PDFProcessingInfo:
        try:
            if not processing_info.id:
                processing_info.id = str(uuid.uuid4())
            
            processing_info.created_at = processing_info.created_at or datetime.now()
            self.processings[processing_info.id] = processing_info
            self._save_metadata()
            return processing_info
        except Exception as e:
            logger.error(f"Lỗi khi lưu thông tin xử lý PDF: {e}", exc_info=True)
            raise StorageException(f"Không thể lưu thông tin xử lý PDF: {str(e)}")

    async def get(self, processing_id: str) -> PDFProcessingInfo:
        try:
            self._load_metadata()
            if processing_id not in self.processings:
                raise DocumentNotFoundException(f"PDF Processing info with id '{processing_id}' not found.")
            return self.processings[processing_id]
        except DocumentNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Lỗi khi lấy thông tin xử lý PDF {processing_id}: {e}", exc_info=True)
            raise StorageException(f"Không thể lấy thông tin xử lý PDF {processing_id}: {str(e)}")

    async def update(self, processing_info: PDFProcessingInfo) -> PDFProcessingInfo:
        """
        Cập nhật thông tin xử lý PDF
        """
        try:
            if not processing_info.id:
                raise ValueError("Processing ID is required for update.")
            
            self.processings[processing_info.id] = processing_info
            self._save_metadata()
            return processing_info
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật thông tin xử lý PDF {processing_info.id}: {e}", exc_info=True)
            raise StorageException(f"Không thể cập nhật thông tin xử lý PDF: {str(e)}")

class MergeRepository:
    """
    Repository để làm việc với thông tin gộp tài liệu PDF
    """
    
    def __init__(self):
        self.merge_metadata_file = os.path.join(settings.TEMP_DIR, "pdf_merge_metadata.json")
        self.merges: Dict[str, MergeInfo] = {}
        self._load_metadata()

    def _load_metadata(self) -> None:
        try:
            if os.path.exists(self.merge_metadata_file):
                with open(self.merge_metadata_file, "r") as f:
                    data = json.load(f)
                    for merge_id, merge_data in data.items():
                        # Convert datetime strings
                        if merge_data.get('created_at') and isinstance(merge_data['created_at'], str):
                            merge_data['created_at'] = datetime.fromisoformat(merge_data['created_at'])
                        
                        self.merges[merge_id] = MergeInfo(**merge_data)
        except Exception as e:
            logger.error(f"Lỗi khi tải metadata merge: {e}", exc_info=True)
            self._save_metadata()

    def _save_metadata(self) -> None:
        try:
            os.makedirs(settings.TEMP_DIR, exist_ok=True)
            
            serializable_data = {}
            for mid, m in self.merges.items():
                m_dict = m.dict()
                # Convert datetime to ISO format  
                if m_dict.get('created_at'):
                    m_dict['created_at'] = m_dict['created_at'].isoformat()
                
                serializable_data[mid] = m_dict
            
            with open(self.merge_metadata_file, "w") as f:
                json.dump(serializable_data, f, indent=4)
        except Exception as e:
            logger.error(f"Lỗi khi lưu metadata merge: {e}", exc_info=True)
            raise StorageException(f"Không thể lưu metadata gộp PDF: {str(e)}")

    async def save(self, merge_info: MergeInfo) -> MergeInfo:
        try:
            if not merge_info.id:
                merge_info.id = str(uuid.uuid4())
            
            merge_info.created_at = merge_info.created_at or datetime.now()
            self.merges[merge_info.id] = merge_info
            self._save_metadata()
            return merge_info
        except Exception as e:
            logger.error(f"Lỗi khi lưu thông tin gộp PDF: {e}", exc_info=True)
            raise StorageException(f"Không thể lưu thông tin gộp PDF: {str(e)}")

    async def get(self, merge_id: str) -> MergeInfo:
        try:
            self._load_metadata()
            if merge_id not in self.merges:
                raise DocumentNotFoundException(f"Merge info with id '{merge_id}' not found.")
            return self.merges[merge_id]
        except DocumentNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Lỗi khi lấy thông tin gộp PDF {merge_id}: {e}", exc_info=True)
            raise StorageException(f"Không thể lấy thông tin gộp PDF {merge_id}: {str(e)}")

    async def update(self, merge_info: MergeInfo) -> MergeInfo:
        """
        Cập nhật thông tin gộp tài liệu PDF
        """
        try:
            if not merge_info.id:
                raise ValueError("Merge ID is required for update.")
            
            self.merges[merge_info.id] = merge_info
            self._save_metadata()
            return merge_info
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật thông tin gộp PDF {merge_info.id}: {e}", exc_info=True)
            raise StorageException(f"Không thể cập nhật thông tin gộp PDF: {str(e)}")