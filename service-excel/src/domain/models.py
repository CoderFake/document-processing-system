from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import uuid


class ExcelDocumentInfo(BaseModel):
    """
    Thông tin cơ bản về tài liệu Excel.
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
    sheet_names: List[str] = []

    class Config:
        arbitrary_types_allowed = True


class ExcelTemplateInfo(BaseModel):
    """
    Thông tin về mẫu tài liệu Excel.
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
    sheet_names: List[str] = []

    class Config:
        arbitrary_types_allowed = True


class BatchProcessingInfo(BaseModel):
    """
    Thông tin về quá trình xử lý hàng loạt.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    template_id: str
    status: str = "processing"  # processing, completed, failed
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


class MergeInfo(BaseModel):
    """
    Thông tin về gộp các tài liệu Excel.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_ids: List[str]
    created_at: datetime = Field(default_factory=datetime.now)
    status: str = "processing"  # processing, completed, failed
    output_filename: str
    result_document_id: Optional[str] = None
    error_message: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True