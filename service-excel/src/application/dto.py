from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class CreateDocumentDTO(BaseModel):
    """
    DTO để tạo mới tài liệu Excel.
    """
    title: str
    description: Optional[str] = ""
    original_filename: str
    metadata: Dict[str, Any] = {}

class CreateTemplateDTO(BaseModel):
    """
    DTO để tạo mới mẫu tài liệu Excel.
    """
    name: str
    description: Optional[str] = ""
    category: Optional[str] = None
    original_filename: str
    data_fields: List[Dict[str, Any]] = []
    metadata: Dict[str, Any] = {}

class TemplateDataDTO(BaseModel):
    """
    DTO chứa dữ liệu để áp dụng vào mẫu tài liệu.
    """
    template_id: str
    data: Dict[str, Any]
    output_format: str = "xlsx"  

class BatchProcessingDTO(BaseModel):
    """
    DTO để xử lý hàng loạt tài liệu từ mẫu.
    """
    template_id: str
    data_list: List[Dict[str, Any]]
    output_format: str = "xlsx"  

class MergeDocumentsDTO(BaseModel):
    """
    DTO để gộp nhiều tài liệu Excel thành một.
    """
    document_ids: List[str]
    output_filename: str

class ConvertToWordDTO(BaseModel):
    """
    DTO để chuyển đổi tài liệu Excel sang Word.
    """
    document_id: str
    sheets: Optional[List[str]] = None

class ConvertToPdfDTO(BaseModel):
    """
    DTO để chuyển đổi tài liệu Excel sang PDF.
    """
    document_id: str
    sheets: Optional[List[str]] = None

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