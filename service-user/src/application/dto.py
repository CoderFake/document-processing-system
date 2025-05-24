from pydantic import BaseModel, EmailStr, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime


class UserRegisterDTO(BaseModel):
    """DTO cho đăng ký người dùng."""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None
    
    @validator('username')
    def username_alphanumeric(cls, v):
        if not v.isalnum():
            raise ValueError('Username chỉ được chứa ký tự chữ và số')
        return v


class UserCreateDTO(BaseModel):
    """DTO cho tạo người dùng mới."""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None
    is_active: Optional[bool] = True
    is_verified: Optional[bool] = False
    
    @validator('username')
    def username_alphanumeric(cls, v):
        if not v.isalnum():
            raise ValueError('Username chỉ được chứa ký tự chữ và số')
        return v


class UserUpdateDTO(BaseModel):
    """DTO cho cập nhật thông tin người dùng."""
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8)
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    profile_image: Optional[str] = None


class UserLoginDTO(BaseModel):
    """DTO cho đăng nhập."""
    username: str
    password: str


class ChangePasswordDTO(BaseModel):
    """DTO cho đổi mật khẩu."""
    current_password: str
    new_password: str = Field(..., min_length=8)


class RefreshTokenDTO(BaseModel):
    """DTO cho làm mới token."""
    refresh_token: str


class TokenResponseDTO(BaseModel):
    """DTO cho phản hồi token."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponseDTO(BaseModel):
    """DTO cho phản hồi thông tin người dùng."""
    id: int
    username: str
    email: str
    full_name: Optional[str] = None
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login: Optional[datetime] = None
    roles: List[str]


class UserDetailsResponseDTO(UserResponseDTO):
    """DTO cho phản hồi thông tin chi tiết người dùng."""
    permissions: List[Dict[str, str]]
    profile_image: Optional[str] = None
    user_metadata: Optional[Dict[str, Any]] = None


class RoleCreateDTO(BaseModel):
    """DTO cho tạo vai trò mới."""
    name: str = Field(..., min_length=3, max_length=50)
    description: Optional[str] = None


class RoleUpdateDTO(BaseModel):
    """DTO cho cập nhật vai trò."""
    name: Optional[str] = Field(None, min_length=3, max_length=50)
    description: Optional[str] = None


class PermissionCreateDTO(BaseModel):
    """DTO cho tạo quyền mới."""
    name: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = None
    resource: str = Field(..., min_length=1, max_length=50)
    action: str = Field(..., min_length=1, max_length=50)


class RoleResponseDTO(BaseModel):
    """DTO cho phản hồi thông tin vai trò."""
    id: int
    name: str
    description: Optional[str] = None
    permissions: List[Dict[str, str]]


class PermissionResponseDTO(BaseModel):
    """DTO cho phản hồi thông tin quyền."""
    id: int
    name: str
    description: Optional[str] = None
    resource: str
    action: str


class AssignRoleDTO(BaseModel):
    """DTO cho gán vai trò cho người dùng."""
    role_id: str


class AssignPermissionDTO(BaseModel):
    """DTO cho gán quyền cho vai trò."""
    permission_id: str 