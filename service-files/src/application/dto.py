from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class CreateFileDTO(BaseModel):
    """
    DTO để tạo mới tệp.
    """
    title: str
    description: Optional[str] = ""
    original_filename: str
    user_id: Optional[int] = None
    metadata: Dict[str, Any] = {}

class CreateArchiveDTO(BaseModel):
    """
    DTO để tạo mới tệp nén.
    """
    title: str
    description: Optional[str] = ""
    original_filename: str
    user_id: Optional[int] = None

class ExtractArchiveDTO(BaseModel):
    """DTO cho việc giải nén tệp."""
    archive_id: str
    extract_path: Optional[str] = None
    password: Optional[str] = None
    extract_all: bool = True
    selected_files: Optional[List[str]] = None
    user_id: Optional[int] = None

class CompressFilesDTO(BaseModel):
    """
    DTO để nén nhiều tệp.
    """
    file_ids: List[str]
    output_filename: str
    archive_format: str = "zip"
    password: Optional[str] = None
    compression_level: Optional[int] = 6
    user_id: Optional[int] = None

class AddFilesToArchiveDTO(BaseModel):
    """DTO cho việc thêm tệp vào tệp nén."""
    archive_id: str
    file_ids: List[str]
    password: Optional[str] = None
    user_id: Optional[int] = None

class RemoveFilesFromArchiveDTO(BaseModel):
    """DTO cho việc xóa tệp khỏi tệp nén."""
    archive_id: str
    file_paths: List[str]
    password: Optional[str] = None
    user_id: Optional[int] = None

class EncryptArchiveDTO(BaseModel):
    """DTO cho việc mã hóa tệp nén."""
    archive_id: str
    password: str
    user_id: Optional[int] = None

class DecryptArchiveDTO(BaseModel):
    """DTO cho việc giải mã tệp nén."""
    archive_id: str
    password: str
    user_id: Optional[int] = None

class CrackArchiveDTO(BaseModel):
    """DTO cho việc crack mật khẩu tệp nén."""
    archive_id: str
    max_length: int = 6
    character_set: Optional[str] = None
    user_id: Optional[int] = None

class ConvertArchiveDTO(BaseModel):
    """DTO cho việc chuyển đổi định dạng tệp nén."""
    archive_id: str
    output_format: str
    password: Optional[str] = None
    user_id: Optional[int] = None

class DecompressArchiveDTO(BaseModel):
    """
    DTO để giải nén tệp.
    """
    archive_id: str
    password: Optional[str] = None
    extract_all: bool = True
    file_paths: Optional[List[str]] = None
    user_id: Optional[int] = None

class CrackArchivePasswordDTO(BaseModel):
    """
    DTO để crack mật khẩu tệp nén.
    """
    archive_id: str
    max_length: int = 6
    user_id: Optional[int] = None

class CleanupFilesDTO(BaseModel):
    """
    DTO để dọn dẹp tệp cũ.
    """
    days: int = 30
    file_types: Optional[List[str]] = None
    user_id: Optional[int] = None

class RestoreTrashDTO(BaseModel):
    """
    DTO để khôi phục tệp từ thùng rác.
    """
    trash_ids: List[str]
    user_id: Optional[int] = None

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
    user_id: Optional[int] = None