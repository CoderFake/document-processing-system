from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
import uuid
from pydantic import BaseModel, Field

Base = declarative_base()

class DBDocument(Base):
    __tablename__ = "documents"
    
    id = Column(UUID, primary_key=True, default=uuid.uuid4, index=True)
    storage_id = Column(UUID, unique=True, index=True, nullable=False, default=uuid.uuid4)
    document_category = Column(String, nullable=False, default="excel")
    title = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    file_size = Column(Integer, nullable=True)
    storage_path = Column(String, nullable=False)
    original_filename = Column(String, nullable=True)
    doc_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    user_id = Column(UUID, nullable=False, index=True)
    
    version = Column(Integer, default=1, nullable=False)
    checksum = Column(String, nullable=True)
    file_type = Column(String, nullable=True)

    sheet_count = Column(Integer, nullable=True)


class ExcelDocumentInfo(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    storage_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_category: str = "excel"
    title: Optional[str] = None
    description: Optional[str] = None
    file_size: Optional[int] = None
    file_type: Optional[str] = Field(default="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    storage_path: Optional[str] = None
    original_filename: Optional[str] = None
    doc_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    user_id: str
    version: int = Field(default=1)
    checksum: Optional[str] = None
    sheet_count: Optional[int] = None

    class Config:
        from_attributes = True

class ExcelDocumentCreate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None

class ExcelDocumentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    doc_metadata: Optional[Dict[str, Any]] = None

class ExcelTemplateInfo:
    id: str
    name: str
    description: Optional[str]
    file_size: int
    category: str
    storage_path: str
    created_at: datetime
    updated_at: Optional[datetime]
    variables: List[str]
    sample_data: Dict[str, Any]
    
    def __init__(
        self,
        id: str = None,
        name: str = "",
        description: str = "",
        file_size: int = 0,
        category: str = "",
        storage_path: str = "",
        created_at: datetime = None,
        updated_at: datetime = None,
        variables: List[str] = None,
        sample_data: Dict[str, Any] = None
    ):
        self.id = id or str(uuid.uuid4())
        self.name = name
        self.description = description
        self.file_size = file_size
        self.category = category
        self.storage_path = storage_path
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at
        self.variables = variables or []
        self.sample_data = sample_data or {}

class BatchProcessingInfo(BaseModel):
    id: str
    job_type: str
    status: str = "processing"
    created_at: datetime
    completed_at: Optional[datetime] = None
    template_id: Optional[str] = None
    data_file_id: Optional[str] = None
    result_file_ids: List[str] = []
    error_message: Optional[str] = None

class MergeInfo(BaseModel):
    id: str
    document_ids: List[str]
    created_at: datetime
    status: str = "processing"
    output_filename: str
    result_document_id: Optional[str] = None
    error_message: Optional[str] = None