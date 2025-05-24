import os
import json
import uuid
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update as sqlalchemy_update, delete as sqlalchemy_delete, and_, func
from sqlalchemy.orm import sessionmaker

from domain.models import PDFDocumentInfo as DomainPDFDocumentInfo, PNGDocumentInfo as DomainPNGDocumentInfo, StampInfo, PDFProcessingInfo, MergeInfo, DBDocument
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
    Repository để làm việc với tài liệu PDF, lưu trữ metadata trong PostgreSQL sử dụng SQLAlchemy.
    """

    def __init__(self, minio_client: MinioClient, db_session_factory: "sessionmaker[AsyncSession]"):
        """
        Khởi tạo repository.

        Args:
            minio_client: Client MinIO để lưu trữ tài liệu
            db_session_factory: SQLAlchemy sessionmaker để tạo AsyncSession
        """
        self.minio_client = minio_client
        self.async_session_factory = db_session_factory

    async def _create_db_document_from_info(self, document_info: DomainPDFDocumentInfo, content_len: int, user_id_param: str) -> DBDocument:

        storage_id = str(uuid.uuid4())
        db_doc_id = str(uuid.uuid4())
        doc_category = "pdf"
        original_filename = document_info.original_filename if document_info.original_filename else f"{storage_id}.pdf"
        storage_path = f"{doc_category}/{storage_id}/{original_filename}"
        metadata_to_save = json.dumps(document_info.doc_metadata) if document_info.doc_metadata else None

        new_document = DBDocument(
            id=db_doc_id,
            storage_id=storage_id,
            document_category="pdf",
            title=document_info.title or original_filename or "Unknown",
            description=document_info.description,
            file_size=content_len,
            file_type="application/pdf",
            storage_path=storage_path,
            original_filename=original_filename,
            doc_metadata=metadata_to_save,
            created_at=document_info.created_at or datetime.now(),
            updated_at=document_info.updated_at or datetime.now(),
            user_id=user_id_param,
            version=getattr(document_info, 'version', 1),
            checksum=getattr(document_info, 'checksum', None),
            page_count=getattr(document_info, 'page_count', None),
            is_encrypted=getattr(document_info, 'is_encrypted', False)
        )

        return new_document

    def _update_info_from_db_document(self, document_info: DomainPDFDocumentInfo, db_doc: DBDocument) -> DomainPDFDocumentInfo:
        document_info.id = str(db_doc.id) 
        document_info.storage_id = db_doc.storage_id 
        document_info.storage_path = db_doc.storage_path
        document_info.created_at = db_doc.created_at
        document_info.updated_at = db_doc.updated_at
        document_info.title = db_doc.title
        document_info.description = db_doc.description
        document_info.file_size = db_doc.file_size
        document_info.page_count = db_doc.page_count
        document_info.is_encrypted = db_doc.is_encrypted
        
        if db_doc.doc_metadata:
            try:
                document_info.doc_metadata = json.loads(db_doc.doc_metadata)
            except json.JSONDecodeError:
                logger.warning(f"Could not parse metadata JSON for doc id {db_doc.id}: {db_doc.doc_metadata}")
                document_info.doc_metadata = {}
        else:
            document_info.doc_metadata = {}
            
        document_info.user_id = db_doc.user_id
        document_info.original_filename = db_doc.original_filename
        document_info.file_type = db_doc.file_type
        document_info.version = db_doc.version
        document_info.checksum = db_doc.checksum
        return document_info
        
    async def save(self, document_info: DomainPDFDocumentInfo, content: bytes, user_id: str) -> DomainPDFDocumentInfo:
        async with self.async_session_factory() as session:
            async with session.begin():
                try:
                    db_document = await self._create_db_document_from_info(document_info, len(content), user_id)
                    
                    await self.minio_client.upload_pdf_document(
                        content=content,
                        filename=db_document.original_filename,
                        object_name_override=db_document.storage_path
                    )
                    
                    session.add(db_document)
                    await session.flush()
                    await session.refresh(db_document)
                    
                    return self._update_info_from_db_document(document_info, db_document)
                except Exception as e:
                    logger.error(f"Error saving PDF document (title: {document_info.title}, user: {user_id}): {e}", exc_info=True)
            raise StorageException(f"Không thể lưu tài liệu PDF: {str(e)}")

    async def get(self, document_id: str, user_id_check: Optional[str] = None) -> Tuple[Optional[DomainPDFDocumentInfo], Optional[bytes]]:
        async with self.async_session_factory() as session:
            try:
                stmt = select(DBDocument).where(and_(DBDocument.id == document_id, DBDocument.document_category == "pdf"))
                if user_id_check is not None:
                    stmt = stmt.where(DBDocument.user_id == user_id_check)
                
                result = await session.execute(stmt)
                db_doc = result.scalar_one_or_none()

                if not db_doc:
                    return None, None
                
                pdf_info = self._update_info_from_db_document(DomainPDFDocumentInfo(), db_doc)
                
                content = await self.minio_client.download_pdf_document(pdf_info.storage_path)
                return pdf_info, content
            except Exception as e:
                logger.error(f"Error getting PDF document (id: {document_id}, user_check: {user_id_check}): {e}", exc_info=True)
                return None, None

    async def update(self, document_info: DomainPDFDocumentInfo, user_id_check: Optional[str] = None) -> DomainPDFDocumentInfo:
        async with self.async_session_factory() as session:
            async with session.begin():
                try:
                    if not document_info.id:
                        raise ValueError("Document ID is required for update.")

                    stmt_select = select(DBDocument).where(and_(DBDocument.id == document_info.id, DBDocument.document_category == "pdf"))
                    if user_id_check is not None:
                        stmt_select = stmt_select.where(DBDocument.user_id == user_id_check)
                    
                    result = await session.execute(stmt_select)
                    db_doc_to_update = result.scalar_one_or_none()

                    if not db_doc_to_update:
                        raise DocumentNotFoundException(f"Tài liệu PDF {document_info.id} không tìm thấy hoặc không có quyền cập nhật.")

                    db_doc_to_update.title = document_info.title
                    db_doc_to_update.description = document_info.description
                    db_doc_to_update.doc_metadata = json.dumps(document_info.doc_metadata) if document_info.doc_metadata else None
                    db_doc_to_update.page_count = getattr(document_info, 'page_count', db_doc_to_update.page_count)
                    db_doc_to_update.is_encrypted = getattr(document_info, 'is_encrypted', db_doc_to_update.is_encrypted)
                    db_doc_to_update.original_filename = getattr(document_info, 'original_filename', db_doc_to_update.original_filename)
                    db_doc_to_update.file_type = getattr(document_info, 'file_type', db_doc_to_update.file_type) or "application/pdf"
                    db_doc_to_update.updated_at = datetime.now()

                    await session.flush()
                    await session.refresh(db_doc_to_update)
                    
                    return self._update_info_from_db_document(document_info, db_doc_to_update)
                except DocumentNotFoundException:
                    raise
                except Exception as e:
                    logger.error(f"Error updating PDF document (id: {document_info.id}, user_check: {user_id_check}): {e}", exc_info=True)
                    raise StorageException(f"Không thể cập nhật tài liệu PDF {document_info.id}: {str(e)}")

    async def delete(self, document_id: str, user_id_check: Optional[str] = None) -> None:
        async with self.async_session_factory() as session: 
            async with session.begin():
                try:
                    stmt_select = select(DBDocument).where(and_(DBDocument.id == document_id, DBDocument.document_category == "pdf"))
                    if user_id_check is not None:
                        stmt_select = stmt_select.where(DBDocument.user_id == user_id_check)
                    
                    result = await session.execute(stmt_select)
                    db_doc_to_delete = result.scalar_one_or_none()

                    if not db_doc_to_delete:
                        raise DocumentNotFoundException(f"Tài liệu PDF {document_id} không tìm thấy hoặc không có quyền xóa.")
                    
                    storage_path_to_delete = db_doc_to_delete.storage_path
                    
                    await session.delete(db_doc_to_delete)
                    await session.flush()

                    if storage_path_to_delete:
                        try:
                            await self.minio_client.delete_pdf_document(storage_path_to_delete)
                        except Exception as minio_e:
                            logger.error(f"Lỗi khi xóa file {storage_path_to_delete} từ MinIO cho PDF document {document_id}: {minio_e}", exc_info=True)
                except DocumentNotFoundException:
                    raise
                except Exception as e:
                    logger.error(f"Error deleting PDF document (id: {document_id}, user_check: {user_id_check}): {e}", exc_info=True)
                    raise StorageException(f"Không thể xóa tài liệu PDF {document_id}: {str(e)}")

    async def list(self, skip: int = 0, limit: int = 10, search: Optional[str] = None, user_id: Optional[str] = None) -> Tuple[List[DomainPDFDocumentInfo], int]:
        async with self.async_session_factory() as session: 
            try:
                stmt_select = select(DBDocument).where(DBDocument.document_category == "pdf")
                stmt_count = select(func.count(DBDocument.id)).where(DBDocument.document_category == "pdf")
            
                if user_id is not None:
                    stmt_select = stmt_select.where(DBDocument.user_id == user_id)
                    stmt_count = stmt_count.where(DBDocument.user_id == user_id)
                
                if search:
                    search_term = f"%{search.lower()}%"
                    stmt_select = stmt_select.where(
                        (DBDocument.title.ilike(search_term)) | (DBDocument.description.ilike(search_term))
                    )
                    stmt_count = stmt_count.where(
                        (DBDocument.title.ilike(search_term)) | (DBDocument.description.ilike(search_term))
                    )
                
                total_count_result = await session.execute(stmt_count)
                total_count = total_count_result.scalar_one_or_none() or 0
                
                stmt_select = stmt_select.order_by(DBDocument.created_at.desc()).offset(skip).limit(limit)
                
                result_select = await session.execute(stmt_select)
                db_documents = result_select.scalars().all()

                documents_list = []
                for db_doc in db_documents:
                    pdf_info = self._update_info_from_db_document(DomainPDFDocumentInfo(), db_doc)
                    documents_list.append(pdf_info)
                
                return documents_list, total_count
            except Exception as e:
                logger.error(f"Error listing PDF documents (user: {user_id}, search: {search}): {e}", exc_info=True)
                return [], 0


class PNGDocumentRepository:
    """
    Repository để làm việc với tài liệu PNG, lưu trữ metadata trong PostgreSQL sử dụng SQLAlchemy.
    """

    def __init__(self, minio_client: MinioClient, db_session_factory: "sessionmaker[AsyncSession]"):
        self.minio_client = minio_client
        self.async_session_factory = db_session_factory

    async def _create_db_document_from_info(self, document_info: DomainPNGDocumentInfo, content_len: int, user_id_param: str) -> DBDocument:
        if user_id_param is None:
            logger.error(f"Attempting to create DBDocument for PNG without user_id. Original name: {document_info.original_filename}")
            raise StorageException("user_id is required to save the PNG document.")

        storage_id = str(uuid.uuid4())
        db_doc_id = str(uuid.uuid4())
        doc_category = "png"
        original_filename = document_info.original_filename if document_info.original_filename else f"{storage_id}.png"
        storage_path = f"{doc_category}/{storage_id}/{original_filename}"
        metadata_to_save = json.dumps(document_info.doc_metadata) if document_info.doc_metadata else None

        return DBDocument(
            id=db_doc_id,
            storage_id=storage_id,
            document_category=doc_category,
            title=document_info.title or os.path.splitext(original_filename)[0],
            description=document_info.description,
            file_size=content_len,
            file_type="image/png",
            storage_path=storage_path,
            original_filename=original_filename,
            doc_metadata=metadata_to_save,
            created_at=document_info.created_at or datetime.now(),
            updated_at=document_info.updated_at or datetime.now(),
            user_id=user_id_param,
            version=getattr(document_info, 'version', 1),
            checksum=getattr(document_info, 'checksum', None)
        )

    def _update_info_from_db_document(self, document_info: DomainPNGDocumentInfo, db_doc: DBDocument) -> DomainPNGDocumentInfo:
        document_info.id = str(db_doc.id)
        document_info.storage_id = db_doc.storage_id
        document_info.storage_path = db_doc.storage_path
        document_info.created_at = db_doc.created_at
        document_info.updated_at = db_doc.updated_at
        document_info.title = db_doc.title
        document_info.description = db_doc.description
        document_info.file_size = db_doc.file_size
        if db_doc.doc_metadata:
            try:
                document_info.doc_metadata = json.loads(db_doc.doc_metadata)
            except json.JSONDecodeError:
                logger.warning(f"Could not parse metadata JSON for PNG doc id {db_doc.id}: {db_doc.doc_metadata}")
                document_info.doc_metadata = {}
        else:
            document_info.doc_metadata = {}
        document_info.user_id = db_doc.user_id
        document_info.original_filename = db_doc.original_filename
        document_info.file_type = db_doc.file_type
        document_info.version = db_doc.version
        document_info.checksum = db_doc.checksum
        return document_info

    async def save(self, document_info: DomainPNGDocumentInfo, content: bytes, user_id: str) -> DomainPNGDocumentInfo:
        async with self.async_session_factory() as session:
            async with session.begin():
                try:
                    db_document = await self._create_db_document_from_info(document_info, len(content), user_id)
                    
                    await self.minio_client.upload_png_document(
                    content=content,
                        filename=db_document.original_filename,
                        object_name_override=db_document.storage_path
                    )
                    
                    session.add(db_document)
                    await session.flush()
                    await session.refresh(db_document)
                    
                    return self._update_info_from_db_document(document_info, db_document)
                except Exception as e:
                    logger.error(f"Error saving PNG document (original_filename: {document_info.original_filename}, user: {user_id}): {e}", exc_info=True)
                    raise StorageException(f"Không thể lưu tài liệu PNG: {str(e)}")

    async def get(self, document_id: str, user_id_check: Optional[str] = None) -> Tuple[Optional[DomainPNGDocumentInfo], Optional[bytes]]:
        async with self.async_session_factory() as session:
            try:
                stmt = select(DBDocument).where(and_(DBDocument.id == document_id, DBDocument.document_category == "png"))
                if user_id_check is not None:
                    stmt = stmt.where(DBDocument.user_id == user_id_check)
                
                result = await session.execute(stmt)
                db_doc = result.scalar_one_or_none()

                if not db_doc:
                    return None, None
                
                png_info = self._update_info_from_db_document(DomainPNGDocumentInfo(), db_doc)
                
                content = await self.minio_client.download_png_document(png_info.storage_path)
                return png_info, content
            except Exception as e:
                logger.error(f"Error getting PNG document (id: {document_id}, user_check: {user_id_check}): {e}", exc_info=True)
                return None, None

    async def update(self, document_info: DomainPNGDocumentInfo, user_id_check: Optional[str] = None) -> DomainPNGDocumentInfo:
        async with self.async_session_factory() as session:
            async with session.begin():
                try:
                    if not document_info.id:
                        raise ValueError("Document ID is required for update.")
                        
                    stmt_select = select(DBDocument).where(and_(DBDocument.id == document_info.id, DBDocument.document_category == "png"))
                    if user_id_check is not None:
                        stmt_select = stmt_select.where(DBDocument.user_id == user_id_check)
                    
                    result = await session.execute(stmt_select)
                    db_doc_to_update = result.scalar_one_or_none()

                    if not db_doc_to_update:
                        raise DocumentNotFoundException(f"Tài liệu PNG {document_info.id} không tìm thấy hoặc không có quyền cập nhật.")

                    db_doc_to_update.title = document_info.title
                    db_doc_to_update.description = document_info.description
                    db_doc_to_update.doc_metadata = json.dumps(document_info.doc_metadata) if document_info.doc_metadata else None
                    db_doc_to_update.original_filename = getattr(document_info, 'original_filename', db_doc_to_update.original_filename)
                    db_doc_to_update.file_type = getattr(document_info, 'file_type', db_doc_to_update.file_type) or "image/png"
                    db_doc_to_update.updated_at = datetime.now()

                    await session.flush()
                    await session.refresh(db_doc_to_update)
                    
                    return self._update_info_from_db_document(document_info, db_doc_to_update)
                except DocumentNotFoundException:
                    raise
                except Exception as e:
                    logger.error(f"Error updating PNG document (id: {document_info.id}, user_check: {user_id_check}): {e}", exc_info=True)
                    raise StorageException(f"Không thể cập nhật tài liệu PNG {document_info.id}: {str(e)}")

    async def delete(self, document_id: str, user_id_check: Optional[str] = None) -> None:
        async with self.async_session_factory() as session: 
            async with session.begin():
                try:
                    stmt_select = select(DBDocument).where(and_(DBDocument.id == document_id, DBDocument.document_category == "png"))
                    if user_id_check is not None:
                        stmt_select = stmt_select.where(DBDocument.user_id == user_id_check)
                    
                    result = await session.execute(stmt_select)
                    db_doc_to_delete = result.scalar_one_or_none()

                    if not db_doc_to_delete:
                        raise DocumentNotFoundException(f"Tài liệu PNG {document_id} không tìm thấy hoặc không có quyền xóa.")
                    
                    storage_path_to_delete = db_doc_to_delete.storage_path
                    
                    await session.delete(db_doc_to_delete)
                    await session.flush()

                    if storage_path_to_delete:
                        try:
                            await self.minio_client.delete_png_document(storage_path_to_delete)
                        except Exception as minio_e:
                            logger.error(f"Lỗi khi xóa file {storage_path_to_delete} từ MinIO cho PNG document {document_id}: {minio_e}", exc_info=True)
                except DocumentNotFoundException:
                    raise
                except Exception as e:
                    logger.error(f"Error deleting PNG document (id: {document_id}, user_check: {user_id_check}): {e}", exc_info=True)
                    raise StorageException(f"Không thể xóa tài liệu PNG {document_id}: {str(e)}")

    async def list(self, skip: int = 0, limit: int = 10, search: Optional[str] = None, user_id: Optional[str] = None) -> Tuple[List[DomainPNGDocumentInfo], int]:
        async with self.async_session_factory() as session: 
            try:
                stmt_select = select(DBDocument).where(DBDocument.document_category == "png")
                stmt_count = select(func.count(DBDocument.id)).where(DBDocument.document_category == "png")
                
                if user_id is not None:
                    stmt_select = stmt_select.where(DBDocument.user_id == user_id)
                    stmt_count = stmt_count.where(DBDocument.user_id == user_id)
                
                if search:
                    search_term = f"%{search.lower()}%"
                    stmt_select = stmt_select.where(
                        (DBDocument.title.ilike(search_term)) | (DBDocument.description.ilike(search_term))
                    )
                    stmt_count = stmt_count.where(
                        (DBDocument.title.ilike(search_term)) | (DBDocument.description.ilike(search_term))
                    )
                
                total_count_result = await session.execute(stmt_count)
                total_count = total_count_result.scalar_one_or_none() or 0
                
                stmt_select = stmt_select.order_by(DBDocument.created_at.desc()).offset(skip).limit(limit)
                
                result_select = await session.execute(stmt_select)
                db_documents = result_select.scalars().all()

                documents_list = []
                for db_doc in db_documents:
                    png_info = self._update_info_from_db_document(DomainPNGDocumentInfo(), db_doc)
                    documents_list.append(png_info)
                
                return documents_list, total_count
            except Exception as e:
                logger.error(f"Error listing PNG documents (user: {user_id}, search: {search}): {e}", exc_info=True)
                return [], 0


class StampRepository:
    """
    Repository để làm việc với mẫu dấu.
    """

    def __init__(self, minio_client: MinioClient):
        """
        Khởi tạo repository.

        Args:
            minio_client: Client MinIO để lưu trữ mẫu dấu
        """
        self.minio_client = minio_client
        self.stamps_metadata_file = os.path.join(settings.TEMP_DIR, "stamps_metadata.json")
        self.stamps: Dict[str, StampInfo] = {}
        self._load_metadata()

    def _load_metadata(self) -> None:
        """
        Tải metadata của mẫu dấu từ file.
        """
        try:
            if os.path.exists(self.stamps_metadata_file):
                with open(self.stamps_metadata_file, "r") as f:
                    data = json.load(f)
                    for stamp_id, stamp_data in data.items():
                        self.stamps[stamp_id] = StampInfo(**stamp_data)
        except Exception as e:
            self._save_metadata()

    def _save_metadata(self) -> None:
        """
        Lưu metadata của mẫu dấu vào file.
        """
        try:
            os.makedirs(settings.TEMP_DIR, exist_ok=True)
            data = {stamp_id: stamp.dict() for stamp_id, stamp in self.stamps.items()}
            with open(self.stamps_metadata_file, "w") as f:
                json.dump(data, f, default=str)
        except Exception as e:
            raise StorageException(f"Không thể lưu metadata mẫu dấu: {str(e)}")

    async def save(self, stamp_info: StampInfo, content: bytes) -> StampInfo:
        """
        Lưu mẫu dấu mới.

        Args:
            stamp_info: Thông tin mẫu dấu
            content: Nội dung mẫu dấu

        Returns:
            Thông tin mẫu dấu đã lưu
        """
        try:
            minio_object_name = f"stamps/{stamp_info.id}/{stamp_info.original_filename}"
            stamp_info.storage_path = minio_object_name
            
            await self.minio_client.upload_stamp(
                content=content,
                object_name_override=minio_object_name
            )

            stamp_info.file_size = len(content)
            self.stamps[stamp_info.id] = stamp_info
            self._save_metadata()
            return stamp_info
        except Exception as e:
            raise StorageException(f"Không thể lưu mẫu dấu: {str(e)}")

    async def get(self, stamp_id: str) -> Tuple[StampInfo, bytes]:
        """
        Lấy thông tin và nội dung mẫu dấu.

        Args:
            stamp_id: ID của mẫu dấu

        Returns:
            Tuple chứa thông tin và nội dung mẫu dấu
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
            raise StorageException(f"Không thể lấy mẫu dấu {stamp_id}: {str(e)}")

    async def update(self, stamp_info: StampInfo) -> StampInfo:
        """
        Cập nhật thông tin mẫu dấu.
        """
        try:
            if stamp_info.id not in self.stamps:
                raise StampNotFoundException(stamp_info.id)

            existing_stamp = self.stamps[stamp_info.id]
            stamp_info.storage_path = existing_stamp.storage_path
            stamp_info.file_size = existing_stamp.file_size
            stamp_info.original_filename = existing_stamp.original_filename

            stamp_info.updated_at = datetime.now()
            self.stamps[stamp_info.id] = stamp_info
            self._save_metadata()
            return stamp_info
        except StampNotFoundException:
            raise
        except Exception as e:
            raise StorageException(f"Không thể cập nhật mẫu dấu {stamp_info.id}: {str(e)}")

    async def delete(self, stamp_id: str) -> None:
        """
        Xóa mẫu dấu.
        """
        try:
            if stamp_id not in self.stamps:
                raise StampNotFoundException(stamp_id)
            stamp_info = self.stamps[stamp_id]
            await self.minio_client.delete_stamp(stamp_info.storage_path)
            del self.stamps[stamp_id]
            self._save_metadata()
        except StampNotFoundException:
            raise
        except Exception as e:
            raise StorageException(f"Không thể xóa mẫu dấu {stamp_id}: {str(e)}")

    async def list(self, skip: int = 0, limit: int = 10) -> List[StampInfo]:
        """
        Lấy danh sách mẫu dấu.
        """
        try:
            stamps_list = list(self.stamps.values())
            sorted_stamps = sorted(
                stamps_list,
                key=lambda x: (x.name.lower() if x.name else '', x.created_at),
                reverse=False 
            )
            return sorted_stamps[skip:skip + limit]
        except Exception as e:
            raise StorageException(f"Không thể lấy danh sách mẫu dấu: {str(e)}")


class PDFProcessingRepository:
    """
    Repository để làm việc với thông tin xử lý PDF.
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
                        self.processings[processing_id] = PDFProcessingInfo(**processing_data)
        except Exception as e:
            self._save_metadata()

    def _save_metadata(self) -> None:
        try:
            os.makedirs(settings.TEMP_DIR, exist_ok=True)
            data = {pid: p.dict() for pid, p in self.processings.items()}
            with open(self.processing_metadata_file, "w") as f:
                json.dump(data, f, default=str)
        except Exception as e:
            raise StorageException(f"Không thể lưu metadata xử lý PDF: {str(e)}")

    async def save(self, processing_info: PDFProcessingInfo) -> PDFProcessingInfo:
        try:
            if not processing_info.id:
                processing_info.id = str(uuid.uuid4())
            self.processings[processing_info.id] = processing_info
            self._save_metadata()
            return processing_info
        except Exception as e:
            raise StorageException(f"Không thể lưu thông tin xử lý PDF: {str(e)}")

    async def get(self, processing_id: str) -> PDFProcessingInfo:
        try:
            if processing_id not in self.processings:
                raise DocumentNotFoundException(f"PDF Processing info with id '{processing_id}' not found.")
            return self.processings[processing_id]
        except DocumentNotFoundException:
            raise
        except Exception as e:
            raise StorageException(f"Không thể lấy thông tin xử lý PDF {processing_id}: {str(e)}")

    async def update(self, processing_info: PDFProcessingInfo) -> PDFProcessingInfo:
        try:
            if processing_info.id not in self.processings:
                raise DocumentNotFoundException(f"PDF Processing info with id '{processing_info.id}' not found for update.")
            processing_info.updated_at = datetime.now()
            self.processings[processing_info.id] = processing_info
            self._save_metadata()
            return processing_info
        except DocumentNotFoundException:
            raise
        except Exception as e:
            raise StorageException(f"Không thể cập nhật thông tin xử lý PDF {processing_info.id}: {str(e)}")

    async def delete(self, processing_id: str) -> None:
        try:
            if processing_id not in self.processings:
                raise DocumentNotFoundException(f"PDF Processing info with id '{processing_id}' not found for deletion.")
            del self.processings[processing_id]
            self._save_metadata()
        except DocumentNotFoundException:
            raise
        except Exception as e:
            raise StorageException(f"Không thể xóa thông tin xử lý PDF {processing_id}: {str(e)}")

    async def list_by_document(self, document_id: str, skip: int = 0, limit: int = 100) -> List[PDFProcessingInfo]:
        try:
            filtered_processings = [
                p for p in self.processings.values() if p.document_id == document_id
            ]
            sorted_processings = sorted(
                filtered_processings, key=lambda x: x.created_at, reverse=True
            )
            return sorted_processings[skip : skip + limit]
        except Exception as e:
            raise StorageException(f"Không thể lấy danh sách xử lý PDF cho document {document_id}: {str(e)}")


class MergeRepository:
    """
    Repository để làm việc với thông tin gộp tài liệu PDF.
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
                        self.merges[merge_id] = MergeInfo(**merge_data)
        except Exception as e:
            self._save_metadata()

    def _save_metadata(self) -> None:
        try:
            os.makedirs(settings.TEMP_DIR, exist_ok=True)
            data = {mid: m.dict() for mid, m in self.merges.items()}
            with open(self.merge_metadata_file, "w") as f:
                json.dump(data, f, default=str)
        except Exception as e:
            raise StorageException(f"Không thể lưu metadata gộp PDF: {str(e)}")

    async def save(self, merge_info: MergeInfo) -> MergeInfo:
        try:
            if not merge_info.id:
                merge_info.id = str(uuid.uuid4())
            self.merges[merge_info.id] = merge_info
            self._save_metadata()
            return merge_info
        except Exception as e:
            raise StorageException(f"Không thể lưu thông tin gộp PDF: {str(e)}")

    async def get(self, merge_id: str) -> MergeInfo:
        try:
            if merge_id not in self.merges:
                raise DocumentNotFoundException(f"Merge info with id '{merge_id}' not found.")
            return self.merges[merge_id]
        except DocumentNotFoundException:
            raise
        except Exception as e:
            raise StorageException(f"Không thể lấy thông tin gộp PDF {merge_id}: {str(e)}")

    async def update(self, merge_info: MergeInfo) -> MergeInfo:
        try:
            if merge_info.id not in self.merges:
                raise DocumentNotFoundException(f"Merge info with id '{merge_info.id}' not found for update.")
            self.merges[merge_info.id] = merge_info
            self._save_metadata()
            return merge_info
        except DocumentNotFoundException:
            raise
        except Exception as e:
            raise StorageException(f"Không thể cập nhật thông tin gộp PDF {merge_info.id}: {str(e)}")

    async def delete(self, merge_id: str) -> None:
        try:
            if merge_id not in self.merges:
                raise DocumentNotFoundException(f"Merge info with id '{merge_id}' not found for deletion.")
            del self.merges[merge_id]
            self._save_metadata()
        except DocumentNotFoundException:
            raise
        except Exception as e:
            raise StorageException(f"Không thể xóa thông tin gộp PDF {merge_id}: {str(e)}")

    async def list(self, skip: int = 0, limit: int = 100) -> List[MergeInfo]:
        try:
            all_merges = list(self.merges.values())
            sorted_merges = sorted(
                all_merges, key=lambda x: x.created_at, reverse=True
            )
            return sorted_merges[skip : skip + limit]
        except Exception as e:
            raise StorageException(f"Không thể lấy danh sách thông tin gộp PDF: {str(e)}")