from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

class CreateDocumentDTO(BaseModel):
    """
    DTO để tạo mới tài liệu Word.
    """
    title: str
    description: str = ""
    original_filename: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class UpdateDocumentDTO(BaseModel):
    """
    DTO để cập nhật thông tin tài liệu Word.
    """
    title: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class CreateTemplateDTO(BaseModel):
    """
    DTO để tạo mới template.
    """
    name: str
    description: str = ""
    category: str = "general"
    fields: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class TemplateDataDTO(BaseModel):
    """
    DTO để áp dụng mẫu Word với dữ liệu.
    """
    template_id: str
    data: Dict[str, Any]
    output_format: str = "docx"  # docx, pdf

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