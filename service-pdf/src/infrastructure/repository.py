import os
import json
import aiofiles
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import uuid

from domain.models import PDFDocumentInfo, PNGDocumentInfo, StampInfo, PDFProcessingInfo, MergeInfo
from domain.exceptions import (
    DocumentNotFoundException, ImageNotFoundException, StampNotFoundException,
    StorageException, PDFPasswordProtectedException, WrongPasswordException
)
from infrastructure.minio_client import MinioClient
from core.config import settings


class PDFDocumentRepository:
    """
    Repository để làm việc với tài liệu PDF.
    """

    def __init__(self, minio_client: MinioClient):
        """
        Khởi tạo repository.

        Args:
            minio_client: Client MinIO để lưu trữ tài liệu
        """
        self.minio_client = minio_client
        self.documents_metadata_file = os.path.join(settings.TEMP_DIR, "pdf_documents_metadata.json")
        self.documents: Dict[str, PDFDocumentInfo] = {}
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
                        self.documents[doc_id] = PDFDocumentInfo(**doc_data)
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

    async def save(self, document_info: PDFDocumentInfo, content: bytes) -> PDFDocumentInfo:
        """
        Lưu tài liệu mới.

        Args:
            document_info: Thông tin tài liệu
            content: Nội dung tài liệu

        Returns:
            Thông tin tài liệu đã lưu
        """
        try:
            object_name = await self.minio_client.upload_pdf_document(
                content=content,
                filename=document_info.original_filename
            )

            document_info.storage_path = object_name
            document_info.file_size = len(content)

            self.documents[document_info.id] = document_info

            self._save_metadata()

            return document_info
        except Exception as e:
            raise StorageException(f"Không thể lưu tài liệu PDF: {str(e)}")

    async def get(self, document_id: str) -> Tuple[PDFDocumentInfo, bytes]:
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

            content = await self.minio_client.download_pdf_document(document_info.storage_path)

            return document_info, content
        except DocumentNotFoundException:
            raise
        except Exception as e:
            raise StorageException(f"Không thể lấy tài liệu PDF: {str(e)}")

    async def update(self, document_info: PDFDocumentInfo) -> PDFDocumentInfo:
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
            raise StorageException(f"Không thể cập nhật tài liệu PDF: {str(e)}")

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

            await self.minio_client.delete_pdf_document(document_info.storage_path)

            del self.documents[document_id]

            self._save_metadata()
        except DocumentNotFoundException:
            raise
        except Exception as e:
            raise StorageException(f"Không thể xóa tài liệu PDF: {str(e)}")

    async def list(self, skip: int = 0, limit: int = 10, search: Optional[str] = None) -> List[PDFDocumentInfo]:
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
            raise StorageException(f"Không thể lấy danh sách tài liệu PDF: {str(e)}")


class PNGDocumentRepository:
    """
    Repository để làm việc với tài liệu PNG.
    """

    def __init__(self, minio_client: MinioClient):
        """
        Khởi tạo repository.

        Args:
            minio_client: Client MinIO để lưu trữ tài liệu
        """
        self.minio_client = minio_client
        self.documents_metadata_file = os.path.join(settings.TEMP_DIR, "png_documents_metadata.json")
        self.documents: Dict[str, PNGDocumentInfo] = {}
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
                        self.documents[doc_id] = PNGDocumentInfo(**doc_data)
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

    async def save(self, document_info: PNGDocumentInfo, content: bytes) -> PNGDocumentInfo:
        """
        Lưu tài liệu mới.

        Args:
            document_info: Thông tin tài liệu
            content: Nội dung tài liệu

        Returns:
            Thông tin tài liệu đã lưu
        """
        try:
            object_name = await self.minio_client.upload_png_document(
                content=content,
                filename=document_info.original_filename
            )

            document_info.storage_path = object_name
            document_info.file_size = len(content)

            self.documents[document_info.id] = document_info

            self._save_metadata()

            return document_info
        except Exception as e:
            raise StorageException(f"Không thể lưu tài liệu PNG: {str(e)}")

    async def get(self, document_id: str) -> Tuple[PNGDocumentInfo, bytes]:
        """
        Lấy thông tin và nội dung tài liệu.

        Args:
            document_id: ID của tài liệu

        Returns:
            Tuple chứa thông tin và nội dung tài liệu
        """
        try:
            if document_id not in self.documents:
                raise ImageNotFoundException(document_id)

            document_info = self.documents[document_id]

            content = await self.minio_client.download_png_document(document_info.storage_path)

            return document_info, content
        except ImageNotFoundException:
            raise
        except Exception as e:
            raise StorageException(f"Không thể lấy tài liệu PNG: {str(e)}")

    async def update(self, document_info: PNGDocumentInfo) -> PNGDocumentInfo:
        """
        Cập nhật thông tin tài liệu.

        Args:
            document_info: Thông tin tài liệu mới

        Returns:
            Thông tin tài liệu đã cập nhật
        """
        try:
            if document_info.id not in self.documents:
                raise ImageNotFoundException(document_info.id)

            document_info.updated_at = datetime.now()
            self.documents[document_info.id] = document_info

            self._save_metadata()

            return document_info
        except ImageNotFoundException:
            raise
        except Exception as e:
            raise StorageException(f"Không thể cập nhật tài liệu PNG: {str(e)}")

    async def delete(self, document_id: str) -> None:
        """
        Xóa tài liệu.

        Args:
            document_id: ID của tài liệu
        """
        try:
            if document_id not in self.documents:
                raise ImageNotFoundException(document_id)

            document_info = self.documents[document_id]

            await self.minio_client.delete_png_document(document_info.storage_path)

            del self.documents[document_id]

            self._save_metadata()
        except ImageNotFoundException:
            raise
        except Exception as e:
            raise StorageException(f"Không thể xóa tài liệu PNG: {str(e)}")

    async def list(self, skip: int = 0, limit: int = 10, search: Optional[str] = None) -> List[PNGDocumentInfo]:
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
            raise StorageException(f"Không thể lấy danh sách tài liệu PNG: {str(e)}")


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
            object_name = await self.minio_client.upload_stamp(
                content=content,
                filename=stamp_info.original_filename
            )

            stamp_info.storage_path = object_name
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
            raise StorageException(f"Không thể lấy mẫu dấu: {str(e)}")

    async def update(self, stamp_info: StampInfo) -> StampInfo:
        """
        Cập nhật thông tin mẫu dấu.

        Args:
            stamp_info: Thông tin mẫu dấu mới

        Returns:
            Thông tin mẫu dấu đã cập nhật
        """
        try:
            if stamp_info.id not in self.stamps:
                raise StampNotFoundException(stamp_info.id)

            stamp_info.updated_at = datetime.now()
            self.stamps[stamp_info.id] = stamp_info

            self._save_metadata()

            return stamp_info
        except StampNotFoundException:
            raise
        except Exception as e:
            raise StorageException(f"Không thể cập nhật mẫu dấu: {str(e)}")

    async def delete(self, stamp_id: str) -> None:
        """
        Xóa mẫu dấu.

        Args:
            stamp_id: ID của mẫu dấu
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
            raise StorageException(f"Không thể xóa mẫu dấu: {str(e)}")

    async def list(self, skip: int = 0, limit: int = 10) -> List[StampInfo]:
        """
        Lấy danh sách mẫu dấu.

        Args:
            skip: Số mẫu dấu bỏ qua
            limit: Số mẫu dấu tối đa trả về

        Returns:
            Danh sách mẫu dấu
        """
        try:
            stamps_list = list(self.stamps.values())
            sorted_stamps = sorted(
                stamps_list,
                key=lambda x: x.created_at,
                reverse=True
            )

            return sorted_stamps[skip:skip + limit]
        except Exception as e:
            raise StorageException(f"Không thể lấy danh sách mẫu dấu: {str(e)}")


class PDFProcessingRepository:
    """
    Repository để làm việc với thông tin xử lý PDF.
    """

    def __init__(self):
        """
        Khởi tạo repository.
        """
        self.processing_metadata_file = os.path.join(settings.TEMP_DIR, "pdf_processing_metadata.json")
        self.processings: Dict[str, PDFProcessingInfo] = {}
        self._load_metadata()

    def _load_metadata(self) -> None:
        """
        Tải metadata của thông tin xử lý PDF từ file.
        """
        try:
            if os.path.exists(self.processing_metadata_file):
                with open(self.processing_metadata_file, "r") as f:
                    data = json.load(f)
                    for processing_id, processing_data in data.items():
                        self.processings[processing_id] = PDFProcessingInfo(**processing_data)
        except Exception as e:
            self._save_metadata()

    def _save_metadata(self) -> None:
        """
        Lưu metadata của thông tin xử lý PDF vào file.
        """
        try:
            data = {processing_id: processing.dict() for processing_id, processing in self.processings.items()}
            with open(self.processing_metadata_file, "w") as f:
                json.dump(data, f, default=str)
        except Exception as e:
            raise StorageException(f"Không thể lưu metadata xử lý PDF: {str(e)}")

    async def save(self, processing_info: PDFProcessingInfo) -> PDFProcessingInfo:
        """
        Lưu thông tin xử lý PDF mới.

        Args:
            processing_info: Thông tin xử lý PDF

        Returns:
            Thông tin xử lý PDF đã lưu
        """
        try:
            self.processings[processing_info.id] = processing_info

            self._save_metadata()

            return processing_info
        except Exception as e:
            raise StorageException(f"Không thể lưu thông tin xử lý PDF: {str(e)}")

    async def get(self, processing_id: str) -> PDFProcessingInfo:
        """
        Lấy thông tin xử lý PDF.

        Args:
            processing_id: ID của thông tin xử lý PDF

        Returns:
            Thông tin xử lý PDF
        """
        try:
            if processing_id not in self.processings:
                raise DocumentNotFoundException(processing_id)

            return self.processings[processing_id]
        except DocumentNotFoundException:
            raise
        except Exception as e:
            raise StorageException(f"Không thể lấy thông tin xử lý PDF: {str(e)}")

    async def update(self, processing_info: PDFProcessingInfo) -> PDFProcessingInfo:
        """
        Cập nhật thông tin xử lý PDF.

        Args:
            processing_info: Thông tin xử lý PDF mới

        Returns:
            Thông tin xử lý PDF đã cập nhật
        """
        try:
            if processing_info.id not in self.processings:
                raise DocumentNotFoundException(processing_info.id)

            self.processings[processing_info.id] = processing_info

            self._save_metadata()

            return processing_info
        except DocumentNotFoundException:
            raise
        except Exception as e:
            raise StorageException(f"Không thể cập nhật thông tin xử lý PDF: {str(e)}")

    async def delete(self, processing_id: str) -> None:
        """
        Xóa thông tin xử lý PDF.

        Args:
            processing_id: ID của thông tin xử lý PDF
        """
        try:
            if processing_id not in self.processings:
                raise DocumentNotFoundException(processing_id)

            del self.processings[processing_id]

            self._save_metadata()
        except DocumentNotFoundException:
            raise
        except Exception as e:
            raise StorageException(f"Không thể xóa thông tin xử lý PDF: {str(e)}")

    async def list_by_document(self, document_id: str) -> List[PDFProcessingInfo]:
        """
        Lấy danh sách thông tin xử lý PDF theo ID tài liệu.

        Args:
            document_id: ID của tài liệu

        Returns:
            Danh sách thông tin xử lý PDF
        """
        try:
            filtered_processings = [
                processing for processing in self.processings.values()
                if processing.document_id == document_id
            ]

            sorted_processings = sorted(
                filtered_processings,
                key=lambda x: x.created_at,
                reverse=True
            )

            return sorted_processings
        except Exception as e:
            raise StorageException(f"Không thể lấy danh sách thông tin xử lý PDF: {str(e)}")


class MergeRepository:
    """
    Repository để làm việc với thông tin gộp tài liệu PDF.
    """

    def __init__(self):
        """
        Khởi tạo repository.
        """
        self.merge_metadata_file = os.path.join(settings.TEMP_DIR, "pdf_merge_metadata.json")
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
            raise StorageException(f"Không thể lưu metadata gộp tài liệu: {str(e)}")

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

    async def list(self) -> List[MergeInfo]:
        """
        Lấy danh sách thông tin gộp tài liệu.

        Returns:
            Danh sách thông tin gộp tài liệu
        """
        try:
            sorted_merges = sorted(
                list(self.merges.values()),
                key=lambda x: x.created_at,
                reverse=True
            )

            return sorted_merges
        except Exception as e:
            raise StorageException(f"Không thể lấy danh sách thông tin gộp tài liệu: {str(e)}")