from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import uuid


class FileInfo(BaseModel):
    """
    Thông tin cơ bản về tệp.
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


class ArchiveInfo(BaseModel):
    """
    Thông tin về tệp nén.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: Optional[str] = ""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    file_size: int
    file_type: str
    compression_type: str  # "zip", "7z", "rar"
    is_encrypted: bool = False
    original_filename: str
    storage_path: str
    file_count: Optional[int] = None
    file_list: List[str] = []
    metadata: Dict[str, Any] = {}

    class Config:
        arbitrary_types_allowed = True


class CompressJobInfo(BaseModel):
    """
    Thông tin về quá trình nén tệp.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    file_ids: List[str]
    status: str = "processing"  # "processing", "completed", "failed"
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    output_filename: str
    compression_type: str  # "zip", "7z", "rar"
    password: Optional[str] = None
    result_archive_id: Optional[str] = None
    error_message: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True


class DecompressJobInfo(BaseModel):
    """
    Thông tin về quá trình giải nén tệp.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    archive_id: str
    status: str = "processing"  # "processing", "completed", "failed"
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    password: Optional[str] = None
    result_folder: Optional[str] = None
    result_file_ids: List[str] = []
    error_message: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True


class CrackJobInfo(BaseModel):
    """
    Thông tin về quá trình crack mật khẩu tệp nén.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    archive_id: str
    status: str = "processing"  # "processing", "completed", "failed"
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    max_length: int = 6
    found_password: Optional[str] = None
    result_file_ids: List[str] = []
    error_message: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True


class CleanupJobInfo(BaseModel):
    """
    Thông tin về quá trình dọn dẹp tệp.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    days: int
    status: str = "processing"  # "processing", "completed", "failed"
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    deleted_files: List[str] = []
    deleted_count: int = 0
    error_message: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True


class TrashInfo(BaseModel):
    """
    Thông tin về thùng rác.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    original_id: str
    original_path: str
    deleted_at: datetime = Field(default_factory=datetime.now)
    expires_at: datetime
    file_size: int
    file_type: str
    original_filename: str
    trash_path: str
    metadata: Dict[str, Any] = {}

    class Config:
        arbitrary_types_allowed = True