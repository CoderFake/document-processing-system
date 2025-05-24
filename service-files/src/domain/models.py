from datetime import datetime
from typing import Dict, Any, List, Optional
from enum import Enum
from pydantic import BaseModel, Field
import uuid
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()

class DBDocument(Base):
    __tablename__ = "documents"
    
    id = Column(UUID, primary_key=True, index=True, default=uuid.uuid4)
    storage_id = Column(UUID, unique=True, index=True, nullable=False, default=uuid.uuid4)
    document_category = Column(String, nullable=False, default="files")
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    file_size = Column(Integer, nullable=False)
    storage_path = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    doc_metadata = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = Column(UUID, nullable=False)
    source_service = Column(String, nullable=True, default="files", index=True)
    
    page_count = Column(Integer, nullable=True)
    is_encrypted = Column(Boolean, default=False)

    sheet_count = Column(Integer, nullable=True)

    compression_type = Column(String, nullable=True)
    file_type = Column(String, nullable=True)

class ArchiveFormat(str, Enum):
    ZIP = "zip"
    RAR = "rar"
    SEVEN_ZIP = "7z"
    TAR = "tar"
    GZIP = "gz"
    TAR_GZIP = "tar.gz"


class FileInfo:
    id: Optional[str]
    title: str
    description: str
    created_at: datetime
    updated_at: Optional[datetime]
    file_size: int
    file_type: str
    original_filename: str
    storage_path: str
    doc_metadata: Dict[str, Any]
    user_id: Optional[str]
    storage_id: Optional[str]
    source_service: Optional[str]

    def __init__(
        self,
        title: str,
        description: str,
        file_size: int,
        file_type: str,
        original_filename: str,
        storage_path: str,
        user_id: Optional[str] = None,
        id: Optional[str] = None,
        storage_id: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        doc_metadata: Optional[Dict[str, Any]] = None,
        source_service: Optional[str] = "files"
    ):
        self.id = id or storage_id
        self.title = title
        self.description = description
        self.file_size = file_size
        self.file_type = file_type
        self.original_filename = original_filename
        self.storage_path = storage_path
        self.user_id = user_id
        self.storage_id = storage_id or id
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at
        self.doc_metadata = doc_metadata or {}
        self.source_service = source_service


class ArchiveInfo:
    id: str
    title: str
    description: Optional[str]
    file_size: int
    file_type: str
    compression_type: str
    storage_path: str
    original_filename: str
    created_at: datetime
    updated_at: Optional[datetime]
    doc_metadata: Dict[str, Any]
    files_count: int
    user_id: Optional[str]
    source_service: Optional[str]

    def __init__(
        self,
        id: str = None,
        title: str = "",
        description: str = "",
        file_size: int = 0,
        file_type: str = "",
        compression_type: str = "",
        storage_path: str = "",
        original_filename: str = "",
        created_at: datetime = None,
        updated_at: datetime = None,
        doc_metadata: Dict[str, Any] = None,
        files_count: int = 0,
        user_id: Optional[str] = None,
        source_service: Optional[str] = "files"
    ):
        self.id = id or str(uuid.uuid4())
        self.title = title
        self.description = description
        self.file_size = file_size
        self.file_type = file_type
        self.compression_type = compression_type
        self.storage_path = storage_path
        self.original_filename = original_filename
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at
        self.doc_metadata = doc_metadata or {}
        self.files_count = files_count
        self.user_id = user_id
        self.source_service = source_service


class FileEntryInfo:
    path: str
    size: int
    is_directory: bool
    last_modified: Optional[datetime]
    
    def __init__(
        self,
        path: str,
        size: int,
        is_directory: bool,
        last_modified: Optional[datetime] = None
    ):
        self.path = path
        self.size = size
        self.is_directory = is_directory
        self.last_modified = last_modified


class ExtractedArchiveInfo:
    id: str
    archive_id: str
    extraction_path: str
    created_at: datetime
    entries: List[FileEntryInfo]
    total_entries: int
    total_size: int
    doc_metadata: Dict[str, Any]

    def __init__(
        self,
        id: str,
        archive_id: str,
        extraction_path: str,
        entries: List[FileEntryInfo],
        total_entries: int,
        total_size: int,
        created_at: Optional[datetime] = None,
        doc_metadata: Optional[Dict[str, Any]] = None
    ):
        self.id = id
        self.archive_id = archive_id
        self.extraction_path = extraction_path
        self.entries = entries
        self.total_entries = total_entries
        self.total_size = total_size
        self.created_at = created_at or datetime.now()
        self.doc_metadata = doc_metadata or {}


class ArchiveProcessingInfo:
    id: str
    archive_id: str
    operation_type: str
    status: str = "processing"
    user_id: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime]
    result: Optional[Dict[str, Any]]
    error: Optional[str]

    def __init__(
        self,
        id: str,
        archive_id: str,
        operation_type: str,
        status: str = "processing",
        user_id: Optional[str] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ):
        self.id = id
        self.archive_id = archive_id
        self.operation_type = operation_type
        self.status = status
        self.user_id = user_id
        self.started_at = started_at or datetime.now()
        self.completed_at = completed_at
        self.result = result
        self.error = error


class ArchiveEntryInfo:
    filename: str
    path: str
    size: int
    is_directory: bool
    modified_at: Optional[datetime]
    crc: Optional[str]

    def __init__(
        self,
        filename: str = "",
        path: str = "",
        size: int = 0,
        is_directory: bool = False,
        modified_at: Optional[datetime] = None,
        crc: Optional[str] = None
    ):
        self.filename = filename
        self.path = path
        self.size = size
        self.is_directory = is_directory
        self.modified_at = modified_at
        self.crc = crc


class ExtractInfo(BaseModel):
    id: str
    archive_id: str
    created_at: datetime
    output_path: str
    target_files: List[str] = []
    preserve_structure: bool = True
    status: str = "processing"
    error_message: Optional[str] = None