import os
import io
import tempfile
import asyncio
import uuid
import json
import zipfile
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from application.dto import (
    CreatePdfDocumentDTO, CreatePngDocumentDTO, CreateStampDTO,
    EncryptPdfDTO, DecryptPdfDTO, WatermarkPdfDTO, SignPdfDTO, MergePdfDTO,
    CrackPdfDTO, ConvertPdfToWordDTO, ConvertPdfToImageDTO
)
from domain.models import PDFDocumentInfo, PNGDocumentInfo, StampInfo, PDFProcessingInfo, MergeInfo
from domain.exceptions import (
    DocumentNotFoundException, StorageException, ConversionException,
    EncryptionException, DecryptionException, WatermarkException,
    SignatureException, MergeException, StampNotFoundException,
    PDFPasswordProtectedException, WrongPasswordException, CrackPasswordException
)
from infrastructure.repository import (
    PDFDocumentRepository, PNGDocumentRepository, StampRepository,
    PDFProcessingRepository, MergeRepository
)
from infrastructure.minio_client import MinioClient
from infrastructure.rabbitmq_client import RabbitMQClient
from core.config import settings

from PyPDF2 import PdfReader, PdfWriter
import fitz  
from PIL import Image
from pdf2docx import Converter


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
            rabbitmq_client: RabbitMQClient
    ):
        """
        Khởi tạo service.

        Args:
            document_repository: Repository để làm việc với tài liệu PDF
            image_repository: Repository để làm việc với tài liệu PNG
            stamp_repository: Repository để làm việc với mẫu dấu
            minio_client: Client MinIO để lưu trữ tài liệu
            rabbitmq_client: Client RabbitMQ để gửi tin nhắn
        """
        self.document_repository = document_repository
        self.image_repository = image_repository
        self.stamp_repository = stamp_repository
        self.minio_client = minio_client
        self.rabbitmq_client = rabbitmq_client
        self.processing_repository = PDFProcessingRepository()
        self.merge_repository = MergeRepository()

    async def create_document(self, dto: CreatePdfDocumentDTO, content: bytes) -> PDFDocumentInfo:
        """
        Tạo tài liệu PDF mới.

        Args:
            dto: DTO chứa thông tin tài liệu
            content: Nội dung tài liệu

        Returns:
            Thông tin tài liệu đã tạo
        """
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                temp_file.write(content)
                temp_file_path = temp_file.name

            try:
                pdf_reader = PdfReader(temp_file_path)
                page_count = len(pdf_reader.pages)
                is_encrypted = pdf_reader.is_encrypted

                document_info = PDFDocumentInfo(
                    title=dto.title,
                    description=dto.description,
                    original_filename=dto.original_filename,
                    file_size=len(content),
                    page_count=page_count,
                    is_encrypted=is_encrypted,
                    storage_path="",  
                    metadata=dto.metadata
                )

                document_info = await self.document_repository.save(document_info, content)

                os.unlink(temp_file_path)

                return document_info
            except Exception as e:
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                raise
        except Exception as e:
            raise StorageException(f"Lỗi khi tạo tài liệu PDF: {str(e)}")

    async def create_png_document(self, dto: CreatePngDocumentDTO, content: bytes) -> PNGDocumentInfo:
        """
        Tạo tài liệu PNG mới.

        Args:
            dto: DTO chứa thông tin tài liệu
            content: Nội dung tài liệu

        Returns:
            Thông tin tài liệu đã tạo
        """
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
                temp_file.write(content)
                temp_file_path = temp_file.name

            try:
                img = Image.open(temp_file_path)
                width, height = img.size

                document_info = PNGDocumentInfo(
                    title=dto.title,
                    description=dto.description,
                    original_filename=dto.original_filename,
                    file_size=len(content),
                    width=width,
                    height=height,
                    storage_path="",  
                    metadata=dto.metadata
                )

                document_info = await self.image_repository.save(document_info, content)

                os.unlink(temp_file_path)

                return document_info
            except Exception as e:
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                raise
        except Exception as e:
            raise StorageException(f"Lỗi khi tạo tài liệu PNG: {str(e)}")

    async def create_stamp(self, dto: CreateStampDTO, content: bytes) -> StampInfo:
        """
        Tạo mẫu dấu mới.

        Args:
            dto: DTO chứa thông tin mẫu dấu
            content: Nội dung mẫu dấu

        Returns:
            Thông tin mẫu dấu đã tạo
        """
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
                temp_file.write(content)
                temp_file_path = temp_file.name

            try:
                img = Image.open(temp_file_path)
                width, height = img.size

                stamp_info = StampInfo(
                    name=dto.name,
                    description=dto.description,
                    original_filename=dto.original_filename,
                    file_size=len(content),
                    width=width,
                    height=height,
                    storage_path="",  
                    metadata=dto.metadata
                )

                stamp_info = await self.stamp_repository.save(stamp_info, content)

                os.unlink(temp_file_path)

                return stamp_info
            except Exception as e:
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                raise
        except Exception as e:
            raise StorageException(f"Lỗi khi tạo mẫu dấu: {str(e)}")

    async def encrypt_pdf(self, dto: EncryptPdfDTO) -> Dict[str, Any]:
        """
        Mã hóa tài liệu PDF.

        Args:
            dto: DTO chứa thông tin mã hóa

        Returns:
            Dict chứa thông tin tài liệu đã mã hóa
        """
        try:
            document_info, document_content = await self.document_repository.get(dto.document_id)

            processing_info = PDFProcessingInfo(
                document_id=dto.document_id,
                operation_type="encrypt"
            )
            await self.processing_repository.save(processing_info)

            try:
                reader = PdfReader(io.BytesIO(document_content))

                if reader.is_encrypted:
                    raise EncryptionException("PDF đã được mã hóa")

                writer = PdfWriter()

                for page in reader.pages:
                    writer.add_page(page)

                if dto.permissions:
                    writer.encrypt(
                        user_password=dto.password,
                        owner_password=None,
                        use_128bit=True,
                        permissions_flag=self._get_permissions_flag(dto.permissions)
                    )
                else:
                    writer.encrypt(dto.password)

                buffer = io.BytesIO()
                writer.write(buffer)
                buffer.seek(0)
                encrypted_content = buffer.read()

                encrypted_filename = f"{os.path.splitext(document_info.original_filename)[0]}_encrypted.pdf"
                new_document_info = PDFDocumentInfo(
                    title=f"{document_info.title} (Encrypted)",
                    description=f"Phiên bản được mã hóa của {document_info.title}",
                    original_filename=encrypted_filename,
                    file_size=len(encrypted_content),
                    page_count=document_info.page_count,
                    is_encrypted=True,
                    storage_path="",  
                    metadata={
                        "original_document_id": dto.document_id,
                        "encrypted": True,
                        "encryption_date": datetime.now().isoformat()
                    }
                )

                new_document_info = await self.document_repository.save(new_document_info, encrypted_content)

                processing_info.status = "completed"
                processing_info.completed_at = datetime.now()
                processing_info.result_document_id = new_document_info.id
                await self.processing_repository.update(processing_info)

                return {
                    "id": new_document_info.id,
                    "filename": new_document_info.original_filename,
                    "file_size": new_document_info.file_size,
                    "is_encrypted": True
                }
            except Exception as e:
                processing_info.status = "failed"
                processing_info.error_message = str(e)
                await self.processing_repository.update(processing_info)
                raise EncryptionException(str(e))
        except DocumentNotFoundException:
            raise
        except Exception as e:
            raise EncryptionException(str(e))

    def _get_permissions_flag(self, permissions: Dict[str, bool]) -> int:
        """
        Chuyển đổi từ dict permissions sang flag.

        Args:
            permissions: Dict chứa các quyền

        Returns:
            Flag permissions
        """
        flag = 0

        if permissions.get("print", True):
            flag |= (1 << 2)  
        if permissions.get("modify", True):
            flag |= (1 << 3)  
        if permissions.get("copy", True):
            flag |= (1 << 4)  
        if permissions.get("annotate", True):
            flag |= (1 << 5)  

        return flag

    async def decrypt_pdf(self, dto: DecryptPdfDTO) -> Dict[str, Any]:
        """
        Giải mã tài liệu PDF.

        Args:
            dto: DTO chứa thông tin giải mã

        Returns:
            Dict chứa thông tin tài liệu đã giải mã
        """
        try:
            document_info, document_content = await self.document_repository.get(dto.document_id)

            processing_info = PDFProcessingInfo(
                document_id=dto.document_id,
                operation_type="decrypt"
            )
            await self.processing_repository.save(processing_info)

            try:
                reader = PdfReader(io.BytesIO(document_content))

                if not reader.is_encrypted:
                    raise DecryptionException("PDF không được mã hóa")

                try:
                    success = reader.decrypt(dto.password)
                    if not success:
                        raise WrongPasswordException()
                except:
                    raise WrongPasswordException()

                writer = PdfWriter()

                for page in reader.pages:
                    writer.add_page(page)

                buffer = io.BytesIO()
                writer.write(buffer)
                buffer.seek(0)
                decrypted_content = buffer.read()

                decrypted_filename = f"{os.path.splitext(document_info.original_filename)[0]}_decrypted.pdf"
                new_document_info = PDFDocumentInfo(
                    title=f"{document_info.title} (Decrypted)",
                    description=f"Phiên bản được giải mã của {document_info.title}",
                    original_filename=decrypted_filename,
                    file_size=len(decrypted_content),
                    page_count=document_info.page_count,
                    is_encrypted=False,
                    storage_path="",  
                    metadata={
                        "original_document_id": dto.document_id,
                        "decrypted": True,
                        "decryption_date": datetime.now().isoformat()
                    }
                )

                new_document_info = await self.document_repository.save(new_document_info, decrypted_content)

                processing_info.status = "completed"
                processing_info.completed_at = datetime.now()
                processing_info.result_document_id = new_document_info.id
                await self.processing_repository.update(processing_info)

                return {
                    "id": new_document_info.id,
                    "filename": new_document_info.original_filename,
                    "file_size": new_document_info.file_size,
                    "is_encrypted": False
                }
            except WrongPasswordException:
                processing_info.status = "failed"
                processing_info.error_message = "Mật khẩu không đúng"
                await self.processing_repository.update(processing_info)
                raise
            except Exception as e:
                processing_info.status = "failed"
                processing_info.error_message = str(e)
                await self.processing_repository.update(processing_info)
                raise DecryptionException(str(e))
        except DocumentNotFoundException:
            raise
        except Exception as e:
            raise DecryptionException(str(e))

    async def add_watermark(self, dto: WatermarkPdfDTO) -> Dict[str, Any]:
        """
        Thêm watermark vào tài liệu PDF.

        Args:
            dto: DTO chứa thông tin watermark

        Returns:
            Dict chứa thông tin tài liệu đã thêm watermark
        """
        try:
            document_info, document_content = await self.document_repository.get(dto.document_id)

            processing_info = PDFProcessingInfo(
                document_id=dto.document_id,
                operation_type="watermark",
                parameters={
                    "watermark_text": dto.watermark_text,
                    "position": dto.position,
                    "opacity": dto.opacity,
                    "color": dto.color,
                    "font_size": dto.font_size
                }
            )
            await self.processing_repository.save(processing_info)

            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
                    temp_pdf.write(document_content)
                    temp_pdf_path = temp_pdf.name

                watermark_filename = f"{os.path.splitext(document_info.original_filename)[0]}_watermark.pdf"
                output_path = os.path.join(settings.TEMP_DIR, watermark_filename)

                try:
                    pdf_doc = fitz.open(temp_pdf_path)

                    for page in pdf_doc:
                        rect = page.rect

                        if dto.position == "center":
                            x, y = rect.width / 2, rect.height / 2
                        elif dto.position == "top-left":
                            x, y = 50, 50
                        elif dto.position == "top-right":
                            x, y = rect.width - 50, 50
                        elif dto.position == "bottom-left":
                            x, y = 50, rect.height - 50
                        elif dto.position == "bottom-right":
                            x, y = rect.width - 50, rect.height - 50
                        else:
                            x, y = rect.width / 2, rect.height / 2

                        font_size = dto.font_size or 40
                        opacity = dto.opacity
                        color = dto.color or  "#808080"

                        r, g, b = tuple(int(color[1:][i:i+2], 16) / 255 for i in (0, 2, 4))

                        txt = fitz.Text()
                        txt.append((x, y), dto.watermark_text, fontsize=font_size, color=(r, g, b))

                        page.insert_text(rect.width / 2, rect.height / 2, dto.watermark_text,
                                fontsize=font_size, color=(r, g, b, opacity), rotate=45)

                    pdf_doc.save(output_path)
                    pdf_doc.close()

                    with open(output_path, "rb") as f:
                        watermarked_content = f.read()

                    os.unlink(temp_pdf_path)
                    os.unlink(output_path)

                    new_document_info = PDFDocumentInfo(
                        title=f"{document_info.title} (Watermark)",
                        description=f"Phiên bản có watermark của {document_info.title}",
                        original_filename=watermark_filename,
                        file_size=len(watermarked_content),
                        page_count=document_info.page_count,
                        is_encrypted=document_info.is_encrypted,
                        storage_path="",  
                        metadata={
                            "original_document_id": dto.document_id,
                            "watermark": True,
                            "watermark_text": dto.watermark_text,
                            "watermark_date": datetime.now().isoformat()
                        }
                    )

                    new_document_info = await self.document_repository.save(new_document_info, watermarked_content)

                    processing_info.status = "completed"
                    processing_info.completed_at = datetime.now()
                    processing_info.result_document_id = new_document_info.id
                    await self.processing_repository.update(processing_info)

                    return {
                        "id": new_document_info.id,
                        "filename": new_document_info.original_filename,
                        "file_size": new_document_info.file_size
                    }
                except Exception as e:
                    if os.path.exists(temp_pdf_path):
                        os.unlink(temp_pdf_path)
                    if os.path.exists(output_path):
                        os.unlink(output_path)
                    raise WatermarkException(f"Lỗi khi thêm watermark: {str(e)}")
            except Exception as e:
                processing_info.status = "failed"
                processing_info.error_message = str(e)
                await self.processing_repository.update(processing_info)
                raise WatermarkException(str(e))
        except DocumentNotFoundException:
            raise
        except Exception as e:
            raise WatermarkException(str(e))

    async def add_signature(self, dto: SignPdfDTO) -> Dict[str, Any]:
        """
        Thêm chữ ký vào tài liệu PDF.

        Args:
            dto: DTO chứa thông tin chữ ký

        Returns:
            Dict chứa thông tin tài liệu đã thêm chữ ký
        """
        try:
            document_info, document_content = await self.document_repository.get(dto.document_id)

            processing_info = PDFProcessingInfo(
                document_id=dto.document_id,
                operation_type="sign",
                parameters={
                    "stamp_id": dto.stamp_id,
                    "signature_position": dto.signature_position,
                    "page_number": dto.page_number,
                    "scale": dto.scale
                }
            )
            await self.processing_repository.save(processing_info)

            try:
                stamp_content = None
                if dto.stamp_id:
                    stamp_info, stamp_content = await self.stamp_repository.get(dto.stamp_id)
                else:
                    stamp_path = os.path.join(settings.TEMPLATES_DIR, "default_stamp.png")
                    if os.path.exists(stamp_path):
                        with open(stamp_path, "rb") as f:
                            stamp_content = f.read()
                    else:
                        raise SignatureException("Không tìm thấy mẫu dấu mặc định")

                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
                    temp_pdf.write(document_content)
                    temp_pdf_path = temp_pdf.name

                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_stamp:
                    temp_stamp.write(stamp_content)
                    temp_stamp_path = temp_stamp.name

                signed_filename = f"{os.path.splitext(document_info.original_filename)[0]}_signed.pdf"
                output_path = os.path.join(settings.TEMP_DIR, signed_filename)

                try:
                    pdf_doc = fitz.open(temp_pdf_path)

                    img = Image.open(temp_stamp_path)
                    width, height = img.size

                    page_idx = dto.page_number
                    if page_idx < 0 or page_idx >= len(pdf_doc):
                        page_idx = len(pdf_doc) - 1  

                    page = pdf_doc[page_idx]
                    rect = page.rect

                    stamp_width = width * dto.scale
                    stamp_height = height * dto.scale

                    if dto.signature_position == "bottom-right":
                        x = rect.width - stamp_width - 30
                        y = rect.height - stamp_height - 30
                    elif dto.signature_position == "bottom-left":
                        x = 30
                        y = rect.height - stamp_height - 30
                    elif dto.signature_position == "top-right":
                        x = rect.width - stamp_width - 30
                        y = 30
                    elif dto.signature_position == "top-left":
                        x = 30
                        y = 30
                    elif dto.signature_position == "custom" and dto.custom_x is not None and dto.custom_y is not None:
                        x = dto.custom_x
                        y = dto.custom_y
                    else:
                        x = rect.width - stamp_width - 30
                        y = rect.height - stamp_height - 30

                    page.insert_image(fitz.Rect(x, y, x + stamp_width, y + stamp_height), filename=temp_stamp_path)

                    pdf_doc.save(output_path)
                    pdf_doc.close()

                    with open(output_path, "rb") as f:
                        signed_content = f.read()

                    os.unlink(temp_pdf_path)
                    os.unlink(temp_stamp_path)
                    os.unlink(output_path)

                    new_document_info = PDFDocumentInfo(
                        title=f"{document_info.title} (Signed)",
                        description=f"Phiên bản có chữ ký của {document_info.title}",
                        original_filename=signed_filename,
                        file_size=len(signed_content),
                        page_count=document_info.page_count,
                        is_encrypted=document_info.is_encrypted,
                        storage_path="",  
                        metadata={
                            "original_document_id": dto.document_id,
                            "signed": True,
                            "stamp_id": dto.stamp_id,
                            "signing_date": datetime.now().isoformat()
                        }
                    )

                    new_document_info = await self.document_repository.save(new_document_info, signed_content)

                    processing_info.status = "completed"
                    processing_info.completed_at = datetime.now()
                    processing_info.result_document_id = new_document_info.id
                    await self.processing_repository.update(processing_info)

                    return {
                        "id": new_document_info.id,
                        "filename": new_document_info.original_filename,
                        "file_size": new_document_info.file_size
                    }
                except Exception as e:
                    if os.path.exists(temp_pdf_path):
                        os.unlink(temp_pdf_path)
                    if os.path.exists(temp_stamp_path):
                        os.unlink(temp_stamp_path)
                    if os.path.exists(output_path):
                        os.unlink(output_path)
                    raise SignatureException(f"Lỗi khi thêm chữ ký: {str(e)}")
            except StampNotFoundException:
                processing_info.status = "failed"
                processing_info.error_message = f"Không tìm thấy mẫu dấu với ID: {dto.stamp_id}"
                await self.processing_repository.update(processing_info)
                raise
            except Exception as e:
                processing_info.status = "failed"
                processing_info.error_message = str(e)
                await self.processing_repository.update(processing_info)
                raise SignatureException(str(e))
        except DocumentNotFoundException:
            raise
        except Exception as e:
            raise SignatureException(str(e))

    async def merge_pdfs(self, dto: MergePdfDTO) -> Dict[str, Any]:
        """
        Gộp nhiều tài liệu PDF thành một.

        Args:
            dto: DTO chứa thông tin gộp tài liệu

        Returns:
            Dict chứa thông tin tài liệu đã gộp
        """
        merge_info = MergeInfo(
            id=str(uuid.uuid4()),
            document_ids=dto.document_ids,
            output_filename=dto.output_filename
        )

        await self.merge_repository.save(merge_info)

        try:
            merger = PdfWriter()

            for doc_id in dto.document_ids:
                try:
                    document_info, content = await self.document_repository.get(doc_id)

                    reader = PdfReader(io.BytesIO(content))
                    if reader.is_encrypted:
                        merge_info.status = "failed"
                        merge_info.error_message = f"Tài liệu {document_info.title} được mã hóa. Vui lòng giải mã trước khi gộp."
                        await self.merge_repository.update(merge_info)
                        raise MergeException(f"Tài liệu {document_info.title} được mã hóa. Vui lòng giải mã trước khi gộp.")

                    for page in reader.pages:
                        merger.add_page(page)
                except DocumentNotFoundException:
                    merge_info.status = "failed"
                    merge_info.error_message = f"Không tìm thấy tài liệu với ID: {doc_id}"
                    await self.merge_repository.update(merge_info)
                    raise

            buffer = io.BytesIO()
            merger.write(buffer)
            buffer.seek(0)
            merged_content = buffer.read()

            new_document_info = PDFDocumentInfo(
                title=os.path.splitext(dto.output_filename)[0],
                description=f"Tài liệu được gộp từ {len(dto.document_ids)} file PDF",
                original_filename=dto.output_filename,
                file_size=len(merged_content),
                page_count=len(merger.pages),
                is_encrypted=False,
                storage_path="",  
                metadata={
                    "merged": True,
                    "merged_from": dto.document_ids,
                    "merge_date": datetime.now().isoformat()
                }
            )

            new_document_info = await self.document_repository.save(new_document_info, merged_content)

            merge_info.status = "completed"
            merge_info.result_document_id = new_document_info.id
            await self.merge_repository.update(merge_info)

            return {
                "id": new_document_info.id,
                "filename": new_document_info.original_filename,
                "file_size": new_document_info.file_size,
                "page_count": new_document_info.page_count
            }
        except Exception as e:
            merge_info.status = "failed"
            merge_info.error_message = str(e)
            await self.merge_repository.update(merge_info)
            raise MergeException(str(e))

    async def crack_pdf_password(self, dto: CrackPdfDTO) -> Dict[str, Any]:
        """
        Thử crack mật khẩu PDF.

        Args:
            dto: DTO chứa thông tin crack mật khẩu

        Returns:
            Dict chứa thông tin tài liệu đã crack
        """
        try:
            document_info, document_content = await self.document_repository.get(dto.document_id)

            processing_info = PDFProcessingInfo(
                document_id=dto.document_id,
                operation_type="crack_password",
                parameters={
                    "max_length": dto.max_length
                }
            )
            await self.processing_repository.save(processing_info)

            try:
                reader = PdfReader(io.BytesIO(document_content))

                if not reader.is_encrypted:
                    processing_info.status = "failed"
                    processing_info.error_message = "PDF không được mã hóa"
                    await self.processing_repository.update(processing_info)
                    raise CrackPasswordException("PDF không được mã hóa")

                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
                    temp_pdf.write(document_content)
                    temp_pdf_path = temp_pdf.name

                found_password = None
                for i in range(10 ** dto.max_length):
                    password = str(i).zfill(dto.max_length)

                    try:
                        reader = PdfReader(temp_pdf_path)
                        if reader.decrypt(password) > 0:  
                            found_password = password
                            break
                    except:
                        pass

                os.unlink(temp_pdf_path)

                if found_password:
                    reader = PdfReader(io.BytesIO(document_content))
                    reader.decrypt(found_password)

                    writer = PdfWriter()
                    for page in reader.pages:
                        writer.add_page(page)

                    buffer = io.BytesIO()
                    writer.write(buffer)
                    buffer.seek(0)
                    decrypted_content = buffer.read()

                    decrypted_filename = f"{os.path.splitext(document_info.original_filename)[0]}_cracked.pdf"
                    new_document_info = PDFDocumentInfo(
                        title=f"{document_info.title} (Cracked)",
                        description=f"Phiên bản đã crack mật khẩu của {document_info.title}",
                        original_filename=decrypted_filename,
                        file_size=len(decrypted_content),
                        page_count=document_info.page_count,
                        is_encrypted=False,
                        storage_path="",  
                        metadata={
                            "original_document_id": dto.document_id,
                            "cracked": True,
                            "cracked_password": found_password,
                            "crack_date": datetime.now().isoformat()
                        }
                    )

                    new_document_info = await self.document_repository.save(new_document_info, decrypted_content)

                    processing_info.status = "completed"
                    processing_info.completed_at = datetime.now()
                    processing_info.result_document_id = new_document_info.id
                    await self.processing_repository.update(processing_info)

                    return {
                        "id": new_document_info.id,
                        "filename": new_document_info.original_filename,
                        "file_size": new_document_info.file_size,
                        "found_password": found_password
                    }
                else:
                    processing_info.status = "failed"
                    processing_info.error_message = "Không tìm thấy mật khẩu"
                    await self.processing_repository.update(processing_info)
                    raise CrackPasswordException("Không tìm thấy mật khẩu trong khoảng thử")
            except CrackPasswordException:
                raise
            except Exception as e:
                processing_info.status = "failed"
                processing_info.error_message = str(e)
                await self.processing_repository.update(processing_info)
                raise CrackPasswordException(str(e))
        except DocumentNotFoundException:
            raise
        except Exception as e:
            raise CrackPasswordException(str(e))

    async def convert_to_word(self, dto: ConvertPdfToWordDTO) -> Dict[str, Any]:
        """
        Chuyển đổi tài liệu PDF sang Word.

        Args:
            dto: DTO chứa thông tin chuyển đổi

        Returns:
            Dict chứa thông tin tài liệu đã chuyển đổi
        """
        try:
            document_info, document_content = await self.document_repository.get(dto.document_id)

            processing_info = PDFProcessingInfo(
                document_id=dto.document_id,
                operation_type="convert_to_word",
                parameters={
                    "output_format": dto.output_format
                }
            )
            await self.processing_repository.save(processing_info)

            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
                    temp_pdf.write(document_content)
                    temp_pdf_path = temp_pdf.name

                output_ext = ".docx" if dto.output_format.lower() == "docx" else ".doc"
                output_filename = f"{os.path.splitext(document_info.original_filename)[0]}{output_ext}"
                output_path = os.path.join(settings.TEMP_DIR, output_filename)

                try:
                    cv = Converter(temp_pdf_path)
                    cv.convert(output_path)
                    cv.close()

                    with open(output_path, "rb") as f:
                        word_content = f.read()

                    os.unlink(temp_pdf_path)
                    os.unlink(output_path)

                    new_document_info = PDFDocumentInfo(
                        title=f"{document_info.title} (Word)",
                        description=f"Phiên bản Word của {document_info.title}",
                        original_filename=output_filename,
                        file_size=len(word_content),
                        page_count=document_info.page_count,
                        is_encrypted=False,
                        storage_path="",  
                        metadata={
                            "original_document_id": dto.document_id,
                            "converted_to_word": True,
                            "conversion_date": datetime.now().isoformat()
                        }
                    )

                    new_document_info = await self.document_repository.save(new_document_info, word_content)

                    processing_info.status = "completed"
                    processing_info.completed_at = datetime.now()
                    processing_info.result_document_id = new_document_info.id
                    await self.processing_repository.update(processing_info)

                    return {
                        "id": new_document_info.id,
                        "filename": new_document_info.original_filename,
                        "file_size": new_document_info.file_size
                    }
                except Exception as e:
                    if os.path.exists(temp_pdf_path):
                        os.unlink(temp_pdf_path)
                    if os.path.exists(output_path):
                        os.unlink(output_path)
                    raise ConversionException(f"Lỗi khi chuyển đổi: {str(e)}")
            except Exception as e:
                processing_info.status = "failed"
                processing_info.error_message = str(e)
                await self.processing_repository.update(processing_info)
                raise ConversionException(str(e))
        except DocumentNotFoundException:
            raise
        except Exception as e:
            raise ConversionException(str(e))

    async def convert_to_images(self, dto: ConvertPdfToImageDTO) -> Dict[str, Any]:
        """
        Chuyển đổi tài liệu PDF sang hình ảnh.

        Args:
            dto: DTO chứa thông tin chuyển đổi

        Returns:
            Dict chứa thông tin tài liệu đã chuyển đổi
        """
        try:
            document_info, document_content = await self.document_repository.get(dto.document_id)

            processing_info = PDFProcessingInfo(
                document_id=dto.document_id,
                operation_type="convert_to_images",
                parameters={
                    "output_format": dto.output_format,
                    "dpi": dto.dpi,
                    "page_numbers": dto.page_numbers
                }
            )
            await self.processing_repository.save(processing_info)

            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
                    temp_pdf.write(document_content)
                    temp_pdf_path = temp_pdf.name

                temp_dir = tempfile.mkdtemp()

                try:
                    doc = fitz.open(temp_pdf_path)

                    if dto.page_numbers:
                        page_indices = [idx for idx in dto.page_numbers if 0 <= idx < len(doc)]
                    else:
                        page_indices = range(len(doc))

                    image_paths = []
                    image_files = []

                    for page_idx in page_indices:
                        page = doc.load_page(page_idx)

                        pix = page.get_pixmap(dpi=dto.dpi)

                        image_filename = f"{os.path.splitext(document_info.original_filename)[0]}_page{page_idx+1}.{dto.output_format.lower()}"
                        image_path = os.path.join(temp_dir, image_filename)

                        if dto.output_format.lower() == "png":
                            pix.save(image_path)
                        else:  
                            pix.pil_save(image_path, format="JPEG", quality=95)

                        image_paths.append(image_path)
                        image_files.append(image_filename)

                    doc.close()

                    if len(image_paths) > 1:
                        zip_filename = f"{os.path.splitext(document_info.original_filename)[0]}_images.zip"
                        zip_path = os.path.join(temp_dir, zip_filename)

                        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                            for image_path, image_filename in zip(image_paths, image_files):
                                zipf.write(image_path, arcname=image_filename)

                        with open(zip_path, "rb") as f:
                            output_content = f.read()

                        new_document_info = PDFDocumentInfo(
                            title=f"{document_info.title} (Images)",
                            description=f"Hình ảnh từ {document_info.title}",
                            original_filename=zip_filename,
                            file_size=len(output_content),
                            page_count=document_info.page_count,
                            is_encrypted=False,
                            storage_path="",  
                            metadata={
                                "original_document_id": dto.document_id,
                                "converted_to_images": True,
                                "image_format": dto.output_format.lower(),
                                "dpi": dto.dpi,
                                "page_count": len(image_paths),
                                "conversion_date": datetime.now().isoformat()
                            }
                        )

                        new_document_info = await self.document_repository.save(new_document_info, output_content)
                    else:
                        with open(image_paths[0], "rb") as f:
                            output_content = f.read()

                        new_document_info = PNGDocumentInfo(
                            title=f"{document_info.title} (Image)",
                            description=f"Hình ảnh từ {document_info.title}",
                            original_filename=image_files[0],
                            file_size=len(output_content),
                            width=int(pix.width),
                            height=int(pix.height),
                            storage_path="",  
                            metadata={
                                "original_document_id": dto.document_id,
                                "converted_from_pdf": True,
                                "image_format": dto.output_format.lower(),
                                "dpi": dto.dpi,
                                "page_number": page_indices[0] + 1,
                                "conversion_date": datetime.now().isoformat()
                            }
                        )

                        new_document_info = await self.image_repository.save(new_document_info, output_content)

                    shutil.rmtree(temp_dir)

                    os.unlink(temp_pdf_path)

                    processing_info.status = "completed"
                    processing_info.completed_at = datetime.now()
                    processing_info.result_document_id = new_document_info.id
                    await self.processing_repository.update(processing_info)

                    return {
                        "id": new_document_info.id,
                        "filename": new_document_info.original_filename,
                        "file_size": new_document_info.file_size,
                        "page_count": len(image_paths)
                    }
                except Exception as e:
                    if os.path.exists(temp_pdf_path):
                        os.unlink(temp_pdf_path)
                    if os.path.exists(temp_dir):
                        shutil.rmtree(temp_dir)
                    raise ConversionException(f"Lỗi khi chuyển đổi: {str(e)}")
            except Exception as e:
                processing_info.status = "failed"
                processing_info.error_message = str(e)
                await self.processing_repository.update(processing_info)
                raise ConversionException(str(e))
        except DocumentNotFoundException:
            raise
        except Exception as e:
            raise ConversionException(str(e))

    async def get_documents(self, skip: int = 0, limit: int = 10, search: Optional[str] = None) -> List[PDFDocumentInfo]:
        """
        Lấy danh sách tài liệu PDF.

        Args:
            skip: Số tài liệu bỏ qua
            limit: Số tài liệu tối đa trả về
            search: Từ khóa tìm kiếm

        Returns:
            Danh sách tài liệu PDF
        """
        return await self.document_repository.list(skip, limit, search)

    async def get_document(self, document_id: str) -> Tuple[PDFDocumentInfo, bytes]:
        """
        Lấy thông tin và nội dung tài liệu PDF.

        Args:
            document_id: ID của tài liệu

        Returns:
            Tuple chứa thông tin và nội dung tài liệu
        """
        return await self.document_repository.get(document_id)

    async def delete_document(self, document_id: str) -> None:
        """
        Xóa tài liệu PDF.

        Args:
            document_id: ID của tài liệu
        """
        await self.document_repository.delete(document_id)

    async def get_stamps(self, skip: int = 0, limit: int = 10) -> List[StampInfo]:
        """
        Lấy danh sách mẫu dấu.

        Args:
            skip: Số mẫu dấu bỏ qua
            limit: Số mẫu dấu tối đa trả về

        Returns:
            Danh sách mẫu dấu
        """
        return await self.stamp_repository.list(skip, limit)

    async def get_stamp(self, stamp_id: str) -> Tuple[StampInfo, bytes]:
        """
        Lấy thông tin và nội dung mẫu dấu.

        Args:
            stamp_id: ID của mẫu dấu

        Returns:
            Tuple chứa thông tin và nội dung mẫu dấu
        """
        return await self.stamp_repository.get(stamp_id)

    async def delete_stamp(self, stamp_id: str) -> None:
        """
        Xóa mẫu dấu.

        Args:
            stamp_id: ID của mẫu dấu
        """
        await self.stamp_repository.delete(stamp_id)

    async def get_processing_status(self, processing_id: str) -> Dict[str, Any]:
        """
        Lấy trạng thái xử lý PDF.

        Args:
            processing_id: ID của quá trình xử lý

        Returns:
            Dict chứa thông tin trạng thái
        """
        try:
            processing_info = await self.processing_repository.get(processing_id)

            status_data = {
                "processing_id": processing_info.id,
                "document_id": processing_info.document_id,
                "operation_type": processing_info.operation_type,
                "status": processing_info.status,
                "created_at": processing_info.created_at.isoformat()
            }

            if processing_info.completed_at:
                status_data["completed_at"] = processing_info.completed_at.isoformat()

            if processing_info.result_document_id:
                status_data["result_document_id"] = processing_info.result_document_id
                status_data["download_url"] = f"/documents/download/{processing_info.result_document_id}"

            if processing_info.error_message:
                status_data["error_message"] = processing_info.error_message

            if processing_info.parameters:
                status_data["parameters"] = processing_info.parameters

            return status_data
        except Exception as e:
            return {
                "processing_id": processing_id,
                "status": "unknown",
                "error_message": str(e)
            }

    async def get_merge_status(self, merge_id: str) -> Dict[str, Any]:
        """
        Lấy trạng thái gộp tài liệu PDF.

        Args:
            merge_id: ID của quá trình gộp

        Returns:
            Dict chứa thông tin trạng thái
        """
        try:
            merge_info = await self.merge_repository.get(merge_id)

            status_data = {
                "merge_id": merge_info.id,
                "document_ids": merge_info.document_ids,
                "status": merge_info.status,
                "created_at": merge_info.created_at.isoformat(),
                "output_filename": merge_info.output_filename
            }

            if merge_info.result_document_id:
                status_data["result_document_id"] = merge_info.result_document_id
                status_data["download_url"] = f"/documents/download/{merge_info.result_document_id}"

            if merge_info.error_message:
                status_data["error_message"] = merge_info.error_message

            return status_data
        except Exception as e:
            return {
                "merge_id": merge_id,
                "status": "unknown",
                "error_message": str(e)
            }