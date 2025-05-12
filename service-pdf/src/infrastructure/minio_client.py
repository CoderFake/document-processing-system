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

            self._ensure_bucket_exists(settings.MINIO_PDF_BUCKET)
            self._ensure_bucket_exists(settings.MINIO_PNG_BUCKET)
            self._ensure_bucket_exists(settings.MINIO_STAMP_BUCKET)
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

    async def upload_pdf_document(self, content: bytes, filename: str) -> str:
        """
        Upload tài liệu PDF lên MinIO.

        Args:
            content: Nội dung file dưới dạng bytes
            filename: Tên file gốc

        Returns:
            Object path trong MinIO
        """
        try:
            object_name = f"{datetime.now().strftime('%Y-%m-%d')}/{str(uuid.uuid4())}/{filename}"

            self.client.put_object(
                bucket_name=settings.MINIO_PDF_BUCKET,
                object_name=object_name,
                data=io.BytesIO(content),
                length=len(content),
                content_type="application/pdf"
            )

            return object_name
        except S3Error as e:
            raise StorageException(f"Không thể upload tài liệu PDF: {str(e)}")

    async def upload_png_document(self, content: bytes, filename: str) -> str:
        """
        Upload tài liệu PNG lên MinIO.

        Args:
            content: Nội dung file dưới dạng bytes
            filename: Tên file gốc

        Returns:
            Object path trong MinIO
        """
        try:
            object_name = f"{datetime.now().strftime('%Y-%m-%d')}/{str(uuid.uuid4())}/{filename}"

            self.client.put_object(
                bucket_name=settings.MINIO_PNG_BUCKET,
                object_name=object_name,
                data=io.BytesIO(content),
                length=len(content),
                content_type="image/png" if filename.endswith(".png") else "image/jpeg"
            )

            return object_name
        except S3Error as e:
            raise StorageException(f"Không thể upload tài liệu PNG: {str(e)}")

    async def upload_stamp(self, content: bytes, filename: str) -> str:
        """
        Upload mẫu dấu lên MinIO.

        Args:
            content: Nội dung file dưới dạng bytes
            filename: Tên file gốc

        Returns:
            Object path trong MinIO
        """
        try:
            object_name = f"{datetime.now().strftime('%Y-%m-%d')}/{str(uuid.uuid4())}/{filename}"

            self.client.put_object(
                bucket_name=settings.MINIO_STAMP_BUCKET,
                object_name=object_name,
                data=io.BytesIO(content),
                length=len(content),
                content_type="image/png" if filename.endswith(".png") else "image/jpeg"
            )

            return object_name
        except S3Error as e:
            raise StorageException(f"Không thể upload mẫu dấu: {str(e)}")

    async def download_pdf_document(self, object_name: str) -> bytes:
        """
        Tải xuống tài liệu PDF từ MinIO.

        Args:
            object_name: Đường dẫn đối tượng trong MinIO

        Returns:
            Nội dung file dưới dạng bytes
        """
        try:
            response = self.client.get_object(
                bucket_name=settings.MINIO_PDF_BUCKET,
                object_name=object_name
            )

            content = response.read()
            response.close()
            response.release_conn()

            return content
        except S3Error as e:
            raise StorageException(f"Không thể tải xuống tài liệu PDF: {str(e)}")

    async def download_png_document(self, object_name: str) -> bytes:
        """
        Tải xuống tài liệu PNG từ MinIO.

        Args:
            object_name: Đường dẫn đối tượng trong MinIO

        Returns:
            Nội dung file dưới dạng bytes
        """
        try:
            response = self.client.get_object(
                bucket_name=settings.MINIO_PNG_BUCKET,
                object_name=object_name
            )

            content = response.read()
            response.close()
            response.release_conn()

            return content
        except S3Error as e:
            raise StorageException(f"Không thể tải xuống tài liệu PNG: {str(e)}")

    async def download_stamp(self, object_name: str) -> bytes:
        """
        Tải xuống mẫu dấu từ MinIO.

        Args:
            object_name: Đường dẫn đối tượng trong MinIO

        Returns:
            Nội dung file dưới dạng bytes
        """
        try:
            response = self.client.get_object(
                bucket_name=settings.MINIO_STAMP_BUCKET,
                object_name=object_name
            )

            content = response.read()
            response.close()
            response.release_conn()

            return content
        except S3Error as e:
            raise StorageException(f"Không thể tải xuống mẫu dấu: {str(e)}")

    async def delete_pdf_document(self, object_name: str) -> None:
        """
        Xóa tài liệu PDF khỏi MinIO.

        Args:
            object_name: Đường dẫn đối tượng trong MinIO
        """
        try:
            self.client.remove_object(
                bucket_name=settings.MINIO_PDF_BUCKET,
                object_name=object_name
            )
        except S3Error as e:
            raise StorageException(f"Không thể xóa tài liệu PDF: {str(e)}")

    async def delete_png_document(self, object_name: str) -> None:
        """
        Xóa tài liệu PNG khỏi MinIO.

        Args:
            object_name: Đường dẫn đối tượng trong MinIO
        """
        try:
            self.client.remove_object(
                bucket_name=settings.MINIO_PNG_BUCKET,
                object_name=object_name
            )
        except S3Error as e:
            raise StorageException(f"Không thể xóa tài liệu PNG: {str(e)}")

    async def delete_stamp(self, object_name: str) -> None:
        """
        Xóa mẫu dấu khỏi MinIO.

        Args:
            object_name: Đường dẫn đối tượng trong MinIO
        """
        try:
            self.client.remove_object(
                bucket_name=settings.MINIO_STAMP_BUCKET,
                object_name=object_name
            )
        except S3Error as e:
            raise StorageException(f"Không thể xóa mẫu dấu: {str(e)}")

    async def get_presigned_url(self, object_name: str, bucket_name: str, expires: int = 3600) -> str:
        """
        Tạo URL có chữ ký trước để truy cập tạm thời vào tài liệu.

        Args:
            object_name: Đường dẫn đối tượng trong MinIO
            bucket_name: Tên bucket chứa đối tượng
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

    async def get_pdf_presigned_url(self, object_name: str, expires: int = 3600) -> str:
        """
        Tạo URL có chữ ký trước để truy cập tạm thời vào tài liệu PDF.

        Args:
            object_name: Đường dẫn đối tượng trong MinIO
            expires: Thời gian hết hạn URL (giây)

        Returns:
            URL có chữ ký trước
        """
        return await self.get_presigned_url(object_name, settings.MINIO_PDF_BUCKET, expires)

    async def get_png_presigned_url(self, object_name: str, expires: int = 3600) -> str:
        """
        Tạo URL có chữ ký trước để truy cập tạm thời vào tài liệu PNG.

        Args:
            object_name: Đường dẫn đối tượng trong MinIO
            expires: Thời gian hết hạn URL (giây)

        Returns:
            URL có chữ ký trước
        """
        return await self.get_presigned_url(object_name, settings.MINIO_PNG_BUCKET, expires)

    async def get_stamp_presigned_url(self, object_name: str, expires: int = 3600) -> str:
        """
        Tạo URL có chữ ký trước để truy cập tạm thời vào mẫu dấu.

        Args:
            object_name: Đường dẫn đối tượng trong MinIO
            expires: Thời gian hết hạn URL (giây)

        Returns:
            URL có chữ ký trước
        """
        return await self.get_presigned_url(object_name, settings.MINIO_STAMP_BUCKET, expires)