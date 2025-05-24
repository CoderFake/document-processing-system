from http.client import HTTPException
import os
import io
import tempfile
import asyncio
import uuid
import json
import zipfile
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging

from application.dto import (
    CreateDocumentDTO as CreatePdfDocumentDTO, CreatePngDocumentDTO, CreateStampDTO,
    EncryptPdfDTO, DecryptPdfDTO, AddWatermarkDTO as WatermarkPdfDTO, SignPdfDTO, MergePdfDTO,
    CrackPdfDTO, ConvertPdfToWordDTO, ConvertPdfToImageDTO,
    UpdateDocumentDTO as UpdatePdfDocumentDTO, UpdatePngDocumentDTO
)
from domain.models import PDFDocumentInfo, PNGDocumentInfo, StampInfo, PDFProcessingInfo, MergeInfo
from domain.exceptions import (
    DocumentNotFoundException, StorageException, ConversionException,
    EncryptionException, DecryptionException, WatermarkException,
    SignatureException, MergeException, StampNotFoundException,
    PDFPasswordProtectedException, WrongPasswordException, CrackPasswordException,
    ImageNotFoundException
)
from infrastructure.repository import (
    PDFDocumentRepository, PNGDocumentRepository, StampRepository,
    PDFProcessingRepository, MergeRepository
)
from infrastructure.minio_client import MinioClient
from infrastructure.rabbitmq_client import RabbitMQClient
from domain.models import DBDocument
from core.config import settings

from PyPDF2 import PdfReader, PdfWriter
import fitz  
from PIL import Image
from pdf2docx import Converter

logger = logging.getLogger(__name__)


class PDFDocumentService:
    """
    Service xử lý tài liệu PDF.
    """

    def __init__(
            self,
            document_repository: PDFDocumentRepository,
            image_repository: PNGDocumentRepository,
            stamp_repository: StampRepository,
            minio_client: MinioClient,
            rabbitmq_client: RabbitMQClient,
            processing_repository: PDFProcessingRepository
    ):
        """
        Khởi tạo service.

        Args:
            document_repository: Repository để làm việc với tài liệu PDF
            image_repository: Repository để làm việc với tài liệu PNG
            stamp_repository: Repository để làm việc với mẫu dấu
            minio_client: Client MinIO để lưu trữ tài liệu
            rabbitmq_client: Client RabbitMQ để gửi tin nhắn
            processing_repository: Repository để làm việc với thông tin xử lý
        """
        self.document_repository = document_repository
        self.image_repository = image_repository
        self.stamp_repository = stamp_repository
        self.minio_client = minio_client
        self.rabbitmq_client = rabbitmq_client
        self.processing_repository = processing_repository
        self.merge_repository = MergeRepository()

    async def _get_pdf_info(self, file_path: str) -> Dict[str, Any]:
        """Helper để lấy thông tin cơ bản từ file PDF."""
        try:
            doc = fitz.open(file_path)
            page_count = doc.page_count
            is_encrypted = doc.is_encrypted
            doc.close()
            return {"page_count": page_count, "is_encrypted": is_encrypted}
        except Exception as e:
            logger.warning(f"Could not get PDF info from {file_path}: {e}")
            return {"page_count": 0, "is_encrypted": False}

    async def create_document(self, document_dto: CreatePdfDocumentDTO, content: bytes, user_id: str) -> PDFDocumentInfo:
        """
        Tạo tài liệu PDF mới.
        Args:
            document_dto: DTO cho việc tạo tài liệu PDF
            content: Nội dung tài liệu PDF
            user_id: ID của người dùng tạo tài liệu
        Returns:
            Thông tin tài liệu PDF đã tạo
        """
        try:
            pdf_info_from_file = {}
            temp_file_path = None
            try:
                with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
                    tmp_file.write(content)
                    temp_file_path = tmp_file.name
                
                pdf_info_from_file = await self._get_pdf_info(temp_file_path)
            finally:
                if temp_file_path and os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)

            document_info = PDFDocumentInfo(
                title=document_dto.title,
                description=document_dto.description,
                original_filename=document_dto.original_filename,
                user_id=user_id,
                page_count=pdf_info_from_file.get("page_count", 0),
                is_encrypted=pdf_info_from_file.get("is_encrypted", False),
                file_size=len(content)
            )
                
            saved_document = await self.document_repository.save(document_info, content, user_id)
            return saved_document
        except Exception as e:
            logger.error(f"Lỗi khi tạo tài liệu PDF (user: {user_id}, title: {document_dto.title}): {e}", exc_info=True)
            raise StorageException(f"Lỗi khi tạo tài liệu PDF: {str(e)}")

    async def create_png_document(self, dto: CreatePngDocumentDTO, content: bytes, user_id: str) -> PNGDocumentInfo:
        """
        Tạo tài liệu PNG mới.
        Args:
            dto: DTO chứa thông tin tài liệu
            content: Nội dung tài liệu
            user_id: ID của người dùng
        Returns:
            Thông tin tài liệu đã tạo
        """
        temp_file_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
                temp_file.write(content)
                temp_file_path = temp_file.name

                img = Image.open(temp_file_path)
                width, height = img.size
            img.close()

            document_info = PNGDocumentInfo(
                title=dto.title,
                description=dto.description,
                original_filename=dto.original_filename,
                file_size=len(content),
                width=width,
                height=height,
                doc_metadata=dto.doc_metadata or {},
                user_id=user_id
            )

            saved_document_info = await self.image_repository.save(document_info, content, user_id)
            return saved_document_info
        except Exception as e:
            logger.error(f"Lỗi khi tạo tài liệu PNG (user: {user_id}, title: {dto.title}): {e}", exc_info=True)
            raise StorageException(f"Lỗi khi tạo tài liệu PNG: {str(e)}")
        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    async def get_documents(
        self, user_id: str, skip: int = 0, limit: int = 10, search: Optional[str] = None
    ) -> Tuple[List[PDFDocumentInfo], int]:
        """
        Lấy danh sách tài liệu PDF của người dùng.
        """
        try:
            documents, total_count = await self.document_repository.list(skip=skip, limit=limit, search=search, user_id=user_id)
            return documents, total_count
        except Exception as e:
            logger.error(f"Lỗi khi lấy danh sách PDF (user: {user_id}): {e}", exc_info=True)
            raise StorageException(f"Lỗi khi lấy danh sách tài liệu PDF: {str(e)}")

    async def get_png_documents(
        self, user_id: str, skip: int = 0, limit: int = 10, search: Optional[str] = None
    ) -> Tuple[List[PNGDocumentInfo], int]:
        try:
            images, total_count = await self.image_repository.list(skip=skip, limit=limit, search=search, user_id=user_id)
            return images, total_count
        except Exception as e:
            logger.error(f"Lỗi khi lấy danh sách PNG (user: {user_id}): {e}", exc_info=True)
            raise StorageException(f"Lỗi khi lấy danh sách tài liệu PNG: {str(e)}")

    async def get_document(self, document_id: str, user_id: str) -> Tuple[PDFDocumentInfo, bytes]:
        """Lấy thông tin và nội dung tài liệu PDF theo ID, kiểm tra user_id."""
        try:
            document_info, content = await self.document_repository.get(document_id, user_id_check=user_id)
            if not document_info or content is None:
                raise DocumentNotFoundException(f"Tài liệu PDF {document_id} không tồn tại hoặc không thuộc về người dùng {user_id}.")
            return document_info, content
        except DocumentNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Lỗi khi lấy chi tiết PDF (id: {document_id}, user: {user_id}): {e}", exc_info=True)
            raise StorageException(f"Lỗi khi lấy tài liệu PDF {document_id}: {str(e)}")

    async def get_png_document(self, document_id: str, user_id: str) -> Tuple[PNGDocumentInfo, bytes]:
        try:
            image_info, content = await self.image_repository.get(document_id, user_id_check=user_id)
            if not image_info or content is None:
                raise ImageNotFoundException(f"Tài liệu PNG {document_id} không tồn tại hoặc không thuộc về người dùng {user_id}.")
            return image_info, content
        except ImageNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Lỗi khi lấy chi tiết PNG (id: {document_id}, user: {user_id}): {e}", exc_info=True)
            raise StorageException(f"Lỗi khi lấy tài liệu PNG {document_id}: {str(e)}")

    async def update_document(self, document_id: str, dto: UpdatePdfDocumentDTO, user_id: str) -> PDFDocumentInfo:
        try:
            existing_doc_info, _ = await self.document_repository.get(document_id, user_id_check=user_id)
            if not existing_doc_info:
                raise DocumentNotFoundException(f"Tài liệu PDF {document_id} không tồn tại hoặc không có quyền cập nhật.")

            update_data = dto.dict(exclude_unset=True)
            for key, value in update_data.items():
                setattr(existing_doc_info, key, value)
            
            updated_doc_info = await self.document_repository.update(existing_doc_info, user_id_check=user_id)
            return updated_doc_info
        except DocumentNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật PDF (id: {document_id}, user: {user_id}): {e}", exc_info=True)
            raise StorageException(f"Không thể cập nhật tài liệu PDF {document_id}: {str(e)}")

    async def update_png_document(self, document_id: str, dto: UpdatePngDocumentDTO, user_id: str) -> PNGDocumentInfo:
        try:
            existing_doc_info, _ = await self.image_repository.get(document_id, user_id_check=user_id)
            if not existing_doc_info:
                raise ImageNotFoundException(f"Tài liệu PNG {document_id} không tồn tại hoặc không có quyền cập nhật.")

            update_data = dto.dict(exclude_unset=True)
            for key, value in update_data.items():
                setattr(existing_doc_info, key, value)

            updated_doc_info = await self.image_repository.update(existing_doc_info, user_id_check=user_id)
            return updated_doc_info
        except ImageNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật PNG (id: {document_id}, user: {user_id}): {e}", exc_info=True)
            raise StorageException(f"Không thể cập nhật tài liệu PNG {document_id}: {str(e)}")

    async def delete_document(self, document_id: str, user_id: str) -> None:
        """Xóa tài liệu PDF theo ID, kiểm tra user_id."""
        try:
            doc_info, _ = await self.document_repository.get(document_id, user_id_check=user_id)
            if not doc_info:
                raise DocumentNotFoundException(f"Tài liệu PDF {document_id} không tồn tại hoặc không có quyền xóa.")
            await self.document_repository.delete(document_id, user_id_check=user_id)
        except DocumentNotFoundException:
                raise
        except Exception as e:
            logger.error(f"Lỗi khi xóa PDF (id: {document_id}, user: {user_id}): {e}", exc_info=True)
            raise StorageException(f"Lỗi khi xóa tài liệu PDF {document_id}: {str(e)}")

    async def delete_png_document(self, document_id: str, user_id: str) -> None:
        try:
            doc_info, _ = await self.image_repository.get(document_id, user_id_check=user_id)
            if not doc_info:
                raise ImageNotFoundException(f"Tài liệu PNG {document_id} không tồn tại hoặc không có quyền xóa.")
            await self.image_repository.delete(document_id, user_id_check=user_id)
        except ImageNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Lỗi khi xóa PNG (id: {document_id}, user: {user_id}): {e}", exc_info=True)
            raise StorageException(f"Lỗi khi xóa tài liệu PNG {document_id}: {str(e)}")

    async def encrypt_pdf(self, dto: EncryptPdfDTO, user_id: str) -> Dict[str, Any]:
        processing_id = str(uuid.uuid4())
        output_path = None
        temp_file_path = None
        original_doc_info = None
        try:
            original_doc_info, document_content = await self.get_document(dto.document_id, user_id)

            processing_info = PDFProcessingInfo(
                id=processing_id,
                document_id=dto.document_id,
                operation_type="encrypt",
                parameters=dto.dict(exclude={'document_id'})
            )
            await self.processing_repository.save(processing_info)

            fd_input, temp_file_path = tempfile.mkstemp(suffix=".pdf")
            with os.fdopen(fd_input, "wb") as tmp_in:
                tmp_in.write(document_content)
                
                reader = PdfReader(temp_file_path)
                if reader.is_encrypted:
                    raise EncryptionException("PDF đã được mã hóa")

                writer = PdfWriter()
                for page in reader.pages:
                    writer.add_page(page)

            fd_output, output_path = tempfile.mkstemp(suffix="_encrypted.pdf")

            permissions_flag = self._get_permissions_flag(dto.permissions) if dto.permissions else 0
            writer.encrypt(
                user_password=dto.password,
                owner_password=None,
                use_128bit=True,
                permissions_flag=permissions_flag
            )

            with os.fdopen(fd_output, "wb") as tmp_out:
                writer.write(tmp_out)

            with open(output_path, "rb") as f_encrypted:
                encrypted_content = f_encrypted.read()
            
            new_doc_filename = f"encrypted_{original_doc_info.original_filename}"
            new_doc_info = PDFDocumentInfo(
                title=f"Encrypted - {original_doc_info.title}",
                description=original_doc_info.description,
                original_filename=new_doc_filename,
                page_count=original_doc_info.page_count, 
                is_encrypted=True,
                doc_metadata=original_doc_info.doc_metadata.copy(),
                user_id=user_id,
                file_size=len(encrypted_content)
            )

            saved_encrypted_doc = await self.document_repository.save(new_doc_info, encrypted_content, user_id)

            processing_info.status = "completed"
            processing_info.completed_at = datetime.now()
            processing_info.result_document_id = saved_encrypted_doc.id
            await self.processing_repository.update(processing_info)

            return {
                "message": "Tài liệu đã được mã hóa thành công",
                "new_document_id": saved_encrypted_doc.id,
                "original_document_id": dto.document_id,
                "processing_id": processing_info.id
            }
        except PDFPasswordProtectedException as e:
            logger.warning(f"PDF Encrypt: {e} (doc: {dto.document_id}, user: {user_id})")
            if processing_id: 
                await self._update_processing_error(processing_id, str(e))
            raise
        except Exception as e:
            logger.error(f"Lỗi khi mã hóa PDF (doc: {dto.document_id}, user: {user_id}): {e}", exc_info=True)
            if processing_id: 
                await self._update_processing_error(processing_id, str(e))
            raise EncryptionException(f"Lỗi khi mã hóa PDF: {str(e)}")
        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            if output_path and os.path.exists(output_path):
                os.unlink(output_path)

    def _get_permissions_flag(self, permissions: Dict[str, bool]) -> int:
        flag = 0
        if permissions.get("print"): flag |= (1 << 2)
        if permissions.get("modify"): flag |= (1 << 3)
        if permissions.get("copy"): flag |= (1 << 4)
        if permissions.get("annotate"): flag |= (1 << 5)
        return flag

    async def _update_processing_error(self, processing_id: str, error_message: str):
        try:
            processing_info = await self.processing_repository.get(processing_id)
            if processing_info:
                processing_info.status = "failed"
                processing_info.error_message = error_message
                processing_info.completed_at = datetime.now()
                await self.processing_repository.update(processing_info)
        except Exception as e_repo:
            logger.error(f"Lỗi khi cập nhật trạng thái lỗi cho processing_id {processing_id}: {e_repo}")

    async def decrypt_pdf(self, dto: DecryptPdfDTO, user_id: str) -> Dict[str, Any]:
        processing_id = str(uuid.uuid4())
        output_path = None
        temp_file_path = None
        original_doc_info = None
        try:
            original_doc_info, document_content = await self.get_document(dto.document_id, user_id)

            processing_info = PDFProcessingInfo(
                id=processing_id,
                document_id=dto.document_id,
                operation_type="decrypt",
                parameters=dto.dict(exclude={'document_id', 'password'})
            )
            await self.processing_repository.save(processing_info)

            fd_input, temp_file_path = tempfile.mkstemp(suffix=".pdf")
            with os.fdopen(fd_input, "wb") as tmp_in:
                tmp_in.write(document_content)

            reader = PdfReader(temp_file_path)
            if not reader.is_encrypted:
                raise DecryptionException("PDF không được mã hóa")

            if not reader.decrypt(dto.password):
                raise WrongPasswordException("Mật khẩu không đúng hoặc không thể giải mã")

                writer = PdfWriter()
                for page in reader.pages:
                    writer.add_page(page)

            fd_output, output_path = tempfile.mkstemp(suffix="_decrypted.pdf")
            with os.fdopen(fd_output, "wb") as tmp_out:
                writer.write(tmp_out)

            with open(output_path, "rb") as f_decrypted:
                decrypted_content = f_decrypted.read()

            new_doc_filename = f"decrypted_{original_doc_info.original_filename}"
            new_doc_info = PDFDocumentInfo(
                title=f"Decrypted - {original_doc_info.title}",
                description=original_doc_info.description,
                original_filename=new_doc_filename,
                page_count=original_doc_info.page_count,
                    is_encrypted=False,
                doc_metadata=original_doc_info.doc_metadata.copy(),
                user_id=user_id,
                file_size=len(decrypted_content)
            )
            saved_decrypted_doc = await self.document_repository.save(new_doc_info, decrypted_content, user_id)

            processing_info.status = "completed"
            processing_info.completed_at = datetime.now()
            processing_info.result_document_id = saved_decrypted_doc.id
            await self.processing_repository.update(processing_info)

            return {
                "message": "Tài liệu đã được giải mã thành công",
                "new_document_id": saved_decrypted_doc.id,
                "original_document_id": dto.document_id,
                "processing_id": processing_info.id
            }
        except (WrongPasswordException, PDFPasswordProtectedException) as e:
            logger.warning(f"PDF Decrypt: {e} (doc: {dto.document_id}, user: {user_id})")
            if processing_id: 
                await self._update_processing_error(processing_id, str(e))
                raise
        except Exception as e:
            logger.error(f"Lỗi khi giải mã PDF (doc: {dto.document_id}, user: {user_id}): {e}", exc_info=True)
            if processing_id: 
                await self._update_processing_error(processing_id, str(e))
            raise DecryptionException(f"Lỗi khi giải mã PDF: {str(e)}")
        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            if output_path and os.path.exists(output_path):
                os.unlink(output_path)

    async def add_watermark(self, dto: WatermarkPdfDTO, user_id: str) -> Dict[str, Any]:
        processing_id = str(uuid.uuid4())
        output_path = None
        temp_input_path = None
        temp_watermark_path = None
        original_doc_info = None
        try:
            original_doc_info, document_content = await self.get_document(dto.document_id, user_id)

            processing_info = PDFProcessingInfo(
                id=processing_id,
                document_id=dto.document_id,
                operation_type="watermark",
                parameters=dto.dict(exclude={'document_id'})
            )
            await self.processing_repository.save(processing_info)

            fd_input, temp_input_path = tempfile.mkstemp(suffix=".pdf")
            with os.fdopen(fd_input, "wb") as tmp_in:
                tmp_in.write(document_content)

            pdf_doc = fitz.open(temp_input_path)
            
            watermark_text = dto.text
            rect = fitz.Rect(0, 0, 100, 50)

            for page_num in range(len(pdf_doc)):
                page = pdf_doc[page_num]
                page_rect = page.rect
                x = (page_rect.width - rect.width) / 2
                y = (page_rect.height - rect.height) / 2
                if dto.position == "top_left":
                    x, y = 20, 20
                elif dto.position == "bottom_right":
                    x, y = page_rect.width - rect.width - 20, page_rect.height - rect.height - 20
            
                page.insert_textbox(fitz.Rect(x, y, x + rect.width, y + rect.height), 
                    watermark_text, 
                    fontsize=dto.font_size, 
                    fontname=dto.font_name or "helv", 
                    color=dto.font_color or (0.5,0.5,0.5),
                    align=1,
                    rotate=dto.rotate or 0,
                )

            fd_output, output_path = tempfile.mkstemp(suffix="_watermarked.pdf")
            pdf_doc.save(output_path, garbage=4, deflate=True)
            pdf_doc.close()

            with open(output_path, "rb") as f_watermarked:
                watermarked_content = f_watermarked.read()

            new_doc_filename = f"watermarked_{original_doc_info.original_filename}"
            new_doc_info = PDFDocumentInfo(
                title=f"Watermarked - {original_doc_info.title}",
                description=original_doc_info.description,
                original_filename=new_doc_filename,
                page_count=original_doc_info.page_count,
                is_encrypted=original_doc_info.is_encrypted,
                doc_metadata=original_doc_info.doc_metadata.copy(),
                user_id=user_id,
                file_size=len(watermarked_content)
            )
            saved_watermarked_doc = await self.document_repository.save(new_doc_info, watermarked_content, user_id)

            processing_info.status = "completed"
            processing_info.completed_at = datetime.now()
            processing_info.result_document_id = saved_watermarked_doc.id
            await self.processing_repository.update(processing_info)

            return {
                "message": "Watermark đã được thêm thành công",
                "new_document_id": saved_watermarked_doc.id,
                "original_document_id": dto.document_id,
                "processing_id": processing_info.id
                    }
        except Exception as e:
            logger.error(f"Lỗi khi thêm watermark (doc: {dto.document_id}, user: {user_id}): {e}", exc_info=True)
            if processing_id: 
                await self._update_processing_error(processing_id, str(e))
                raise WatermarkException(f"Lỗi khi thêm watermark: {str(e)}")
        finally:
            if temp_input_path and os.path.exists(temp_input_path):
                os.unlink(temp_input_path)
            if output_path and os.path.exists(output_path):
                os.unlink(output_path)

    async def add_signature(self, dto: SignPdfDTO, user_id: str) -> Dict[str, Any]:
        processing_id = str(uuid.uuid4())
        output_path = None
        temp_input_path = None
        temp_signature_path = None
        original_doc_info = None
        try:
            original_doc_info, document_content = await self.get_document(dto.document_id, user_id)
            
            stamp_info, signature_content = await self.get_stamp(dto.stamp_id)
            if not stamp_info:
                raise StampNotFoundException(f"Mẫu dấu {dto.stamp_id} không tìm thấy.")

            processing_info = PDFProcessingInfo(
                id=processing_id,
                document_id=dto.document_id,
                operation_type="sign",
                parameters=dto.dict(exclude={'document_id'})
            )
            await self.processing_repository.save(processing_info)

            fd_input, temp_input_path = tempfile.mkstemp(suffix=".pdf")
            with os.fdopen(fd_input, "wb") as tmp_in:
                tmp_in.write(document_content)
            
            fd_sig, temp_signature_path = tempfile.mkstemp(suffix=".png")
            with os.fdopen(fd_sig, "wb") as tmp_sig:
                tmp_sig.write(signature_content)

            pdf_doc = fitz.open(temp_input_path)
            signature_rect = fitz.Rect(dto.x, dto.y, dto.x + dto.width, dto.y + dto.height)

            pages_to_sign = range(len(pdf_doc)) if dto.page_number is None else [dto.page_number -1] 

            for page_num in pages_to_sign:
                if 0 <= page_num < len(pdf_doc):
                    page = pdf_doc[page_num]
                    page.insert_image(signature_rect, filename=temp_signature_path)
                else:
                    logger.warning(f"Số trang {dto.page_number} không hợp lệ cho tài liệu {dto.document_id}")

            fd_output, output_path = tempfile.mkstemp(suffix="_signed.pdf")
            pdf_doc.save(output_path, garbage=4, deflate=True)
            pdf_doc.close()

            with open(output_path, "rb") as f_signed:
                signed_content = f_signed.read()

            new_doc_filename = f"signed_{original_doc_info.original_filename}"
            new_doc_info = PDFDocumentInfo(
                title=f"Signed - {original_doc_info.title}",
                description=original_doc_info.description,
                original_filename=new_doc_filename,
                page_count=original_doc_info.page_count,
                is_encrypted=original_doc_info.is_encrypted,
                doc_metadata=original_doc_info.doc_metadata.copy(),
                user_id=user_id,
                file_size=len(signed_content)
            )
            saved_signed_doc = await self.document_repository.save(new_doc_info, signed_content, user_id)

            processing_info.status = "completed"
            processing_info.completed_at = datetime.now()
            processing_info.result_document_id = saved_signed_doc.id
            await self.processing_repository.update(processing_info)

            return {
                "message": "Tài liệu đã được ký thành công",
                "new_document_id": saved_signed_doc.id,
                "original_document_id": dto.document_id,
                "processing_id": processing_info.id
            }
        except StampNotFoundException as e:
            logger.warning(f"PDF Sign: {e} (doc: {dto.document_id}, user: {user_id})")
            if processing_id:
                await self._update_processing_error(processing_id, str(e))
                raise
        except Exception as e:
            logger.error(f"Lỗi khi ký PDF (doc: {dto.document_id}, user: {user_id}): {e}", exc_info=True)
            if processing_id:
                await self._update_processing_error(processing_id, str(e))
            raise SignatureException(f"Lỗi khi ký PDF: {str(e)}")
        finally:
            if temp_input_path and os.path.exists(temp_input_path):
                os.unlink(temp_input_path)
            if temp_signature_path and os.path.exists(temp_signature_path):
                os.unlink(temp_signature_path)
            if output_path and os.path.exists(output_path):
                os.unlink(output_path)

    async def merge_pdfs(self, dto: MergePdfDTO, user_id: str) -> Dict[str, Any]:
        merge_id = str(uuid.uuid4())
        output_path = None
        temp_files_paths = []
        try:
            merge_info_repo = MergeInfo(
                id=merge_id,
            document_ids=dto.document_ids,
                output_filename=dto.output_filename,
            )
            await self.merge_repository.save(merge_info_repo)

            writer = PdfWriter()
            merged_page_count = 0
            merged_is_encrypted = False
            first_doc_metadata = {}

            for i, doc_id in enumerate(dto.document_ids):
                doc_info, doc_content = await self.get_document(doc_id, user_id)

                if i == 0:
                    first_doc_metadata = doc_info.doc_metadata.copy()
            
                merged_page_count += doc_info.page_count or 0
                if doc_info.is_encrypted:
                    merged_is_encrypted = True

                fd, temp_path = tempfile.mkstemp(suffix=".pdf")
                temp_files_paths.append(temp_path)
                with os.fdopen(fd, "wb") as tmp_file:
                    tmp_file.write(doc_content)
            
                reader = PdfReader(temp_path)
                for page in reader.pages:
                    writer.add_page(page)
            
            if not writer.pages:
                raise MergeException("Không có trang nào để gộp.")

            fd_output, output_path = tempfile.mkstemp(suffix=".pdf")
            with os.fdopen(fd_output, "wb") as tmp_out:
                writer.write(tmp_out)
            
            with open(output_path, "rb") as f_merged:
                merged_content = f_merged.read()
            
            new_doc_info = PDFDocumentInfo(
                title=dto.output_filename or f"Merged Document - {datetime.now().strftime('%Y%m%d%H%M%S')}",
                description=f"Merged from {len(dto.document_ids)} documents.",
                original_filename=dto.output_filename + ".pdf" if not dto.output_filename.lower().endswith(".pdf") else dto.output_filename,
                page_count=merged_page_count,
                is_encrypted=merged_is_encrypted,
                doc_metadata=first_doc_metadata,
                user_id=user_id,
                file_size=len(merged_content)
            )
            saved_merged_doc = await self.document_repository.save(new_doc_info, merged_content, user_id)

            merge_info_repo.status = "completed"
            merge_info_repo.result_document_id = saved_merged_doc.id
            await self.merge_repository.update(merge_info_repo)

            return {
                "message": "Các tài liệu đã được gộp thành công",
                "new_document_id": saved_merged_doc.id,
                "merge_id": merge_info_repo.id
            }
        except Exception as e:
            logger.error(f"Lỗi khi gộp PDF (user: {user_id}): {e}", exc_info=True)
            if merge_id: 
                try:
                    merge_info_to_update = await self.merge_repository.get(merge_id)
                    if merge_info_to_update:
                        merge_info_to_update.status = "failed"
                        merge_info_to_update.error_message = str(e)
                        await self.merge_repository.update(merge_info_to_update)
                except Exception as e_repo:
                    logger.error(f"Lỗi khi cập nhật trạng thái lỗi cho merge_id {merge_id}: {e_repo}")
            raise MergeException(f"Lỗi khi gộp PDF: {str(e)}")
        finally:
            for p in temp_files_paths:
                if os.path.exists(p):
                    os.unlink(p)
            if output_path and os.path.exists(output_path):
                os.unlink(output_path)

    async def crack_pdf_password(self, dto: CrackPdfDTO, user_id: str) -> Dict[str, Any]:
        processing_id = str(uuid.uuid4())
        original_doc_info = None
        try:
            original_doc_info, document_content = await self.get_document(dto.document_id, user_id)
            if not original_doc_info.is_encrypted:
                raise CrackPasswordException("Tài liệu không được mã hóa.")

            processing_info = PDFProcessingInfo(
                id=processing_id,
                document_id=dto.document_id,
                operation_type="crack_password",
                status="queued",
                parameters=dto.dict(exclude={'document_id'})
            )
            await self.processing_repository.save(processing_info)

            message_body = {
                "processing_id": processing_id,
                "document_id": dto.document_id,
                "user_id": user_id,
                "storage_path": original_doc_info.storage_path,
                "wordlist": dto.wordlist,
                "charset": dto.charset,
                "min_length": dto.min_length,
                "max_length": dto.max_length
            }
            
            await self.rabbitmq_client.publish_message(
                exchange_name=settings.RABBITMQ_EXCHANGE_NAME,
                routing_key=settings.RABBITMQ_PDF_CRACK_ROUTING_KEY,
                message_body=json.dumps(message_body)
            )

            return {
                "message": "Yêu cầu bẻ khóa mật khẩu đã được gửi đi xử lý.",
                "processing_id": processing_id,
                "document_id": dto.document_id
            }
        except DocumentNotFoundException:
            raise
        except CrackPasswordException:
            raise
        except Exception as e:
            logger.error(f"Lỗi khi gửi yêu cầu bẻ khóa PDF (doc: {dto.document_id}, user: {user_id}): {e}", exc_info=True)
            raise CrackPasswordException(f"Lỗi khi gửi yêu cầu bẻ khóa PDF: {str(e)}")

    async def convert_to_word(self, dto: ConvertPdfToWordDTO, user_id: str) -> Dict[str, Any]:
        processing_id = str(uuid.uuid4())
        temp_pdf_path = None
        temp_docx_path = None
        original_doc_info = None
        try:
            original_doc_info, pdf_content = await self.get_document(dto.document_id, user_id)

            processing_info = PDFProcessingInfo(
                id=processing_id,
                document_id=dto.document_id,
                operation_type="convert_to_word",
                parameters=dto.dict(exclude={'document_id'})
            )
            await self.processing_repository.save(processing_info)

            fd_pdf, temp_pdf_path = tempfile.mkstemp(suffix=".pdf")
            with os.fdopen(fd_pdf, "wb") as tmp_pdf:
                tmp_pdf.write(pdf_content)

            fd_docx, temp_docx_path = tempfile.mkstemp(suffix=".docx")
            os.close(fd_docx)

            cv = Converter(temp_pdf_path)
            page_spec = None
            if dto.start_page is not None and dto.end_page is not None:
                page_spec = f"{dto.start_page}-{dto.end_page}"
            elif dto.start_page is not None:
                page_spec = str(dto.start_page)
            
            if page_spec:
                cv.convert(temp_docx_path, start=dto.start_page or 0, end=dto.end_page or None)
            else:
                cv.convert(temp_docx_path)
            cv.close()

            with open(temp_docx_path, "rb") as f_docx:
                docx_content = f_docx.read()
            
            new_doc_filename = f"{os.path.splitext(original_doc_info.original_filename)[0]}.docx"
            
            generic_doc_info = {
                "id": str(uuid.uuid4()),
                "storage_id": str(uuid.uuid4()),
                "document_category": "word",
                "title": f"Word - {original_doc_info.title}",
                "description": f"Converted from PDF {original_doc_info.id}",
                "original_filename": new_doc_filename,
                "file_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "file_size": len(docx_content),
                "doc_metadata": {"source_pdf_id": original_doc_info.id, "conversion_type": "pdf_to_word"},
                "user_id": user_id,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "version": 1
            }
            
            storage_path = f"word/{generic_doc_info['storage_id']}/{new_doc_filename}"
            await self.minio_client.upload_document(
                content=docx_content,
                filename=new_doc_filename,
                object_name_override=storage_path,
                bucket_name="word-documents"
            )
            
            # Save to database using SQLAlchemy
            async with self.document_repository.async_session_factory() as session:
                async with session.begin():
                    # Create DBDocument instance
                    db_document = DBDocument(
                        id=generic_doc_info["id"],
                        storage_id=generic_doc_info["storage_id"],
                        document_category=generic_doc_info["document_category"],
                        title=generic_doc_info["title"],
                        description=generic_doc_info["description"],
                        file_size=generic_doc_info["file_size"],
                        file_type=generic_doc_info["file_type"],
                        storage_path=storage_path,
                        original_filename=new_doc_filename,
                        doc_metadata=json.dumps(generic_doc_info["doc_metadata"]),
                        created_at=generic_doc_info["created_at"],
                        updated_at=generic_doc_info["updated_at"],
                        user_id=generic_doc_info["user_id"],
                        version=generic_doc_info["version"]
                    )
                    
                    session.add(db_document)
                    await session.flush()
                    saved_doc_id = str(db_document.id)

            processing_info.status = "completed"
            processing_info.completed_at = datetime.now()
            processing_info.result_document_id = saved_doc_id
            await self.processing_repository.update(processing_info)

            return {
                "message": "Tài liệu đã được chuyển đổi sang Word thành công",
                "new_document_id": saved_doc_id,
                "original_document_id": dto.document_id,
                "processing_id": processing_info.id,
                "filename": new_doc_filename
                    }
        except Exception as e:
            logger.error(f"Lỗi khi chuyển PDF sang Word (doc: {dto.document_id}, user: {user_id}): {e}", exc_info=True)
            if processing_id:
                await self._update_processing_error(processing_id, str(e))
            raise ConversionException(f"Lỗi khi chuyển đổi PDF sang Word: {str(e)}")
        finally:
            if temp_pdf_path and os.path.exists(temp_pdf_path):
                        os.unlink(temp_pdf_path)
            if temp_docx_path and os.path.exists(temp_docx_path):
                os.unlink(temp_docx_path)

    async def convert_to_images(
        self, dto: ConvertPdfToImageDTO, user_id: str
    ) -> Dict[str, Any]:
        processing_id = str(uuid.uuid4())
        temp_pdf_path = None
        output_zip_path = None
        temp_image_folder = None
        original_doc_info = None
        try:
            original_doc_info, pdf_content = await self.get_document(dto.document_id, user_id)

            processing_info = PDFProcessingInfo(
                id=processing_id,
                document_id=dto.document_id,
                operation_type="convert_to_images",
                parameters=dto.dict(exclude={'document_id'})
            )
            await self.processing_repository.save(processing_info)

            fd_pdf, temp_pdf_path = tempfile.mkstemp(suffix=".pdf")
            with os.fdopen(fd_pdf, "wb") as tmp_pdf:
                tmp_pdf.write(pdf_content)

            pdf_fitz_doc = fitz.open(temp_pdf_path)
            image_ids = []
            
            temp_image_folder = tempfile.mkdtemp(prefix="pdf_images_")

            pages_to_convert = range(len(pdf_fitz_doc))
            if dto.page_numbers:
                pages_to_convert = [p - 1 for p in dto.page_numbers if 0 <= p - 1 < len(pdf_fitz_doc)]
            
            output_image_paths = []

            for page_num in pages_to_convert:
                page = pdf_fitz_doc.load_page(page_num)
                pix = page.get_pixmap(dpi=dto.dpi or 150)
                image_bytes = pix.tobytes("png")
            
                image_filename = f"{os.path.splitext(original_doc_info.original_filename)[0]}_page_{page_num + 1}.png"
            
                png_doc_info_dto = CreatePngDocumentDTO(
                    title=f"Page {page_num + 1} - {original_doc_info.title}",
                    original_filename=image_filename,
                    doc_metadata={"source_pdf_id": original_doc_info.id, "page_number": page_num + 1}
                )
                saved_png_doc = await self.create_png_document(png_doc_info_dto, image_bytes, user_id)
                image_ids.append(saved_png_doc.id)
                output_image_paths.append(saved_png_doc.storage_path)
            
            pdf_fitz_doc.close()

            result_payload = {
                "message": "Các trang PDF đã được chuyển đổi thành hình ảnh thành công.",
                "image_document_ids": image_ids,
                "original_document_id": dto.document_id,
                "processing_id": processing_id
            }

            if dto.output_format and dto.output_format.lower() == "zip" and image_ids:
                fd_zip, output_zip_path = tempfile.mkstemp(suffix=".zip")
                with zipfile.ZipFile(os.fdopen(fd_zip, "w+b"), "w") as zf:
                    for img_id in image_ids:
                        png_info, png_content = await self.get_png_document(img_id, user_id)
                        if png_info and png_content:
                            zf.writestr(png_info.original_filename, png_content)
            
                with open(output_zip_path, "rb") as f_zip:
                    zip_content = f_zip.read()
            
                zip_filename = f"images_{os.path.splitext(original_doc_info.original_filename)[0]}.zip"
                
                generic_zip_info = {
                    "id": str(uuid.uuid4()),
                    "storage_id": str(uuid.uuid4()),
                    "document_category": "files", 
                    "title": f"Images ZIP - {original_doc_info.title}",
                    "description": f"ZIP archive of PDF pages converted to images",
                    "original_filename": zip_filename,
                    "file_type": "application/zip",
                    "file_size": len(zip_content),
                    "doc_metadata": {"source_pdf_id": original_doc_info.id, "contained_image_ids": image_ids, "conversion_type": "pdf_to_images_zip"},
                    "user_id": user_id,
                    "created_at": datetime.now(),
                    "updated_at": datetime.now(),
                    "source_service": "pdf"
                }
                
                zip_storage_path = f"files/{generic_zip_info['storage_id']}/{zip_filename}"
                await self.minio_client.upload_document(
                    content=zip_content,
                    filename=zip_filename,
                    object_name_override=zip_storage_path,
                    bucket_name=settings.MINIO_FILES_BUCKET
                )
                
                # Save ZIP document to database using SQLAlchemy
                async with self.document_repository.async_session_factory() as session:
                    async with session.begin():
                        db_document = DBDocument(
                            id=generic_zip_info["id"],
                            storage_id=generic_zip_info["storage_id"],
                            document_category=generic_zip_info["document_category"],
                            title=generic_zip_info["title"],
                            description=generic_zip_info["description"],
                            file_size=generic_zip_info["file_size"],
                            file_type=generic_zip_info["file_type"],
                            storage_path=zip_storage_path,
                            original_filename=zip_filename,
                            doc_metadata=json.dumps(generic_zip_info["doc_metadata"]),
                            created_at=generic_zip_info["created_at"],
                            updated_at=generic_zip_info["updated_at"],
                            user_id=generic_zip_info["user_id"],
                            source_service=generic_zip_info["source_service"]
                        )
                        
                        session.add(db_document)
                        await session.flush()
                        saved_zip_doc_id = str(db_document.id)
                
                result_payload["zip_document_id"] = saved_zip_doc_id
                result_payload["message"] = "Các trang PDF đã được chuyển đổi thành hình ảnh và nén vào file ZIP."

            processing_info.status = "completed"
            processing_info.completed_at = datetime.now()
            if dto.output_format and dto.output_format.lower() == "zip" and result_payload.get("zip_document_id"):
                processing_info.result_document_id = result_payload["zip_document_id"]
            elif image_ids:
                pass 

            await self.processing_repository.update(processing_info)
            return result_payload

        except Exception as e:
            logger.error(f"Lỗi khi chuyển PDF sang ảnh (doc: {dto.document_id}, user: {user_id}): {e}", exc_info=True)
            if processing_id:
                await self._update_processing_error(processing_id, str(e))
            raise ConversionException(f"Lỗi khi chuyển đổi PDF sang hình ảnh: {str(e)}")
        finally:
            if temp_pdf_path and os.path.exists(temp_pdf_path):
                        os.unlink(temp_pdf_path)
            if temp_image_folder and os.path.exists(temp_image_folder):
                shutil.rmtree(temp_image_folder, ignore_errors=True)
            if output_zip_path and os.path.exists(output_zip_path):
                os.unlink(output_zip_path)

    async def get_processing_status(self, processing_id: str) -> Dict[str, Any]:
        try:
            processing_info = await self.processing_repository.get(processing_id)
            if not processing_info:
                raise DocumentNotFoundException(f"Không tìm thấy thông tin xử lý với ID: {processing_id}")
            
            response = processing_info.dict()
            if processing_info.status == "completed" and processing_info.result_document_id:
                pass

            return response
        except DocumentNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Lỗi khi lấy trạng thái xử lý (id: {processing_id}): {e}", exc_info=True)
            raise StorageException(f"Lỗi khi lấy trạng thái xử lý {processing_id}")

    async def get_merge_status(self, merge_id: str) -> Dict[str, Any]:
        try:
            merge_info = await self.merge_repository.get(merge_id)
            if not merge_info:
                raise DocumentNotFoundException(f"Không tìm thấy thông tin gộp với ID: {merge_id}")
            return merge_info.dict()
        except DocumentNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Lỗi khi lấy trạng thái gộp (id: {merge_id}): {e}", exc_info=True)
            raise StorageException(f"Lỗi khi lấy trạng thái gộp {merge_id}")

    async def create_stamp(self, dto: CreateStampDTO, content: bytes) -> StampInfo:
        temp_file_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
                temp_file.write(content)
                temp_file_path = temp_file.name

            img = Image.open(temp_file_path)
            width, height = img.size
            img.close()

            stamp_info = StampInfo(
                name=dto.name,
                text=dto.text,
                color=dto.color,
                font_size=dto.font_size,
                shape=dto.shape,
                width=width,
                height=height,
                storage_path="",
                doc_metadata=dto.doc_metadata or {}
            )
            saved_stamp_info = await self.stamp_repository.save(stamp_info, content)
            return saved_stamp_info
        except Exception as e:
            logger.error(f"Lỗi khi tạo mẫu dấu (name: {dto.name}): {e}", exc_info=True)
            raise StorageException(f"Lỗi khi tạo mẫu dấu: {str(e)}")
        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    async def get_stamps(self, skip: int = 0, limit: int = 10) -> List[StampInfo]:
        try:
            return await self.stamp_repository.list(skip, limit)
        except Exception as e:
            logger.error(f"Lỗi khi lấy danh sách mẫu dấu: {e}", exc_info=True)
            raise StorageException(f"Lỗi khi lấy danh sách mẫu dấu: {str(e)}")

    async def get_stamp(self, stamp_id: str) -> Tuple[StampInfo, bytes]:
        try:
            stamp_info, content = await self.stamp_repository.get(stamp_id)
            if not stamp_info or content is None:
                raise StampNotFoundException(stamp_id)
            return stamp_info, content
        except StampNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Lỗi khi lấy mẫu dấu (id: {stamp_id}): {e}", exc_info=True)
            raise StorageException(f"Lỗi khi lấy mẫu dấu {stamp_id}: {str(e)}")

    async def delete_stamp(self, stamp_id: str) -> None:
        try:
            doc_info, _ = await self.stamp_repository.get(stamp_id)
            if not doc_info:
                raise StampNotFoundException(stamp_id)
            await self.stamp_repository.delete(stamp_id)
        except StampNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Lỗi khi xóa mẫu dấu (id: {stamp_id}): {e}", exc_info=True)
            raise StorageException(f"Lỗi khi xóa mẫu dấu {stamp_id}: {str(e)}")
