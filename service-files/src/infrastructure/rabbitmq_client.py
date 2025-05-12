import json
import pika
import asyncio
import threading
import logging
from typing import Dict, Any, Callable, Optional

from core.config import settings


class RabbitMQClient:
    def __init__(self):
        self.connection = None
        self.channel = None
        self.callback_queue = 'files_callback_queue'
        self.extract_queue = 'extract_queue'
        self.compress_queue = 'compress_queue'
        self.archive_modify_queue = 'archive_modify_queue'
        self.archive_security_queue = 'archive_security_queue'
        self.archive_convert_queue = 'archive_convert_queue'
        
        self.logger = logging.getLogger("rabbitmq_client")
        self.callbacks = {}
        self.response = None
        self.corr_id = None
        self.connect()
        
    def connect(self):
        """Kết nối đến RabbitMQ server."""
        try:
            self.connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=settings.RABBITMQ_HOST,
                    port=settings.RABBITMQ_PORT,
                    virtual_host=settings.RABBITMQ_VHOST,
                    credentials=pika.PlainCredentials(
                        settings.RABBITMQ_USER,
                        settings.RABBITMQ_PASS
                    )
                )
            )
            self.channel = self.connection.channel()

            self.channel.queue_declare(queue=self.callback_queue, durable=True)
            self.channel.queue_declare(queue=self.extract_queue, durable=True)
            self.channel.queue_declare(queue=self.compress_queue, durable=True)
            self.channel.queue_declare(queue=self.archive_modify_queue, durable=True)
            self.channel.queue_declare(queue=self.archive_security_queue, durable=True)
            self.channel.queue_declare(queue=self.archive_convert_queue, durable=True)
            
        except Exception as e:
            self.logger.error(f"Không thể kết nối đến RabbitMQ: {str(e)}")
            
    def reconnect(self):
        """Kết nối lại RabbitMQ nếu kết nối bị ngắt."""
        try:
            if self.connection is None or self.connection.is_closed:
                self.connect()
                return True
            return False
        except Exception as e:
            self.logger.error(f"Không thể kết nối lại RabbitMQ: {str(e)}")
            return False
            
    async def publish_message(self, queue: str, message: Dict[str, Any]) -> bool:
        """Gửi tin nhắn vào queue."""
        try:
            if self.reconnect():
                self.logger.info("Đã kết nối lại RabbitMQ thành công")
                
            self.channel.basic_publish(
                exchange='',
                routing_key=queue,
                body=json.dumps(message).encode(),
                properties=pika.BasicProperties(
                    delivery_mode=2,
                )
            )
            return True
        except Exception as e:
            self.logger.error(f"Lỗi khi gửi tin nhắn: {str(e)}")
            return False
            
    def consume_message(self, queue: str, callback: Callable) -> None:
        """Tiêu thụ tin nhắn từ queue."""
        try:
            if self.reconnect():
                self.logger.info("Đã kết nối lại RabbitMQ thành công")
                
            self.callbacks[queue] = callback
            self.channel.basic_consume(
                queue=queue,
                on_message_callback=self._on_message,
                auto_ack=False
            )
        except Exception as e:
            self.logger.error(f"Lỗi khi tiêu thụ tin nhắn: {str(e)}")
            
    def _on_message(self, ch, method, props, body):
        """Xử lý tin nhắn được nhận."""
        try:
            message = json.loads(body)
            
            if method.routing_key in self.callbacks:
                self.callbacks[method.routing_key](message)
                
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            self.logger.error(f"Lỗi khi xử lý tin nhắn: {str(e)}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            
    def start_consuming(self) -> None:
        """Bắt đầu consuming trong thread riêng."""
        consume_thread = threading.Thread(target=self._consume)
        consume_thread.daemon = True
        consume_thread.start()
        
    def _consume(self) -> None:
        """Consuming thread."""
        try:
            self.channel.start_consuming()
        except Exception as e:
            self.logger.error(f"Lỗi consuming: {str(e)}")
            self.reconnect()
            
    def close(self) -> None:
        """Đóng kết nối RabbitMQ."""
        if self.connection and self.connection.is_open:
            try:
                if self.channel and self.channel.is_open:
                    self.channel.close()
                self.connection.close()
            except Exception as e:
                self.logger.error(f"Lỗi khi đóng kết nối RabbitMQ: {str(e)}") 