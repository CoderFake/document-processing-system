from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Depends, Query, Path, Request
from fastapi.responses import JSONResponse, FileResponse
from typing import List, Optional, Dict, Any
import os
import uuid
import tempfile
import shutil
from datetime import datetime
import json
import logging

from domain.models import WordDocumentInfo as DocumentInfo, TemplateInfo, InternshipReportModel, RewardReportModel, LaborContractModel
from application.dto import CreateDocumentDTO, TemplateDataDTO, WatermarkDTO
from application.services import DocumentService, TemplateService
from infrastructure.repository import DocumentRepository, TemplateRepository, BatchProcessingRepository
from infrastructure.minio_client import MinioClient
from infrastructure.rabbitmq_client import RabbitMQClient
from .dependencies import get_current_user_id_from_header

router = APIRouter()
logger = logging.getLogger(__name__)


def get_document_service(request: Request) -> DocumentService:
    minio_client = MinioClient()
    rabbitmq_client = RabbitMQClient()
    db_session_factory = request.app.state.db_session_factory
    if not db_session_factory:
        logger.error("Lỗi nghiêm trọng: Database session factory không khả dụng trong get_document_service.")
        raise HTTPException(status_code=503, detail="Database session factory không khả dụng.")
    
    document_repo = DocumentRepository(minio_client, db_session_factory)
    return DocumentService(document_repo, minio_client, rabbitmq_client)


def get_template_service(request: Request) -> TemplateService:
    minio_client = MinioClient()
    rabbitmq_client = RabbitMQClient()
    db_session_factory = request.app.state.db_session_factory

    if not db_session_factory:
        logger.error("Lỗi nghiêm trọng: Database session factory không khả dụng trong get_template_service.")
        raise HTTPException(status_code=503, detail="Database session factory không khả dụng.")

    document_repo = DocumentRepository(minio_client, db_session_factory)
    
    template_repo = TemplateRepository(minio_client)
    
    batch_repo = BatchProcessingRepository()
    
    template_service = TemplateService(
        template_repository=template_repo, 
        minio_client=minio_client,
        rabbitmq_client=rabbitmq_client,
        batch_processing_repository=batch_repo
    )
    
    template_service.set_document_repository(document_repo)
    
    return template_service


@router.get("/documents", summary="Lấy danh sách tài liệu Word")
async def get_documents(
        skip: int = 0,
        limit: int = 10,
        search: Optional[str] = None,
        current_user_id: str = Depends(get_current_user_id_from_header),
        document_service: DocumentService = Depends(get_document_service)
):
    """
    Lấy danh sách tài liệu Word từ hệ thống.
    Chỉ trả về tài liệu của người dùng (current_user_id).
    """
    try:
        documents, total_count = await document_service.get_documents(skip, limit, search, current_user_id)
        return {"items": documents, "total_count": total_count}
    except Exception as e:
        logger.error(f"Lỗi khi lấy danh sách tài liệu: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/upload", summary="Tải lên tài liệu Word mới")
async def upload_document(
        background_tasks: BackgroundTasks,
        file: UploadFile = File(...),
        title: Optional[str] = Form(None),
        description: Optional[str] = Form(None),
        current_user_id: str = Depends(get_current_user_id_from_header),
        document_service: DocumentService = Depends(get_document_service)
):
    """
    Tải lên tài liệu Word mới vào hệ thống.
    """
    try:
        if not file.filename.endswith(('.doc', '.docx')):
            raise HTTPException(status_code=400, detail="Chỉ chấp nhận file .doc hoặc .docx")

        document_dto = CreateDocumentDTO(
            title=title or os.path.splitext(file.filename)[0],
            description=description or "",
            original_filename=file.filename,
            user_id=current_user_id
        )

        content = await file.read()
        document_info = await document_service.create_document(document_dto, content)

        background_tasks.add_task(
                document_service.process_document_async,
            document_id=document_info.id,
            user_id=current_user_id
            )

        return {
            "id": document_info.id,
            "title": document_info.title,
            "description": document_info.description,
            "created_at": document_info.created_at.isoformat(),
            "file_size": document_info.file_size,
            "file_type": document_info.file_type,
            "original_filename": document_info.original_filename
        }
    except Exception as e:
        logger.error(f"Lỗi khi tải lên tài liệu: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/convert/to-pdf", summary="Chuyển đổi tài liệu Word sang PDF")
async def convert_to_pdf(
        file: UploadFile = File(...),
        current_user_id: str = Depends(get_current_user_id_from_header),
        document_service: DocumentService = Depends(get_document_service)
):
    """
    Chuyển đổi tài liệu Word sang định dạng PDF.
    """
    try:
        if not file.filename.endswith(('.doc', '.docx')):
            raise HTTPException(status_code=400, detail="Only .doc or .docx files are accepted")

        content = await file.read()
        result = await document_service.convert_to_pdf(content, file.filename, current_user_id)

        return {
            "status": "success",
            "message": "Tài liệu đã được chuyển đổi thành công",
            "filename": result["filename"],
            "download_url": f"/documents/download/{result['id']}"
        }
    except Exception as e:
        logger.error(f"Lỗi khi chuyển đổi Word sang PDF: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/watermark", summary="Thêm watermark vào tài liệu Word")
async def add_watermark(
        file: UploadFile = File(...),
        watermark_text: str = Form(...),
        current_user_id: str = Depends(get_current_user_id_from_header),
        position: str = Form("center"),
        opacity: float = Form(0.5),
        document_service: DocumentService = Depends(get_document_service)
):
    """
    Thêm watermark vào tài liệu Word.
    """
    try:
        if not file.filename.endswith(('.doc', '.docx')):
            raise HTTPException(status_code=400, detail="Chỉ chấp nhận file .doc hoặc .docx")

        content = await file.read()
        watermark_dto = WatermarkDTO(text=watermark_text, position=position, opacity=opacity)
        result = await document_service.add_watermark(content, file.filename, watermark_dto, current_user_id)

        return {
            "status": "success",
            "message": "Watermark đã được thêm thành công",
            "filename": result["filename"],
            "download_url": f"/documents/download/{result['id']}"
        }
    except Exception as e:
        logger.error(f"Lỗi khi thêm watermark: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/templates", summary="Lấy danh sách mẫu tài liệu Word")
async def get_templates(
        category: Optional[str] = None,
        skip: int = 0,
        limit: int = 10,
        template_service: TemplateService = Depends(get_template_service)
):
    """
    Lấy danh sách mẫu tài liệu Word từ hệ thống (public templates).
    """
    try:
        templates, total_count = await template_service.get_templates(category, skip, limit)
        return {"items": templates, "total_count": total_count}
    except Exception as e:
        logger.error(f"Lỗi khi lấy danh sách mẫu: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/templates/apply", summary="Áp dụng mẫu tài liệu Word")
async def apply_template(
        template_id: str = Form(...),
        data: str = Form(...),
        current_user_id: str = Depends(get_current_user_id_from_header),
        output_format: str = Form("docx"),
        template_service: TemplateService = Depends(get_template_service)
):
    """
    Áp dụng mẫu tài liệu Word với dữ liệu được cung cấp.
    """
    try:
        json_data = json.loads(data)
        template_data_dto = TemplateDataDTO(
            template_id=template_id,
            data=json_data,
            output_format=output_format,
            user_id=current_user_id
        )
        result = await template_service.apply_template(template_data_dto)

        return {
            "status": "success",
            "message": "Mẫu đã được áp dụng thành công",
            "filename": result["filename"],
            "download_url": f"/documents/download/{result['id']}"
        }
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Dữ liệu JSON không hợp lệ")
    except Exception as e:
        logger.error(f"Lỗi khi áp dụng mẫu: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/templates/batch", summary="Tạo nhiều tài liệu Word từ template")
async def create_batch_documents(
        background_tasks: BackgroundTasks,
        template_id: str = Form(...),
        data_file: UploadFile = File(...),
        current_user_id: str = Depends(get_current_user_id_from_header),
        output_format: str = Form("docx"),
        template_service: TemplateService = Depends(get_template_service)
):
    """
    Tạo nhiều tài liệu Word từ một template và tập dữ liệu (CSV, Excel).
    """
    try:
        if not data_file.filename.endswith(('.csv', '.xlsx', '.xls')):
            raise HTTPException(status_code=400, detail="Chỉ chấp nhận file .csv, .xlsx hoặc .xls")

        content = await data_file.read()
        result_task_id = await template_service.create_batch_documents_from_file(
            template_id=template_id, 
            file_content=content, 
            original_filename=data_file.filename,
            output_format=output_format, 
            user_id=current_user_id,
            background_tasks=background_tasks
            )

        return {
            "status": "processing",
            "message": "Yêu cầu tạo tài liệu hàng loạt đã được nhận và đang được xử lý.",
            "task_id": result_task_id
        }
    except Exception as e:
        logger.error(f"Lỗi khi tạo batch tài liệu: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/download/{document_id}", summary="Tải xuống tài liệu Word")
async def download_document(
        document_id: str = Path(..., description="ID của tài liệu"),
        current_user_id: str = Depends(get_current_user_id_from_header),
        document_service: DocumentService = Depends(get_document_service)
):
    """
    Tải xuống tài liệu Word theo ID.
    Service sẽ kiểm tra quyền truy cập dựa trên current_user_id.
    """
    try:
        file_path, media_type, filename = await document_service.download_document(document_id, current_user_id)
        if not file_path or not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Tài liệu không tồn tại hoặc không có quyền truy cập")
        
        response_background_tasks = BackgroundTasks()
        response_background_tasks.add_task(os.unlink, file_path)

        return FileResponse(path=file_path, media_type=media_type, filename=filename, background=response_background_tasks)
    except Exception as e:
        logger.error(f"Lỗi khi tải tài liệu {document_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Lỗi máy chủ khi tải tài liệu.")


@router.delete("/documents/{document_id}", summary="Xóa tài liệu Word")
async def delete_document(
        document_id: str = Path(..., description="ID của tài liệu"),
        current_user_id: str = Depends(get_current_user_id_from_header),
        document_service: DocumentService = Depends(get_document_service)
):
    """
    Xóa tài liệu Word theo ID.
    Service sẽ kiểm tra quyền xóa dựa trên current_user_id.
    """
    try:
        await document_service.delete_document(document_id, current_user_id)
        return {"status": "success", "message": "Tài liệu đã được xóa thành công"}
    except Exception as e:
        logger.error(f"Lỗi khi xóa tài liệu {document_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/templates/internship-report", summary="Tạo báo cáo kết quả thực tập")
async def create_internship_report(
        data: InternshipReportModel,
        current_user_id: str = Depends(get_current_user_id_from_header),
        template_service: TemplateService = Depends(get_template_service)
):
    """
    Tạo báo cáo kết quả thực tập từ mẫu.
    """
    try:
        result = await template_service.create_internship_report(data, current_user_id)
        return {
            "status": "success",
            "message": "Báo cáo thực tập đã được tạo thành công",
            "filename": result["filename"],
            "download_url": f"/documents/download/{result['id']}"
        }
    except Exception as e:
        logger.error(f"Lỗi khi tạo báo cáo thực tập: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/templates/reward-report", summary="Tạo báo cáo thưởng")
async def create_reward_report(
        data: RewardReportModel,
        current_user_id: str = Depends(get_current_user_id_from_header),
        template_service: TemplateService = Depends(get_template_service)
):
    """
    Tạo báo cáo thưởng từ mẫu.
    """
    try:
        result = await template_service.create_reward_report(data, current_user_id)
        return {
            "status": "success",
            "message": "Báo cáo thưởng đã được tạo thành công",
            "filename": result["filename"],
            "download_url": f"/documents/download/{result['id']}"
        }
    except Exception as e:
        logger.error(f"Lỗi khi tạo báo cáo thưởng: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/templates/labor-contract", summary="Tạo hợp đồng lao động")
async def create_labor_contract(
        data: LaborContractModel,
        current_user_id: str = Depends(get_current_user_id_from_header),
        template_service: TemplateService = Depends(get_template_service)
):
    """
    Tạo hợp đồng lao động từ mẫu.
    """
    try:
        result = await template_service.create_labor_contract(data, current_user_id)
        return {
            "status": "success",
            "message": "Hợp đồng lao động đã được tạo thành công",
            "filename": result["filename"],
            "download_url": f"/documents/download/{result['id']}"
        }
    except Exception as e:
        logger.error(f"Lỗi khi tạo hợp đồng lao động: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/templates/invitation", summary="Tạo lời mời từ danh sách nhân viên")
async def generate_invitations(
        background_tasks: BackgroundTasks,
        data_file: UploadFile = File(...),
        output_format: str = Form("docx"),
        current_user_id: str = Depends(get_current_user_id_from_header),
        template_service: TemplateService = Depends(get_template_service)
):
    """
    Tạo lời mời từ danh sách nhân viên trong file Excel.
    
    - **data_file**: File Excel chứa danh sách nhân viên
    - **output_format**: Định dạng đầu ra (docx, pdf, zip)
    """
    try:
        if not data_file.filename.endswith(('.xlsx', '.xls', '.csv')):
            raise HTTPException(status_code=400, detail="Chỉ chấp nhận file Excel (.xlsx, .xls) hoặc CSV (.csv)")

        file_content = await data_file.read()
        task_id = await template_service.generate_invitations_from_file(
            file_content=file_content,
            original_filename=data_file.filename,
            output_format=output_format,
            user_id=current_user_id,
            background_tasks=background_tasks
        )
        return {
            "status": "processing",
            "message": "Yêu cầu tạo lời mời hàng loạt đang được xử lý.",
            "task_id": task_id
        }
    except Exception as e:
        logger.error(f"Lỗi khi tạo lời mời hàng loạt: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))