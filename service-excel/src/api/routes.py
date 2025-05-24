from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Depends, Query, Path, Request, Header
from fastapi.responses import JSONResponse, FileResponse
from typing import List, Optional, Dict, Any
import os
import uuid
import tempfile
import shutil
from datetime import datetime
import json

from domain.models import ExcelDocumentInfo, ExcelTemplateInfo, ExcelDocumentCreate, ExcelDocumentUpdate
from application.dto import CreateDocumentDTO, TemplateDataDTO, MergeDocumentsDTO
from application.services import ExcelDocumentService, ExcelTemplateService
from infrastructure.repository import ExcelDocumentRepository, ExcelTemplateRepository
from infrastructure.minio_client import MinioClient
from infrastructure.rabbitmq_client import RabbitMQClient

router = APIRouter()

def get_user_id_from_header(x_user_id: Optional[str] = Header(None, alias="X-User-ID")) -> str:
    """Extract user_id from X-User-ID header and validate it as UUID."""
    if not x_user_id:
        raise HTTPException(status_code=400, detail="X-User-ID header is required")
    try:
        # Validate UUID format
        uuid.UUID(x_user_id)
        return x_user_id
    except ValueError:
        raise HTTPException(status_code=400, detail="X-User-ID header must be a valid UUID")

def get_document_service(request: Request):
    """Create ExcelDocumentService with proper dependencies."""
    db_session_factory = request.app.state.db_session_factory
    if not db_session_factory:
        raise HTTPException(status_code=503, detail="Database session factory is not available.")
    
    minio_client = MinioClient()
    rabbitmq_client = RabbitMQClient()
    document_repo = ExcelDocumentRepository(db_session_factory)  # Updated constructor
    return ExcelDocumentService(document_repo, minio_client, rabbitmq_client)

def get_template_service():
    """Create ExcelTemplateService with proper dependencies."""
    minio_client = MinioClient()
    rabbitmq_client = RabbitMQClient()
    template_repo = ExcelTemplateRepository(minio_client)
    return ExcelTemplateService(template_repo, minio_client, rabbitmq_client)

@router.get("/documents", summary="Lấy danh sách tài liệu Excel")
async def get_documents(
        skip: int = Query(0, ge=0),
        limit: int = Query(10, ge=1, le=100),
        search: Optional[str] = Query(None),
        sort_by: str = Query('created_at'),
        sort_order: str = Query('desc'),
        user_id: str = Depends(get_user_id_from_header),
        document_service: ExcelDocumentService = Depends(get_document_service)
):
    """
    Lấy danh sách tài liệu Excel của người dùng từ hệ thống.
    Sử dụng user_id từ header X-User-ID.
    """
    try:
        documents, total_count = await document_service.list_documents_by_user(
            user_id=user_id,
            skip=skip,
            limit=limit,
            search_term=search,
            sort_by=sort_by,
            sort_order=sort_order
        )
        return {
            "items": [doc.model_dump() for doc in documents],
            "total": total_count,
            "skip": skip,
            "limit": limit
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/documents/upload", summary="Tải lên tài liệu Excel mới")
async def upload_document(
        file: UploadFile = File(...),
        title: Optional[str] = Form(None),
        description: Optional[str] = Form(None),
        background_tasks: BackgroundTasks = BackgroundTasks(),
        user_id: str = Depends(get_user_id_from_header),
        document_service: ExcelDocumentService = Depends(get_document_service)
):
    """
    Tải lên tài liệu Excel mới vào hệ thống.
    Sử dụng user_id từ header X-User-ID.
    """
    try:
        if not file.filename or not file.filename.lower().endswith(('.xls', '.xlsx')):
            raise HTTPException(status_code=400, detail="Chỉ chấp nhận file .xls hoặc .xlsx")

        doc_create_info = ExcelDocumentCreate(
            title=title,
            description=description
        )

        document_info = await document_service.upload_document(
            user_id=user_id,
            file=file,
            doc_create_info=doc_create_info,
            background_tasks=background_tasks
        )

        return {
            "id": document_info.id,
            "title": document_info.title,
            "description": document_info.description,
            "created_at": document_info.created_at.isoformat(),
            "file_size": document_info.file_size,
            "file_type": document_info.file_type,
            "original_filename": document_info.original_filename,
            "sheet_count": document_info.sheet_count,
            "user_id": document_info.user_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload document: {str(e)}")

@router.get("/documents/{document_id}", summary="Lấy thông tin tài liệu Excel")
async def get_document(
        document_id: str = Path(..., description="ID của tài liệu"),
        user_id: str = Depends(get_user_id_from_header),
        document_service: ExcelDocumentService = Depends(get_document_service)
):
    """
    Lấy thông tin chi tiết của một tài liệu Excel.
    """
    try:
        document_info = await document_service.get_document_by_id(document_id, user_id)
        return document_info.model_dump()
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/documents/{document_id}", summary="Cập nhật thông tin tài liệu Excel")
async def update_document(
        document_id: str = Path(..., description="ID của tài liệu"),
        title: Optional[str] = Form(None),
        description: Optional[str] = Form(None),
        user_id: str = Depends(get_user_id_from_header),
        document_service: ExcelDocumentService = Depends(get_document_service)
):
    """
    Cập nhật thông tin tài liệu Excel.
    """
    try:
        update_data = ExcelDocumentUpdate(title=title, description=description)
        updated_document = await document_service.update_document_metadata(document_id, user_id, update_data)
        return updated_document.model_dump()
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/documents/{document_id}/convert/to-pdf", summary="Chuyển đổi tài liệu Excel sang PDF")
async def convert_to_pdf(
        document_id: str = Path(..., description="ID của tài liệu Excel"),
        background_tasks: BackgroundTasks = BackgroundTasks(),
        user_id: str = Depends(get_user_id_from_header),
        document_service: ExcelDocumentService = Depends(get_document_service)
):
    """
    Chuyển đổi tài liệu Excel sang định dạng PDF.
    """
    try:
        temp_pdf_path, pdf_filename = await document_service.convert_to_pdf(
            user_id=user_id,
            doc_id=document_id,
            background_tasks=background_tasks
        )
        
        return FileResponse(
            path=temp_pdf_path,
            filename=pdf_filename,
            media_type="application/pdf"
        )
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
        raise HTTPException(status_code=500, detail=f"Failed to convert to PDF: {str(e)}")

@router.post("/documents/{document_id}/convert/to-word", summary="Chuyển đổi tài liệu Excel sang Word")
async def convert_to_word(
        document_id: str = Path(..., description="ID của tài liệu Excel"),
        background_tasks: BackgroundTasks = BackgroundTasks(),
        user_id: str = Depends(get_user_id_from_header),
        document_service: ExcelDocumentService = Depends(get_document_service)
):
    """
    Chuyển đổi tài liệu Excel sang định dạng Word và lưu vào hệ thống.
    """
    try:
        word_document = await document_service.convert_to_word(
            user_id=user_id,
            doc_id=document_id,
            background_tasks=background_tasks
        )
        
        return {
            "id": word_document.id,
            "title": word_document.title,
            "original_filename": word_document.original_filename,
            "file_size": word_document.file_size,
            "message": "Document converted to Word successfully"
        }
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
        raise HTTPException(status_code=500, detail=f"Failed to convert to Word: {str(e)}")

@router.post("/documents/merge", summary="Gộp nhiều file Excel thành một")
async def merge_excel_documents(
        document_ids: List[str] = Form(..., description="Danh sách ID các tài liệu cần gộp"),
        output_filename: str = Form(..., description="Tên file kết quả"),
        background_tasks: BackgroundTasks = BackgroundTasks(),
        user_id: str = Depends(get_user_id_from_header),
        document_service: ExcelDocumentService = Depends(get_document_service)
):
    """
    Gộp nhiều tài liệu Excel đã có trong hệ thống thành một file duy nhất.
    """
    try:
        if not document_ids:
            raise HTTPException(status_code=400, detail="At least one document ID is required")
        
        # Parse document_ids if it's a JSON string
        if isinstance(document_ids, str):
            try:
                document_ids = json.loads(document_ids)
            except json.JSONDecodeError:
                # If it's not valid JSON, treat as a single ID
                document_ids = [document_ids]

        merge_dto = MergeDocumentsDTO(
            document_ids=document_ids,
            output_filename=output_filename if output_filename.lower().endswith(('.xls', '.xlsx')) else f"{output_filename}.xlsx"
        )

        merged_document = await document_service.merge_documents(
            user_id=user_id,
            dto=merge_dto,
            background_tasks=background_tasks
        )

        return {
            "id": merged_document.id,
            "title": merged_document.title,
            "original_filename": merged_document.original_filename,
            "file_size": merged_document.file_size,
            "sheet_count": merged_document.sheet_count,
            "message": "Documents merged successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to merge documents: {str(e)}")

@router.post("/documents/merge/async", summary="Gộp nhiều file Excel bất đồng bộ")
async def merge_excel_documents_async(
        document_ids: List[str] = Form(..., description="Danh sách ID các tài liệu cần gộp"),
        output_filename: str = Form(..., description="Tên file kết quả"),
        user_id: str = Depends(get_user_id_from_header),
        document_service: ExcelDocumentService = Depends(get_document_service)
):
    """
    Gộp nhiều tài liệu Excel bất đồng bộ thông qua RabbitMQ.
    """
    try:
        if not document_ids:
            raise HTTPException(status_code=400, detail="At least one document ID is required")
        
        # Parse document_ids if it's a JSON string
        if isinstance(document_ids, str):
            try:
                document_ids = json.loads(document_ids)
            except json.JSONDecodeError:
                document_ids = [document_ids]

        task_id = str(uuid.uuid4())
        merge_dto = MergeDocumentsDTO(
            document_ids=document_ids,
            output_filename=output_filename if output_filename.lower().endswith(('.xls', '.xlsx')) else f"{output_filename}.xlsx"
        )

        await document_service.merge_documents_async(
            user_id=user_id,
            task_id=task_id,
            dto=merge_dto
        )

        return {
            "task_id": task_id,
            "status": "submitted",
            "message": "Merge task submitted successfully. Use GET /status/merge/{task_id} to check progress."
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit merge task: {str(e)}")

@router.get("/documents/download/{document_id}", summary="Tải xuống tài liệu Excel")
async def download_document(
        document_id: str = Path(..., description="ID của tài liệu"),
        background_tasks: BackgroundTasks = BackgroundTasks(),
        user_id: str = Depends(get_user_id_from_header),
        document_service: ExcelDocumentService = Depends(get_document_service)
):
    """
    Tải xuống tài liệu Excel.
    """
    try:
        temp_download_path, original_filename, file_size = await document_service.download_document_content(
            doc_id=document_id,
            user_id=user_id,
            background_tasks=background_tasks
        )

        return FileResponse(
            path=temp_download_path,
            filename=original_filename,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
        raise HTTPException(status_code=500, detail=f"Failed to download document: {str(e)}")

@router.delete("/documents/{document_id}", summary="Xóa tài liệu Excel")
async def delete_document(
        document_id: str = Path(..., description="ID của tài liệu"),
        background_tasks: BackgroundTasks = BackgroundTasks(),
        user_id: str = Depends(get_user_id_from_header),
        document_service: ExcelDocumentService = Depends(get_document_service)
):
    """
    Xóa tài liệu Excel.
    """
    try:
        deleted = await document_service.delete_document(
            doc_id=document_id,
            user_id=user_id,
            background_tasks=background_tasks
        )
        
        if deleted:
            return {"message": f"Document {document_id} deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")

@router.post("/documents/{document_id}/process/async", summary="Xử lý tài liệu bất đồng bộ")
async def process_document_async(
        document_id: str = Path(..., description="ID của tài liệu"),
        task_type: str = Form("convert_to_pdf", description="Loại tác vụ cần thực hiện"),
        user_id: str = Depends(get_user_id_from_header),
        document_service: ExcelDocumentService = Depends(get_document_service)
):
    """
    Xử lý tài liệu bất đồng bộ (ví dụ: convert to PDF, convert to Word).
    """
    try:
        result = await document_service.process_document_async(
            user_id=user_id,
            document_id=document_id,
            task_type=task_type
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit processing task: {str(e)}")

# Status endpoints
@router.get("/status/merge/{task_id}", summary="Kiểm tra trạng thái gộp tài liệu")
async def get_merge_status(
        task_id: str = Path(..., description="ID của tác vụ gộp tài liệu"),
        user_id: str = Depends(get_user_id_from_header),
        document_service: ExcelDocumentService = Depends(get_document_service)
):
    """
    Kiểm tra trạng thái của tác vụ gộp tài liệu bất đồng bộ.
    """
    try:
        status = await document_service.get_merge_status(user_id, task_id)
        return status
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get merge status: {str(e)}")

@router.get("/templates", summary="Lấy danh sách mẫu tài liệu Excel")
async def get_templates(
        category: Optional[str] = Query(None),
        skip: int = Query(0, ge=0),
        limit: int = Query(10, ge=1, le=100),
        template_service: ExcelTemplateService = Depends(get_template_service)
):
    """
    Lấy danh sách mẫu tài liệu Excel.
    """
    try:
        templates = await template_service.get_templates(category, skip, limit)
        return {"items": templates, "total": len(templates)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
