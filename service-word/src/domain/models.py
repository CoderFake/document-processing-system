from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
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