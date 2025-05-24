from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

class CreateDocumentDTO(BaseModel):
    """
    DTO để tạo mới tài liệu Word.
    """
    title: str
    description: str = ""
    original_filename: str
    doc_metadata: Dict[str, Any] = Field(default_factory=dict)
    user_id: Optional[str] = None

    def __init__(
        self,
        title: str,
        description: str,
        original_filename: str,
        doc_metadata: Dict[str, Any] = None,
        user_id: Optional[str] = None
    ):
        """
        Khởi tạo DTO cho việc tạo tài liệu Word mới.

        Args:
            title: Tiêu đề của tài liệu
            description: Mô tả của tài liệu
            original_filename: Tên file gốc
            doc_metadata: Metadata của tài liệu
            user_id: ID của người dùng tạo tài liệu
        """
        super().__init__(
            title=title,
            description=description,
            original_filename=original_filename,
            doc_metadata=doc_metadata or {},
            user_id=user_id
        )

class UpdateDocumentDTO(BaseModel):
    """
    DTO để cập nhật thông tin tài liệu Word.
    """
    title: Optional[str] = None
    description: Optional[str] = None
    doc_metadata: Optional[Dict[str, Any]] = None

class CreateTemplateDTO(BaseModel):
    """
    DTO để tạo mới template.
    """
    name: str
    description: str = ""
    category: str = "general"
    fields: List[Dict[str, Any]] = Field(default_factory=list)
    doc_metadata: Dict[str, Any] = Field(default_factory=dict)

class TemplateDataDTO(BaseModel):
    """
    DTO để áp dụng mẫu Word với dữ liệu.
    """
    template_id: str
    data: Dict[str, Any]
    output_format: str = "docx"  # docx, pdf
    user_id: str

class WatermarkDTO(BaseModel):
    """
    DTO cho việc thêm watermark vào tài liệu.
    """
    text: str
    position: str = "center"  # center, top-left, top-right, bottom-left, bottom-right
    opacity: float = 0.5  # 0.0 - 1.0
    font_size: int = 40  # Kích thước font
    font_name: str = "Times New Roman"  # Tên font
    rotation: int = -45  # Góc xoay (độ)

class BatchProcessingDTO(BaseModel):
    """
    DTO cho việc xử lý hàng loạt tài liệu.
    """
    task_id: str
    template_id: str
    data_items: List[Dict[str, Any]]
    output_format: str = "docx"  # docx, pdf, zip
    callback_url: Optional[str] = None

class TaskStatusDTO(BaseModel):
    """
    DTO cho trạng thái của task xử lý bất đồng bộ.
    """
    task_id: str
    status: str  # processing, completed, failed
    message: str = ""
    result: Optional[Dict[str, Any]] = None
    progress: float = 0.0  # 0.0 - 1.0

class DocumentFilterDTO(BaseModel):
    """
    DTO để lọc danh sách tài liệu.
    """
    search: Optional[str] = None
    category: Optional[str] = None
    from_date: Optional[str] = None
    to_date: Optional[str] = None
    sort_by: Optional[str] = "created_at"
    sort_order: Optional[str] = "desc"

class InternshipReportModel(BaseModel):
    """
    DTO cho báo cáo kết quả thực tập.
    """
    department: str
    location: str
    day: str
    month: str
    year: str
    intern_name: str
    internship_duration: str
    supervisor_name: str
    ethics_evaluation: str
    capacity_evaluation: str
    compliance_evaluation: str
    group_activities: str

class RewardReportModel(BaseModel):
    """
    DTO cho báo cáo thưởng.
    """
    location: str
    day: str
    month: str
    year: str
    title: str
    recipient: str
    approver_name: str
    submitter_name: str

class LaborContractModel(BaseModel):
    """
    DTO cho hợp đồng lao động.
    """
    contract_number: str
    day: str
    month: str
    year: str
    representative_name: str
    position: str
    employee_name: str
    nationality: str
    date_of_birth: str
    gender: str
    profession: str
    permanent_address: str
    current_address: str
    id_number: str
    id_issue_date: str
    id_issue_place: str
    job_position: str
    start_date: str
    end_date: str
    salary: str
    allowance: str