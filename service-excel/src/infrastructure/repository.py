import os
import json
import tempfile
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import uuid

from domain.models import ExcelDocumentInfo, ExcelTemplateInfo, BatchProcessingInfo, MergeInfo
from domain.exceptions import DocumentNotFoundException, TemplateNotFoundException, StorageException
from infrastructure.minio_client import MinioClient
from core.config import settings


class ExcelDocumentRepository:
    """
    Repository để làm việc với tài liệu Excel.
    """

    def __init__(self, minio_client: MinioClient):
        """
        Khởi tạo repository.

        Args:
            minio_client: Client MinIO để lưu trữ tài liệu
        """
        self.minio_client = minio_client
        self.documents_metadata_file = os.path.join(settings.TEMP_DIR, "excel_documents_metadata.json")
        self.documents: Dict[str, ExcelDocumentInfo] = {}
        self._load_metadata()

    def _load_metadata(self) -> None:
        """
        Tải metadata của tài liệu từ file.
        """
        try:
            if os.path.exists(self.documents_metadata_file):
                with open(self.documents_metadata_file, "r") as f:
                    data = json.load(f)
                    for doc_id, doc_data in data.items():
                        self.documents[doc_id] = ExcelDocumentInfo(**doc_data)
        except Exception as e:
            self._save_metadata()

    def _save_metadata(self) -> None:
        """
        Lưu metadata của tài liệu vào file.
        """
        try:
            data = {doc_id: doc.dict() for doc_id, doc in self.documents.items()}
            with open(self.documents_metadata_file, "w") as f:
                json.dump(data, f, default=str)
        except Exception as e:
            raise StorageException(f"Không thể lưu metadata: {str(e)}")

    async def save(self, document_info: ExcelDocumentInfo, content: bytes) -> ExcelDocumentInfo:
        """
        Lưu tài liệu mới.

        Args:
            document_info: Thông tin tài liệu
            content: Nội dung tài liệu

        Returns:
            Thông tin tài liệu đã lưu
        """
        try:
            object_name = await self.minio_client.upload_document(
                content=content,
                filename=document_info.original_filename
            )

            document_info.storage_path = object_name
            document_info.file_size = len(content)
            document_info.file_type = (
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                if document_info.original_filename.endswith(".xlsx")
                else "application/vnd.ms-excel"
            )

            sheet_names = await self._get_sheet_names(content)
            document_info.sheet_names = sheet_names

            self.documents[document_info.id] = document_info

            self._save_metadata()

            return document_info
        except Exception as e:
            raise StorageException(f"Không thể lưu tài liệu: {str(e)}")

    async def _get_sheet_names(self, content: bytes) -> List[str]:
        """
        Đọc tên các sheet từ nội dung tài liệu Excel.

        Args:
            content: Nội dung tài liệu Excel

        Returns:
            Danh sách tên sheet
        """
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as temp:
                temp.write(content)
                temp_path = temp.name

            try:
                import openpyxl
                wb = openpyxl.load_workbook(temp_path, read_only=True)
                sheet_names = wb.sheetnames

                wb.close()

                os.unlink(temp_path)

                return sheet_names
            except Exception as e:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

                raise
        except Exception as e:
            return []

    async def get(self, document_id: str) -> Tuple[ExcelDocumentInfo, bytes]:
        """
        Lấy thông tin và nội dung tài liệu.

        Args:
            document_id: ID của tài liệu

        Returns:
            Tuple chứa thông tin và nội dung tài liệu
        """
        try:
            if document_id not in self.documents:
                raise DocumentNotFoundException(document_id)

            document_info = self.documents[document_id]

            content = await self.minio_client.download_document(document_info.storage_path)

            return document_info, content
        except DocumentNotFoundException:
            raise
        except Exception as e:
            raise StorageException(f"Không thể lấy tài liệu: {str(e)}")

    async def update(self, document_info: ExcelDocumentInfo) -> ExcelDocumentInfo:
        """
        Cập nhật thông tin tài liệu.

        Args:
            document_info: Thông tin tài liệu mới

        Returns:
            Thông tin tài liệu đã cập nhật
        """
        try:
            if document_info.id not in self.documents:
                raise DocumentNotFoundException(document_info.id)

            document_info.updated_at = datetime.now()
            self.documents[document_info.id] = document_info

            self._save_metadata()

            return document_info
        except DocumentNotFoundException:
            raise
        except Exception as e:
            raise StorageException(f"Không thể cập nhật tài liệu: {str(e)}")

    async def delete(self, document_id: str) -> None:
        """
        Xóa tài liệu.

        Args:
            document_id: ID của tài liệu
        """
        try:
            if document_id not in self.documents:
                raise DocumentNotFoundException(document_id)

            document_info = self.documents[document_id]

            await self.minio_client.delete_document(document_info.storage_path)

            del self.documents[document_id]

            self._save_metadata()
        except DocumentNotFoundException:
            raise
        except Exception as e:
            raise StorageException(f"Không thể xóa tài liệu: {str(e)}")

    async def list(self, skip: int = 0, limit: int = 10, search: Optional[str] = None) -> List[ExcelDocumentInfo]:
        """
        Lấy danh sách tài liệu.

        Args:
            skip: Số tài liệu bỏ qua
            limit: Số tài liệu tối đa trả về
            search: Từ khóa tìm kiếm (tìm trong title và description)

        Returns:
            Danh sách tài liệu
        """
        try:
            if search:
                search = search.lower()
                filtered_documents = [
                    doc for doc in self.documents.values()
                    if search in doc.title.lower() or (doc.description and search in doc.description.lower())
                ]
            else:
                filtered_documents = list(self.documents.values())

            sorted_documents = sorted(
                filtered_documents,
                key=lambda x: x.created_at,
                reverse=True
            )

            return sorted_documents[skip:skip + limit]
        except Exception as e:
            raise StorageException(f"Không thể lấy danh sách tài liệu: {str(e)}")


class ExcelTemplateRepository:
    """
    Repository để làm việc với mẫu tài liệu Excel.
    """

    def __init__(self, minio_client: MinioClient):
        """
        Khởi tạo repository.

        Args:
            minio_client: Client MinIO để lưu trữ mẫu tài liệu
        """
        self.minio_client = minio_client
        self.templates_metadata_file = os.path.join(settings.TEMP_DIR, "excel_templates_metadata.json")
        self.templates: Dict[str, ExcelTemplateInfo] = {}
        self._load_metadata()

    def _load_metadata(self) -> None:
        """
        Tải metadata của mẫu tài liệu từ file.
        """
        try:
            if os.path.exists(self.templates_metadata_file):
                with open(self.templates_metadata_file, "r") as f:
                    data = json.load(f)
                    for template_id, template_data in data.items():
                        self.templates[template_id] = ExcelTemplateInfo(**template_data)
        except Exception as e:
            self._save_metadata()

    def _save_metadata(self) -> None:
        """
        Lưu metadata của mẫu tài liệu vào file.
        """
        try:
            data = {template_id: template.dict() for template_id, template in self.templates.items()}
            with open(self.templates_metadata_file, "w") as f:
                json.dump(data, f, default=str)
        except Exception as e:
            raise StorageException(f"Không thể lưu metadata: {str(e)}")

    async def save(self, template_info: ExcelTemplateInfo, content: bytes) -> ExcelTemplateInfo:
        """
        Lưu mẫu tài liệu mới.

        Args:
            template_info: Thông tin mẫu tài liệu
            content: Nội dung mẫu tài liệu

        Returns:
            Thông tin mẫu tài liệu đã lưu
        """
        try:
            object_name = await self.minio_client.upload_template(
                content=content,
                filename=template_info.original_filename
            )

            template_info.storage_path = object_name
            template_info.file_size = len(content)

            sheet_names = await self._get_sheet_names(content)
            template_info.sheet_names = sheet_names

            self.templates[template_info.id] = template_info

            self._save_metadata()

            return template_info
        except Exception as e:
            raise StorageException(f"Không thể lưu mẫu tài liệu: {str(e)}")

    async def _get_sheet_names(self, content: bytes) -> List[str]:
        """
        Đọc tên các sheet từ nội dung tài liệu Excel.

        Args:
            content: Nội dung tài liệu Excel

        Returns:
            Danh sách tên sheet
        """
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as temp:
                temp.write(content)
                temp_path = temp.name

            try:
                import openpyxl
                wb = openpyxl.load_workbook(temp_path, read_only=True)
                sheet_names = wb.sheetnames

                wb.close()

                os.unlink(temp_path)

                return sheet_names
            except Exception as e:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

                raise
        except Exception as e:
            return []

    async def get(self, template_id: str) -> Tuple[ExcelTemplateInfo, bytes]:
        """
        Lấy thông tin và nội dung mẫu tài liệu.

        Args:
            template_id: ID của mẫu tài liệu

        Returns:
            Tuple chứa thông tin và nội dung mẫu tài liệu
        """
        try:
            if template_id not in self.templates:
                raise TemplateNotFoundException(template_id)

            template_info = self.templates[template_id]

            content = await self.minio_client.download_template(template_info.storage_path)

            return template_info, content
        except TemplateNotFoundException:
            raise
        except Exception as e:
            raise StorageException(f"Không thể lấy mẫu tài liệu: {str(e)}")

    async def update(self, template_info: ExcelTemplateInfo) -> ExcelTemplateInfo:
        """
        Cập nhật thông tin mẫu tài liệu.

        Args:
            template_info: Thông tin mẫu tài liệu mới

        Returns:
            Thông tin mẫu tài liệu đã cập nhật
        """
        try:
            if template_info.id not in self.templates:
                raise TemplateNotFoundException(template_info.id)

            template_info.updated_at = datetime.now()
            self.templates[template_info.id] = template_info

            self._save_metadata()

            return template_info
        except TemplateNotFoundException:
            raise
        except Exception as e:
            raise StorageException(f"Không thể cập nhật mẫu tài liệu: {str(e)}")

    async def delete(self, template_id: str) -> None:
        """
        Xóa mẫu tài liệu.

        Args:
            template_id: ID của mẫu tài liệu
        """
        try:
            if template_id not in self.templates:
                raise TemplateNotFoundException(template_id)

            template_info = self.templates[template_id]

            await self.minio_client.delete_template(template_info.storage_path)

            del self.templates[template_id]

            self._save_metadata()
        except TemplateNotFoundException:
            raise
        except Exception as e:
            raise StorageException(f"Không thể xóa mẫu tài liệu: {str(e)}")

    async def list(self, category: Optional[str] = None, skip: int = 0, limit: int = 10) -> List[ExcelTemplateInfo]:
        """
        Lấy danh sách mẫu tài liệu.

        Args:
            category: Danh mục để lọc
            skip: Số mẫu tài liệu bỏ qua
            limit: Số mẫu tài liệu tối đa trả về

        Returns:
            Danh sách mẫu tài liệu
        """
        try:
            if category:
                filtered_templates = [
                    template for template in self.templates.values()
                    if template.category == category
                ]
            else:
                filtered_templates = list(self.templates.values())

            sorted_templates = sorted(
                filtered_templates,
                key=lambda x: x.name
            )

            return sorted_templates[skip:skip + limit]
        except Exception as e:
            raise StorageException(f"Không thể lấy danh sách mẫu tài liệu: {str(e)}")


class BatchProcessingRepository:
    """
    Repository để làm việc với thông tin xử lý hàng loạt.
    """

    def __init__(self):
        """
        Khởi tạo repository.
        """
        self.batch_metadata_file = os.path.join(settings.TEMP_DIR, "excel_batch_metadata.json")
        self.batches: Dict[str, BatchProcessingInfo] = {}
        self._load_metadata()

    def _load_metadata(self) -> None:
        """
        Tải metadata của thông tin xử lý hàng loạt từ file.
        """
        try:
            if os.path.exists(self.batch_metadata_file):
                with open(self.batch_metadata_file, "r") as f:
                    data = json.load(f)
                    for batch_id, batch_data in data.items():
                        self.batches[batch_id] = BatchProcessingInfo(**batch_data)
        except Exception as e:
            self._save_metadata()

    def _save_metadata(self) -> None:
        """
        Lưu metadata của thông tin xử lý hàng loạt vào file.
        """
        try:
            data = {batch_id: batch.dict() for batch_id, batch in self.batches.items()}
            with open(self.batch_metadata_file, "w") as f:
                json.dump(data, f, default=str)
        except Exception as e:
            raise StorageException(f"Không thể lưu metadata: {str(e)}")

    async def save(self, batch_info: BatchProcessingInfo) -> BatchProcessingInfo:
        """
        Lưu thông tin xử lý hàng loạt mới.

        Args:
            batch_info: Thông tin xử lý hàng loạt

        Returns:
            Thông tin xử lý hàng loạt đã lưu
        """
        try:
            self.batches[batch_info.id] = batch_info

            self._save_metadata()

            return batch_info
        except Exception as e:
            raise StorageException(f"Không thể lưu thông tin xử lý hàng loạt: {str(e)}")

    async def get(self, batch_id: str) -> BatchProcessingInfo:
        """
        Lấy thông tin xử lý hàng loạt.

        Args:
            batch_id: ID của thông tin xử lý hàng loạt

        Returns:
            Thông tin xử lý hàng loạt
        """
        try:
            if batch_id not in self.batches:
                raise DocumentNotFoundException(batch_id)

            return self.batches[batch_id]
        except DocumentNotFoundException:
            raise
        except Exception as e:
            raise StorageException(f"Không thể lấy thông tin xử lý hàng loạt: {str(e)}")

    async def update(self, batch_info: BatchProcessingInfo) -> BatchProcessingInfo:
        """
        Cập nhật thông tin xử lý hàng loạt.

        Args:
            batch_info: Thông tin xử lý hàng loạt mới

        Returns:
            Thông tin xử lý hàng loạt đã cập nhật
        """
        try:
            if batch_info.id not in self.batches:
                raise DocumentNotFoundException(batch_info.id)

            self.batches[batch_info.id] = batch_info

            self._save_metadata()

            return batch_info
        except DocumentNotFoundException:
            raise
        except Exception as e:
            raise StorageException(f"Không thể cập nhật thông tin xử lý hàng loạt: {str(e)}")

    async def delete(self, batch_id: str) -> None:
        """
        Xóa thông tin xử lý hàng loạt.

        Args:
            batch_id: ID của thông tin xử lý hàng loạt
        """
        try:
            if batch_id not in self.batches:
                raise DocumentNotFoundException(batch_id)

            del self.batches[batch_id]

            self._save_metadata()
        except DocumentNotFoundException:
            raise
        except Exception as e:
            raise StorageException(f"Không thể xóa thông tin xử lý hàng loạt: {str(e)}")


class MergeRepository:
    """
    Repository để làm việc với thông tin gộp tài liệu Excel.
    """

    def __init__(self):
        """
        Khởi tạo repository.
        """
        self.merge_metadata_file = os.path.join(settings.TEMP_DIR, "excel_merge_metadata.json")
        self.merges: Dict[str, MergeInfo] = {}
        self._load_metadata()

    def _load_metadata(self) -> None:
        """
        Tải metadata của thông tin gộp tài liệu từ file.
        """
        try:
            if os.path.exists(self.merge_metadata_file):
                with open(self.merge_metadata_file, "r") as f:
                    data = json.load(f)
                    for merge_id, merge_data in data.items():
                        self.merges[merge_id] = MergeInfo(**merge_data)
        except Exception as e:
            self._save_metadata()

    def _save_metadata(self) -> None:
        """
        Lưu metadata của thông tin gộp tài liệu vào file.
        """
        try:
            data = {merge_id: merge.dict() for merge_id, merge in self.merges.items()}
            with open(self.merge_metadata_file, "w") as f:
                json.dump(data, f, default=str)
        except Exception as e:
            raise StorageException(f"Không thể lưu metadata: {str(e)}")

    async def save(self, merge_info: MergeInfo) -> MergeInfo:
        """
        Lưu thông tin gộp tài liệu mới.

        Args:
            merge_info: Thông tin gộp tài liệu

        Returns:
            Thông tin gộp tài liệu đã lưu
        """
        try:
            self.merges[merge_info.id] = merge_info

            self._save_metadata()

            return merge_info
        except Exception as e:
            raise StorageException(f"Không thể lưu thông tin gộp tài liệu: {str(e)}")

    async def get(self, merge_id: str) -> MergeInfo:
        """
        Lấy thông tin gộp tài liệu.

        Args:
            merge_id: ID của thông tin gộp tài liệu

        Returns:
            Thông tin gộp tài liệu
        """
        try:
            if merge_id not in self.merges:
                raise DocumentNotFoundException(merge_id)

            return self.merges[merge_id]
        except DocumentNotFoundException:
            raise
        except Exception as e:
            raise StorageException(f"Không thể lấy thông tin gộp tài liệu: {str(e)}")

    async def update(self, merge_info: MergeInfo) -> MergeInfo:
        """
        Cập nhật thông tin gộp tài liệu.

        Args:
            merge_info: Thông tin gộp tài liệu mới

        Returns:
            Thông tin gộp tài liệu đã cập nhật
        """
        try:
            if merge_info.id not in self.merges:
                raise DocumentNotFoundException(merge_info.id)

            self.merges[merge_info.id] = merge_info

            self._save_metadata()

            return merge_info
        except DocumentNotFoundException:
            raise
        except Exception as e:
            raise StorageException(f"Không thể cập nhật thông tin gộp tài liệu: {str(e)}")

    async def delete(self, merge_id: str) -> None:
        """
        Xóa thông tin gộp tài liệu.

        Args:
            merge_id: ID của thông tin gộp tài liệu
        """
        try:
            if merge_id not in self.merges:
                raise DocumentNotFoundException(merge_id)

            del self.merges[merge_id]

            self._save_metadata()
        except DocumentNotFoundException:
            raise
        except Exception as e:
            raise StorageException(f"Không thể xóa thông tin gộp tài liệu: {str(e)}")