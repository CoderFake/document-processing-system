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

        # Các queue mặc định
        self.QUEUE_CONVERT_TO_PDF = "word_service.convert_to_pdf"
        self.QUEUE_WATERMARK = "word_service.watermark"
        self.QUEUE_APPLY_TEMPLATE = "word_service.apply_template"
        self.QUEUE_BATCH_PROCESSING = "word_service.batch_processing"

        # Khởi tạo logger
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

            # Đảm bảo các queue tồn tại
            self.channel.queue_declare(queue=self.QUEUE_CONVERT_TO_PDF, durable=True)
            self.channel.queue_declare(queue=self.QUEUE_WATERMARK, durable=True)
            self.channel.queue_declare(queue=self.QUEUE_APPLY_TEMPLATE, durable=True)
            self.channel.queue_declare(queue=self.QUEUE_BATCH_PROCESSING, durable=True)

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
                    delivery_mode=2,  # Persistent message
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
                # Parse JSON message
                message = json.loads(body)

                # Gọi callback
                callback(message)

                # Acknowledge message
                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as e:
                self.logger.error(f"Lỗi khi xử lý tin nhắn: {str(e)}")

                # Nack message và requeue
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

        try:
            channel = self._get_channel()
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=queue, on_message_callback=_callback)

            # Bắt đầu consuming trong thread riêng
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

    async def publish_convert_to_pdf_task(self, document_id: str, priority: int = 1) -> None:
        """
        Đăng tác vụ chuyển đổi tài liệu Word sang PDF.

        Args:
            document_id: ID của tài liệu cần chuyển đổi
            priority: Độ ưu tiên của tác vụ (1-10, 10 là cao nhất)
        """
        message = {
            "document_id": document_id,
            "priority": priority,
            "task_type": "convert_to_pdf",
            "timestamp": str(datetime.now())
        }

        self.send_message(self.QUEUE_CONVERT_TO_PDF, message)

    async def publish_watermark_task(self, document_id: str, watermark_text: str, position: str,
                                     opacity: float) -> None:
        """
        Đăng tác vụ thêm watermark vào tài liệu Word.

        Args:
            document_id: ID của tài liệu cần thêm watermark
            watermark_text: Nội dung watermark
            position: Vị trí của watermark
            opacity: Độ mờ của watermark
        """
        message = {
            "document_id": document_id,
            "watermark_text": watermark_text,
            "position": position,
            "opacity": opacity,
            "task_type": "watermark",
            "timestamp": str(datetime.now())
        }

        self.send_message(self.QUEUE_WATERMARK, message)

    async def publish_apply_template_task(self, template_id: str, data: Dict[str, Any], output_format: str) -> None:
        """
        Đăng tác vụ áp dụng mẫu tài liệu.

        Args:
            template_id: ID của mẫu tài liệu
            data: Dữ liệu áp dụng vào mẫu
            output_format: Định dạng đầu ra (docx, pdf)
        """
        message = {
            "template_id": template_id,
            "data": data,
            "output_format": output_format,
            "task_type": "apply_template",
            "timestamp": str(datetime.now())
        }

        self.send_message(self.QUEUE_APPLY_TEMPLATE, message)

    async def publish_batch_processing_task(self, task_id: str, template_id: str, data_list: Dict[str, Any],
                                            output_format: str) -> None:
        """
        Đăng tác vụ xử lý hàng loạt.

        Args:
            task_id: ID của tác vụ
            template_id: ID của mẫu tài liệu
            data_list: Danh sách dữ liệu áp dụng vào mẫu
            output_format: Định dạng đầu ra (docx, pdf, zip)
        """
        message = {
            "task_id": task_id,
            "template_id": template_id,
            "data_list": data_list,
            "output_format": output_format,
            "task_type": "batch_processing",
            "timestamp": str(datetime.now())
        }

        self.send_message(self.QUEUE_BATCH_PROCESSING, message)