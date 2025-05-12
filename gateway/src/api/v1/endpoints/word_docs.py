from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Depends, Query
from fastapi.responses import JSONResponse, FileResponse
import httpx
from typing import List, Optional, Dict, Any
import os
import tempfile
import shutil
from core.config import settings
from utils.client import ServiceClient
from api.v1.endpoints.auth import get_current_user

router = APIRouter()
word_service = ServiceClient(settings.WORD_SERVICE_URL)


@router.get("/", summary="Lấy danh sách tài liệu Word")
async def get_word_documents(
        skip: int = 0,
        limit: int = 10,
        search: Optional[str] = None,
        current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Lấy danh sách tài liệu Word từ hệ thống.
    """
    params = {"skip": skip, "limit": limit, "user_id": current_user["id"]}
    if search:
        params["search"] = search

    response = await word_service.get("/documents", params=params)
    return response


@router.post("/upload", summary="Tải lên tài liệu Word mới")
async def upload_word_document(
        file: UploadFile = File(...),
        title: Optional[str] = Form(None),
        description: Optional[str] = Form(None),
        background_tasks: BackgroundTasks = None,
        current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Tải lên tài liệu Word mới vào hệ thống.
    """
    if not file.filename.endswith(('.doc', '.docx')):
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận file .doc hoặc .docx")

    response = await word_service.upload_file(
        "/documents/upload",
        file=file,
        data={
            "title": title, 
            "description": description,
            "user_id": str(current_user["id"])
        }
    )

    return response


@router.post("/convert/to-pdf", summary="Chuyển đổi tài liệu Word sang PDF")
async def convert_word_to_pdf(
        file: UploadFile = File(...),
        background_tasks: BackgroundTasks = None,
        current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Chuyển đổi tài liệu Word sang định dạng PDF.
    """
    if not file.filename.endswith(('.doc', '.docx')):
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận file .doc hoặc .docx")

    response = await word_service.upload_file(
        "/documents/convert/to-pdf",
        file=file,
        data={"user_id": str(current_user["id"])}
    )

    return response


@router.post("/templates/apply", summary="Áp dụng mẫu tài liệu Word")
async def apply_word_template(
        template_id: str = Form(...),
        data: str = Form(...),
        output_format: str = Form("docx"),
        current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Áp dụng mẫu tài liệu Word với dữ liệu được cung cấp.

    - **template_id**: ID của mẫu tài liệu
    - **data**: Dữ liệu JSON cho mẫu (dạng chuỗi JSON)
    - **output_format**: Định dạng đầu ra (docx, pdf)
    """
    response = await word_service.post(
        "/documents/templates/apply",
        json={
            "template_id": template_id,
            "data": data,
            "output_format": output_format,
            "user_id": current_user["id"]
        }
    )

    return response


@router.post("/watermark", summary="Thêm watermark vào tài liệu Word")
async def add_watermark_to_word(
        file: UploadFile = File(...),
        watermark_text: str = Form(...),
        position: str = Form("center"),
        opacity: float = Form(0.5),
        current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Thêm watermark vào tài liệu Word.

    - **file**: Tài liệu Word cần thêm watermark
    - **watermark_text**: Nội dung watermark
    - **position**: Vị trí của watermark (center, top-left, top-right, bottom-left, bottom-right)
    - **opacity**: Độ mờ của watermark (0.0 - 1.0)
    """
    if not file.filename.endswith(('.doc', '.docx')):
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận file .doc hoặc .docx")

    response = await word_service.upload_file(
        "/documents/watermark",
        file=file,
        data={
            "watermark_text": watermark_text,
            "position": position,
            "opacity": str(opacity),
            "user_id": str(current_user["id"])
        }
    )

    return response


@router.get("/templates", summary="Lấy danh sách mẫu tài liệu Word")
async def get_word_templates(
        category: Optional[str] = None,
        skip: int = 0,
        limit: int = 10,
        current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Lấy danh sách mẫu tài liệu Word từ hệ thống.
    """
    params = {"skip": skip, "limit": limit, "user_id": current_user["id"]}
    if category:
        params["category"] = category

    response = await word_service.get("/documents/templates", params=params)
    return response


@router.get("/download/{document_id}", summary="Tải xuống tài liệu Word")
async def download_word_document(
    document_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Tải xuống tài liệu Word theo ID.
    """
    return await word_service.get_file(f"/documents/download/{document_id}?user_id={current_user['id']}")


@router.delete("/{document_id}", summary="Xóa tài liệu Word")
async def delete_word_document(
    document_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Xóa tài liệu Word theo ID.
    """
    response = await word_service.delete(f"/documents/{document_id}?user_id={current_user['id']}")
    return response


@router.post("/batch", summary="Tạo nhiều tài liệu Word từ template")
async def create_batch_word_documents(
        template_id: str = Form(...),
        data_file: UploadFile = File(...),
        output_format: str = Form("docx"),
        current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Tạo nhiều tài liệu Word từ một template và tập dữ liệu (CSV, Excel).

    - **template_id**: ID của mẫu tài liệu
    - **data_file**: File dữ liệu CSV hoặc Excel
    - **output_format**: Định dạng đầu ra (docx, pdf, zip)
    """
    if not data_file.filename.endswith(('.csv', '.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận file .csv, .xlsx hoặc .xls")

    response = await word_service.upload_file(
        "/documents/templates/batch",
        file=data_file,
        data={
            "template_id": template_id,
            "output_format": output_format,
            "user_id": str(current_user["id"])
        }
    )

    return response


@router.post("/templates/internship-report", summary="Tạo báo cáo kết quả thực tập")
async def create_internship_report(
        department: str = Form(..., description="Tên phòng ban"),
        location: str = Form(..., description="Địa danh"),
        day: str = Form(..., description="Ngày (2 chữ số)"),
        month: str = Form(..., description="Tháng (2 chữ số)"),
        year: str = Form(..., description="Năm (4 chữ số)"),
        intern_name: str = Form(..., description="Họ và tên thực tập sinh"),
        internship_duration: str = Form(..., description="Thời gian thực tập"),
        supervisor_name: str = Form(..., description="Tên người hướng dẫn"),
        ethics_evaluation: str = Form(..., description="Đánh giá phẩm chất đạo đức"),
        capacity_evaluation: str = Form(..., description="Đánh giá năng lực"),
        compliance_evaluation: str = Form(..., description="Đánh giá ý thức chấp hành"),
        group_activities: str = Form(..., description="Đánh giá hoạt động đoàn thể"),
        current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Tạo báo cáo kết quả thực tập từ mẫu.
    """
    response = await word_service.post(
        "/documents/templates/internship-report",
        json={
            "department": department,
            "location": location,
            "day": day,
            "month": month,
            "year": year,
            "intern_name": intern_name,
            "internship_duration": internship_duration,
            "supervisor_name": supervisor_name,
            "ethics_evaluation": ethics_evaluation,
            "capacity_evaluation": capacity_evaluation,
            "compliance_evaluation": compliance_evaluation,
            "group_activities": group_activities,
            "user_id": current_user["id"]
        }
    )

    return response


@router.post("/templates/reward-report", summary="Tạo báo cáo thưởng")
async def create_reward_report(
        location: str = Form(..., description="Địa danh"),
        day: str = Form(..., description="Ngày (2 chữ số)"),
        month: str = Form(..., description="Tháng (2 chữ số)"),
        year: str = Form(..., description="Năm (4 chữ số)"),
        title: str = Form(..., description="Tiêu đề báo cáo"),
        recipient: str = Form(..., description="Người nhận báo cáo"),
        approver_name: str = Form(..., description="Người ký xác nhận"),
        submitter_name: str = Form(..., description="Người làm đơn"),
        current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Tạo báo cáo thưởng từ mẫu.
    """
    response = await word_service.post(
        "/documents/templates/reward-report",
        json={
            "location": location,
            "day": day,
            "month": month,
            "year": year,
            "title": title,
            "recipient": recipient,
            "approver_name": approver_name,
            "submitter_name": submitter_name,
            "user_id": current_user["id"]
        }
    )

    return response


@router.post("/templates/labor-contract", summary="Tạo hợp đồng lao động")
async def create_labor_contract(
        contract_number: str = Form(..., description="Số hợp đồng"),
        day: str = Form(..., description="Ngày ký (2 chữ số)"),
        month: str = Form(..., description="Tháng ký (2 chữ số)"),
        year: str = Form(..., description="Năm ký (4 chữ số)"),
        representative_name: str = Form(..., description="Tên người đại diện công ty"),
        position: str = Form(..., description="Chức vụ người đại diện"),
        employee_name: str = Form(..., description="Tên người lao động"),
        nationality: str = Form(..., description="Quốc tịch"),
        date_of_birth: str = Form(..., description="Ngày tháng năm sinh (dd/mm/yyyy)"),
        gender: str = Form(..., description="Giới tính (Nam/Nữ)"),
        profession: str = Form(..., description="Nghề nghiệp"),
        permanent_address: str = Form(..., description="Địa chỉ thường trú"),
        current_address: str = Form(..., description="Địa chỉ cư trú hiện tại"),
        id_number: str = Form(..., description="Số CMND/CCCD"),
        id_issue_date: str = Form(..., description="Ngày cấp CMND/CCCD"),
        id_issue_place: str = Form(..., description="Nơi cấp CMND/CCCD"),
        job_position: str = Form(..., description="Vị trí công việc"),
        start_date: str = Form(..., description="Ngày bắt đầu làm việc"),
        end_date: str = Form(..., description="Ngày kết thúc hợp đồng"),
        salary: str = Form(..., description="Mức lương cơ bản"),
        allowance: str = Form(..., description="Phụ cấp (nếu có)"),
        current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Tạo hợp đồng lao động từ mẫu.
    """
    response = await word_service.post(
        "/documents/templates/labor-contract",
        json={
            "contract_number": contract_number,
            "day": day,
            "month": month,
            "year": year,
            "representative_name": representative_name,
            "position": position,
            "employee_name": employee_name,
            "nationality": nationality,
            "date_of_birth": date_of_birth,
            "gender": gender,
            "profession": profession,
            "permanent_address": permanent_address,
            "current_address": current_address,
            "id_number": id_number,
            "id_issue_date": id_issue_date,
            "id_issue_place": id_issue_place,
            "job_position": job_position,
            "start_date": start_date,
            "end_date": end_date,
            "salary": salary,
            "allowance": allowance,
            "user_id": current_user["id"]
        }
    )

    return response


@router.post("/templates/invitation", summary="Tạo lời mời từ danh sách nhân viên")
async def create_invitations(
        data_file: UploadFile = File(...),
        output_format: str = Form("docx"),
        current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Tạo lời mời từ danh sách nhân viên trong file Excel.
    """
    if not data_file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận file Excel (.xlsx, .xls)")

    response = await word_service.upload_file(
        "/documents/templates/invitation",
        file=data_file,
        data={
            "output_format": output_format,
            "user_id": str(current_user["id"])
        }
    )

    return response