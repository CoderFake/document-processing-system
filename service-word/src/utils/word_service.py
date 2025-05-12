import os
import tempfile
import subprocess
from pathlib import Path
import logging
from typing import Optional
import uuid
import time
import grpc

from utils.word_pb2 import ConvertRequest, ConvertReply
from utils.word_pb2_grpc import WordServiceStub

logger = logging.getLogger(__name__)

DEFAULT_GRPC_SERVER = "service-word:50051"

class WordConverter:
    """
    Lớp chuyển đổi tài liệu Word sang PDF sử dụng nhiều phương pháp.
    """

    @staticmethod
    def convert_to_pdf_using_libreoffice(input_path: str, output_path: Optional[str] = None) -> str:
        """
        Chuyển đổi tài liệu Word sang PDF sử dụng LibreOffice.
        
        Args:
            input_path: Đường dẫn đến tài liệu Word
            output_path: Đường dẫn để lưu tài liệu PDF đầu ra (tùy chọn)
            
        Returns:
            Đường dẫn đến tài liệu PDF đã tạo
        """
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Tệp đầu vào không tồn tại: {input_path}")
        
        if output_path is None:
            output_dir = os.path.dirname(input_path)
            output_path = os.path.join(output_dir, f"{os.path.splitext(os.path.basename(input_path))[0]}.pdf")
        
        try:
            cmd = [
                'libreoffice', 
                '--headless', 
                '--convert-to', 
                'pdf', 
                '--outdir', 
                os.path.dirname(output_path), 
                input_path
            ]
            
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                logger.error(f"Lỗi khi chuyển đổi: {stderr.decode()}")
                raise Exception(f"Lỗi khi chuyển đổi: {stderr.decode()}")
            
            generated_pdf = os.path.join(
                os.path.dirname(output_path), 
                f"{os.path.splitext(os.path.basename(input_path))[0]}.pdf"
            )
            
            if generated_pdf != output_path:
                os.rename(generated_pdf, output_path)
            
            return output_path
        except Exception as e:
            logger.error(f"Lỗi khi chuyển đổi file Word sang PDF: {str(e)}")
            raise

    @staticmethod
    def convert_to_pdf_using_docx2pdf(input_path: str, output_path: Optional[str] = None) -> str:
        """
        Chuyển đổi tài liệu Word sang PDF sử dụng thư viện docx2pdf.
        
        Args:
            input_path: Đường dẫn đến tài liệu Word
            output_path: Đường dẫn để lưu tài liệu PDF đầu ra (tùy chọn)
            
        Returns:
            Đường dẫn đến tài liệu PDF đã tạo
        """
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Tệp đầu vào không tồn tại: {input_path}")
        
        try:
            from docx2pdf import convert
            
            if output_path is None:
                output_dir = os.path.dirname(input_path)
                output_path = os.path.join(output_dir, f"{os.path.splitext(os.path.basename(input_path))[0]}.pdf")
            
            convert(input_path, output_path)
            return output_path
        except ImportError:
            logger.warning("Thư viện docx2pdf không được cài đặt. Sử dụng phương thức thay thế.")
            return WordConverter.convert_to_pdf_using_libreoffice(input_path, output_path)
        except Exception as e:
            logger.error(f"Lỗi khi chuyển đổi file Word sang PDF bằng docx2pdf: {str(e)}")
            return WordConverter.convert_to_pdf_using_libreoffice(input_path, output_path)

    @staticmethod
    def convert_to_pdf_using_grpc(input_path: str, output_path: Optional[str] = None, server_address: str = DEFAULT_GRPC_SERVER) -> str:
        """
        Chuyển đổi tài liệu Word sang PDF sử dụng gRPC service.
        
        Args:
            input_path: Đường dẫn đến tài liệu Word
            output_path: Đường dẫn để lưu tài liệu PDF đầu ra (tùy chọn)
            server_address: Địa chỉ của gRPC server
            
        Returns:
            Đường dẫn đến tài liệu PDF đã tạo
        """
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Tệp đầu vào không tồn tại: {input_path}")
        
        if output_path is None:
            output_dir = os.path.dirname(input_path)
            output_path = os.path.join(output_dir, f"{os.path.splitext(os.path.basename(input_path))[0]}.pdf")
        
        try:
            request = ConvertRequest(
                input_path=input_path,
                output_path=output_path
            )
            
            try:
                channel = grpc.insecure_channel(server_address)
                stub = WordServiceStub(channel)
                
                response = stub.ConvertToPDF(request)
                
                if not response.success:
                    raise Exception(f"Lỗi từ gRPC server: {response.message}")
                
                return output_path
                
            except grpc.RpcError as e:
                logger.error(f"Lỗi gRPC khi kết nối tới server: {str(e)}")
                logger.warning("Không thể kết nối tới gRPC server, sử dụng phương pháp thay thế")
                response = WordConverter._mock_grpc_convert(request)
                
                if not response.success:
                    raise Exception(f"Lỗi khi chuyển đổi: {response.message}")
                
                return output_path
                
        except Exception as e:
            logger.error(f"Lỗi khi chuyển đổi file Word sang PDF thông qua gRPC: {str(e)}")
            return WordConverter.convert_to_pdf_using_libreoffice(input_path, output_path)

    @staticmethod
    def _mock_grpc_convert(request: ConvertRequest) -> ConvertReply:
        """
        Hàm giả lập chức năng của gRPC service để chuyển đổi Word sang PDF.
        
        Args:
            request: ConvertRequest chứa đường dẫn đầu vào và đầu ra
            
        Returns:
            ConvertReply chứa kết quả chuyển đổi
        """
        try:
            output_path = WordConverter.convert_to_pdf_using_libreoffice(
                request.input_path, 
                request.output_path
            )
            
            if os.path.exists(output_path):
                return ConvertReply(success=True, message="Chuyển đổi thành công")
            else:
                return ConvertReply(success=False, message="Không tìm thấy file đầu ra sau khi chuyển đổi")
        except Exception as e:
            return ConvertReply(success=False, message=str(e))

    @staticmethod
    def convert_to_pdf(input_path: str, output_path: Optional[str] = None, method: str = "libreoffice") -> str:
        """
        Chuyển đổi tài liệu Word sang PDF sử dụng phương pháp được chỉ định.
        
        Args:
            input_path: Đường dẫn đến tài liệu Word
            output_path: Đường dẫn để lưu tài liệu PDF đầu ra (tùy chọn)
            method: Phương pháp chuyển đổi ('libreoffice', 'docx2pdf', 'grpc')
            
        Returns:
            Đường dẫn đến tài liệu PDF đã tạo
        """
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Tệp đầu vào không tồn tại: {input_path}")
        
        if output_path is None:
            output_dir = os.path.dirname(input_path)
            output_path = os.path.join(output_dir, f"{os.path.splitext(os.path.basename(input_path))[0]}.pdf")
        
        methods = {
            "libreoffice": WordConverter.convert_to_pdf_using_libreoffice,
            "docx2pdf": WordConverter.convert_to_pdf_using_docx2pdf,
            "grpc": WordConverter.convert_to_pdf_using_grpc
        }
        
        if method not in methods:
            logger.warning(f"Phương pháp không hợp lệ: {method}. Sử dụng LibreOffice thay thế.")
            method = "libreoffice"
        
        try:
            converter = methods[method]
            return converter(input_path, output_path)
        except Exception as e:
            logger.error(f"Lỗi khi chuyển đổi file Word sang PDF bằng {method}: {str(e)}")
            return WordConverter.convert_to_pdf_using_libreoffice(input_path, output_path) 