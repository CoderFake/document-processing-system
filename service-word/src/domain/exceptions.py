class BaseServiceException(Exception):
    """
    Lớp ngoại lệ cơ sở cho tất cả các ngoại lệ trong dịch vụ.
    """
    def __init__(self, message: str, code: str = "internal_error"):
        self.message = message
        self.code = code
        super().__init__(self.message)

class DocumentNotFoundException(BaseServiceException):
    """
    Ngoại lệ khi không tìm thấy tài liệu.
    """
    def __init__(self, document_id: str):
        super().__init__(
            message=f"Không tìm thấy tài liệu với ID: {document_id}",
            code="document_not_found"
        )

class TemplateNotFoundException(BaseServiceException):
    """
    Ngoại lệ khi không tìm thấy mẫu tài liệu.
    """
    def __init__(self, template_id: str):
        super().__init__(
            message=f"Không tìm thấy mẫu tài liệu với ID: {template_id}",
            code="template_not_found"
        )

class InvalidDocumentFormatException(BaseServiceException):
    """
    Ngoại lệ khi định dạng tài liệu không hợp lệ.
    """
    def __init__(self, filename: str):
        super().__init__(
            message=f"Định dạng tài liệu không hợp lệ: {filename}. Chỉ hỗ trợ .doc và .docx",
            code="invalid_document_format"
        )

class StorageException(BaseServiceException):
    """
    Ngoại lệ khi có lỗi lưu trữ.
    """
    def __init__(self, message: str):
        super().__init__(
            message=f"Lỗi lưu trữ: {message}",
            code="storage_error"
        )

class ConversionException(BaseServiceException):
    """
    Ngoại lệ khi có lỗi chuyển đổi tài liệu.
    """
    def __init__(self, message: str):
        super().__init__(
            message=f"Lỗi chuyển đổi tài liệu: {message}",
            code="conversion_error"
        )

class WatermarkException(BaseServiceException):
    """
    Ngoại lệ khi có lỗi thêm watermark.
    """
    def __init__(self, message: str):
        super().__init__(
            message=f"Lỗi thêm watermark: {message}",
            code="watermark_error"
        )

class TemplateApplicationException(BaseServiceException):
    """
    Ngoại lệ khi có lỗi áp dụng mẫu tài liệu.
    """
    def __init__(self, message: str):
        super().__init__(
            message=f"Lỗi áp dụng mẫu: {message}",
            code="template_application_error"
        )

class BatchProcessingException(BaseServiceException):
    """
    Ngoại lệ khi có lỗi xử lý hàng loạt.
    """
    def __init__(self, message: str):
        super().__init__(
            message=f"Lỗi xử lý hàng loạt: {message}",
            code="batch_processing_error"
        )