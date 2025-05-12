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
    Ngoại lệ khi không tìm thấy tài liệu PDF.
    """
    def __init__(self, document_id: str):
        super().__init__(
            message=f"Không tìm thấy tài liệu PDF với ID: {document_id}",
            code="document_not_found"
        )

class ImageNotFoundException(BaseServiceException):
    """
    Ngoại lệ khi không tìm thấy hình ảnh PNG.
    """
    def __init__(self, image_id: str):
        super().__init__(
            message=f"Không tìm thấy hình ảnh PNG với ID: {image_id}",
            code="image_not_found"
        )

class StampNotFoundException(BaseServiceException):
    """
    Ngoại lệ khi không tìm thấy mẫu dấu.
    """
    def __init__(self, stamp_id: str):
        super().__init__(
            message=f"Không tìm thấy mẫu dấu với ID: {stamp_id}",
            code="stamp_not_found"
        )

class InvalidDocumentFormatException(BaseServiceException):
    """
    Ngoại lệ khi định dạng tài liệu không hợp lệ.
    """
    def __init__(self, filename: str, expected_format: str):
        super().__init__(
            message=f"Định dạng tài liệu không hợp lệ: {filename}. Chỉ hỗ trợ {expected_format}",
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

class EncryptionException(BaseServiceException):
    """
    Ngoại lệ khi có lỗi mã hóa PDF.
    """
    def __init__(self, message: str):
        super().__init__(
            message=f"Lỗi mã hóa PDF: {message}",
            code="encryption_error"
        )

class DecryptionException(BaseServiceException):
    """
    Ngoại lệ khi có lỗi giải mã PDF.
    """
    def __init__(self, message: str):
        super().__init__(
            message=f"Lỗi giải mã PDF: {message}",
            code="decryption_error"
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

class SignatureException(BaseServiceException):
    """
    Ngoại lệ khi có lỗi thêm chữ ký.
    """
    def __init__(self, message: str):
        super().__init__(
            message=f"Lỗi thêm chữ ký: {message}",
            code="signature_error"
        )

class MergeException(BaseServiceException):
    """
    Ngoại lệ khi có lỗi gộp tài liệu PDF.
    """
    def __init__(self, message: str):
        super().__init__(
            message=f"Lỗi gộp tài liệu PDF: {message}",
            code="merge_error"
        )

class PDFPasswordProtectedException(BaseServiceException):
    """
    Ngoại lệ khi PDF được bảo vệ bằng mật khẩu.
    """
    def __init__(self):
        super().__init__(
            message="PDF được bảo vệ bằng mật khẩu. Vui lòng cung cấp mật khẩu để mở khóa.",
            code="pdf_password_protected"
        )

class WrongPasswordException(BaseServiceException):
    """
    Ngoại lệ khi mật khẩu cung cấp không đúng.
    """
    def __init__(self):
        super().__init__(
            message="Mật khẩu không đúng.",
            code="wrong_password"
        )

class CrackPasswordException(BaseServiceException):
    """
    Ngoại lệ khi không thể crack mật khẩu.
    """
    def __init__(self, message: str):
        super().__init__(
            message=f"Không thể crack mật khẩu: {message}",
            code="crack_password_error"
        )