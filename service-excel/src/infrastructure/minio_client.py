import io
import os
from typing import Optional, List, Dict, Any, Tuple
from minio import Minio
from minio.error import S3Error
from datetime import datetime, timedelta
import uuid

from core.config import settings
from domain.exceptions import StorageException


class MinioClient:
    """
    Client để làm việc với MinIO S3 Storage.
    """

    def __init__(self):
        """
        Khởi tạo client với các thông tin cấu hình từ settings.
        """
        try:
            self.client = Minio(
                f"{settings.MINIO_HOST}:{settings.MINIO_PORT}",
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=False  # Sử dụng HTTP thay vì HTTPS
            )

            # Đảm bảo bucket tồn tại
            self._ensure_bucket_exists(settings.MINIO_EXCEL_BUCKET)
            self._ensure_bucket_exists(settings.MINIO_TEMPLATES_BUCKET)
        except Exception as e:
            raise StorageException(f"Không thể kết nối đến MinIO: {str(e)}")

    def _ensure_bucket_exists(self, bucket_name: str) -> None:
        """
        Đảm bảo bucket đã tồn tại, nếu không thì tạo mới.

        Args:
            bucket_name: Tên bucket cần kiểm tra/tạo
        """
        try:
            if not self.client.bucket_exists(bucket_name):
                self.client.make_bucket(bucket_name)
        except S3Error as e:
            raise StorageException(f"Không thể tạo bucket {bucket_name}: {str(e)}")

    async def upload_document(self, content: bytes, filename: str) -> str:
        """
        Upload tài liệu Excel lên MinIO.

        Args:
            content: Nội dung file dưới dạng bytes
            filename: Tên file gốc

        Returns:
            Object path trong MinIO
        """
        try:
            # Tạo tên file duy nhất
            object_name = f"{datetime.now().strftime('%Y-%m-%d')}/{str(uuid.uuid4())}/{filename}"

            # Upload file
            self.client.put_object(
                bucket_name=settings.MINIO_EXCEL_BUCKET,
                object_name=object_name,
                data=io.BytesIO(content),
                length=len(content),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if filename.endswith(
                    ".xlsx") else "application/vnd.ms-excel"
            )

            return object_name
        except S3Error as e:
            raise StorageException(f"Không thể upload tài liệu: {str(e)}")

    async def upload_template(self, content: bytes, filename: str) -> str:
        """
        Upload mẫu tài liệu Excel lên MinIO.

        Args:
            content: Nội dung file dưới dạng bytes
            filename: Tên file gốc

        Returns:
            Object path trong MinIO
        """
        try:
            # Tạo tên file duy nhất
            object_name = f"{datetime.now().strftime('%Y-%m-%d')}/{str(uuid.uuid4())}/{filename}"

            # Upload file
            self.client.put_object(
                bucket_name=settings.MINIO_TEMPLATES_BUCKET,
                object_name=object_name,
                data=io.BytesIO(content),
                length=len(content),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if filename.endswith(
                    ".xlsx") else "application/vnd.ms-excel"
            )

            return object_name
        except S3Error as e:
            raise StorageException(f"Không thể upload mẫu tài liệu: {str(e)}")

    async def download_document(self, object_name: str) -> bytes:
        """
        Tải xuống tài liệu Excel từ MinIO.

        Args:
            object_name: Đường dẫn đối tượng trong MinIO

        Returns:
            Nội dung file dưới dạng bytes
        """
        try:
            # Tải xuống file
            response = self.client.get_object(
                bucket_name=settings.MINIO_EXCEL_BUCKET,
                object_name=object_name
            )

            # Đọc nội dung
            content = response.read()
            response.close()
            response.release_conn()

            return content
        except S3Error as e:
            raise StorageException(f"Không thể tải xuống tài liệu: {str(e)}")

    async def download_template(self, object_name: str) -> bytes:
        """
        Tải xuống mẫu tài liệu Excel từ MinIO.

        Args:
            object_name: Đường dẫn đối tượng trong MinIO

        Returns:
            Nội dung file dưới dạng bytes
        """
        try:
            # Tải xuống file
            response = self.client.get_object(
                bucket_name=settings.MINIO_TEMPLATES_BUCKET,
                object_name=object_name
            )

            # Đọc nội dung
            content = response.read()
            response.close()
            response.release_conn()

            return content
        except S3Error as e:
            raise StorageException(f"Không thể tải xuống mẫu tài liệu: {str(e)}")

    async def delete_document(self, object_name: str) -> None:
        """
        Xóa tài liệu Excel khỏi MinIO.

        Args:
            object_name: Đường dẫn đối tượng trong MinIO
        """
        try:
            self.client.remove_object(
                bucket_name=settings.MINIO_EXCEL_BUCKET,
                object_name=object_name
            )
        except S3Error as e:
            raise StorageException(f"Không thể xóa tài liệu: {str(e)}")

    async def delete_template(self, object_name: str) -> None:
        """
        Xóa mẫu tài liệu Excel khỏi MinIO.

        Args:
            object_name: Đường dẫn đối tượng trong MinIO
        """
        try:
            self.client.remove_object(
                bucket_name=settings.MINIO_TEMPLATES_BUCKET,
                object_name=object_name
            )
        except S3Error as e:
            raise StorageException(f"Không thể xóa mẫu tài liệu: {str(e)}")

    async def get_presigned_url(self, object_name: str, expires: int = 3600, is_template: bool = False) -> str:
        """
        Tạo URL có chữ ký trước để truy cập tạm thời vào tài liệu.

        Args:
            object_name: Đường dẫn đối tượng trong MinIO
            expires: Thời gian hết hạn URL (giây)
            is_template: True nếu đối tượng là mẫu tài liệu

        Returns:
            URL có chữ ký trước
        """
        try:
            bucket_name = settings.MINIO_TEMPLATES_BUCKET if is_template else settings.MINIO_EXCEL_BUCKET

            url = self.client.presigned_get_object(
                bucket_name=bucket_name,
                object_name=object_name,
                expires=timedelta(seconds=expires)
            )

            return url
        except S3Error as e:
            raise StorageException(f"Không thể tạo URL có chữ ký trước: {str(e)}")