from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Depends, Query, Path
from fastapi.responses import JSONResponse, FileResponse
from typing import List, Optional, Dict, Any
import os
import uuid
import tempfile
import shutil
from datetime import datetime
import json

from domain.models import ExcelDocumentInfo, ExcelTemplateInfo
from application.dto import CreateDocumentDTO, TemplateDataDTO, MergeDocumentsDTO
from application.services import ExcelDocumentService, ExcelTemplateService
from infrastructure.repository import ExcelDocumentRepository, ExcelTemplateRepository
from infrastructure.minio_client import MinioClient
from infrastructure.rabbitmq_client import RabbitMQClient

router = APIRouter()


def get_document_service():
    minio_client = MinioClient()
    rabbitmq_client = RabbitMQClient()
    document_repo = ExcelDocumentRepository(minio_client)
    return ExcelDocumentService(document_repo, minio_client, rabbitmq_client)


def get_template_service():
    minio_client = MinioClient()
    rabbitmq_client = RabbitMQClient()
    template_repo = ExcelTemplateRepository(minio_client)
    return ExcelTemplateService(template_repo, minio_client, rabbitmq_client)


@router.get("/documents", summary="Lấy danh sách tài liệu Excel")
async def get_documents(
        skip: int = 0,
        limit: int = 10,
        search: Optional[str] = None,
        document_service: ExcelDocumentService = Depends(get_document_service)
):
    """
    Lấy danh sách tài liệu Excel từ hệ thống.
    """
    try:
        documents = await document_service.get_documents(skip, limit, search)
        return {"items": documents, "total": len(documents)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/upload", summary="Tải lên tài liệu Excel mới")
async def upload_document(
        file: UploadFile = File(...),
        title: Optional[str] = Form(None),
        description: Optional[str] = Form(None),
        background_tasks: BackgroundTasks = None,
        document_service: ExcelDocumentService = Depends(get_document_service)
):
    """
    Tải lên tài liệu Excel mới vào hệ thống.
    """
    try:
        if not file.filename.endswith(('.xls', '.xlsx')):
            raise HTTPException(status_code=400, detail="Chỉ chấp nhận file .xls hoặc .xlsx")

        document_dto = CreateDocumentDTO(
            title=title or os.path.splitext(file.filename)[0],
            description=description or "",
            original_filename=file.filename
        )

        content = await file.read()

        document_info = await document_service.create_document(document_dto, content)

        if background_tasks:
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
            "original_filename": document_info.original_filename,
            "sheet_names": document_info.sheet_names
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/convert/to-pdf", summary="Chuyển đổi tài liệu Excel sang PDF")
async def convert_to_pdf(
        file: UploadFile = File(...),
        background_tasks: BackgroundTasks = None,
        document_service: ExcelDocumentService = Depends(get_document_service)
):
    """
    Chuyển đổi tài liệu Excel sang định dạng PDF.
    """
    try:
        if not file.filename.endswith(('.xls', '.xlsx')):
            raise HTTPException(status_code=400, detail="Chỉ chấp nhận file .xls hoặc .xlsx")

        content = await file.read()

        result = await document_service.convert_to_pdf(content, file.filename)

        return {
            "status": "success",
            "message": "Tài liệu đã được chuyển đổi thành công",
            "filename": result["filename"],
            "download_url": f"/documents/download/{result['id']}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/convert/to-word", summary="Chuyển đổi tài liệu Excel sang Word")
async def convert_to_word(
        file: UploadFile = File(...),
        background_tasks: BackgroundTasks = None,
        document_service: ExcelDocumentService = Depends(get_document_service)
):
    """
    Chuyển đổi tài liệu Excel sang định dạng Word.
    """
    try:
        if not file.filename.endswith(('.xls', '.xlsx')):
            raise HTTPException(status_code=400, detail="Chỉ chấp nhận file .xls hoặc .xlsx")

        content = await file.read()

        result = await document_service.convert_to_word(content, file.filename)

        return {
            "status": "success",
            "message": "Tài liệu đã được chuyển đổi thành công",
            "filename": result["filename"],
            "download_url": f"/documents/download/{result['id']}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/merge", summary="Gộp nhiều file Excel thành một")
async def merge_excel_files(
        files: List[UploadFile] = File(...),
        output_filename: str = Form(...),
        background_tasks: BackgroundTasks = None,
        document_service: ExcelDocumentService = Depends(get_document_service)
):
    """
    Gộp nhiều file Excel thành một file duy nhất.

    - **files**: Danh sách các file Excel cần gộp
    - **output_filename**: Tên file kết quả
    """
    try:
        for file in files:
            if not file.filename.endswith(('.xls', '.xlsx')):
                raise HTTPException(status_code=400,
                                    detail=f"File {file.filename} không phải là file Excel (.xls, .xlsx)")

        document_ids = []

        for file in files:
            content = await file.read()

            document_dto = CreateDocumentDTO(
                title=os.path.splitext(file.filename)[0],
                description=f"Phần của tài liệu gộp: {output_filename}",
                original_filename=file.filename
            )

            document_info = await document_service.create_document(document_dto, content)

            document_ids.append(document_info.id)

        merge_dto = MergeDocumentsDTO(
            document_ids=document_ids,
            output_filename=output_filename if output_filename.endswith('.xlsx') else f"{output_filename}.xlsx"
        )

        if background_tasks:
            task_id = str(uuid.uuid4())
            background_tasks.add_task(
                document_service.merge_documents_async,
                task_id,
                merge_dto
            )

            return {
                "status": "processing",
                "message": "Yêu cầu gộp tài liệu đang được xử lý",
                "task_id": task_id
            }
        else:
            result = await document_service.merge_documents(merge_dto)

            return {
                "status": "success",
                "message": "Các tài liệu đã được gộp thành công",
                "filename": result["filename"],
                "download_url": f"/documents/download/{result['id']}"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/templates", summary="Lấy danh sách mẫu tài liệu Excel")
async def get_templates(
        category: Optional[str] = None,
        skip: int = 0,
        limit: int = 10,
        template_service: ExcelTemplateService = Depends(get_template_service)
):
    """
    Lấy danh sách mẫu tài liệu Excel từ hệ thống.
    """
    try:
        templates = await template_service.get_templates(category, skip, limit)
        return {"items": templates, "total": len(templates)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/templates/apply", summary="Áp dụng mẫu tài liệu Excel")
async def apply_template(
        template_id: str = Form(...),
        data: str = Form(...),
        output_format: str = Form("xlsx"),
        template_service: ExcelTemplateService = Depends(get_template_service)
):
    """
    Áp dụng mẫu tài liệu Excel với dữ liệu được cung cấp.

    - **template_id**: ID của mẫu tài liệu
    - **data**: Dữ liệu JSON cho mẫu (dạng chuỗi JSON)
    - **output_format**: Định dạng đầu ra (xlsx, pdf)
    """
    try:
        json_data = json.loads(data)

        template_data_dto = TemplateDataDTO(
            template_id=template_id,
            data=json_data,
            output_format=output_format
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
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/download/{document_id}", summary="Tải xuống tài liệu Excel")
async def download_document(
        document_id: str = Path(..., description="ID của tài liệu"),
        document_service: ExcelDocumentService = Depends(get_document_service)
):
    """
    Tải xuống tài liệu Excel theo ID.
    """
    try:
        document_info, document_content = await document_service.get_document(document_id)

        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{document_info.original_filename}") as temp:
            temp.write(document_content)
            temp_path = temp.name

        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if document_info.original_filename.endswith(
            ".xlsx") else "application/vnd.ms-excel"

        return FileResponse(
            path=temp_path,
            filename=document_info.original_filename,
            media_type=media_type,
            background=BackgroundTasks().add_task(lambda: os.unlink(temp_path))
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/documents/{document_id}", summary="Xóa tài liệu Excel")
async def delete_document(
        document_id: str = Path(..., description="ID của tài liệu"),
        document_service: ExcelDocumentService = Depends(get_document_service)
):
    """
    Xóa tài liệu Excel theo ID.
    """
    try:
        await document_service.delete_document(document_id)
        return {"status": "success", "message": "Tài liệu đã được xóa thành công"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/templates/batch", summary="Tạo nhiều tài liệu Excel từ template")
async def create_batch_documents(
        template_id: str = Form(...),
        data_file: UploadFile = File(...),
        output_format: str = Form("xlsx"),
        background_tasks: BackgroundTasks = None,
        template_service: ExcelTemplateService = Depends(get_template_service)
):
    """
    Tạo nhiều tài liệu Excel từ một template và tập dữ liệu (CSV, JSON).

    - **template_id**: ID của mẫu tài liệu
    - **data_file**: File dữ liệu CSV hoặc JSON
    - **output_format**: Định dạng đầu ra (xlsx, pdf, zip)
    """
    try:
        if not data_file.filename.endswith(('.csv', '.json')):
            raise HTTPException(status_code=400, detail="Chỉ chấp nhận file .csv hoặc .json")

        content = await data_file.read()

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


@router.get("/documents/sheet_names/{document_id}", summary="Lấy danh sách tên sheet của tài liệu Excel")
async def get_sheet_names(
        document_id: str = Path(..., description="ID của tài liệu"),
        document_service: ExcelDocumentService = Depends(get_document_service)
):
    """
    Lấy danh sách tên sheet của tài liệu Excel.
    """
    try:
        document_info, _ = await document_service.get_document(document_id)
        return {"sheet_names": document_info.sheet_names}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/batch/{task_id}", summary="Kiểm tra trạng thái xử lý batch")
async def get_batch_status(
        task_id: str = Path(..., description="ID của tác vụ batch"),
        template_service: ExcelTemplateService = Depends(get_template_service)
):
    """
    Kiểm tra trạng thái xử lý batch.
    """
    try:
        status = await template_service.get_batch_status(task_id)
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/merge/{task_id}", summary="Kiểm tra trạng thái gộp tài liệu")
async def get_merge_status(
        task_id: str = Path(..., description="ID của tác vụ gộp tài liệu"),
        document_service: ExcelDocumentService = Depends(get_document_service)
):
    """
    Kiểm tra trạng thái gộp tài liệu.
    """
    try:
        status = await document_service.get_merge_status(task_id)
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))