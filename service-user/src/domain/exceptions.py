class BaseServiceException(Exception):
    """
    Exception cơ sở cho service.
    """
    def __init__(self, message: str, code: str):
        self.message = message
        self.code = code
        super().__init__(self.message)


class UserNotFoundException(BaseServiceException):
    """
    Ngoại lệ khi không tìm thấy người dùng.
    """
    def __init__(self, user_id: str = None, username: str = None, email: str = None):
        identifier = ""
        if user_id:
            identifier = f"ID: {user_id}"
        elif username:
            identifier = f"username: {username}"
        elif email:
            identifier = f"email: {email}"
        
        super().__init__(
            message=f"Không tìm thấy người dùng với {identifier}",
            code="user_not_found"
        )


class UserAlreadyExistsException(BaseServiceException):
    """
    Ngoại lệ khi người dùng đã tồn tại.
    """
    def __init__(self, username: str = None, email: str = None):
        identifier = ""
        if username:
            identifier = f"username: {username}"
        elif email:
            identifier = f"email: {email}"
        
        super().__init__(
            message=f"Người dùng đã tồn tại với {identifier}",
            code="user_already_exists"
        )


class InvalidCredentialsException(BaseServiceException):
    """
    Ngoại lệ khi thông tin đăng nhập không hợp lệ.
    """
    def __init__(self):
        super().__init__(
            message="Thông tin đăng nhập không hợp lệ",
            code="invalid_credentials"
        )


class TokenExpiredException(BaseServiceException):
    """
    Ngoại lệ khi token đã hết hạn.
    """
    def __init__(self):
        super().__init__(
            message="Token đã hết hạn",
            code="token_expired"
        )


class InvalidTokenException(BaseServiceException):
    """
    Ngoại lệ khi token không hợp lệ.
    """
    def __init__(self):
        super().__init__(
            message="Token không hợp lệ",
            code="invalid_token"
        )


class InsufficientPermissionsException(BaseServiceException):
    """
    Ngoại lệ khi không đủ quyền truy cập.
    """
    def __init__(self, required_permission: str = None):
        message = "Không đủ quyền truy cập"
        if required_permission:
            message += f": {required_permission}"
            
        super().__init__(
            message=message,
            code="insufficient_permissions"
        )


class RoleNotFoundException(BaseServiceException):
    """
    Ngoại lệ khi không tìm thấy vai trò.
    """
    def __init__(self, role_id: str = None, role_name: str = None):
        identifier = ""
        if role_id:
            identifier = f"ID: {role_id}"
        elif role_name:
            identifier = f"tên: {role_name}"
        
        super().__init__(
            message=f"Không tìm thấy vai trò với {identifier}",
            code="role_not_found"
        )


class PermissionNotFoundException(BaseServiceException):
    """
    Ngoại lệ khi không tìm thấy quyền.
    """
    def __init__(self, permission_id: str = None, permission_name: str = None):
        identifier = ""
        if permission_id:
            identifier = f"ID: {permission_id}"
        elif permission_name:
            identifier = f"tên: {permission_name}"
        
        super().__init__(
            message=f"Không tìm thấy quyền với {identifier}",
            code="permission_not_found"
        )


class UserNotActiveException(BaseServiceException):
    """
    Ngoại lệ khi tài khoản không hoạt động.
    """
    def __init__(self):
        super().__init__(
            message="Tài khoản không hoạt động",
            code="user_not_active"
        )


class EmailNotVerifiedException(BaseServiceException):
    """
    Ngoại lệ khi email chưa được xác minh.
    """
    def __init__(self):
        super().__init__(
            message="Email chưa được xác minh",
            code="email_not_verified"
        ) 