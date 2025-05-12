from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class CreateFileDTO(BaseModel):
    """
    DTO để tạo mới tệp.
    """
    title: str
    description: Optional[str] = ""
    original_filename: str
    metadata: Dict[str, Any] = {}

class CreateArchiveDTO(BaseModel):
    """
    DTO để tạo mới tệp nén.
    """
    title: str
    description: Optional[str] = ""
    original_filename: str
    compression_type: str
    is_encrypted: bool = False
    metadata: Dict[str, Any] = {}

class CompressFilesDTO(BaseModel):
    """
    DTO để nén nhiều tệp.
    """
    file_ids: List[str]
    output_filename: str
    compression_type: str = "zip"  # "zip", "7z", "rar"
    password: Optional[str] = None

class DecompressArchiveDTO(BaseModel):
    """
    DTO để giải nén tệp.
    """
    archive_id: str
    password: Optional[str] = None
    extract_all: bool = True
    file_paths: Optional[List[str]] = None

class CrackArchivePasswordDTO(BaseModel):
    """
    DTO để crack mật khẩu tệp nén.
    """
    archive_id: str
    max_length: int = 6

class CleanupFilesDTO(BaseModel):
    """
    DTO để dọn dẹp tệp cũ.
    """
    days: int = 30
    file_types: Optional[List[str]] = None

class RestoreTrashDTO(BaseModel):
    """
    DTO để khôi phục tệp từ thùng rác.
    """
    trash_ids: List[str]

class FileFilterDTO(BaseModel):
    """
    DTO để lọc danh sách tệp.
    """
    search: Optional[str] = None
    file_type: Optional[str] = None
    from_date: Optional[str] = None
    to_date: Optional[str] = None
    sort_by: Optional[str] = "created_at"
    sort_order: Optional[str] = "desc"