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
    Repository để làm việc với tài liệu Word, lưu trữ metadata trong PostgreSQL.
    """

    def __init__(self, minio_client: MinioClient, db_pool: asyncpg.Pool):
        """
        Khởi tạo repository.

        Args:
            minio_client: Client MinIO để lưu trữ tài liệu
            db_pool: Connection pool của AsyncPG
        """
        self.minio_client = minio_client
        self.db_pool = db_pool

    async def save(self, document_info: DocumentInfo, content: bytes) -> DocumentInfo:
        """
        Lưu tài liệu mới vào MinIO và metadata vào PostgreSQL.

        Args:
            document_info: Thông tin tài liệu (chưa có storage_id, storage_path, file_size, file_type)
            content: Nội dung tài liệu

        Returns:
            Thông tin tài liệu đã lưu (bao gồm các trường được cập nhật)
        """
        async with self.db_pool.acquire() as connection:
            async with connection.transaction():
                try:
                    document_info.storage_id = str(uuid.uuid4())
                    document_info.document_category = "word"
                    document_info.storage_path = f"{document_info.document_category}/{document_info.storage_id}/{document_info.original_filename}"
                    
                    await self.minio_client.upload_document(
                        content=content,
                        filename=document_info.original_filename,
                        object_name_override=document_info.storage_path
                    )

                    document_info.file_size = len(content)
                    if not document_info.file_type:
                        document_info.file_type = (
                            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                            if document_info.original_filename.endswith(".docx")
                            else "application/msword"
                        )
                    
                    metadata_json = json.dumps(document_info.doc_metadata) if document_info.doc_metadata else None
                    
                    user_id_to_save = getattr(document_info, 'user_id', None)
                    if user_id_to_save is None:
                        logger.error(f"Attempting to save document without user_id. Title: {document_info.title}")
                        raise StorageException("user_id is required to save the document.")
                    
                    now = datetime.now()
                    document_info.created_at = document_info.created_at or now
                    document_info.updated_at = document_info.updated_at or now

                    query_insert = """
                        INSERT INTO documents (
                            id, storage_id, document_category, title, description, 
                            file_size, file_type, storage_path, original_filename, doc_metadata,
                            created_at, updated_at, user_id, version, checksum 
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                        RETURNING id, created_at, updated_at; 
                    """
                    db_id = str(uuid.uuid4())
                    
                    record = await connection.fetchrow(
                        query_insert,
                        db_id,
                        document_info.storage_id, 
                        document_info.document_category, 
                        document_info.title, 
                        document_info.description, 
                        document_info.file_size, 
                        document_info.file_type,
                        document_info.storage_path,
                        document_info.original_filename, 
                        metadata_json,
                        document_info.created_at, 
                        document_info.updated_at, 
                        user_id_to_save,
                        getattr(document_info, 'version', 1),
                        getattr(document_info, 'checksum', None)
                    )
                    
                    if record:
                        document_info.id = str(record['id'])
                        document_info.created_at = record['created_at']
                        document_info.updated_at = record['updated_at']
                    else:
                        raise StorageException("Không thể lưu tài liệu vào database, không có record trả về.")

                    return document_info
                except asyncpg.exceptions.UniqueViolationError as e:
                    logger.error(f"Lỗi trùng lặp khi lưu tài liệu (title: {document_info.title}): {e}", exc_info=True)
                    raise StorageException(f"Lỗi trùng lặp khi lưu tài liệu: {str(e)}")
                except Exception as e:
                    logger.error(f"Không thể lưu tài liệu (title: {document_info.title}): {e}", exc_info=True)
                    raise StorageException(f"Không thể lưu tài liệu: {str(e)}")

    async def get(self, document_id: str, user_id_check: Optional[str] = None) -> Tuple[Optional[DocumentInfo], Optional[bytes]]:
        """
        Lấy thông tin và nội dung tài liệu từ PostgreSQL và MinIO.
        Kiểm tra user_id nếu được cung cấp.
        Args:
            document_id: ID của tài liệu (PK trong bảng documents)
            user_id_check: ID người dùng để kiểm tra quyền sở hữu (optional)

        Returns:
            Tuple chứa thông tin và nội dung tài liệu
        """
        async with self.db_pool.acquire() as connection:
            try:
                query_parts = ["SELECT * FROM documents WHERE id = $1 AND document_category = 'word'"]
                params: list[Any] = [document_id]
                param_idx = 2

                if user_id_check is not None:
                    query_parts.append(f"AND user_id = ${param_idx}")
                    params.append(user_id_check)
                
                final_query = " ".join(query_parts) + ";"
                record = await connection.fetchrow(final_query, *params)

                if not record:
                    return None, None

                doc_data = dict(record)
                if 'doc_metadata' in doc_data and isinstance(doc_data['doc_metadata'], str):
                    try:
                        doc_data['doc_metadata'] = json.loads(doc_data['doc_metadata'])
                    except (json.JSONDecodeError, TypeError):
                        doc_data['doc_metadata'] = {}
                elif 'doc_metadata' not in doc_data or doc_data['doc_metadata'] is None:
                    doc_data['doc_metadata'] = {}
                
                doc_data['id'] = str(doc_data['id'])
                
                document_info = DocumentInfo(**doc_data)
                
                try:
                    content = await self.minio_client.download_document(document_info.storage_path)
                except Exception as minio_e:
                    logger.error(f"MinIO error downloading {document_info.storage_path} for doc id {document_id}: {minio_e}", exc_info=True)
                    raise StorageException(f"Không thể tải nội dung tài liệu từ MinIO: {minio_e}")

                return document_info, content
            except Exception as e:
                logger.error(f"Lỗi khi lấy tài liệu {document_id}: {e}", exc_info=True)
                return None, None

    async def update(self, document_info: DocumentInfo, user_id_check: Optional[str] = None) -> DocumentInfo:
        """
        Cập nhật thông tin tài liệu trong PostgreSQL.
        Không cho phép cập nhật nội dung file qua hàm này, chỉ metadata.
        Kiểm tra user_id nếu được cung cấp.

        Args:
            document_info: Thông tin tài liệu mới (phải có id)
            user_id_check: ID người dùng để kiểm tra quyền sở hữu (optional)

        Returns:
            Thông tin tài liệu đã cập nhật
        """
        async with self.db_pool.acquire() as connection:
            try:
                if not document_info.id:
                    raise ValueError("Document ID is required for update.")

                document_info.updated_at = datetime.now()
                metadata_json_to_save = json.dumps(document_info.doc_metadata) if document_info.doc_metadata else None
                
                set_clauses = [
                    "title = $1", 
                    "description = $2", 
                    "doc_metadata = $3",
                    "updated_at = $4",
                    "original_filename = $5",
                    "file_type = $6"
                ]
                params: list[Any] = [
                    document_info.title, 
                    document_info.description, 
                    metadata_json_to_save,
                    document_info.updated_at,
                    document_info.original_filename,
                    document_info.file_type
                ]
                param_idx = len(params) + 1

                where_clauses = [f"id = ${param_idx}", "document_category = 'word'"]
                params.append(document_info.id)
                param_idx += 1

                if user_id_check is not None:
                    where_clauses.append(f"user_id = ${param_idx}")
                    params.append(user_id_check)
                
                query = f"UPDATE documents SET {', '.join(set_clauses)} WHERE {' AND '.join(where_clauses)} RETURNING *;"
                
                record = await connection.fetchrow(query, *params)

                if not record:
                    raise DocumentNotFoundException(f"Tài liệu {document_info.id} không tìm thấy hoặc không có quyền cập nhật.")
                
                updated_data = dict(record)
                if 'doc_metadata' in updated_data and isinstance(updated_data['doc_metadata'], str):
                    try:
                        updated_data['doc_metadata'] = json.loads(updated_data['doc_metadata'])
                    except (json.JSONDecodeError, TypeError):
                        updated_data['doc_metadata'] = {}
                elif 'doc_metadata' not in updated_data or updated_data['doc_metadata'] is None:
                    updated_data['doc_metadata'] = {}
                
                updated_data['id'] = str(updated_data['id'])
                return DocumentInfo(**updated_data)
            except DocumentNotFoundException:
                raise
            except Exception as e:
                logger.error(f"Lỗi khi cập nhật tài liệu {document_info.id}: {e}", exc_info=True)
                raise StorageException(f"Không thể cập nhật tài liệu: {str(e)}")

    async def delete(self, document_id: str, user_id_check: Optional[str] = None) -> None:
        """
        Xóa tài liệu khỏi PostgreSQL và MinIO.
        Kiểm tra user_id nếu được cung cấp.

        Args:
            document_id: ID của tài liệu
            user_id_check: ID người dùng để kiểm tra quyền sở hữu (optional)
        """
        async with self.db_pool.acquire() as connection:
            async with connection.transaction():
                try:
                    get_query_parts = ["SELECT storage_path FROM documents WHERE id = $1 AND document_category = 'word'"]
                    get_params: list[Any] = [document_id]
                    get_param_idx = 2
                    if user_id_check is not None:
                        get_query_parts.append(f"AND user_id = ${get_param_idx}")
                        get_params.append(user_id_check)
                    
                    get_final_query = " ".join(get_query_parts) + ";"
                    record = await connection.fetchrow(get_final_query, *get_params)

                    if not record:
                        raise DocumentNotFoundException(f"Tài liệu {document_id} không tìm thấy hoặc không có quyền xóa.")
                    
                    storage_path = record['storage_path']

                    delete_query_parts = ["DELETE FROM documents WHERE id = $1 AND document_category = 'word'"]
                    delete_params: list[Any] = [document_id]
                    delete_param_idx = 2
                    if user_id_check is not None:
                        delete_query_parts.append(f"AND user_id = ${delete_param_idx}")
                        delete_params.append(user_id_check)
                    
                    delete_final_query = " ".join(delete_query_parts) + " RETURNING id;"
                    deleted_record = await connection.fetchrow(delete_final_query, *delete_params)

                    if not deleted_record:
                        raise DocumentNotFoundException(f"Tài liệu {document_id} không tìm thấy khi cố gắng xóa (sau khi select).")

                    if storage_path:
                        try:
                            await self.minio_client.delete_document(storage_path)
                        except Exception as minio_e:
                            logger.error(f"Lỗi khi xóa file {storage_path} từ MinIO cho document {document_id}: {minio_e}", exc_info=True)
                    
                except DocumentNotFoundException:
                    raise
                except Exception as e:
                    logger.error(f"Lỗi khi xóa tài liệu {document_id}: {e}", exc_info=True)
                    raise StorageException(f"Không thể xóa tài liệu: {str(e)}")

    async def list(self, skip: int = 0, limit: int = 10, search: Optional[str] = None, user_id: Optional[str] = None) -> Tuple[List[DocumentInfo], int]:
        """
        Lấy danh sách tài liệu từ PostgreSQL.
        Lọc theo user_id nếu được cung cấp.
        """
        async with self.db_pool.acquire() as connection:
            try:
                base_query = "FROM documents WHERE document_category = 'word'"
                count_query_str = "SELECT COUNT(*) as total_count " + base_query
                select_query_str = "SELECT * " + base_query

                where_clauses: List[str] = []
                params: List[Any] = []
                param_idx = 1

                if user_id is not None:
                    where_clauses.append(f"user_id = ${param_idx}")
                    params.append(user_id)
                    param_idx += 1
                
                if search:
                    search_term_lower = f"%{search.lower()}%" 
                    where_clauses.append(f"(LOWER(title) LIKE ${param_idx} OR LOWER(description) LIKE ${param_idx})")
                    params.extend([search_term_lower, search_term_lower])
                    param_idx += 2

                if where_clauses:
                    conditions = " AND ".join(where_clauses)
                    count_query_str += " AND " + conditions
                    select_query_str += " AND " + conditions
                
                total_count_record = await connection.fetchrow(count_query_str, *params)
                total_count = total_count_record['total_count'] if total_count_record else 0

                select_query_str += f" ORDER BY created_at DESC LIMIT ${param_idx} OFFSET ${param_idx + 1};"
                params.append(limit)
                params.append(skip)

                records = await connection.fetch(select_query_str, *params)
                
                documents = []
                for r_dict in records:
                    doc_data = dict(r_dict)
                    if 'doc_metadata' in doc_data and isinstance(doc_data['doc_metadata'], str):
                        try:
                            doc_data['doc_metadata'] = json.loads(doc_data['doc_metadata'])
                        except (json.JSONDecodeError, TypeError):
                            doc_data['doc_metadata'] = {}
                    elif 'doc_metadata' not in doc_data or doc_data['doc_metadata'] is None:
                        doc_data['doc_metadata'] = {}
                    doc_data['id'] = str(doc_data['id'])
                    documents.append(DocumentInfo(**doc_data))
                
                return documents, total_count
            except Exception as e:
                logger.error(f"Lỗi khi liệt kê tài liệu (user: {user_id}, search: {search}): {e}", exc_info=True)
                return [], 0


class TemplateRepository:
    """
    Repository để làm việc với mẫu tài liệu Word.
    """

    def __init__(self, minio_client: MinioClient):
        """
        Khởi tạo repository.

        Args:
            minio_client: Client MinIO để lưu trữ mẫu tài liệu
        """
        self.minio_client = minio_client
        self.templates_dir = settings.TEMPLATES_DIR 
        os.makedirs(self.templates_dir, exist_ok=True)
        self.doc_metadata_file = os.path.join(self.templates_dir, "word_templates_metadata.json")
        self._templates_metadata: List[TemplateInfo] = []
        self._load_metadata()

    def _load_metadata(self) -> None:
        """
        Tải metadata của mẫu tài liệu từ file.
        """
        try:
            if os.path.exists(self.doc_metadata_file):
                with open(self.doc_metadata_file, 'r', encoding='utf-8') as f:
                    raw_list = json.load(f)
                    self._templates_metadata = [TemplateInfo(**data) for data in raw_list]
            else:
                self._templates_metadata = []
        except (json.JSONDecodeError, IOError, TypeError) as e:
            logger.error(f"Lỗi khi tải metadata cho template: {e}", exc_info=True)
            self._templates_metadata = []

    def _save_metadata(self) -> None:
        """
        Lưu metadata của mẫu tài liệu vào file.
        """
        try:
            os.makedirs(os.path.dirname(self.doc_metadata_file), exist_ok=True)
            with open(self.doc_metadata_file, 'w', encoding='utf-8') as f:
                json.dump([template.dict() for template in self._templates_metadata], f, ensure_ascii=False, indent=4)
        except IOError as e:
            logger.error(f"Lỗi khi lưu metadata cho template: {e}", exc_info=True)
            raise StorageException(f"Không thể lưu metadata cho template: {str(e)}")

    async def save(self, template_info: TemplateInfo, content: bytes) -> TemplateInfo:
        """
        Lưu mẫu tài liệu mới.

        Args:
            template_info: Thông tin mẫu tài liệu
            content: Nội dung mẫu tài liệu

        Returns:
            Thông tin mẫu tài liệu đã lưu
        """
        if any(t.template_id == template_info.template_id for t in self._templates_metadata):
            raise StorageException(f"Template với ID '{template_info.template_id}' đã tồn tại.")
        
        template_file_dir = os.path.join(self.templates_dir, template_info.template_id)
        os.makedirs(template_file_dir, exist_ok=True)
        template_file_path = os.path.join(template_file_dir, template_info.original_filename)
        
        try:
            with open(template_file_path, 'wb') as f:
                f.write(content)
        except IOError as e:
            logger.error(f"Lỗi khi lưu file template {template_info.original_filename}: {e}", exc_info=True)
            raise StorageException(f"Không thể lưu file template: {str(e)}")

        template_info.storage_path = template_file_path
        template_info.created_at = template_info.created_at or datetime.now()
        template_info.updated_at = template_info.updated_at or datetime.now()
        
        self._templates_metadata.append(template_info)
        self._save_metadata()
        return template_info

    async def get(self, template_id: str) -> Tuple[Optional[TemplateInfo], Optional[bytes]]:
        """
        Lấy thông tin và nội dung mẫu tài liệu.

        Args:
            template_id: ID của mẫu tài liệu

        Returns:
            Tuple chứa thông tin và nội dung mẫu tài liệu
        """
        found_template = next((t for t in self._templates_metadata if t.template_id == template_id), None)
        if not found_template:
            return None, None
        
        if not found_template.storage_path or not os.path.exists(found_template.storage_path):
            logger.error(f"File template không tìm thấy tại storage_path: {found_template.storage_path} cho template ID: {template_id}")
            return found_template, None

        try:
            with open(found_template.storage_path, 'rb') as f:
                content = f.read()
            return found_template, content
        except IOError as e:
            logger.error(f"Lỗi khi đọc file template {found_template.original_filename}: {e}", exc_info=True)
            return found_template, None

    async def update(self, template_info_to_update: TemplateInfo) -> TemplateInfo:
        """
        Cập nhật thông tin mẫu tài liệu.
        Lưu ý: Hàm này chỉ cập nhật metadata. Nếu cần cập nhật nội dung file,
        cần có logic upload file mới lên MinIO và cập nhật storage_path.

        Args:
            template_info: Thông tin mẫu tài liệu mới

        Returns:
            Thông tin mẫu tài liệu đã cập nhật
        """
        index_to_update = -1
        for i, t in enumerate(self._templates_metadata):
            if t.template_id == template_info_to_update.template_id:
                index_to_update = i
                break
        
        if index_to_update == -1:
            raise TemplateNotFoundException(template_info_to_update.template_id)

        current_template = self._templates_metadata[index_to_update]
        current_template.name = template_info_to_update.name or current_template.name
        current_template.description = template_info_to_update.description or current_template.description
        current_template.category = template_info_to_update.category or current_template.category
        current_template.tags = template_info_to_update.tags or current_template.tags
        current_template.doc_metadata = template_info_to_update.doc_metadata or current_template.doc_metadata
        current_template.updated_at = datetime.now()
        
        self._templates_metadata[index_to_update] = current_template
        self._save_metadata()
        return current_template

    async def delete(self, template_id: str) -> None:
        """
        Xóa mẫu tài liệu.

        Args:
            template_id: ID của mẫu tài liệu
        """
        template_to_delete = None
        index_to_delete = -1
        for i, t in enumerate(self._templates_metadata):
            if t.template_id == template_id:
                template_to_delete = t
                index_to_delete = i
                break
        
        if not template_to_delete:
            raise TemplateNotFoundException(template_id)

        if template_to_delete.storage_path and os.path.exists(template_to_delete.storage_path):
            try:
                if os.path.basename(template_dir) == template_id:
                     shutil.rmtree(template_dir, ignore_errors=True)
                elif os.path.isfile(template_to_delete.storage_path):
                    os.unlink(template_to_delete.storage_path)
            except Exception as e:
                logger.error(f"Lỗi khi xóa file/thư mục template {template_to_delete.storage_path}: {e}", exc_info=True)

        del self._templates_metadata[index_to_delete]
        self._save_metadata()

    async def list(self, category: Optional[str] = None, skip: int = 0, limit: int = 10) -> Tuple[List[TemplateInfo], int]:
        """
        Lấy danh sách mẫu tài liệu.

        Args:
            category: Danh mục để lọc
            skip: Số mẫu tài liệu bỏ qua
            limit: Số mẫu tài liệu tối đa trả về

        Returns:
            Danh sách mẫu tài liệu
        """
        self._load_metadata()
        
        filtered_templates = self._templates_metadata
        if category:
            filtered_templates = [t for t in filtered_templates if t.category and t.category.lower() == category.lower()]
        
        total_count = len(filtered_templates)
        
        paginated_templates = filtered_templates[skip : skip + limit]
        
        return paginated_templates, total_count


class BatchProcessingRepository:
    """
    Repository để làm việc với thông tin xử lý hàng loạt.
    """

    def __init__(self):
        """
        Khởi tạo repository.
        """
        self.batches_dir = os.path.join(settings.TEMP_DIR, "word_batches")
        os.makedirs(self.batches_dir, exist_ok=True)
        self.doc_metadata_file = os.path.join(self.batches_dir, "_batch_metadata.json")
        self._batch_metadata: Dict[str, BatchProcessingInfo] = {}
        self._load_metadata()

    def _load_metadata(self) -> None:
        """
        Tải metadata của thông tin xử lý hàng loạt từ file.
        """
        try:
            if os.path.exists(self.doc_metadata_file):
                with open(self.doc_metadata_file, 'r', encoding='utf-8') as f:
                    raw_dict = json.load(f)
                    for task_id, data in raw_dict.items():
                        if data.get('created_at') and isinstance(data['created_at'], str):
                            data['created_at'] = datetime.fromisoformat(data['created_at'])
                        if data.get('updated_at') and isinstance(data['updated_at'], str):
                            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
                        self._batch_metadata[task_id] = BatchProcessingInfo(**data)
            else:
                 self._batch_metadata = {}
        except (json.JSONDecodeError, IOError, TypeError) as e:
            logger.error(f"Lỗi khi tải metadata cho batch processing: {e}", exc_info=True)
            self._batch_metadata = {}

    def _serialize_datetime(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

    def _save_metadata(self) -> None:
        """
        Lưu metadata của thông tin xử lý hàng loạt vào file.
        """
        try:
            os.makedirs(os.path.dirname(self.doc_metadata_file), exist_ok=True)
            serializable_metadata = {
                task_id: batch_info.dict() 
                for task_id, batch_info in self._batch_metadata.items()
            }
            with open(self.doc_metadata_file, 'w', encoding='utf-8') as f:
                json.dump(serializable_metadata, f, ensure_ascii=False, indent=4, default=self._serialize_datetime)
        except IOError as e:
            logger.error(f"Lỗi khi lưu metadata cho batch processing: {e}", exc_info=True)
            raise StorageException(f"Không thể lưu metadata cho batch processing: {str(e)}")

    async def save(self, batch_info: BatchProcessingInfo) -> BatchProcessingInfo:
        """
        Lưu thông tin xử lý hàng loạt mới.

        Args:
            batch_info: Thông tin xử lý hàng loạt

        Returns:
            Thông tin xử lý hàng loạt đã lưu
        """
        if not batch_info.task_id:
            batch_info.task_id = str(uuid.uuid4())
        
        now = datetime.now()
        batch_info.created_at = batch_info.created_at or now
        batch_info.updated_at = batch_info.updated_at or now
        
        self._batch_metadata[batch_info.task_id] = batch_info
        self._save_metadata()
        return batch_info

    async def get(self, batch_id: str) -> Optional[BatchProcessingInfo]:
        """
        Lấy thông tin xử lý hàng loạt.

        Args:
            batch_id: ID của thông tin xử lý hàng loạt

        Returns:
            Thông tin xử lý hàng loạt
        """
        self._load_metadata()
        return self._batch_metadata.get(batch_id)

    async def update(self, batch_info_to_update: BatchProcessingInfo) -> BatchProcessingInfo:
        """
        Cập nhật thông tin xử lý hàng loạt.

        Args:
            batch_info: Thông tin xử lý hàng loạt mới

        Returns:
            Thông tin xử lý hàng loạt đã cập nhật
        """
        if not batch_info_to_update.task_id or batch_info_to_update.task_id not in self._batch_metadata:
            raise DocumentNotFoundException(f"Batch task with ID '{batch_info_to_update.task_id}' not found for update.")
        
        batch_info_to_update.updated_at = datetime.now()
        self._batch_metadata[batch_info_to_update.task_id] = batch_info_to_update
        self._save_metadata()
        return batch_info_to_update

    async def delete(self, batch_id: str) -> None:
        """
        Xóa thông tin xử lý hàng loạt.

        Args:
            batch_id: ID của thông tin xử lý hàng loạt
        """
        if batch_id in self._batch_metadata:
            del self._batch_metadata[batch_id]
            self._save_metadata()
        else:
            raise DocumentNotFoundException(f"Batch task with ID '{batch_id}' not found for deletion.")