from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Depends, Query, Path
from fastapi.responses import JSONResponse, FileResponse
from typing import List, Optional, Dict, Any
import os
import uuid
import tempfile
import shutil
from datetime import datetime
import json

from domain.models import DocumentInfo, TemplateInfo
from application.dto import CreateDocumentDTO, TemplateDataDTO, WatermarkDTO
from application.services import DocumentService, TemplateService
from infrastructure.repository import DocumentRepository, TemplateRepository
from infrastructure.minio_client import MinioClient
from infrastructure.rabbitmq_client import RabbitMQClient

router = APIRouter()


# Khởi tạo dependencies
def get_document_service():
    minio_client = MinioClient()
    rabbitmq_client = RabbitMQClient()
    document_repo = DocumentRepository(minio_client)
    return DocumentService(document_repo, minio_client, rabbitmq_client)


def get_template_service():
    minio_client = MinioClient()
    rabbitmq_client = RabbitMQClient()
    template_repo = TemplateRepository(minio_client)
    return TemplateService(template_repo, minio_client, rabbitmq_client)


# Routes cho tài liệu Word
@router.get("/documents", summary="Lấy danh sách tài liệu Word")
async def get_documents(
        skip: int = 0,
        limit: int = 10,
        search: Optional[str] = None,
        document_service: DocumentService = Depends(get_document_service)
):
    """
    Lấy danh sách tài liệu Word từ hệ thống.
    """
    try:
        documents = await document_service.get_documents(skip, limit, search)
        return {"items": documents, "total": len(documents)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/upload", summary="Tải lên tài liệu Word mới")
async def upload_document(
        file: UploadFile = File(...),
        title: Optional[str] = Form(None),
        description: Optional[str] = Form(None),
        background_tasks: BackgroundTasks = None,
        document_service: DocumentService = Depends(get_document_service)
):
    """
    Tải lên tài liệu Word mới vào hệ thống.
    """
    try:
        # Kiểm tra loại file
        if not file.filename.endswith(('.doc', '.docx')):
            raise HTTPException(status_code=400, detail="Chỉ chấp nhận file .doc hoặc .docx")

        # Tạo DTO và lưu tài liệu
        document_dto = CreateDocumentDTO(
            title=title or os.path.splitext(file.filename)[0],
            description=description or "",
            original_filename=file.filename
        )

        # Đọc nội dung file
        content = await file.read()

        # Lưu tài liệu
        document_info = await document_service.create_document(document_dto, content)

        if background_tasks:
            # Thêm tác vụ nền (nếu cần)
            background_tasks.add_task(
                document_service.process_document_async,
                document_info.id
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
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/convert/to-pdf", summary="Chuyển đổi tài liệu Word sang PDF")
async def convert_to_pdf(
        file: UploadFile = File(...),
        background_tasks: BackgroundTasks = None,
        document_service: DocumentService = Depends(get_document_service)
):
    """
    Chuyển đổi tài liệu Word sang định dạng PDF.
    """
    try:
        # Kiểm tra loại file
        if not file.filename.endswith(('.doc', '.docx')):
            raise HTTPException(status_code=400, detail="Chỉ chấp nhận file .doc hoặc .docx")

        # Đọc nội dung file
        content = await file.read()

        # Chuyển đổi tài liệu
        result = await document_service.convert_to_pdf(content, file.filename)

        return {
            "status": "success",
            "message": "Tài liệu đã được chuyển đổi thành công",
            "filename": result["filename"],
            "download_url": f"/documents/download/{result['id']}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/watermark", summary="Thêm watermark vào tài liệu Word")
async def add_watermark(
        file: UploadFile = File(...),
        watermark_text: str = Form(...),
        position: str = Form("center"),
        opacity: float = Form(0.5),
        document_service: DocumentService = Depends(get_document_service)
):
    """
    Thêm watermark vào tài liệu Word.

    - **file**: Tài liệu Word cần thêm watermark
    - **watermark_text**: Nội dung watermark
    - **position**: Vị trí của watermark (center, top-left, top-right, bottom-left, bottom-right)
    - **opacity**: Độ mờ của watermark (0.0 - 1.0)
    """
    try:
        # Kiểm tra loại file
        if not file.filename.endswith(('.doc', '.docx')):
            raise HTTPException(status_code=400, detail="Chỉ chấp nhận file .doc hoặc .docx")

        # Đọc nội dung file
        content = await file.read()

        # Tạo DTO cho watermark
        watermark_dto = WatermarkDTO(
            text=watermark_text,
            position=position,
            opacity=opacity
        )

        # Thêm watermark
        result = await document_service.add_watermark(content, file.filename, watermark_dto)

        return {
            "status": "success",
            "message": "Watermark đã được thêm thành công",
            "filename": result["filename"],
            "download_url": f"/documents/download/{result['id']}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/templates", summary="Lấy danh sách mẫu tài liệu Word")
async def get_templates(
        category: Optional[str] = None,
        skip: int = 0,
        limit: int = 10,
        template_service: TemplateService = Depends(get_template_service)
):
    """
    Lấy danh sách mẫu tài liệu Word từ hệ thống.
    """
    try:
        templates = await template_service.get_templates(category, skip, limit)
        return {"items": templates, "total": len(templates)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/templates/apply", summary="Áp dụng mẫu tài liệu Word")
async def apply_template(
        template_id: str = Form(...),
        data: str = Form(...),
        output_format: str = Form("docx"),
        template_service: TemplateService = Depends(get_template_service)
):
    """
    Áp dụng mẫu tài liệu Word với dữ liệu được cung cấp.

    - **template_id**: ID của mẫu tài liệu
    - **data**: Dữ liệu JSON cho mẫu (dạng chuỗi JSON)
    - **output_format**: Định dạng đầu ra (docx, pdf)
    """
    try:
        # Parse JSON data
        json_data = json.loads(data)

        # Tạo DTO
        template_data_dto = TemplateDataDTO(
            template_id=template_id,
            data=json_data,
            output_format=output_format
        )

        # Áp dụng mẫu
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
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/templates/batch", summary="Tạo nhiều tài liệu Word từ template")
async def create_batch_documents(
        template_id: str = Form(...),
        data_file: UploadFile = File(...),
        output_format: str = Form("docx"),
        background_tasks: BackgroundTasks = None,
        template_service: TemplateService = Depends(get_template_service)
):
    """
    Tạo nhiều tài liệu Word từ một template và tập dữ liệu (CSV, Excel).

    - **template_id**: ID của mẫu tài liệu
    - **data_file**: File dữ liệu CSV hoặc Excel
    - **output_format**: Định dạng đầu ra (docx, pdf, zip)
    """
    try:
        # Kiểm tra loại file
        if not data_file.filename.endswith(('.csv', '.xlsx', '.xls')):
            raise HTTPException(status_code=400, detail="Chỉ chấp nhận file .csv, .xlsx hoặc .xls")

        # Đọc nội dung file
        content = await data_file.read()

        # Thực hiện batch processing - đây là tác vụ nặng nên thực hiện bất đồng bộ
        task_id = str(uuid.uuid4())

        if background_tasks:
            background_tasks.add_task(
                template_service.process_batch_async,
                task_id,
                template_id,
                content,
                data_file.filename,
                output_format
            )

        return {
            "status": "processing",
            "message": "Yêu cầu tạo batch tài liệu đã được gửi đi",
            "task_id": task_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/download/{document_id}", summary="Tải xuống tài liệu Word")
async def download_document(
        document_id: str = Path(..., description="ID của tài liệu"),
        document_service: DocumentService = Depends(get_document_service)
):
    """
    Tải xuống tài liệu Word theo ID.
    """
    try:
        # Tải tài liệu
        document_info, document_content = await document_service.get_document(document_id)

        # Tạo file tạm
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{document_info.original_filename}") as temp:
            temp.write(document_content)
            temp_path = temp.name

        # Trả về file response
        return FileResponse(
            path=temp_path,
            filename=document_info.original_filename,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document" if document_info.original_filename.endswith(
                ".docx") else "application/msword",
            background=BackgroundTasks().add_task(lambda: os.unlink(temp_path))
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/documents/{document_id}", summary="Xóa tài liệu Word")
async def delete_document(
        document_id: str = Path(..., description="ID của tài liệu"),
        document_service: DocumentService = Depends(get_document_service)
):
    """
    Xóa tài liệu Word theo ID.
    """
    try:
        await document_service.delete_document(document_id)
        return {"status": "success", "message": "Tài liệu đã được xóa thành công"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))