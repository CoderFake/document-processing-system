from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class CreatePdfDocumentDTO(BaseModel):
    """
    DTO để tạo mới tài liệu PDF.
    """
    title: str
    description: Optional[str] = ""
    original_filename: str
    metadata: Dict[str, Any] = {}

class CreatePngDocumentDTO(BaseModel):
    """
    DTO để tạo mới tài liệu PNG.
    """
    title: str
    description: Optional[str] = ""
    original_filename: str
    metadata: Dict[str, Any] = {}

class CreateStampDTO(BaseModel):
    """
    DTO để tạo mới mẫu dấu.
    """
    name: str
    description: Optional[str] = ""
    original_filename: str
    metadata: Dict[str, Any] = {}

class EncryptPdfDTO(BaseModel):
    """
    DTO để mã hóa tài liệu PDF.
    """
    document_id: str
    password: str
    permissions: Optional[Dict[str, bool]] = None

class DecryptPdfDTO(BaseModel):
    """
    DTO để giải mã tài liệu PDF.
    """
    document_id: str
    password: str

class WatermarkPdfDTO(BaseModel):
    """
    DTO để thêm watermark vào tài liệu PDF.
    """
    document_id: str
    watermark_text: str
    position: str = "center"  # center, top-left, top-right, bottom-left, bottom-right
    opacity: float = 0.5
    color: Optional[str] = "#808080"  # Gray
    font_size: Optional[int] = 40

class SignPdfDTO(BaseModel):
    """
    DTO để thêm chữ ký vào tài liệu PDF.
    """
    document_id: str
    stamp_id: Optional[str] = None
    signature_position: str = "bottom-right"  # bottom-right, bottom-left, top-right, top-left, custom
    page_number: int = -1  # -1 for last page
    custom_x: Optional[int] = None
    custom_y: Optional[int] = None
    scale: float = 0.5

class MergePdfDTO(BaseModel):
    """
    DTO để gộp nhiều tài liệu PDF thành một.
    """
    document_ids: List[str]
    output_filename: str

class CrackPdfDTO(BaseModel):
    """
    DTO để crack mật khẩu PDF.
    """
    document_id: str
    max_length: int = 6  # Độ dài tối đa của mật khẩu để thử

class ConvertPdfToWordDTO(BaseModel):
    """
    DTO để chuyển đổi PDF sang Word.
    """
    document_id: str
    output_format: str = "docx"  # docx, doc

class ConvertPdfToImageDTO(BaseModel):
    """
    DTO để chuyển đổi PDF sang hình ảnh.
    """
    document_id: str
    output_format: str = "png"  # png, jpg
    dpi: int = 300
    page_numbers: Optional[List[int]] = None  # None = tất cả các trang

class DocumentFilterDTO(BaseModel):
    """
    DTO để lọc danh sách tài liệu.
    """
    search: Optional[str] = None
    from_date: Optional[str] = None
    to_date: Optional[str] = None
    sort_by: Optional[str] = "created_at"
    sort_order: Optional[str] = "desc"