from fastapi import APIRouter, UploadFile, File, Form, Body, HTTPException, BackgroundTasks, Depends, Query, Path, Request
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from typing import List, Optional, Dict, Any, Union
import os
import tempfile
import json
import logging
import shutil

from application.dto import (
    CreateDocumentDTO as CreatePdfDocumentDTO, CreatePngDocumentDTO, CreateStampDTO,
    EncryptPdfDTO, DecryptPdfDTO, AddWatermarkDTO as WatermarkPdfDTO, SignPdfDTO, MergePdfDTO,
    CrackPdfDTO, ConvertPdfToWordDTO, ConvertPdfToImageDTO,
    UpdateDocumentDTO as UpdatePdfDocumentDTO, UpdatePngDocumentDTO,
    PdfDocumentResponseDTO, PngDocumentResponseDTO, StampResponseDTO,
    PaginatedResponseDTO
)
from infrastructure.repository import (
    PDFDocumentRepository, PNGDocumentRepository, StampRepository,
    PDFProcessingRepository, MergeRepository
)
from infrastructure.minio_client import MinioClient
from infrastructure.rabbitmq_client import RabbitMQClient
from application.services import PDFDocumentService
from domain.models import PDFDocumentInfo, PNGDocumentInfo, PDFProcessingInfo, MergeInfo
from domain.exceptions import (
    DocumentNotFoundException, StorageException, ConversionException,
    EncryptionException, DecryptionException, WatermarkException,
    SignatureException, MergeException, StampNotFoundException,
    PDFPasswordProtectedException, WrongPasswordException, CrackPasswordException,
    ImageNotFoundException
)
from api.dependencies import get_current_user_id_from_header

logger = logging.getLogger(__name__)
router = APIRouter()


def get_pdf_service(request: Request) -> PDFDocumentService:
    db_session_factory = request.app.state.db_pool
    minio_client = MinioClient()
    rabbitmq_client = RabbitMQClient()
    
    document_repo = PDFDocumentRepository(minio_client, db_session_factory)
    image_repo = PNGDocumentRepository(minio_client, db_session_factory)
    stamp_repo = StampRepository(minio_client)
    processing_repo = PDFProcessingRepository()
    
    return PDFDocumentService(
        document_repository=document_repo, 
        image_repository=image_repo, 
        stamp_repository=stamp_repo, 
        minio_client=minio_client, 
        rabbitmq_client=rabbitmq_client, 
        processing_repository=processing_repo
    )


@router.post(
    "/documents", 
    summary="Tải lên tài liệu PDF mới", 
    response_model=PdfDocumentResponseDTO,
    status_code=201
)
async def upload_pdf_document(
    current_user_id: str = Depends(get_current_user_id_from_header),
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    pdf_service: PDFDocumentService = Depends(get_pdf_service)
):
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận file .pdf và tên file không được trống.")
    
    try:
        document_dto = CreatePdfDocumentDTO(
            title=title or os.path.splitext(file.filename)[0],
            description=description or "",
            original_filename=file.filename,
        )
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="File không được để trống.")

        document_info = await pdf_service.create_document(document_dto, content, current_user_id)
        return document_info
    except StorageException as e:
        logger.error(f"Lỗi lưu trữ khi upload PDF cho user {current_user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Lỗi máy chủ khi lưu tài liệu: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Lỗi không xác định khi upload PDF cho user {current_user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Lỗi máy chủ không xác định: {str(e)}")


@router.get(
    "/documents", 
    summary="Lấy danh sách tài liệu PDF của người dùng",
    response_model=PaginatedResponseDTO[PdfDocumentResponseDTO]
)
async def get_pdf_documents(
    current_user_id: str = Depends(get_current_user_id_from_header),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    pdf_service: PDFDocumentService = Depends(get_pdf_service)
):
    try:
        documents, total_count = await pdf_service.get_documents(current_user_id, skip, limit, search)
        return {"items": documents, "total_count": total_count, "skip": skip, "limit": limit}
    except Exception as e:
        logger.error(f"Lỗi khi lấy danh sách PDF cho user {current_user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Lỗi máy chủ: {str(e)}")


@router.get(
    "/documents/{document_id}", 
    summary="Lấy thông tin chi tiết tài liệu PDF",
    response_model=PdfDocumentResponseDTO
)
async def get_pdf_document(
    document_id: str = Path(..., description="ID của tài liệu PDF"),
    current_user_id: str = Depends(get_current_user_id_from_header),
    pdf_service: PDFDocumentService = Depends(get_pdf_service)
):
    try:
        document_info, _ = await pdf_service.get_document(document_id, current_user_id)
        return document_info
    except DocumentNotFoundException as e:
        logger.warning(f"PDF document not found (id: {document_id}, user: {current_user_id}): {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except StorageException as e:
        logger.error(f"Lỗi storage khi lấy PDF (id: {document_id}, user: {current_user_id}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Lỗi máy chủ khi lấy tài liệu: {str(e)}")
    except Exception as e:
        logger.error(f"Lỗi không xác định khi lấy PDF (id: {document_id}, user: {current_user_id}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Lỗi máy chủ không xác định: {str(e)}")


@router.put(
    "/documents/{document_id}",
    summary="Cập nhật thông tin tài liệu PDF",
    response_model=PdfDocumentResponseDTO
)
async def update_pdf_document(
    document_id: str = Path(..., description="ID của tài liệu PDF"),
    update_dto: UpdatePdfDocumentDTO = Body(...),
    current_user_id: str = Depends(get_current_user_id_from_header),
    pdf_service: PDFDocumentService = Depends(get_pdf_service)
):
    try:
        updated_document = await pdf_service.update_document(document_id, update_dto, current_user_id)
        return updated_document
    except DocumentNotFoundException as e:
        logger.warning(f"PDF document not found for update (id: {document_id}, user: {current_user_id}): {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except StorageException as e:
        logger.error(f"Lỗi storage khi cập nhật PDF (id: {document_id}, user: {current_user_id}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Lỗi máy chủ khi cập nhật tài liệu: {str(e)}")
    except Exception as e:
        logger.error(f"Lỗi không xác định khi cập nhật PDF (id: {document_id}, user: {current_user_id}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Lỗi máy chủ không xác định: {str(e)}")


@router.delete(
    "/documents/{document_id}", 
    summary="Xóa tài liệu PDF",
    status_code=204
)
async def delete_pdf_document(
    document_id: str = Path(..., description="ID của tài liệu PDF"),
    current_user_id: str = Depends(get_current_user_id_from_header),
    pdf_service: PDFDocumentService = Depends(get_pdf_service)
):
    try:
        await pdf_service.delete_document(document_id, current_user_id)
        return None
    except DocumentNotFoundException as e:
        logger.warning(f"PDF document not found for deletion (id: {document_id}, user: {current_user_id}): {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except StorageException as e:
        logger.error(f"Lỗi storage khi xóa PDF (id: {document_id}, user: {current_user_id}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Lỗi máy chủ khi xóa tài liệu: {str(e)}")
    except Exception as e:
        logger.error(f"Lỗi không xác định khi xóa PDF (id: {document_id}, user: {current_user_id}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Lỗi máy chủ không xác định: {str(e)}")


@router.get(
    "/documents/download/{document_id}", 
    summary="Tải xuống tài liệu PDF"
)
async def download_pdf_document(
    document_id: str = Path(..., description="ID của tài liệu PDF"),
    current_user_id: str = Depends(get_current_user_id_from_header),
    pdf_service: PDFDocumentService = Depends(get_pdf_service)
):
    temp_file_path = None
    try:
        document_info, content = await pdf_service.get_document(document_id, current_user_id)
        
        fd, temp_file_path = tempfile.mkstemp(suffix=f"_{document_info.original_filename}")
        with os.fdopen(fd, "wb") as tmp:
            tmp.write(content)
            
        return FileResponse(
            path=temp_file_path,
            filename=document_info.original_filename,
            media_type='application/pdf'
        )
    except DocumentNotFoundException as e:
        logger.warning(f"PDF document not found for download (id: {document_id}, user: {current_user_id}): {e}")
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Lỗi khi tải PDF (id: {document_id}, user: {current_user_id}): {e}", exc_info=True)
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        raise HTTPException(status_code=500, detail=f"Lỗi máy chủ: {str(e)}")


@router.post("/documents/encrypt", summary="Mã hóa tài liệu PDF", response_model=Dict[str, Any])
async def encrypt_pdf_document(
    current_user_id: str = Depends(get_current_user_id_from_header),
    dto: EncryptPdfDTO = Body(...),
    pdf_service: PDFDocumentService = Depends(get_pdf_service)
):
    try:
        result = await pdf_service.encrypt_pdf(dto, current_user_id)
        return result
    except DocumentNotFoundException as e:
        logger.warning(f"PDF not found for encryption (doc: {dto.document_id}, user: {current_user_id}): {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except (EncryptionException, PDFPasswordProtectedException) as e:
        logger.warning(f"Encryption failed (doc: {dto.document_id}, user: {current_user_id}): {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Lỗi khi mã hóa PDF (doc: {dto.document_id}, user: {current_user_id}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Lỗi máy chủ: {str(e)}")


@router.post("/documents/decrypt", summary="Giải mã tài liệu PDF", response_model=Dict[str, Any])
async def decrypt_pdf_document(
    current_user_id: str = Depends(get_current_user_id_from_header),
    dto: DecryptPdfDTO = Body(...),
    pdf_service: PDFDocumentService = Depends(get_pdf_service)
):
    try:
        result = await pdf_service.decrypt_pdf(dto, current_user_id)
        return result
    except DocumentNotFoundException as e:
        logger.warning(f"PDF not found for decryption (doc: {dto.document_id}, user: {current_user_id}): {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except (DecryptionException, WrongPasswordException, PDFPasswordProtectedException) as e:
        logger.warning(f"Decryption failed (doc: {dto.document_id}, user: {current_user_id}): {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Lỗi khi giải mã PDF (doc: {dto.document_id}, user: {current_user_id}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Lỗi máy chủ: {str(e)}")


@router.post("/documents/watermark", summary="Thêm watermark vào tài liệu PDF", response_model=Dict[str, Any])
async def add_watermark_to_pdf(
    current_user_id: str = Depends(get_current_user_id_from_header),
    dto: WatermarkPdfDTO = Body(...),
    pdf_service: PDFDocumentService = Depends(get_pdf_service)
):
    try:
        result = await pdf_service.add_watermark(dto, current_user_id)
        return result
    except DocumentNotFoundException as e:
        logger.warning(f"PDF not found for watermarking (doc: {dto.document_id}, user: {current_user_id}): {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except WatermarkException as e:
        logger.warning(f"Watermark failed (doc: {dto.document_id}, user: {current_user_id}): {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Lỗi khi thêm watermark (doc: {dto.document_id}, user: {current_user_id}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Lỗi máy chủ: {str(e)}")


@router.post("/documents/sign", summary="Thêm chữ ký vào tài liệu PDF", response_model=Dict[str, Any])
async def add_signature_to_pdf(
    current_user_id: str = Depends(get_current_user_id_from_header),
    dto: SignPdfDTO = Body(...),
    pdf_service: PDFDocumentService = Depends(get_pdf_service)
):
    try:
        result = await pdf_service.add_signature(dto, current_user_id)
        return result
    except DocumentNotFoundException as e:
        logger.warning(f"PDF not found for signing (doc: {dto.document_id}, user: {current_user_id}): {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except StampNotFoundException as e:
        logger.warning(f"Stamp not found for signing (stamp: {dto.stamp_id}, user: {current_user_id}): {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except SignatureException as e:
        logger.warning(f"Sign failed (doc: {dto.document_id}, user: {current_user_id}): {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Lỗi khi ký PDF (doc: {dto.document_id}, user: {current_user_id}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Lỗi máy chủ: {str(e)}")


@router.post("/documents/merge", summary="Gộp nhiều tài liệu PDF", response_model=Dict[str, Any])
async def merge_pdf_documents(
    current_user_id: str = Depends(get_current_user_id_from_header),
    dto: MergePdfDTO = Body(...),
    pdf_service: PDFDocumentService = Depends(get_pdf_service)
):
    try:
        result = await pdf_service.merge_pdfs(dto, current_user_id)
        return result
    except DocumentNotFoundException as e:
        logger.warning(f"One or more PDFs not found for merging (user: {current_user_id}): {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except MergeException as e:
        logger.warning(f"Merge failed (user: {current_user_id}): {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Lỗi khi gộp PDF (user: {current_user_id}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Lỗi máy chủ: {str(e)}")


@router.post("/documents/crack", summary="Crack mật khẩu tài liệu PDF (gửi yêu cầu)", response_model=Dict[str, Any])
async def crack_pdf_password(
    current_user_id: str = Depends(get_current_user_id_from_header),
    dto: CrackPdfDTO = Body(...),
    pdf_service: PDFDocumentService = Depends(get_pdf_service)
):
    try:
        result = await pdf_service.crack_pdf_password(dto, current_user_id)
        return result
    except DocumentNotFoundException as e:
        logger.warning(f"PDF not found for password cracking (doc: {dto.document_id}, user: {current_user_id}): {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except CrackPasswordException as e:
        logger.warning(f"Cannot crack password (doc: {dto.document_id}, user: {current_user_id}): {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Lỗi khi gửi yêu cầu crack PDF (doc: {dto.document_id}, user: {current_user_id}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Lỗi máy chủ: {str(e)}")


@router.post("/documents/convert/to-word", summary="Chuyển đổi PDF sang Word", response_model=Dict[str, Any])
async def convert_pdf_to_word(
    current_user_id: str = Depends(get_current_user_id_from_header),
    dto: ConvertPdfToWordDTO = Body(...),
    pdf_service: PDFDocumentService = Depends(get_pdf_service)
):
    try:
        result = await pdf_service.convert_to_word(dto, current_user_id)
        return result
    except DocumentNotFoundException as e:
        logger.warning(f"PDF not found for Word conversion (doc: {dto.document_id}, user: {current_user_id}): {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except ConversionException as e:
        logger.warning(f"PDF to Word conversion failed (doc: {dto.document_id}, user: {current_user_id}): {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Lỗi khi chuyển PDF sang Word (doc: {dto.document_id}, user: {current_user_id}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Lỗi máy chủ: {str(e)}")


@router.post("/documents/convert/to-images", summary="Chuyển đổi PDF sang hình ảnh", response_model=Dict[str, Any])
async def convert_pdf_to_images(
    current_user_id: str = Depends(get_current_user_id_from_header),
    dto: ConvertPdfToImageDTO = Body(...),
    pdf_service: PDFDocumentService = Depends(get_pdf_service)
):
    try:
        result = await pdf_service.convert_to_images(dto, current_user_id)
        return result
    except DocumentNotFoundException as e:
        logger.warning(f"PDF not found for image conversion (doc: {dto.document_id}, user: {current_user_id}): {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except ConversionException as e:
        logger.warning(f"PDF to image conversion failed (doc: {dto.document_id}, user: {current_user_id}): {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Lỗi khi chuyển PDF sang ảnh (doc: {dto.document_id}, user: {current_user_id}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Lỗi máy chủ: {str(e)}")


@router.get("/status/processing/{processing_id}", summary="Kiểm tra trạng thái xử lý PDF", response_model=PDFProcessingInfo)
async def get_pdf_processing_status(
    processing_id: str = Path(..., description="ID của quá trình xử lý"),
    pdf_service: PDFDocumentService = Depends(get_pdf_service)
):
    try:
        status_info = await pdf_service.get_processing_status(processing_id)
        return status_info
    except DocumentNotFoundException as e:
        logger.warning(f"Processing info not found (id: {processing_id}): {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Lỗi khi lấy trạng thái xử lý (id: {processing_id}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Lỗi máy chủ: {str(e)}")


@router.get("/status/merge/{merge_id}", summary="Kiểm tra trạng thái gộp tài liệu", response_model=MergeInfo)
async def get_pdf_merge_status(
    merge_id: str = Path(..., description="ID của quá trình gộp"),
    pdf_service: PDFDocumentService = Depends(get_pdf_service)
):
    try:
        status_info = await pdf_service.get_merge_status(merge_id)
        return status_info
    except DocumentNotFoundException as e:
        logger.warning(f"Merge info not found (id: {merge_id}): {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Lỗi khi lấy trạng thái gộp (id: {merge_id}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Lỗi máy chủ: {str(e)}")


async def safe_remove_temp_file(file_path: Optional[str]):
    if file_path and os.path.exists(file_path):
        try:
            os.unlink(file_path)
            logger.info(f"Successfully removed temp file: {file_path}")
        except Exception as e:
            logger.error(f"Error removing temp file {file_path}: {e}", exc_info=True)


@router.get(
    "/documents/download-stream/{document_id}", 
    summary="Tải xuống tài liệu PDF (Streaming)",
    response_class=StreamingResponse 
)
async def download_pdf_document_stream(
    document_id: str = Path(..., description="ID của tài liệu PDF"),
    current_user_id: str = Depends(get_current_user_id_from_header),
    pdf_service: PDFDocumentService = Depends(get_pdf_service),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    temp_file_path = None
    try:
        document_info, content = await pdf_service.get_document(document_id, current_user_id)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{document_info.original_filename}") as tmp_file:
            tmp_file.write(content)
            temp_file_path = tmp_file.name

        async def file_iterator(file_path: str):
            with open(file_path, "rb") as f:
                while chunk := f.read(8192):
                    yield chunk
        
        background_tasks.add_task(safe_remove_temp_file, temp_file_path)

        return StreamingResponse(
            file_iterator(temp_file_path),
            media_type='application/pdf',
            headers={"Content-Disposition": f"attachment; filename=\"{document_info.original_filename}\""}
        )
    except DocumentNotFoundException as e:
        logger.warning(f"PDF document not found for streaming download (id: {document_id}, user: {current_user_id}): {e}")
        if temp_file_path: await safe_remove_temp_file(temp_file_path)
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Lỗi khi stream PDF (id: {document_id}, user: {current_user_id}): {e}", exc_info=True)
        if temp_file_path: await safe_remove_temp_file(temp_file_path)
        raise HTTPException(status_code=500, detail=f"Lỗi máy chủ khi stream tài liệu: {str(e)}")
