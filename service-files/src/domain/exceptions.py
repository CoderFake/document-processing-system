class BaseServiceException(Exception):
    """
    Exception cơ sở cho service.
    """
    def __init__(self, message: str, code: str):
        self.message = message
        self.code = code
        super().__init__(self.message)

class FileNotFoundException(BaseServiceException):
    """
    Ngoại lệ khi không tìm thấy tệp.
    """
    def __init__(self, file_id: str):
        super().__init__(
            message=f"Không tìm thấy tệp với ID: {file_id}",
            code="file_not_found"
        )

class ArchiveException(Exception):
    """Exception cơ sở cho các lỗi liên quan đến tệp nén."""
    pass

class ArchiveNotFoundException(BaseServiceException):
    """
    Ngoại lệ khi không tìm thấy tệp nén.
    """
    def __init__(self, archive_id: str):
        super().__init__(
            message=f"Không tìm thấy tệp nén với ID: {archive_id}",
            code="archive_not_found"
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

class CompressionException(BaseServiceException):
    """
    Ngoại lệ khi có lỗi nén tệp.
    """
    def __init__(self, message: str):
        super().__init__(
            message=f"Lỗi nén tệp: {message}",
            code="compression_error"
        )

class ExtractionException(BaseServiceException):
    """
    Ngoại lệ khi có lỗi giải nén tệp.
    """
    def __init__(self, message: str):
        super().__init__(
            message=f"Lỗi giải nén tệp: {message}",
            code="extraction_error"
        )

class UnsupportedFormatException(BaseServiceException):
    """
    Ngoại lệ khi định dạng tệp không được hỗ trợ.
    """
    def __init__(self, format: str):
        super().__init__(
            message=f"Định dạng tệp không được hỗ trợ: {format}",
            code="unsupported_format"
        )

class PasswordProtectedException(BaseServiceException):
    """
    Ngoại lệ khi tệp nén được bảo vệ bằng mật khẩu.
    """
    def __init__(self):
        super().__init__(
            message="Tệp nén được bảo vệ bằng mật khẩu",
            code="password_protected"
        )

class WrongPasswordException(BaseServiceException):
    """
    Ngoại lệ khi mật khẩu không đúng.
    """
    def __init__(self):
        super().__init__(
            message="Mật khẩu không đúng",
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

class InvalidArchiveException(BaseServiceException):
    """
    Ngoại lệ khi tệp nén không hợp lệ.
    """
    def __init__(self, message: str = "Tệp nén không hợp lệ"):
        super().__init__(
            message=message,
            code="invalid_archive"
        )

class InvalidFileFormatException(BaseServiceException):
    """
    Ngoại lệ khi định dạng tệp không hợp lệ.
    """
    def __init__(self, filename: str, expected_formats: str):
        super().__init__(
            message=f"Định dạng tệp không hợp lệ: {filename}. Chỉ hỗ trợ {expected_formats}",
            code="invalid_file_format"
        )

class FileTooLargeException(BaseServiceException):
    """
    Ngoại lệ khi tệp quá lớn.
    """
    def __init__(self, file_size: int, max_size: int):
        super().__init__(
            message=f"Tệp quá lớn: {file_size} bytes. Kích thước tối đa cho phép: {max_size} bytes",
            code="file_too_large"
        )

class CleanupException(BaseServiceException):
    """
    Ngoại lệ khi có lỗi dọn dẹp tệp.
    """
    def __init__(self, message: str):
        super().__init__(
            message=f"Lỗi dọn dẹp tệp: {message}",
            code="cleanup_error"
        )

class ProcessingException(BaseServiceException):
    """
    Ngoại lệ khi có lỗi xử lý tệp.
    """
    def __init__(self, message: str):
        super().__init__(
            message=f"Lỗi xử lý tệp: {message}",
            code="processing_error"
        )