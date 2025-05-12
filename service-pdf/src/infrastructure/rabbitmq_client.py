import json
import pika
from typing import Dict, Any, Optional, Callable
import asyncio
from datetime import datetime
import threading
import logging

from core.config import settings
from domain.exceptions import BaseServiceException


class RabbitMQClient:
    """
    Client để làm việc với RabbitMQ.
    """

    def __init__(self):
        """
        Khởi tạo client với các thông tin cấu hình từ settings.
        """
        self.connection = None
        self.channel = None
        self.credentials = pika.PlainCredentials(
            settings.RABBITMQ_USER,
            settings.RABBITMQ_PASS
        )

        self.QUEUE_ENCRYPT_PDF = "pdf_service.encrypt_pdf"
        self.QUEUE_DECRYPT_PDF = "pdf_service.decrypt_pdf"
        self.QUEUE_WATERMARK_PDF = "pdf_service.watermark_pdf"
        self.QUEUE_SIGN_PDF = "pdf_service.sign_pdf"
        self.QUEUE_MERGE_PDF = "pdf_service.merge_pdf"
        self.QUEUE_CRACK_PDF = "pdf_service.crack_pdf"
        self.QUEUE_CONVERT_TO_WORD = "pdf_service.convert_to_word"
        self.QUEUE_CONVERT_TO_IMAGES = "pdf_service.convert_to_images"

        self.logger = logging.getLogger("rabbitmq_client")

    def _get_connection(self) -> pika.BlockingConnection:
        """
        Lấy connection đến RabbitMQ.

        Returns:
            Connection đến RabbitMQ
        """
        if self.connection is None or self.connection.is_closed:
            self.connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=settings.RABBITMQ_HOST,
                    port=settings.RABBITMQ_PORT,
                    virtual_host=settings.RABBITMQ_VHOST,
                    credentials=self.credentials
                )
            )

        return self.connection

    def _get_channel(self) -> pika.channel.Channel:
        """
        Lấy channel từ connection.

        Returns:
            Channel để làm việc với RabbitMQ
        """
        if self.channel is None or self.channel.is_closed:
            self.channel = self._get_connection().channel()

            self.channel.queue_declare(queue=self.QUEUE_ENCRYPT_PDF, durable=True)
            self.channel.queue_declare(queue=self.QUEUE_DECRYPT_PDF, durable=True)
            self.channel.queue_declare(queue=self.QUEUE_WATERMARK_PDF, durable=True)
            self.channel.queue_declare(queue=self.QUEUE_SIGN_PDF, durable=True)
            self.channel.queue_declare(queue=self.QUEUE_MERGE_PDF, durable=True)
            self.channel.queue_declare(queue=self.QUEUE_CRACK_PDF, durable=True)
            self.channel.queue_declare(queue=self.QUEUE_CONVERT_TO_WORD, durable=True)
            self.channel.queue_declare(queue=self.QUEUE_CONVERT_TO_IMAGES, durable=True)

        return self.channel

    def send_message(self, queue: str, message: Dict[str, Any]) -> None:
        """
        Gửi message đến RabbitMQ.

        Args:
            queue: Tên queue
            message: Nội dung tin nhắn dưới dạng dict
        """
        try:
            channel = self._get_channel()
            channel.basic_publish(
                exchange='',
                routing_key=queue,
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,  
                    content_type='application/json'
                )
            )
        except Exception as e:
            self.logger.error(f"Lỗi khi gửi tin nhắn đến RabbitMQ: {str(e)}")
            raise BaseServiceException(f"Lỗi khi gửi tin nhắn đến RabbitMQ: {str(e)}")

    def start_consuming(self, queue: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Bắt đầu lắng nghe tin nhắn từ queue.

        Args:
            queue: Tên queue
            callback: Hàm callback xử lý tin nhắn
        """

        def _callback(ch, method, properties, body):
            try:
                message = json.loads(body)

                callback(message)

                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as e:
                self.logger.error(f"Lỗi khi xử lý tin nhắn: {str(e)}")

                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

        try:
            channel = self._get_channel()
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=queue, on_message_callback=_callback)

            thread = threading.Thread(target=channel.start_consuming)
            thread.daemon = True
            thread.start()
        except Exception as e:
            self.logger.error(f"Lỗi khi bắt đầu consuming: {str(e)}")
            raise BaseServiceException(f"Lỗi khi bắt đầu consuming: {str(e)}")

    def close(self) -> None:
        """
        Đóng kết nối đến RabbitMQ.
        """
        if self.connection is not None and self.connection.is_open:
            self.connection.close()

    async def publish_encrypt_pdf_task(self, document_id: str, password: str, permissions: Optional[Dict[str, bool]] = None) -> None:
        """
        Đăng tác vụ mã hóa tài liệu PDF.

        Args:
            document_id: ID của tài liệu cần mã hóa
            password: Mật khẩu để mã hóa
            permissions: Các quyền cho tài liệu
        """
        message = {
            "document_id": document_id,
            "password": password,
            "permissions": permissions,
            "task_type": "encrypt_pdf",
            "timestamp": str(datetime.now())
        }

        self.send_message(self.QUEUE_ENCRYPT_PDF, message)

    async def publish_decrypt_pdf_task(self, document_id: str, password: str) -> None:
        """
        Đăng tác vụ giải mã tài liệu PDF.

        Args:
            document_id: ID của tài liệu cần giải mã
            password: Mật khẩu để giải mã
        """
        message = {
            "document_id": document_id,
            "password": password,
            "task_type": "decrypt_pdf",
            "timestamp": str(datetime.now())
        }

        self.send_message(self.QUEUE_DECRYPT_PDF, message)

    async def publish_watermark_pdf_task(self, document_id: str, watermark_text: str, position: str, opacity: float,
                                        color: Optional[str] = None, font_size: Optional[int] = None) -> None:
        """
        Đăng tác vụ thêm watermark vào tài liệu PDF.

        Args:
            document_id: ID của tài liệu cần thêm watermark
            watermark_text: Nội dung watermark
            position: Vị trí của watermark
            opacity: Độ mờ của watermark
            color: Màu sắc của watermark
            font_size: Kích thước font của watermark
        """
        message = {
            "document_id": document_id,
            "watermark_text": watermark_text,
            "position": position,
            "opacity": opacity,
            "color": color,
            "font_size": font_size,
            "task_type": "watermark_pdf",
            "timestamp": str(datetime.now())
        }

        self.send_message(self.QUEUE_WATERMARK_PDF, message)

    async def publish_sign_pdf_task(self, document_id: str, stamp_id: Optional[str], signature_position: str,
                                    page_number: int, scale: float, custom_x: Optional[int] = None,
                                    custom_y: Optional[int] = None) -> None:
        """
        Đăng tác vụ thêm chữ ký vào tài liệu PDF.

        Args:
            document_id: ID của tài liệu cần thêm chữ ký
            stamp_id: ID của mẫu dấu (nếu có)
            signature_position: Vị trí của chữ ký
            page_number: Số trang cần thêm chữ ký
            scale: Tỷ lệ của chữ ký
            custom_x: Tọa độ X tùy chỉnh
            custom_y: Tọa độ Y tùy chỉnh
        """
        message = {
            "document_id": document_id,
            "stamp_id": stamp_id,
            "signature_position": signature_position,
            "page_number": page_number,
            "scale": scale,
            "custom_x": custom_x,
            "custom_y": custom_y,
            "task_type": "sign_pdf",
            "timestamp": str(datetime.now())
        }

        self.send_message(self.QUEUE_SIGN_PDF, message)

    async def publish_merge_pdf_task(self, task_id: str, document_ids: list, output_filename: str) -> None:
        """
        Đăng tác vụ gộp tài liệu PDF.

        Args:
            task_id: ID của tác vụ
            document_ids: Danh sách ID tài liệu cần gộp
            output_filename: Tên file kết quả
        """
        message = {
            "task_id": task_id,
            "document_ids": document_ids,
            "output_filename": output_filename,
            "task_type": "merge_pdf",
            "timestamp": str(datetime.now())
        }

        self.send_message(self.QUEUE_MERGE_PDF, message)

    async def publish_crack_pdf_task(self, document_id: str, max_length: int) -> None:
        """
        Đăng tác vụ crack mật khẩu PDF.

        Args:
            document_id: ID của tài liệu cần crack
            max_length: Độ dài tối đa của mật khẩu để thử
        """
        message = {
            "document_id": document_id,
            "max_length": max_length,
            "task_type": "crack_pdf",
            "timestamp": str(datetime.now())
        }

        self.send_message(self.QUEUE_CRACK_PDF, message)

    async def publish_convert_to_word_task(self, document_id: str, output_format: str) -> None:
        """
        Đăng tác vụ chuyển đổi tài liệu PDF sang Word.

        Args:
            document_id: ID của tài liệu cần chuyển đổi
            output_format: Định dạng đầu ra
        """
        message = {
            "document_id": document_id,
            "output_format": output_format,
            "task_type": "convert_to_word",
            "timestamp": str(datetime.now())
        }

        self.send_message(self.QUEUE_CONVERT_TO_WORD, message)

    async def publish_convert_to_images_task(self, document_id: str, output_format: str, dpi: int,
                                           page_numbers: Optional[list] = None) -> None:
        """
        Đăng tác vụ chuyển đổi tài liệu PDF sang hình ảnh.

        Args:
            document_id: ID của tài liệu cần chuyển đổi
            output_format: Định dạng đầu ra
            dpi: Độ phân giải của hình ảnh
            page_numbers: Danh sách số trang cần chuyển đổi
        """
        message = {
            "document_id": document_id,
            "output_format": output_format,
            "dpi": dpi,
            "page_numbers": page_numbers,
            "task_type": "convert_to_images",
            "timestamp": str(datetime.now())
        }

        self.send_message(self.QUEUE_CONVERT_TO_IMAGES, message)