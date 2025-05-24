import os
import json
import asyncpg
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import uuid
import logging

from domain.models import WordDocumentInfo as DocumentInfo, TemplateInfo, BatchProcessingInfo
from domain.exceptions import DocumentNotFoundException, TemplateNotFoundException, StorageException
from infrastructure.minio_client import MinioClient
from core.config import settings

logger = logging.getLogger(__name__)

class DocumentRepository:
    """
    Repository để làm việc với tài liệu Word sử dụng bảng documents chung
    """

    def __init__(self, minio_client: MinioClient, db_pool: asyncpg.Pool):
        self.minio_client = minio_client
        self.db_pool = db_pool

    async def save(self, document_info: DocumentInfo, content: bytes) -> DocumentInfo:
        """
        Lưu tài liệu Word vào MinIO và metadata vào bảng documents
        """
        async with self.db_pool.acquire() as connection:
            async with connection.transaction():
                try:
                    # Tạo các ID và paths
                    doc_id = str(uuid.uuid4())
                    storage_id = str(uuid.uuid4())
                    document_info.id = doc_id
                    document_info.storage_id = storage_id
                    document_info.document_category = "word"
                    
                    # Tạo storage path
                    object_name = f"word/{storage_id}/{document_info.original_filename}"
                    document_info.storage_path = object_name
                    
                    # Upload lên MinIO
                    await self.minio_client.upload_document(
                        content=content,
                        filename=document_info.original_filename
                    )
                    
                    # Cập nhật thông tin file
                    document_info.file_size = len(content)
                    if not document_info.file_type:
                        document_info.file_type = (
                            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                            if document_info.original_filename.endswith(".docx")
                            else "application/msword"
                        )
                    
                    # Validate user_id
                    if not document_info.user_id:
                        raise StorageException("user_id is required to save the document.")
                    
                    # Validate UUID format cho user_id
                    try:
                        uuid.UUID(document_info.user_id)
                    except ValueError:
                        raise StorageException("user_id must be a valid UUID format.")
                    
                    # Thiết lập timestamps
                    now = datetime.now()
                    document_info.created_at = document_info.created_at or now
                    document_info.updated_at = document_info.updated_at or now
                    
                    # Serialize metadata
                    metadata_json = json.dumps(document_info.doc_metadata) if document_info.doc_metadata else None
                    
                    # Insert vào database
                    query = """
                        INSERT INTO documents (
                            id, storage_id, document_category, title, description,
                            file_size, file_type, storage_path, original_filename, 
                            doc_metadata, created_at, updated_at, user_id,
                            version, checksum
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                        RETURNING id, created_at, updated_at
                    """
                    
                    record = await connection.fetchrow(
                        query,
                        doc_id, storage_id, "word", document_info.title, document_info.description,
                        document_info.file_size, document_info.file_type, object_name,
                        document_info.original_filename, metadata_json,
                        document_info.created_at, document_info.updated_at, document_info.user_id,
                        document_info.version or 1, document_info.checksum
                    )
                    
                    if record:
                        document_info.id = str(record['id'])
                        document_info.created_at = record['created_at']
                        document_info.updated_at = record['updated_at']
                    
                    return document_info
                    
                except Exception as e:
                    logger.error(f"Lỗi khi lưu tài liệu Word: {e}", exc_info=True)
                    raise StorageException(f"Không thể lưu tài liệu: {str(e)}")

    async def get(self, document_id: str, user_id_check: Optional[str] = None) -> Tuple[Optional[DocumentInfo], Optional[bytes]]:
        """
        Lấy tài liệu Word từ database và MinIO
        """
        async with self.db_pool.acquire() as connection:
            try:
                # Build query với user check nếu cần
                base_query = "SELECT * FROM documents WHERE id = $1 AND document_category = $2"
                params = [document_id, "word"]
                
                if user_id_check:
                    base_query += " AND user_id = $3"
                    params.append(user_id_check)
                
                record = await connection.fetchrow(base_query, *params)
                
                if not record:
                    return None, None
                
                # Convert record to dict và parse metadata
                doc_data = dict(record)
                if doc_data.get('doc_metadata'):
                    try:
                        doc_data['doc_metadata'] = json.loads(doc_data['doc_metadata'])
                    except json.JSONDecodeError:
                        doc_data['doc_metadata'] = {}
                else:
                    doc_data['doc_metadata'] = {}
                
                # Convert UUID fields to string
                doc_data['id'] = str(doc_data['id'])
                doc_data['storage_id'] = str(doc_data['storage_id'])
                doc_data['user_id'] = str(doc_data['user_id'])
                
                # Tạo DocumentInfo object
                document_info = DocumentInfo(**doc_data)
                
                # Download content từ MinIO
                try:
                    content = await self.minio_client.download_document(document_info.storage_path)
                    return document_info, content
                except Exception as minio_e:
                    logger.error(f"Lỗi MinIO khi tải {document_info.storage_path}: {minio_e}")
                    raise StorageException(f"Không thể tải nội dung tài liệu: {str(minio_e)}")
                    
            except Exception as e:
                logger.error(f"Lỗi khi lấy tài liệu {document_id}: {e}", exc_info=True)
                return None, None

    async def list(self, skip: int = 0, limit: int = 10, search: Optional[str] = None, user_id: Optional[str] = None) -> Tuple[List[DocumentInfo], int]:
        """
        Lấy danh sách tài liệu Word
        """
        async with self.db_pool.acquire() as connection:
            try:
                # Build base queries
                where_conditions = ["document_category = 'word'"]
                params = []
                param_count = 1
                
                # Add user filter
                if user_id:
                    where_conditions.append(f"user_id = ${param_count}")
                    params.append(user_id)
                    param_count += 1
                
                # Add search filter
                if search:
                    search_condition = f"(LOWER(title) LIKE ${param_count} OR LOWER(description) LIKE ${param_count})"
                    where_conditions.append(search_condition)
                    search_term = f"%{search.lower()}%"
                    params.extend([search_term, search_term])
                    param_count += 2
                
                where_clause = " AND ".join(where_conditions)
                
                # Count query
                count_query = f"SELECT COUNT(*) as total FROM documents WHERE {where_clause}"
                count_record = await connection.fetchrow(count_query, *params)
                total_count = count_record['total'] if count_record else 0
                
                # List query với pagination
                list_query = f"""
                    SELECT * FROM documents 
                    WHERE {where_clause}
                    ORDER BY created_at DESC 
                    LIMIT ${param_count} OFFSET ${param_count + 1}
                """
                params.extend([limit, skip])
                
                records = await connection.fetch(list_query, *params)
                
                # Convert records to DocumentInfo objects
                documents = []
                for record in records:
                    doc_data = dict(record)
                    
                    # Parse metadata
                    if doc_data.get('doc_metadata'):
                        try:
                            doc_data['doc_metadata'] = json.loads(doc_data['doc_metadata'])
                        except json.JSONDecodeError:
                            doc_data['doc_metadata'] = {}
                    else:
                        doc_data['doc_metadata'] = {}
                    
                    # Convert UUID fields
                    doc_data['id'] = str(doc_data['id'])
                    doc_data['storage_id'] = str(doc_data['storage_id'])
                    doc_data['user_id'] = str(doc_data['user_id'])
                    
                    documents.append(DocumentInfo(**doc_data))
                
                return documents, total_count
                
            except Exception as e:
                logger.error(f"Lỗi khi lấy danh sách tài liệu: {e}", exc_info=True)
                return [], 0

    async def update(self, document_info: DocumentInfo, user_id_check: Optional[str] = None) -> DocumentInfo:
        """
        Cập nhật thông tin tài liệu Word
        """
        async with self.db_pool.acquire() as connection:
            async with connection.transaction():
                try:
                    if not document_info.id:
                        raise ValueError("Document ID is required for update.")
                    
                    # Build update query
                    set_clauses = [
                        "title = $1",
                        "description = $2", 
                        "doc_metadata = $3",
                        "updated_at = $4"
                    ]
                    
                    document_info.updated_at = datetime.now()
                    metadata_json = json.dumps(document_info.doc_metadata) if document_info.doc_metadata else None
                    
                    params = [
                        document_info.title,
                        document_info.description,
                        metadata_json,
                        document_info.updated_at
                    ]
                    
                    # Build where conditions
                    where_conditions = ["id = $5", "document_category = $6"]
                    params.extend([document_info.id, "word"])
                    param_count = 7
                    
                    if user_id_check:
                        where_conditions.append(f"user_id = ${param_count}")
                        params.append(user_id_check)
                    
                    query = f"""
                        UPDATE documents 
                        SET {', '.join(set_clauses)}
                        WHERE {' AND '.join(where_conditions)}
                        RETURNING *
                    """
                    
                    record = await connection.fetchrow(query, *params)
                    
                    if not record:
                        raise DocumentNotFoundException(f"Tài liệu {document_info.id} không tìm thấy hoặc không có quyền cập nhật.")
                    
                    # Convert và return updated document
                    doc_data = dict(record)
                    if doc_data.get('doc_metadata'):
                        try:
                            doc_data['doc_metadata'] = json.loads(doc_data['doc_metadata'])
                        except json.JSONDecodeError:
                            doc_data['doc_metadata'] = {}
                    else:
                        doc_data['doc_metadata'] = {}
                    
                    doc_data['id'] = str(doc_data['id'])
                    doc_data['storage_id'] = str(doc_data['storage_id'])
                    doc_data['user_id'] = str(doc_data['user_id'])
                    
                    return DocumentInfo(**doc_data)
                    
                except DocumentNotFoundException:
                    raise
                except Exception as e:
                    logger.error(f"Lỗi khi cập nhật tài liệu {document_info.id}: {e}", exc_info=True)
                    raise StorageException(f"Không thể cập nhật tài liệu: {str(e)}")

    async def delete(self, document_id: str, user_id_check: Optional[str] = None) -> None:
        """
        Xóa tài liệu Word
        """
        async with self.db_pool.acquire() as connection:
            async with connection.transaction():
                try:
                    # Get document info trước khi xóa
                    get_query = "SELECT storage_path FROM documents WHERE id = $1 AND document_category = $2"
                    params = [document_id, "word"]
                    
                    if user_id_check:
                        get_query += " AND user_id = $3"
                        params.append(user_id_check)
                    
                    record = await connection.fetchrow(get_query, *params)
                    
                    if not record:
                        raise DocumentNotFoundException(f"Tài liệu {document_id} không tìm thấy hoặc không có quyền xóa.")
                    
                    storage_path = record['storage_path']
                    
                    # Delete từ database
                    delete_query = "DELETE FROM documents WHERE id = $1 AND document_category = $2"
                    delete_params = [document_id, "word"]
                    
                    if user_id_check:
                        delete_query += " AND user_id = $3"
                        delete_params.append(user_id_check)
                    
                    result = await connection.execute(delete_query, *delete_params)
                    
                    if result == "DELETE 0":
                        raise DocumentNotFoundException(f"Không thể xóa tài liệu {document_id}.")
                    
                    # Delete từ MinIO
                    if storage_path:
                        try:
                            await self.minio_client.delete_document(storage_path)
                        except Exception as minio_e:
                            logger.error(f"Lỗi khi xóa file từ MinIO {storage_path}: {minio_e}")
                    
                except DocumentNotFoundException:
                    raise
                except Exception as e:
                    logger.error(f"Lỗi khi xóa tài liệu {document_id}: {e}", exc_info=True)
                    raise StorageException(f"Không thể xóa tài liệu: {str(e)}")

class TemplateRepository:
    """
    Repository để làm việc với mẫu tài liệu Word
    """

    def __init__(self, minio_client: MinioClient):
        self.minio_client = minio_client
        self.templates_dir = settings.TEMPLATES_DIR 
        os.makedirs(self.templates_dir, exist_ok=True)
        self.metadata_file = os.path.join(self.templates_dir, "word_templates_metadata.json")
        self._templates_metadata: List[TemplateInfo] = []
        self._load_metadata()

    def _load_metadata(self) -> None:
        """
        Tải metadata của templates từ file
        """
        try:
            if os.path.exists(self.metadata_file):
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    raw_list = json.load(f)
                    self._templates_metadata = [TemplateInfo(**data) for data in raw_list]
            else:
                self._templates_metadata = []
        except Exception as e:
            logger.error(f"Lỗi khi tải metadata templates: {e}", exc_info=True)
            self._templates_metadata = []

    def _save_metadata(self) -> None:
        """
        Lưu metadata của templates vào file
        """
        try:
            os.makedirs(os.path.dirname(self.metadata_file), exist_ok=True)
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                serialized_data = []
                for template in self._templates_metadata:
                    template_dict = template.dict()
                    # Convert datetime to ISO format
                    if template_dict.get('created_at'):
                        template_dict['created_at'] = template_dict['created_at'].isoformat()
                    if template_dict.get('updated_at'):
                        template_dict['updated_at'] = template_dict['updated_at'].isoformat()
                    serialized_data.append(template_dict)
                
                json.dump(serialized_data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error(f"Lỗi khi lưu metadata templates: {e}", exc_info=True)
            raise StorageException(f"Không thể lưu metadata templates: {str(e)}")

    async def save(self, template_info: TemplateInfo, content: bytes) -> TemplateInfo:
        """
        Lưu template mới
        """
        try:
            # Check duplicate
            if any(t.template_id == template_info.template_id for t in self._templates_metadata):
                raise StorageException(f"Template với ID '{template_info.template_id}' đã tồn tại.")
            
            # Tạo thư mục template
            template_dir = os.path.join(self.templates_dir, template_info.template_id)
            os.makedirs(template_dir, exist_ok=True)
            
            # Lưu file
            template_file_path = os.path.join(template_dir, template_info.original_filename)
            with open(template_file_path, 'wb') as f:
                f.write(content)
            
            # Cập nhật thông tin
            template_info.storage_path = template_file_path
            template_info.file_size = len(content)
            template_info.created_at = template_info.created_at or datetime.now()
            template_info.updated_at = template_info.updated_at or datetime.now()
            
            # Lưu metadata
            self._templates_metadata.append(template_info)
            self._save_metadata()
            
            return template_info
            
        except Exception as e:
            logger.error(f"Lỗi khi lưu template: {e}", exc_info=True)
            raise StorageException(f"Không thể lưu template: {str(e)}")

    async def get(self, template_id: str) -> Tuple[Optional[TemplateInfo], Optional[bytes]]:
        """
        Lấy template theo ID
        """
        try:
            self._load_metadata()
            
            template = next((t for t in self._templates_metadata if t.template_id == template_id), None)
            if not template:
                return None, None
            
            if not template.storage_path or not os.path.exists(template.storage_path):
                logger.error(f"Template file không tồn tại: {template.storage_path}")
                return template, None
            
            with open(template.storage_path, 'rb') as f:
                content = f.read()
            
            return template, content
            
        except Exception as e:
            logger.error(f"Lỗi khi lấy template {template_id}: {e}", exc_info=True)
            return None, None

    async def list(self, category: Optional[str] = None, skip: int = 0, limit: int = 10) -> Tuple[List[TemplateInfo], int]:
        """
        Lấy danh sách templates
        """
        try:
            self._load_metadata()
            
            filtered_templates = self._templates_metadata
            if category:
                filtered_templates = [t for t in filtered_templates if t.category.lower() == category.lower()]
            
            total_count = len(filtered_templates)
            paginated_templates = filtered_templates[skip:skip + limit]
            
            return paginated_templates, total_count
            
        except Exception as e:
            logger.error(f"Lỗi khi lấy danh sách templates: {e}", exc_info=True)
            return [], 0

    async def update(self, template_info: TemplateInfo) -> TemplateInfo:
        """
        Cập nhật template
        """
        try:
            index = -1
            for i, t in enumerate(self._templates_metadata):
                if t.template_id == template_info.template_id:
                    index = i
                    break
            
            if index == -1:
                raise TemplateNotFoundException(template_info.template_id)
            
            # Cập nhật thông tin
            current_template = self._templates_metadata[index]
            current_template.name = template_info.name or current_template.name
            current_template.description = template_info.description or current_template.description
            current_template.category = template_info.category or current_template.category
            current_template.tags = template_info.tags or current_template.tags
            current_template.doc_metadata = template_info.doc_metadata or current_template.doc_metadata
            current_template.updated_at = datetime.now()
            
            self._templates_metadata[index] = current_template
            self._save_metadata()
            
            return current_template
            
        except TemplateNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật template {template_info.template_id}: {e}", exc_info=True)
            raise StorageException(f"Không thể cập nhật template: {str(e)}")

    async def delete(self, template_id: str) -> None:
        """
        Xóa template
        """
        try:
            template = None
            index = -1
            
            for i, t in enumerate(self._templates_metadata):
                if t.template_id == template_id:
                    template = t
                    index = i
                    break
            
            if not template:
                raise TemplateNotFoundException(template_id)
            
            # Xóa file và thư mục
            if template.storage_path and os.path.exists(template.storage_path):
                template_dir = os.path.dirname(template.storage_path)
                if os.path.exists(template_dir):
                    import shutil
                    shutil.rmtree(template_dir, ignore_errors=True)
            
            # Xóa khỏi metadata
            del self._templates_metadata[index]
            self._save_metadata()
            
        except TemplateNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Lỗi khi xóa template {template_id}: {e}", exc_info=True)
            raise StorageException(f"Không thể xóa template: {str(e)}")

class BatchProcessingRepository:
    """
    Repository để làm việc với batch processing
    """

    def __init__(self):
        self.batches_dir = os.path.join(settings.TEMP_DIR, "word_batches")
        os.makedirs(self.batches_dir, exist_ok=True)
        self.metadata_file = os.path.join(self.batches_dir, "_batch_metadata.json")
        self._batch_metadata: Dict[str, BatchProcessingInfo] = {}
        self._load_metadata()

    def _load_metadata(self) -> None:
        """
        Tải metadata của batch processing
        """
        try:
            if os.path.exists(self.metadata_file):
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    raw_dict = json.load(f)
                    for task_id, data in raw_dict.items():
                        # Convert datetime strings back to datetime objects
                        if data.get('created_at') and isinstance(data['created_at'], str):
                            data['created_at'] = datetime.fromisoformat(data['created_at'])
                        if data.get('updated_at') and isinstance(data['updated_at'], str):
                            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
                        
                        self._batch_metadata[task_id] = BatchProcessingInfo(**data)
            else:
                self._batch_metadata = {}
        except Exception as e:
            logger.error(f"Lỗi khi tải metadata batch processing: {e}", exc_info=True)
            self._batch_metadata = {}

    def _save_metadata(self) -> None:
        """
        Lưu metadata của batch processing
        """
        try:
            os.makedirs(os.path.dirname(self.metadata_file), exist_ok=True)
            serializable_metadata = {}
            
            for task_id, batch_info in self._batch_metadata.items():
                batch_dict = batch_info.dict()
                # Convert datetime to ISO format
                if batch_dict.get('created_at'):
                    batch_dict['created_at'] = batch_dict['created_at'].isoformat()
                if batch_dict.get('updated_at'):
                    batch_dict['updated_at'] = batch_dict['updated_at'].isoformat()
                
                serializable_metadata[task_id] = batch_dict
            
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(serializable_metadata, f, ensure_ascii=False, indent=4)
                
        except Exception as e:
            logger.error(f"Lỗi khi lưu metadata batch processing: {e}", exc_info=True)
            raise StorageException(f"Không thể lưu metadata batch processing: {str(e)}")

    async def save(self, batch_info: BatchProcessingInfo) -> BatchProcessingInfo:
        """
        Lưu thông tin batch processing
        """
        try:
            if not batch_info.task_id:
                batch_info.task_id = str(uuid.uuid4())
            
            now = datetime.now()
            batch_info.created_at = batch_info.created_at or now
            batch_info.updated_at = batch_info.updated_at or now
            
            self._batch_metadata[batch_info.task_id] = batch_info
            self._save_metadata()
            
            return batch_info
            
        except Exception as e:
            logger.error(f"Lỗi khi lưu batch processing: {e}", exc_info=True)
            raise StorageException(f"Không thể lưu batch processing: {str(e)}")

    async def get(self, batch_id: str) -> Optional[BatchProcessingInfo]:
        """
        Lấy thông tin batch processing
        """
        try:
            self._load_metadata()
            return self._batch_metadata.get(batch_id)
        except Exception as e:
            logger.error(f"Lỗi khi lấy batch processing {batch_id}: {e}", exc_info=True)
            return None

    async def update(self, batch_info: BatchProcessingInfo) -> BatchProcessingInfo:
        """
        Cập nhật thông tin batch processing
        """
        try:
            if not batch_info.task_id or batch_info.task_id not in self._batch_metadata:
                raise DocumentNotFoundException(f"Batch task with ID '{batch_info.task_id}' not found.")
            
            batch_info.updated_at = datetime.now()
            self._batch_metadata[batch_info.task_id] = batch_info
            self._save_metadata()
            
            return batch_info
            
        except DocumentNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật batch processing {batch_info.task_id}: {e}", exc_info=True)
            raise StorageException(f"Không thể cập nhật batch processing: {str(e)}")

    async def delete(self, batch_id: str) -> None:
        """
        Xóa thông tin batch processing
        """
        try:
            if batch_id in self._batch_metadata:
                del self._batch_metadata[batch_id]
                self._save_metadata()
            else:
                raise DocumentNotFoundException(f"Batch task with ID '{batch_id}' not found.")
                
        except DocumentNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Lỗi khi xóa batch processing {batch_id}: {e}", exc_info=True)
            raise StorageException(f"Không thể xóa batch processing: {str(e)}")