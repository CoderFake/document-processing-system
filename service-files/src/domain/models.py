from datetime import datetime
from typing import Dict, Any, List, Optional
from enum import Enum
from pydantic import BaseModel, Field
import uuid


class ArchiveFormat(str, Enum):
    ZIP = "zip"
    RAR = "rar"
    SEVEN_ZIP = "7z"
    TAR = "tar"
    GZIP = "gz"
    TAR_GZIP = "tar.gz"


class FileInfo:
    id: str
    title: str
    description: str
    created_at: datetime
    updated_at: Optional[datetime]
    file_size: int
    file_type: str
    original_filename: str
    storage_path: str
    metadata: Dict[str, Any]

    def __init__(
        self,
        id: str,
        title: str,
        description: str,
        file_size: int,
        file_type: str,
        original_filename: str,
        storage_path: str,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.id = id
        self.title = title
        self.description = description
        self.file_size = file_size
        self.file_type = file_type
        self.original_filename = original_filename
        self.storage_path = storage_path
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at
        self.metadata = metadata or {}


class ArchiveInfo:
    id: str
    title: str
    description: str
    created_at: datetime
    updated_at: Optional[datetime]
    format: ArchiveFormat
    file_size: int
    original_filename: str
    storage_path: str
    is_encrypted: bool
    metadata: Dict[str, Any]

    def __init__(
        self,
        id: str,
        title: str,
        description: str,
        format: ArchiveFormat,
        file_size: int,
        original_filename: str,
        storage_path: str,
        is_encrypted: bool = False,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.id = id
        self.title = title
        self.description = description
        self.format = format
        self.file_size = file_size
        self.original_filename = original_filename
        self.storage_path = storage_path
        self.is_encrypted = is_encrypted
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at
        self.metadata = metadata or {}


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
    metadata: Dict[str, Any]

    def __init__(
        self,
        id: str,
        archive_id: str,
        extraction_path: str,
        entries: List[FileEntryInfo],
        total_entries: int,
        total_size: int,
        created_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.id = id
        self.archive_id = archive_id
        self.extraction_path = extraction_path
        self.entries = entries
        self.total_entries = total_entries
        self.total_size = total_size
        self.created_at = created_at or datetime.now()
        self.metadata = metadata or {}


class ArchiveProcessingInfo:
    id: str
    archive_id: str
    operation_type: str
    status: str = "processing"
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
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ):
        self.id = id
        self.archive_id = archive_id
        self.operation_type = operation_type
        self.status = status
        self.started_at = started_at or datetime.now()
        self.completed_at = completed_at
        self.result = result
        self.error = error