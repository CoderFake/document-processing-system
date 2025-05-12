from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Depends, Query, Path
from fastapi.responses import JSONResponse, FileResponse
from typing import List, Optional, Dict, Any
import os
import tempfile
import json

from application.dto import (
    CreatePdfDocumentDTO, CreatePngDocumentDTO, CreateStampDTO,
    EncryptPdfDTO, DecryptPdfDTO, WatermarkPdfDTO, SignPdfDTO, MergePdfDTO,
    CrackPdfDTO, ConvertPdfToWordDTO, ConvertPdfToImageDTO
)
from infrastructure.repository import (
    PDFDocumentRepository, PNGDocumentRepository, StampRepository,
    PDFProcessingRepository, MergeRepository
)
from infrastructure.minio_client import MinioClient
from infrastructure.rabbitmq_client import RabbitMQClient
from application.services import PDFDocumentService
from domain.exceptions import (
    DocumentNotFoundException, StorageException, ConversionException,
    EncryptionException, DecryptionException, WatermarkException,
    SignatureException, MergeException, StampNotFoundException,
    PDFPasswordProtectedException, WrongPasswordException, CrackPasswordException
)

router = APIRouter()


def get_pdf_service():
    minio_client = MinioClient()
    rabbitmq_client = RabbitMQClient()
    document_repo = PDFDocumentRepository(minio_client)
    image_repo = PNGDocumentRepository(minio_client)
    stamp_repo = StampRepository(minio_client)
    return PDFDocumentService(document_repo, image_repo, stamp_repo, minio_client, rabbitmq_client)


@router.get("/documents", summary="Lấy danh sách tài liệu PDF")
async def get_pdf_documents(
    skip: int = 0,
    limit: int = 10,
    search: Optional[str] = None,
    pdf_service: PDFDocumentService = Depends(get_pdf_service)
):
    """
    Lấy danh sách tài liệu PDF từ hệ thống.
    """
    try:
        documents = await pdf_service.get_documents(skip, limit, search)
        return {"items": documents, "total": len(documents)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/upload", summary="Tải lên tài liệu PDF mới")
async def upload_pdf_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    pdf_service: PDFDocumentService = Depends(get_pdf_service)
):
    """
    Tải lên tài liệu PDF mới vào hệ thống.
    """
    try:
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Chỉ chấp nhận file .pdf")

        document_dto = CreatePdfDocumentDTO(
            title=title or os.path.splitext(file.filename)[0],
            description=description or "",
            original_filename=file.filename
        )

        content = await file.read()

        document_info = await pdf_service.create_document(document_dto, content)

        return {
            "id": document_info.id,
            "title": document_info.title,
            "description": document_info.description,
            "created_at": document_info.created_at.isoformat(),
            "file_size": document_info.file_size,
            "page_count": document_info.page_count,
            "is_encrypted": document_info.is_encrypted,
            "original_filename": document_info.original_filename
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stamps/upload", summary="Tải lên mẫu dấu mới")
async def upload_stamp(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: Optional[str] = Form(None),
    pdf_service: PDFDocumentService = Depends(get_pdf_service)
):
    """
    Tải lên mẫu dấu mới vào hệ thống.
    """
    try:
        if not file.filename.endswith(('.png', '.jpg', '.jpeg')):
            raise HTTPException(status_code=400, detail="Chỉ chấp nhận file .png, .jpg hoặc .jpeg")

        stamp_dto = CreateStampDTO(
            name=name,
            description=description or "",
            original_filename=file.filename
        )

        content = await file.read()

        stamp_info = await pdf_service.create_stamp(stamp_dto, content)

        return {
            "id": stamp_info.id,
            "name": stamp_info.name,
            "description": stamp_info.description,
            "created_at": stamp_info.created_at.isoformat(),
            "file_size": stamp_info.file_size,
            "width": stamp_info.width,
            "height": stamp_info.height,
            "original_filename": stamp_info.original_filename
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/encrypt", summary="Mã hóa tài liệu PDF")
async def encrypt_pdf_document(
    document_id: str = Form(...),
    password: str = Form(...),
    permissions: Optional[str] = Form(None),
    pdf_service: PDFDocumentService = Depends(get_pdf_service)
):
    """
    Mã hóa tài liệu PDF với mật khẩu.
    """
    try:
        permissions_dict = None
        if permissions:
            try:
                permissions_dict = json.loads(permissions)
            except:
                raise HTTPException(status_code=400, detail="Định dạng permissions không hợp lệ")

        encrypt_dto = EncryptPdfDTO(
            document_id=document_id,
            password=password,
            permissions=permissions_dict
        )

        result = await pdf_service.encrypt_pdf(encrypt_dto)

        return {
            "status": "success",
            "message": "Tài liệu đã được mã hóa thành công",
            "document_id": result["id"],
            "filename": result["filename"],
            "file_size": result["file_size"],
            "is_encrypted": result["is_encrypted"]
        }
    except DocumentNotFoundException:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy tài liệu với ID: {document_id}")
    except EncryptionException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/decrypt", summary="Giải mã tài liệu PDF")
async def decrypt_pdf_document(
    document_id: str = Form(...),
    password: str = Form(...),
    pdf_service: PDFDocumentService = Depends(get_pdf_service)
):
    """
    Giải mã tài liệu PDF với mật khẩu.
    """
    try:
        decrypt_dto = DecryptPdfDTO(
            document_id=document_id,
            password=password
        )

        result = await pdf_service.decrypt_pdf(decrypt_dto)

        return {
            "status": "success",
            "message": "Tài liệu đã được giải mã thành công",
            "document_id": result["id"],
            "filename": result["filename"],
            "file_size": result["file_size"],
            "is_encrypted": result["is_encrypted"]
        }
    except DocumentNotFoundException:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy tài liệu với ID: {document_id}")
    except WrongPasswordException:
        raise HTTPException(status_code=400, detail="Mật khẩu không đúng")
    except DecryptionException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/watermark", summary="Thêm watermark vào tài liệu PDF")
async def add_watermark_to_pdf(
    document_id: str = Form(...),
    watermark_text: str = Form(...),
    position: str = Form("center"),
    opacity: float = Form(0.5),
    color: Optional[str] = Form(None),
    font_size: Optional[int] = Form(None),
    pdf_service: PDFDocumentService = Depends(get_pdf_service)
):
    """
    Thêm watermark vào tài liệu PDF.
    """
    try:
        watermark_dto = WatermarkPdfDTO(
            document_id=document_id,
            watermark_text=watermark_text,
            position=position,
            opacity=opacity,
            color=color,
            font_size=font_size
        )

        result = await pdf_service.add_watermark(watermark_dto)

        return {
            "status": "success",
            "message": "Watermark đã được thêm thành công",
            "document_id": result["id"],
            "filename": result["filename"],
            "file_size": result["file_size"]
        }
    except DocumentNotFoundException:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy tài liệu với ID: {document_id}")
    except WatermarkException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/sign", summary="Thêm chữ ký vào tài liệu PDF")
async def add_signature_to_pdf(
    document_id: str = Form(...),
    stamp_id: Optional[str] = Form(None),
    signature_position: str = Form("bottom-right"),
    page_number: int = Form(-1),
    scale: float = Form(0.5),
    custom_x: Optional[int] = Form(None),
    custom_y: Optional[int] = Form(None),
    pdf_service: PDFDocumentService = Depends(get_pdf_service)
):
    """
    Thêm chữ ký vào tài liệu PDF.
    """
    try:
        sign_dto = SignPdfDTO(
            document_id=document_id,
            stamp_id=stamp_id,
            signature_position=signature_position,
            page_number=page_number,
            scale=scale,
            custom_x=custom_x,
            custom_y=custom_y
        )

        result = await pdf_service.add_signature(sign_dto)

        return {
            "status": "success",
            "message": "Chữ ký đã được thêm thành công",
            "document_id": result["id"],
            "filename": result["filename"],
            "file_size": result["file_size"]
        }
    except DocumentNotFoundException:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy tài liệu với ID: {document_id}")
    except StampNotFoundException:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy mẫu dấu với ID: {stamp_id}")
    except SignatureException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/merge", summary="Gộp nhiều tài liệu PDF")
async def merge_pdf_documents(
    document_ids: List[str] = Form(...),
    output_filename: str = Form(...),
    pdf_service: PDFDocumentService = Depends(get_pdf_service)
):
    """
    Gộp nhiều tài liệu PDF thành một.
    """
    try:
        if not output_filename.endswith('.pdf'):
            output_filename += '.pdf'

        merge_dto = MergePdfDTO(
            document_ids=document_ids,
            output_filename=output_filename
        )

        result = await pdf_service.merge_pdfs(merge_dto)

        return {
            "status": "success",
            "message": "Các tài liệu đã được gộp thành công",
            "document_id": result["id"],
            "filename": result["filename"],
            "file_size": result["file_size"],
            "page_count": result["page_count"]
        }
    except DocumentNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except MergeException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/crack", summary="Crack mật khẩu tài liệu PDF")
async def crack_pdf_password(
    document_id: str = Form(...),
    max_length: int = Form(6),
    pdf_service: PDFDocumentService = Depends(get_pdf_service)
):
    """
    Thử crack mật khẩu tài liệu PDF sử dụng phương pháp brute-force.
    """
    try:
        crack_dto = CrackPdfDTO(
            document_id=document_id,
            max_length=max_length
        )

        result = await pdf_service.crack_pdf_password(crack_dto)

        return {
            "status": "success",
            "message": "Đã crack mật khẩu thành công",
            "document_id": result["id"],
            "filename": result["filename"],
            "file_size": result["file_size"],
            "found_password": result["found_password"]
        }
    except DocumentNotFoundException:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy tài liệu với ID: {document_id}")
    except CrackPasswordException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/convert/to-word", summary="Chuyển đổi PDF sang Word")
async def convert_pdf_to_word(
    document_id: str = Form(...),
    output_format: str = Form("docx"),
    pdf_service: PDFDocumentService = Depends(get_pdf_service)
):
    """
    Chuyển đổi tài liệu PDF sang định dạng Word.
    """
    try:
        if output_format.lower() not in ["docx", "doc"]:
            raise HTTPException(status_code=400, detail="Định dạng đầu ra không hợp lệ. Chỉ hỗ trợ 'docx' hoặc 'doc'")

        convert_dto = ConvertPdfToWordDTO(
            document_id=document_id,
            output_format=output_format
        )

        result = await pdf_service.convert_to_word(convert_dto)

        return {
            "status": "success",
            "message": "Tài liệu đã được chuyển đổi thành công",
            "document_id": result["id"],
            "filename": result["filename"],
            "file_size": result["file_size"]
        }
    except DocumentNotFoundException:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy tài liệu với ID: {document_id}")
    except ConversionException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/convert/to-images", summary="Chuyển đổi PDF sang hình ảnh")
async def convert_pdf_to_images(
    document_id: str = Form(...),
    output_format: str = Form("png"),
    dpi: int = Form(300),
    page_numbers: Optional[str] = Form(None),
    pdf_service: PDFDocumentService = Depends(get_pdf_service)
):
    """
    Chuyển đổi tài liệu PDF sang hình ảnh.
    """
    try:
        if output_format.lower() not in ["png", "jpg"]:
            raise HTTPException(status_code=400, detail="Định dạng đầu ra không hợp lệ. Chỉ hỗ trợ 'png' hoặc 'jpg'")

        page_numbers_list = None
        if page_numbers:
            try:
                page_numbers_list = [int(p.strip()) for p in page_numbers.split(",")]
            except:
                raise HTTPException(status_code=400, detail="Định dạng page_numbers không hợp lệ. Sử dụng định dạng: 1,2,3")

        convert_dto = ConvertPdfToImageDTO(
            document_id=document_id,
            output_format=output_format,
            dpi=dpi,
            page_numbers=page_numbers_list
        )

        result = await pdf_service.convert_to_images(convert_dto)

        return {
            "status": "success",
            "message": "Tài liệu đã được chuyển đổi thành công",
            "document_id": result["id"],
            "filename": result["filename"],
            "file_size": result["file_size"],
            "page_count": result["page_count"]
        }
    except DocumentNotFoundException:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy tài liệu với ID: {document_id}")
    except ConversionException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/{document_id}", summary="Lấy thông tin tài liệu PDF")
async def get_pdf_document(
    document_id: str,
    pdf_service: PDFDocumentService = Depends(get_pdf_service)
):
    """
    Lấy thông tin tài liệu PDF theo ID.
    """
    try:
        document_info, _ = await pdf_service.get_document(document_id)
        return {
            "id": document_info.id,
            "title": document_info.title,
            "description": document_info.description,
            "created_at": document_info.created_at.isoformat(),
            "updated_at": document_info.updated_at.isoformat() if document_info.updated_at else None,
            "file_size": document_info.file_size,
            "page_count": document_info.page_count,
            "is_encrypted": document_info.is_encrypted,
            "original_filename": document_info.original_filename,
            "metadata": document_info.metadata
        }
    except DocumentNotFoundException:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy tài liệu với ID: {document_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/download/{document_id}", summary="Tải xuống tài liệu PDF")
async def download_pdf_document(
    document_id: str,
    pdf_service: PDFDocumentService = Depends(get_pdf_service)
):
    """
    Tải xuống tài liệu PDF theo ID.
    """
    try:
        document_info, document_content = await pdf_service.get_document(document_id)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(document_content)
            temp_path = temp_file.name

        return FileResponse(
            path=temp_path,
            filename=document_info.original_filename,
            media_type="application/pdf",
            background=BackgroundTasks().add_task(lambda: os.unlink(temp_path))
        )
    except DocumentNotFoundException:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy tài liệu với ID: {document_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/documents/{document_id}", summary="Xóa tài liệu PDF")
async def delete_pdf_document(
    document_id: str,
    pdf_service: PDFDocumentService = Depends(get_pdf_service)
):
    """
    Xóa tài liệu PDF theo ID.
    """
    try:
        await pdf_service.delete_document(document_id)
        return {
            "status": "success",
            "message": "Tài liệu đã được xóa thành công",
            "document_id": document_id
        }
    except DocumentNotFoundException:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy tài liệu với ID: {document_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stamps", summary="Lấy danh sách mẫu dấu")
async def get_stamps(
    skip: int = 0,
    limit: int = 10,
    pdf_service: PDFDocumentService = Depends(get_pdf_service)
):
    """
    Lấy danh sách mẫu dấu từ hệ thống.
    """
    try:
        stamps = await pdf_service.get_stamps(skip, limit)
        return {"items": stamps, "total": len(stamps)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stamps/{stamp_id}", summary="Lấy thông tin mẫu dấu")
async def get_stamp(
    stamp_id: str,
    pdf_service: PDFDocumentService = Depends(get_pdf_service)
):
    """
    Lấy thông tin mẫu dấu theo ID.
    """
    try:
        stamp_info, _ = await pdf_service.get_stamp(stamp_id)
        return {
            "id": stamp_info.id,
            "name": stamp_info.name,
            "description": stamp_info.description,
            "created_at": stamp_info.created_at.isoformat(),
            "updated_at": stamp_info.updated_at.isoformat() if stamp_info.updated_at else None,
            "file_size": stamp_info.file_size,
            "width": stamp_info.width,
            "height": stamp_info.height,
            "original_filename": stamp_info.original_filename,
            "metadata": stamp_info.metadata
        }
    except StampNotFoundException:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy mẫu dấu với ID: {stamp_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/stamps/{stamp_id}", summary="Xóa mẫu dấu")
async def delete_stamp(
    stamp_id: str,
    pdf_service: PDFDocumentService = Depends(get_pdf_service)
):
    """
    Xóa mẫu dấu theo ID.
    """
    try:
        await pdf_service.delete_stamp(stamp_id)
        return {
            "status": "success",
            "message": "Mẫu dấu đã được xóa thành công",
            "stamp_id": stamp_id
        }
    except StampNotFoundException:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy mẫu dấu với ID: {stamp_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/processing/{processing_id}", summary="Kiểm tra trạng thái xử lý PDF")
async def get_processing_status(
    processing_id: str,
    pdf_service: PDFDocumentService = Depends(get_pdf_service)
):
    """
    Kiểm tra trạng thái xử lý PDF.
    """
    try:
        status = await pdf_service.get_processing_status(processing_id)
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/merge/{merge_id}", summary="Kiểm tra trạng thái gộp tài liệu")
async def get_merge_status(
    merge_id: str,
    pdf_service: PDFDocumentService = Depends(get_pdf_service)
):
    """
    Kiểm tra trạng thái gộp tài liệu.
    """
    try:
        status = await pdf_service.get_merge_status(merge_id)
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))