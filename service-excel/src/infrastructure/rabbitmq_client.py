import json
import pika
from typing import Dict, Any, Optional, Callable
import asyncio
import threading
import logging
from datetime import datetime

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

        self.QUEUE_CONVERT_TO_PDF = "excel_service.convert_to_pdf"
        self.QUEUE_CONVERT_TO_WORD = "excel_service.convert_to_word"
        self.QUEUE_MERGE_DOCUMENTS = "excel_service.merge_documents"
        self.QUEUE_APPLY_TEMPLATE = "excel_service.apply_template"
        self.QUEUE_BATCH_PROCESSING = "excel_service.batch_processing"

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

            self.channel.queue_declare(queue=self.QUEUE_CONVERT_TO_PDF, durable=True)
            self.channel.queue_declare(queue=self.QUEUE_CONVERT_TO_WORD, durable=True)
            self.channel.queue_declare(queue=self.QUEUE_MERGE_DOCUMENTS, durable=True)
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

    async def publish_convert_to_pdf_task(self, document_id: str, priority: int = 1) -> None:
        """
        Đăng tác vụ chuyển đổi tài liệu Excel sang PDF.

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

    async def publish_convert_to_word_task(self, document_id: str, priority: int = 1) -> None:
        """
        Đăng tác vụ chuyển đổi tài liệu Excel sang Word.

        Args:
            document_id: ID của tài liệu cần chuyển đổi
            priority: Độ ưu tiên của tác vụ (1-10, 10 là cao nhất)
        """
        message = {
            "document_id": document_id,
            "priority": priority,
            "task_type": "convert_to_word",
            "timestamp": str(datetime.now())
        }

        self.send_message(self.QUEUE_CONVERT_TO_WORD, message)

    async def publish_merge_documents_task(self, task_id: str, document_ids: List[str], output_filename: str) -> None:
        """
        Đăng tác vụ gộp tài liệu Excel.

        Args:
            task_id: ID của tác vụ
            document_ids: Danh sách ID tài liệu cần gộp
            output_filename: Tên file kết quả
        """
        message = {
            "task_id": task_id,
            "document_ids": document_ids,
            "output_filename": output_filename,
            "task_type": "merge_documents",
            "timestamp": str(datetime.now())
        }

        self.send_message(self.QUEUE_MERGE_DOCUMENTS, message)

    async def publish_apply_template_task(self, template_id: str, data: Dict[str, Any], output_format: str) -> None:
        """
        Đăng tác vụ áp dụng mẫu tài liệu.

        Args:
            template_id: ID của mẫu tài liệu
            data: Dữ liệu áp dụng vào mẫu
            output_format: Định dạng đầu ra (xlsx, pdf)
        """
        message = {
            "template_id": template_id,
            "data": data,
            "output_format": output_format,
            "task_type": "apply_template",
            "timestamp": str(datetime.now())
        }

        self.send_message(self.QUEUE_APPLY_TEMPLATE, message)

    async def publish_batch_processing_task(self, task_id: str, template_id: str, data_list: List[Dict[str, Any]],
                                            output_format: str) -> None:
        """
        Đăng tác vụ xử lý hàng loạt.

        Args:
            task_id: ID của tác vụ
            template_id: ID của mẫu tài liệu
            data_list: Danh sách dữ liệu áp dụng vào mẫu
            output_format: Định dạng đầu ra (xlsx, pdf, zip)
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