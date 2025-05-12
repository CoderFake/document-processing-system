import os
import grpc
import time
import logging
import threading
from concurrent import futures
from typing import Optional, Callable

from utils.word_pb2 import ConvertRequest, ConvertReply
from utils.word_pb2_grpc import WordServiceServicer, add_WordServiceServicer_to_server
from utils.word_service import WordConverter

logger = logging.getLogger(__name__)

class WordServiceImpl(WordServiceServicer):
    """
    Triển khai dịch vụ gRPC cho việc chuyển đổi Word sang PDF.
    """
    
    def ConvertToPDF(self, request, context):
        """
        Chuyển đổi tệp Word sang PDF qua gRPC.
        
        Args:
            request: ConvertRequest với input_path và output_path
            context: Context của gRPC
            
        Returns:
            ConvertReply với trạng thái và thông báo
        """
        try:
            logger.info(f"Nhận yêu cầu chuyển đổi từ: {request.input_path} sang {request.output_path}")
            
            if not os.path.exists(request.input_path):
                error_msg = f"Tệp đầu vào không tồn tại: {request.input_path}"
                logger.error(error_msg)
                return ConvertReply(success=False, message=error_msg)
            
            try:
                output_path = WordConverter.convert_to_pdf_using_libreoffice(
                    request.input_path, 
                    request.output_path
                )
                
                if os.path.exists(output_path):
                    logger.info(f"Chuyển đổi thành công: {output_path}")
                    return ConvertReply(success=True, message=f"Chuyển đổi thành công: {output_path}")
                else:
                    error_msg = f"Không tìm thấy tệp đầu ra sau khi chuyển đổi: {output_path}"
                    logger.error(error_msg)
                    return ConvertReply(success=False, message=error_msg)
                    
            except Exception as e:
                error_msg = f"Lỗi khi chuyển đổi: {str(e)}"
                logger.error(error_msg)
                return ConvertReply(success=False, message=error_msg)
                
        except Exception as e:
            error_msg = f"Lỗi không xác định: {str(e)}"
            logger.error(error_msg)
            return ConvertReply(success=False, message=error_msg)


class GRPCServer:
    """
    Quản lý vòng đời của gRPC server.
    """
    
    def __init__(self, host: str = "[::]:50051", max_workers: int = 10):
        """
        Khởi tạo gRPC server.
        
        Args:
            host: Host và port để server lắng nghe
            max_workers: Số lượng worker tối đa
        """
        self.host = host
        self.max_workers = max_workers
        self.server = None
        self.server_thread = None
        self.running = False
        
    def start(self, block: bool = False) -> None:
        """
        Khởi động gRPC server.
        
        Args:
            block: Nếu True, hàm sẽ block cho đến khi server dừng
        """
        if self.running:
            logger.warning("gRPC server đã đang chạy")
            return
            
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=self.max_workers))
        add_WordServiceServicer_to_server(WordServiceImpl(), self.server)
        self.server.add_insecure_port(self.host)
        self.server.start()
        self.running = True
        
        logger.info(f"gRPC server đang chạy trên {self.host}")
        
        if block:
            self._serve_forever()
        else:
            self.server_thread = threading.Thread(target=self._serve_forever)
            self.server_thread.daemon = True
            self.server_thread.start()
            
    def _serve_forever(self) -> None:
        """
        Giữ server chạy cho đến khi có lệnh dừng.
        """
        try:
            while self.running:
                time.sleep(60*60*24)
        except KeyboardInterrupt:
            self.stop()
        except Exception as e:
            logger.error(f"Lỗi trong gRPC server: {str(e)}")
            self.stop()
            
    def stop(self, grace: Optional[float] = None) -> None:
        """
        Dừng gRPC server.
        
        Args:
            grace: Thời gian chờ (giây) trước khi dừng hẳn
        """
        if not self.running:
            logger.warning("gRPC server không chạy")
            return
            
        if self.server:
            self.server.stop(grace)
            self.running = False
            logger.info("gRPC server đã dừng")


def start_grpc_server(host: str = "[::]:50051", 
                     max_workers: int = 10,
                     block: bool = False,
                     on_start: Optional[Callable] = None) -> GRPCServer:
    """
    Khởi động gRPC server.
    
    Args:
        host: Host và port để server lắng nghe
        max_workers: Số lượng worker tối đa
        block: Nếu True, hàm sẽ block cho đến khi server dừng
        on_start: Callback được gọi sau khi server khởi động
        
    Returns:
        Instance của GRPCServer
    """
    server = GRPCServer(host, max_workers)
    server.start(block=False)
    
    if on_start:
        on_start(server)
        
    if block:
        try:
            server._serve_forever()
        except KeyboardInterrupt:
            server.stop()
            
    return server


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    start_grpc_server(block=True) 