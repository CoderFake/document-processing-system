from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field
import uuid
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class WordDocumentInfo(BaseModel):
    """
    Thông tin tài liệu Word
    """
    id: Optional[str] = None
    storage_id: Optional[str] = None
    title: str
    description: Optional[str] = ""
    file_size: Optional[int] = 0
    page_count: Optional[int] = None
    storage_path: Optional[str] = ""
    original_filename: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    doc_metadata: Dict[str, Any] = Field(default_factory=dict)
    user_id: Optional[str] = None
    document_category: str = "word"
    file_type: Optional[str] = None
    version: Optional[int] = 1
    checksum: Optional[str] = None

    def __init__(self, **data):
        if 'id' not in data or data['id'] is None:
            data['id'] = str(uuid.uuid4())
        if 'storage_id' not in data or data['storage_id'] is None:
            data['storage_id'] = str(uuid.uuid4())
        if 'created_at' not in data or data['created_at'] is None:
            data['created_at'] = datetime.now()
        super().__init__(**data)

    class Config:
        arbitrary_types_allowed = True
        from_attributes = True

class TemplateInfo(BaseModel):
    """
    Thông tin mẫu tài liệu Word
    """
    template_id: str
    name: str
    description: Optional[str] = ""
    category: str = "general"
    tags: List[str] = Field(default_factory=list)
    original_filename: str
    file_size: int = 0
    storage_path: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    doc_metadata: Dict[str, Any] = Field(default_factory=dict)

    def __init__(self, **data):
        if 'template_id' not in data:
            data['template_id'] = str(uuid.uuid4())
        if 'created_at' not in data or data['created_at'] is None:
            data['created_at'] = datetime.now()
        super().__init__(**data)

    class Config:
        arbitrary_types_allowed = True

class BatchProcessingInfo(BaseModel):
    """
    Thông tin xử lý hàng loạt
    """
    task_id: str
    user_id: str
    template_id: str
    status: str = "PROCESSING"
    total_files: int = 0
    processed_files: int = 0
    output_format: str = "docx"
    original_data_filename: str = ""
    generated_documents: List[Dict[str, str]] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __init__(self, **data):
        if 'task_id' not in data:
            data['task_id'] = str(uuid.uuid4())
        if 'created_at' not in data or data['created_at'] is None:
            data['created_at'] = datetime.now()
        super().__init__(**data)

    class Config:
        arbitrary_types_allowed = True

class InternshipReportModel(BaseModel):
    """
    Model cho báo cáo kết quả thực tập
    """
    department: str = Field(..., description="Tên phòng ban")
    location: str = Field(..., description="Địa danh")
    day: str = Field(..., description="Ngày (2 chữ số)")
    month: str = Field(..., description="Tháng (2 chữ số)")
    year: str = Field(..., description="Năm (4 chữ số)")
    intern_name: str = Field(..., description="Họ tên thực tập sinh")
    internship_duration: str = Field(..., description="Thời gian thực tập")
    supervisor_name: str = Field(..., description="Tên người hướng dẫn")
    ethics_evaluation: str = Field(..., description="Đánh giá phẩm chất đạo đức")
    capacity_evaluation: str = Field(..., description="Đánh giá năng lực")
    compliance_evaluation: str = Field(..., description="Đánh giá ý thức chấp hành")
    group_activities: str = Field(..., description="Đánh giá hoạt động đoàn thể")

class RewardReportModel(BaseModel):
    """
    Model cho báo cáo thưởng
    """
    location: str = Field(..., description="Địa danh")
    day: str = Field(..., description="Ngày (2 chữ số)")
    month: str = Field(..., description="Tháng (2 chữ số)")
    year: str = Field(..., description="Năm (4 chữ số)")
    title: str = Field(..., description="Tiêu đề báo cáo")
    recipient: str = Field(..., description="Người nhận báo cáo")
    approver_name: str = Field(..., description="Người ký xác nhận")
    submitter_name: str = Field(..., description="Người làm đơn")

class LaborContractModel(BaseModel):
    """
    Model cho hợp đồng lao động
    """
    contract_number: str = Field(..., description="Số hợp đồng")
    day: str = Field(..., description="Ngày ký")
    month: str = Field(..., description="Tháng ký")
    year: str = Field(..., description="Năm ký")
    representative_name: str = Field(..., description="Tên đại diện công ty")
    position: str = Field(..., description="Chức vụ đại diện")
    employee_name: str = Field(..., description="Tên nhân viên")
    nationality: str = Field(..., description="Quốc tịch")
    date_of_birth: str = Field(..., description="Ngày sinh")
    gender: str = Field(..., description="Giới tính")
    profession: str = Field(..., description="Nghề nghiệp")
    permanent_address: str = Field(..., description="Địa chỉ thường trú")
    current_address: str = Field(..., description="Địa chỉ hiện tại")
    id_number: str = Field(..., description="Số CMND/CCCD")
    id_issue_date: str = Field(..., description="Ngày cấp")
    id_issue_place: str = Field(..., description="Nơi cấp")
    job_position: str = Field(..., description="Vị trí công việc")
    start_date: str = Field(..., description="Ngày bắt đầu")
    end_date: str = Field(..., description="Ngày kết thúc")
    salary: str = Field(..., description="Mức lương")
    allowance: str = Field(..., description="Phụ cấp")