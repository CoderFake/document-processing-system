from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import uuid


class PDFDocumentInfo(BaseModel):
    """
    Thông tin cơ bản về tài liệu PDF.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: Optional[str] = ""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    file_size: int
    page_count: Optional[int] = None
    is_encrypted: bool = False
    storage_path: str
    original_filename: str
    metadata: Dict[str, Any] = {}

    class Config:
        arbitrary_types_allowed = True


class PNGDocumentInfo(BaseModel):
    """
    Thông tin cơ bản về tài liệu PNG.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: Optional[str] = ""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    file_size: int
    width: Optional[int] = None
    height: Optional[int] = None
    storage_path: str
    original_filename: str
    metadata: Dict[str, Any] = {}

    class Config:
        arbitrary_types_allowed = True


class StampInfo(BaseModel):
    """
    Thông tin về mẫu dấu (stamp).
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = ""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    file_size: int
    width: Optional[int] = None
    height: Optional[int] = None
    storage_path: str
    original_filename: str
    metadata: Dict[str, Any] = {}

    class Config:
        arbitrary_types_allowed = True


class PDFProcessingInfo(BaseModel):
    """
    Thông tin về quá trình xử lý PDF.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str
    operation_type: str  # encrypt, decrypt, sign, watermark, crack, merge
    status: str = "processing"  # processing, completed, failed
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    result_document_id: Optional[str] = None
    error_message: Optional[str] = None
    parameters: Dict[str, Any] = {}

    class Config:
        arbitrary_types_allowed = True


class MergeInfo(BaseModel):
    """
    Thông tin về gộp các tài liệu PDF.
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