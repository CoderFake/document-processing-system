from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, UUID4
import uuid


class DocumentInfo(BaseModel):
    """
    Thông tin cơ bản về tài liệu Word.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: Optional[str] = ""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    file_size: int
    file_type: str
    original_filename: str
    storage_path: str
    metadata: Dict[str, Any] = {}

    class Config:
        arbitrary_types_allowed = True


class TemplateInfo(BaseModel):
    """
    Thông tin về mẫu tài liệu Word.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = ""
    category: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    file_size: int
    original_filename: str
    storage_path: str
    metadata: Dict[str, Any] = {}
    data_fields: List[Dict[str, Any]] = []

    class Config:
        arbitrary_types_allowed = True


class BatchProcessingInfo(BaseModel):
    """
    Thông tin về quá trình xử lý hàng loạt.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    template_id: str
    status: str = "processing"  
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    total_documents: int = 0
    processed_documents: int = 0
    output_format: str
    result_file_id: Optional[str] = None
    result_file_path: Optional[str] = None
    error_message: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True


class DocumentException(Exception):
    """
    Ngoại lệ xảy ra khi xử lý tài liệu.
    """

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class TemplateException(Exception):
    """
    Ngoại lệ xảy ra khi xử lý mẫu tài liệu.
    """

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class InternshipReportModel(BaseModel):
    """
    Báo cáo kết quả thực tập template model.
    """
    department: str = Field(..., description="Department name", example="Technical Department", alias="phong_ban")
    location: str = Field(..., description="Location where report is created", example="Hanoi", alias="dia_danh")
    day: str = Field(..., description="Day of report (2 digits)", example="01", pattern="^[0-3][0-9]$", alias="ngay")
    month: str = Field(..., description="Month of report (2 digits)", example="01", pattern="^[0-1][0-9]$", alias="thang")
    year: str = Field(..., description="Year of report (4 digits)", example="2023", pattern="^[0-9]{4}$", alias="nam")
    intern_name: str = Field(..., description="Full name of intern", example="Nguyen Van A", alias="ho_ten_tap_su")
    internship_duration: str = Field(..., description="Duration of internship", example="3 months", alias="thoi_gian_tap_su")
    supervisor_name: str = Field(..., description="Full name of supervisor", example="Tran Thi B", alias="nguoi_huong_dan")
    ethics_evaluation: str = Field(..., description="Ethics evaluation", example="Good", alias="pham_chat_dao_duc")
    capacity_evaluation: str = Field(..., description="Capacity and qualification evaluation", example="Meets requirements", alias="nang_luc_trinh_do")
    compliance_evaluation: str = Field(..., description="Compliance evaluation", example="Good", alias="y_thuc_chap_hanh")
    group_activities: str = Field(..., description="Group activities evaluation", example="Active", alias="hoat_dong_doan_the")


class RewardReportModel(BaseModel):
    """
    Báo cáo thưởng template model.
    """
    location: str = Field(..., description="Location where report is created", example="Hanoi", alias="dia_danh")
    day: str = Field(..., description="Day of report (2 digits)", example="01", pattern="^[0-3][0-9]$", alias="ngay")
    month: str = Field(..., description="Month of report (2 digits)", example="01", pattern="^[0-1][0-9]$", alias="thang")
    year: str = Field(..., description="Year of report (4 digits)", example="2023", pattern="^[0-9]{4}$", alias="nam")
    title: str = Field(..., description="Report title", example="Reward Report for Q1/2023", alias="tieu_de")
    recipient: str = Field(..., description="Report recipient", example="Board of Directors", alias="kinh_gui")
    approver_name: str = Field(..., description="Name of approver", example="Nguyen Van C", alias="ky_xac_nhan")
    submitter_name: str = Field(..., description="Name of submitter", example="Tran Thi D", alias="ky_ten_nguoi_lam_don")


class LaborContractModel(BaseModel):
    """
    Hợp đồng lao động template model.
    """
    contract_number: str = Field(..., description="Contract number", example="HD-2023-001", alias="so")
    day: str = Field(..., description="Day of signing (2 digits)", example="01", pattern="^[0-3][0-9]$", alias="ngay")
    month: str = Field(..., description="Month of signing (2 digits)", example="01", pattern="^[0-1][0-9]$", alias="thang")
    year: str = Field(..., description="Year of signing (4 digits)", example="2023", pattern="^[0-9]{4}$", alias="nam")
    representative_name: str = Field(..., description="Name of company representative", example="Nguyen Van E", alias="nguoi_dai_dien")
    position: str = Field(..., description="Position of representative", example="Director", alias="chuc_vu")
    employee_name: str = Field(..., description="Name of employee", example="Pham Van F", alias="ten_nguoi_lao_dong")
    nationality: str = Field(..., description="Nationality of employee", example="Vietnam", alias="quoc_tich")
    date_of_birth: str = Field(..., description="Date of birth (dd/mm/yyyy)", example="15/05/1990", pattern="^[0-3][0-9]/[0-1][0-9]/[0-9]{4}$", alias="ngay_thang_nam_sinh")
    gender: str = Field(..., description="Gender of employee", example="Male", pattern="^(Male|Female)$", alias="gioi_tinh")
    profession: str = Field(..., description="Profession of employee", example="Software Engineer", alias="nghe_nghiep")
    permanent_address: str = Field(..., description="Permanent address", example="123 ABC Street, XYZ District, Hanoi", alias="dia_chi_thuong_tru")
    current_address: str = Field(..., description="Current residence address", example="456 DEF Street, GHI District, Hanoi", alias="dia_chi_cu_tru")
    id_number: str = Field(..., description="ID card number", example="123456789012", pattern="^[0-9]{9,12}$", alias="cmnd")
    id_issue_date: str = Field(..., description="ID card issue date (dd/mm/yyyy)", example="01/01/2020", pattern="^[0-3][0-9]/[0-1][0-9]/[0-9]{4}$", alias="ngay_cap")
    id_issue_place: str = Field(..., description="ID card issuing authority", example="Police Department", alias="noi_cap")
    job_position: str = Field(..., description="Job position", example="Software Engineer", alias="vi_tri")
    start_date: str = Field(..., description="Work start date (dd/mm/yyyy)", example="01/02/2023", pattern="^[0-3][0-9]/[0-1][0-9]/[0-9]{4}$", alias="ngay_lam_viec")
    end_date: str = Field(..., description="Contract end date (dd/mm/yyyy)", example="31/01/2024", pattern="^[0-3][0-9]/[0-1][0-9]/[0-9]{4}$", alias="ngay_ket_thuc")
    salary: str = Field(..., description="Basic salary", example="15,000,000 VND", alias="luong")
    allowance: str = Field(..., description="Allowance (if any)", example="2,000,000 VND", alias="phu_cap")


class InvitationModel(BaseModel):
    """
    Giấy mời template model.
    """
    event_name: str = Field(..., description="Tên sự kiện", example="Kết thúc năm", alias="event_name")
    location: str = Field(..., description="Địa điểm sự kiện", example="Hà Nội", alias="location")
    day: str = Field(..., description="Ngày sự kiện (2 chữ số)", example="25", pattern="^[0-3][0-9]$", alias="day")
    month: str = Field(..., description="Tháng sự kiện (2 chữ số)", example="12", pattern="^[0-1][0-9]$", alias="month")
    year: str = Field(..., description="Năm sự kiện (4 chữ số)", example="2023", pattern="^[0-9]{4}$", alias="year")
    time: str = Field(..., description="Thời gian sự kiện", example="18:30", alias="time")
    recipient_name: str = Field(..., description="Tên người nhận", example="Nguyễn Văn A", alias="recipient_name")
    recipient_position: str = Field(..., description="Chức vụ của người nhận", example="Kỹ sư phần mềm", alias="recipient_position")
    recipient_department: str = Field(..., description="Phòng ban của người nhận", example="Phòng ban IT", alias="recipient_department")
    sender_name: str = Field(..., description="Tên người gửi", example="Trần Thị B", alias="sender_name")
    sender_position: str = Field(..., description="Chức vụ của người gửi", example="Quản lý nhân sự", alias="sender_position")
    note: Optional[str] = Field(None, description="Ghi chú thêm", example="Làm ơn xác nhận tham dự", alias="note")