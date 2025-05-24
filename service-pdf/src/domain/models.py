from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()

class DBDocument(Base):
    __tablename__ = "documents"
    
    id = Column(UUID, primary_key=True, index=True, default=uuid.uuid4)
    storage_id = Column(UUID, unique=True, index=True, nullable=False, default=uuid.uuid4)
    document_category = Column(String, nullable=False, default="pdf")
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    file_size = Column(Integer, nullable=False)
    storage_path = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    doc_metadata = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = Column(UUID, nullable=False)
    source_service = Column(String, nullable=True, default="pdf", index=True)
    
    # PDF specific fields
    page_count = Column(Integer, nullable=True)
    is_encrypted = Column(Boolean, default=False)
    
    # Additional fields for compatibility
    file_type = Column(String, nullable=True)
    version = Column(Integer, default=1)
    checksum = Column(String, nullable=True)

class PDFDocumentInfo(BaseModel):
    """
    Thông tin tài liệu PDF
    """
    id: Optional[str] = None
    storage_id: Optional[str] = None
    title: str
    description: Optional[str] = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    file_size: Optional[int] = None
    page_count: Optional[int] = None
    is_encrypted: Optional[bool] = False
    storage_path: Optional[str] = None
    original_filename: str
    metadata: Dict[str, Any] = Field(default_factory=dict, alias='doc_metadata')
    user_id: Optional[str] = None
    file_type: Optional[str] = "application/pdf"
    document_category: str = "pdf"
    version: Optional[int] = 1
    checksum: Optional[str] = None

    def __init__(self, **data):
        # Handle metadata alias
        if 'doc_metadata' in data and 'metadata' not in data:
            data['metadata'] = data['doc_metadata']
        
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
        populate_by_name = True

class PNGDocumentInfo(BaseModel):
    """
    Thông tin tài liệu PNG
    """
    id: Optional[str] = None
    storage_id: Optional[str] = None
    title: str
    description: Optional[str] = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    file_size: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    storage_path: Optional[str] = None
    original_filename: str
    metadata: Dict[str, Any] = Field(default_factory=dict, alias='doc_metadata')
    user_id: Optional[str] = None
    file_type: Optional[str] = "image/png"
    document_category: str = "png"
    version: Optional[int] = 1
    checksum: Optional[str] = None

    def __init__(self, **data):
        if 'doc_metadata' in data and 'metadata' not in data:
            data['metadata'] = data['doc_metadata']
        
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
        populate_by_name = True

class StampInfo(BaseModel):
    """
    Thông tin mẫu dấu
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = ""
    created_at: Optional[datetime] = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    file_size: int
    width: Optional[int] = None
    height: Optional[int] = None
    storage_path: str
    original_filename: str
    doc_metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True

class PDFProcessingInfo(BaseModel):
    """
    Thông tin xử lý PDF
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str
    operation_type: str  
    status: str = "processing"  
    created_at: Optional[datetime] = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    result_document_id: Optional[str] = None
    error_message: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True

class MergeInfo(BaseModel):
    """
    Thông tin gộp tài liệu PDF
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_ids: List[str]
    created_at: Optional[datetime] = Field(default_factory=datetime.now)
    status: str = "processing"  
    output_filename: str
    result_document_id: Optional[str] = None
    error_message: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True