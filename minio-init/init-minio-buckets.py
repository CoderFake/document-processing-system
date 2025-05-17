#!/usr/bin/env python3
import os
from minio import Minio
from minio.error import S3Error

def create_bucket(client, bucket_name):
    """Tạo bucket nếu chưa tồn tại"""
    try:
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)
            print(f"Bucket '{bucket_name}' đã được tạo thành công")
        else:
            print(f"Bucket '{bucket_name}' đã tồn tại")
    except S3Error as err:
        print(f"Lỗi khi tạo bucket '{bucket_name}': {err}")

def main():
    minio_host = os.environ.get('MINIO_HOST', 'minio')
    minio_port = os.environ.get('MINIO_PORT', '9000')
    minio_access_key = os.environ.get('MINIO_ACCESS_KEY', 'minioadmin')
    minio_secret_key = os.environ.get('MINIO_SECRET_KEY', 'minioadmin')
    
    try:
        client = Minio(
            f"{minio_host}:{minio_port}",
            access_key=minio_access_key,
            secret_key=minio_secret_key,
            secure=False
        )
        
        print("Đã kết nối thành công tới MinIO Server")

        buckets = [
            # Excel service
            "excel-documents",
            "excel-templates",
            
            # PDF service
            "pdf-documents",
            "png-documents",
            "stamp-templates",
            
            # Files service
            "files-bucket",
            "archive-files",
            "extracted-files",
            
            # User service
            "user-profiles",
            
            # Word service
            "word-documents",
            "word-templates"
        ]
        
        # Tạo các bucket
        for bucket in buckets:
            create_bucket(client, bucket)
            
        print("Hoàn tất khởi tạo các bucket MinIO")
        
    except Exception as e:
        print(f"Lỗi kết nối tới MinIO: {e}")
        return

if __name__ == "__main__":
    main()