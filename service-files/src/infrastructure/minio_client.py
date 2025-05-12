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
                secure=False
            )

            self._ensure_bucket_exists(settings.MINIO_FILES_BUCKET)
            self._ensure_bucket_exists(settings.MINIO_RAW_BUCKET)
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

    async def upload_file(self, content: bytes, filename: str) -> str:
        """
        Upload tệp lên MinIO.

        Args:
            content: Nội dung file dưới dạng bytes
            filename: Tên file gốc

        Returns:
            Object path trong MinIO
        """
        try:
            object_name = f"{datetime.now().strftime('%Y-%m-%d')}/{str(uuid.uuid4())}/{filename}"

            content_type = self._get_content_type(filename)

            self.client.put_object(
                bucket_name=settings.MINIO_RAW_BUCKET,
                object_name=object_name,
                data=io.BytesIO(content),
                length=len(content),
                content_type=content_type
            )

            return object_name
        except S3Error as e:
            raise StorageException(f"Không thể upload tệp: {str(e)}")

    async def upload_archive(self, content: bytes, filename: str) -> str:
        """
        Upload tệp nén lên MinIO.

        Args:
            content: Nội dung file dưới dạng bytes
            filename: Tên file gốc

        Returns:
            Object path trong MinIO
        """
        try:
            object_name = f"{datetime.now().strftime('%Y-%m-%d')}/{str(uuid.uuid4())}/{filename}"

            content_type = self._get_content_type(filename)

            self.client.put_object(
                bucket_name=settings.MINIO_FILES_BUCKET,
                object_name=object_name,
                data=io.BytesIO(content),
                length=len(content),
                content_type=content_type
            )

            return object_name
        except S3Error as e:
            raise StorageException(f"Không thể upload tệp nén: {str(e)}")

    def _get_content_type(self, filename: str) -> str:
        """
        Xác định content-type dựa vào tên file.

        Args:
            filename: Tên file

        Returns:
            Content-type
        """
        extension = os.path.splitext(filename.lower())[1]
        content_types = {
            ".zip": "application/zip",
            ".7z": "application/x-7z-compressed",
            ".rar": "application/vnd.rar",
            ".tar": "application/x-tar",
            ".gz": "application/gzip",
            ".tgz": "application/gzip",
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".doc": "application/msword",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".xls": "application/vnd.ms-excel",
            ".csv": "text/csv",
            ".txt": "text/plain",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".html": "text/html",
            ".json": "application/json",
            ".xml": "application/xml"
        }

        return content_types.get(extension, "application/octet-stream")

    async def download_file(self, object_name: str) -> bytes:
        """
        Tải xuống tệp từ MinIO.

        Args:
            object_name: Đường dẫn đối tượng trong MinIO

        Returns:
            Nội dung file dưới dạng bytes
        """
        try:
            response = self.client.get_object(
                bucket_name=settings.MINIO_RAW_BUCKET,
                object_name=object_name
            )

            content = response.read()
            response.close()
            response.release_conn()

            return content
        except S3Error as e:
            raise StorageException(f"Không thể tải xuống tệp: {str(e)}")

    async def download_archive(self, object_name: str) -> bytes:
        """
        Tải xuống tệp nén từ MinIO.

        Args:
            object_name: Đường dẫn đối tượng trong MinIO

        Returns:
            Nội dung file dưới dạng bytes
        """
        try:
            response = self.client.get_object(
                bucket_name=settings.MINIO_FILES_BUCKET,
                object_name=object_name
            )

            content = response.read()
            response.close()
            response.release_conn()

            return content
        except S3Error as e:
            raise StorageException(f"Không thể tải xuống tệp nén: {str(e)}")

    async def delete_file(self, object_name: str) -> None:
        """
        Xóa tệp khỏi MinIO.

        Args:
            object_name: Đường dẫn đối tượng trong MinIO
        """
        try:
            self.client.remove_object(
                bucket_name=settings.MINIO_RAW_BUCKET,
                object_name=object_name
            )
        except S3Error as e:
            raise StorageException(f"Không thể xóa tệp: {str(e)}")

    async def delete_archive(self, object_name: str) -> None:
        """
        Xóa tệp nén khỏi MinIO.

        Args:
            object_name: Đường dẫn đối tượng trong MinIO
        """
        try:
            self.client.remove_object(
                bucket_name=settings.MINIO_FILES_BUCKET,
                object_name=object_name
            )
        except S3Error as e:
            raise StorageException(f"Không thể xóa tệp nén: {str(e)}")

    async def get_presigned_url(self, object_name: str, bucket_name: str, expires: int = 3600) -> str:
        """
        Tạo URL có chữ ký trước để truy cập tạm thời vào tệp.

        Args:
            object_name: Đường dẫn đối tượng trong MinIO
            bucket_name: Tên bucket
            expires: Thời gian hết hạn URL (giây)

        Returns:
            URL có chữ ký trước
        """
        try:
            url = self.client.presigned_get_object(
                bucket_name=bucket_name,
                object_name=object_name,
                expires=timedelta(seconds=expires)
            )

            return url
        except S3Error as e:
            raise StorageException(f"Không thể tạo URL có chữ ký trước: {str(e)}")

    async def get_file_presigned_url(self, object_name: str, expires: int = 3600) -> str:
        """
        Tạo URL có chữ ký trước để truy cập tạm thời vào tệp.

        Args:
            object_name: Đường dẫn đối tượng trong MinIO
            expires: Thời gian hết hạn URL (giây)

        Returns:
            URL có chữ ký trước
        """
        return await self.get_presigned_url(object_name, settings.MINIO_RAW_BUCKET, expires)

    async def get_archive_presigned_url(self, object_name: str, expires: int = 3600) -> str:
        """
        Tạo URL có chữ ký trước để truy cập tạm thời vào tệp nén.

        Args:
            object_name: Đường dẫn đối tượng trong MinIO
            expires: Thời gian hết hạn URL (giây)

        Returns:
            URL có chữ ký trước
        """
        return await self.get_presigned_url(object_name, settings.MINIO_FILES_BUCKET, expires)