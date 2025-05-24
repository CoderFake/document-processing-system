from typing import Dict, Any, List, Optional, TypeVar, Generic
from pydantic import BaseModel, Field, validator
from datetime import datetime

T = TypeVar('T')

class PaginatedResponseDTO(Generic[T], BaseModel):
    items: List[T]
    total_count: int
    skip: int
    limit: int

class CreateDocumentDTO(BaseModel):
    """
    DTO để tạo mới tài liệu PDF.
    """
    title: str
    description: str = ""
    original_filename: str
    doc_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    user_id: Optional[str] = None

    def __init__(
        self,
        title: str,
        description: str,
        original_filename: str,
        doc_metadata: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
    ):
        """
        Khởi tạo DTO cho việc tạo tài liệu PDF mới.

        Args:
            title: Tiêu đề của tài liệu
            description: Mô tả của tài liệu
            original_filename: Tên file gốc
            doc_metadata: Metadata của tài liệu
            user_id: ID của người dùng
        """
        super().__init__(
            title=title,
            description=description,
            original_filename=original_filename,
            doc_metadata=doc_metadata or {},
            user_id=user_id
        )

class UpdateDocumentDTO(BaseModel):
    """
    DTO để cập nhật tài liệu PDF.
    """
    title: Optional[str] = None
    description: Optional[str] = None
    doc_metadata: Dict[str, Any] = Field(default_factory=dict)

class PdfDocumentResponseDTO(BaseModel):
    id: str
    storage_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    file_size: Optional[int] = None
    page_count: Optional[int] = None
    is_encrypted: Optional[bool] = False
    storage_path: Optional[str] = None
    original_filename: Optional[str] = None
    doc_metadata: Dict[str, Any] = Field(default_factory=dict)
    user_id: Optional[str] = None
    file_type: Optional[str] = None
    version: Optional[int] = None
    checksum: Optional[str] = None

    class Config:
        orm_mode = True

class CreatePngDocumentDTO(BaseModel):
    """
    DTO để tạo tài liệu PNG mới.
    """
    title: str
    description: Optional[str] = ""
    original_filename: str
    doc_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class UpdatePngDocumentDTO(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    doc_metadata: Optional[Dict[str, Any]] = None
    original_filename: Optional[str] = None

class PngDocumentResponseDTO(BaseModel):
    id: str
    storage_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    file_size: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    storage_path: Optional[str] = None
    original_filename: Optional[str] = None
    doc_metadata: Dict[str, Any] = Field(default_factory=dict)
    user_id: Optional[str] = None
    file_type: Optional[str] = None
    version: Optional[int] = None
    checksum: Optional[str] = None

    class Config:
        orm_mode = True

class CreateStampDTO(BaseModel):
    """
    DTO để tạo mẫu dấu.
    """
    name: str
    text: str
    color: str = "red"
    font_size: int = 12
    shape: str = "rectangle"  # "rectangle", "circle", "oval"
    doc_metadata: Dict[str, Any] = Field(default_factory=dict)

class StampResponseDTO(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    file_size: int
    width: Optional[int] = None
    height: Optional[int] = None
    storage_path: str
    original_filename: str
    doc_metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        orm_mode = True

class EncryptPdfDTO(BaseModel):
    """
    DTO để mã hóa tài liệu PDF.
    """
    document_id: str
    password: str = Field(..., min_length=1)
    permissions: Optional[Dict[str, bool]] = None

class DecryptPdfDTO(BaseModel):
    """
    DTO để giải mã tài liệu PDF.
    """
    document_id: str
    password: str = Field(..., min_length=1)

class AddWatermarkDTO(BaseModel):
    """
    DTO để thêm watermark vào tài liệu PDF.
    """
    document_id: str
    text: str
    font_size: Optional[int] = 12
    font_name: Optional[str] = "helv"
    font_color: Optional[tuple] = (0.5, 0.5, 0.5)
    position: str = "center"  # "center", "top_left", "bottom_right"
    rotate: Optional[int] = 0
    opacity: float = 0.3
    rotation: int = 45
    doc_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

    def __init__(
        self,
        document_id: str,
        text: str,
        font_size: Optional[int] = 12,
        font_name: Optional[str] = "helv", 
        font_color: Optional[tuple] = (0.5, 0.5, 0.5),
        position: str = "center",
        rotate: Optional[int] = 0,
        opacity: float = 0.3,
        rotation: int = 45,
        doc_metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Khởi tạo DTO cho việc thêm watermark.

        Args:
            document_id: ID của tài liệu PDF
            text: Nội dung watermark
            font_size: Kích thước font
            font_name: Tên font
            font_color: Màu font (tuple RGB)
            position: Vị trí watermark
            rotate: Góc xoay (degrees)
            opacity: Độ trong suốt (0.0 - 1.0)
            rotation: Góc xoay (degrees) - alias của rotate
            doc_metadata: Metadata bổ sung
        """
        super().__init__(
            document_id=document_id,
            text=text,
            font_size=font_size,
            font_name=font_name,
            font_color=font_color,
            position=position,
            rotate=rotate,
            opacity=opacity,
            rotation=rotation,
            doc_metadata=doc_metadata or {}
        )

class AddStampDTO(BaseModel):
    """
    DTO để thêm dấu vào tài liệu PDF.
    """
    stamp_id: str
    page_number: int = 1
    x_position: float = 100
    y_position: float = 100
    doc_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class MergeDocumentsDTO(BaseModel):
    """
    DTO để gộp nhiều tài liệu PDF.
    """
    document_ids: List[str]
    output_filename: str
    doc_metadata: Dict[str, Any] = Field(default_factory=dict)

class ConvertToImagesDTO(BaseModel):
    """
    DTO để chuyển đổi PDF sang hình ảnh.
    """
    format: str = "PNG"  # PNG, JPEG
    quality: int = 200  # DPI
    doc_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class SignPdfDTO(BaseModel):
    """
    DTO để thêm chữ ký vào tài liệu PDF.
    """
    document_id: str
    stamp_id: str
    x: int = Field(..., ge=0)
    y: int = Field(..., ge=0)
    width: int = Field(..., gt=0)
    height: int = Field(..., gt=0)
    page_number: Optional[int] = Field(None, ge=1)

class MergePdfDTO(BaseModel):
    """
    DTO để gộp nhiều tài liệu PDF.
    """
    document_ids: List[str] = Field(..., min_items=2)
    output_filename: str = Field(..., min_length=1)

class CrackPdfDTO(BaseModel):
    """
    DTO để crack mật khẩu PDF.
    """
    document_id: str
    wordlist: Optional[List[str]] = None
    charset: Optional[str] = None
    min_length: Optional[int] = Field(None, ge=1)
    max_length: Optional[int] = Field(None, ge=1)

    @validator('max_length')
    def max_length_greater_than_min_length(cls, v, values, **kwargs):
        if v is not None and values.get('min_length') is not None and v < values['min_length']:
            raise ValueError('max_length must be greater than or equal to min_length')
        return v

class ConvertPdfToWordDTO(BaseModel):
    """
    DTO để chuyển đổi PDF sang Word.
    """
    document_id: str
    start_page: Optional[int] = Field(None, ge=1)
    end_page: Optional[int] = Field(None, ge=1)

    @validator('end_page')
    def end_page_greater_than_start_page(cls, v, values, **kwargs):
        if v is not None and values.get('start_page') is not None and v < values['start_page']:
            raise ValueError('end_page must be greater than or equal to start_page')
        return v

class ConvertPdfToImageDTO(BaseModel):
    """
    DTO để chuyển đổi PDF sang hình ảnh.
    """
    document_id: str
    output_format: Optional[str] = "png"
    dpi: Optional[int] = Field(150, ge=72, le=600)
    page_numbers: Optional[List[int]] = None

    @validator('output_format')
    def validate_output_format(cls, v):
        if v and v.lower() not in ['png', 'zip']:
            raise ValueError("output_format must be 'png' or 'zip'")
        return v