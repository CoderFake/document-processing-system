from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class CreateDocumentDTO(BaseModel):
    """
    DTO để tạo mới tài liệu Excel.
    """
    title: str
    description: Optional[str] = ""
    original_filename: str
    doc_metadata: Dict[str, Any] = {}
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
        Khởi tạo DTO cho việc tạo tài liệu Excel mới.

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
            doc_metadata=metadata or {},
            user_id=user_id
        )

class CreateTemplateDTO(BaseModel):
    """
    DTO để tạo mới mẫu tài liệu Excel.
    """
    name: str
    description: Optional[str] = ""
    category: Optional[str] = None
    original_filename: str
    data_fields: List[Dict[str, Any]] = []
    doc_metadata: Dict[str, Any] = {}

class TemplateDataDTO(BaseModel):
    """
    DTO chứa dữ liệu để áp dụng vào mẫu tài liệu.
    """
    template_id: str
    data: Dict[str, Any]
    output_format: str = "xlsx"  
    user_id: Optional[str] = None

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
    user_id: Optional[str] = None

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