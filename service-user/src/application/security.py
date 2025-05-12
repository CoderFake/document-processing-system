from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from passlib.context import CryptContext
from jose import jwt, JWTError
import uuid
import json

from core.config import settings
from domain.models import User, TokenData
from domain.exceptions import TokenExpiredException, InvalidTokenException

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Xác minh mật khẩu bằng cách so sánh mật khẩu gốc với mật khẩu đã được băm.
    
    Args:
        plain_password: Mật khẩu gốc
        hashed_password: Mật khẩu đã được băm
    
    Returns:
        True nếu mật khẩu khớp, ngược lại False
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Tạo mật khẩu được băm từ mật khẩu gốc.
    
    Args:
        password: Mật khẩu gốc
    
    Returns:
        Mật khẩu đã được băm
    """
    return pwd_context.hash(password)


def create_access_token(
    user_id: int,
    username: str,
    roles: List[str],
    permissions: List[Dict[str, str]],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Tạo JWT access token.
    
    Args:
        user_id: ID của người dùng
        username: Tên người dùng
        roles: Danh sách các vai trò của người dùng
        permissions: Danh sách các quyền của người dùng
        expires_delta: Thời gian tồn tại của token (nếu không được thiết lập, mặc định là 30 phút)
    
    Returns:
        JWT access token
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "sub": str(user_id),
        "username": username,
        "roles": roles,
        "permissions": permissions,
        "exp": expire,
        "jti": str(uuid.uuid4())
    }
    
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def create_refresh_token() -> str:
    """
    Tạo refresh token độc nhất.
    
    Returns:
        Refresh token
    """
    return str(uuid.uuid4())


def decode_token(token: str) -> TokenData:
    """
    Giải mã JWT token.
    
    Args:
        token: JWT token cần giải mã
    
    Returns:
        Dữ liệu giải mã từ token
    
    Raises:
        InvalidTokenException: Nếu token không hợp lệ
        TokenExpiredException: Nếu token đã hết hạn
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id: int = int(payload.get("sub"))
        username: str = payload.get("username")
        roles: List[str] = payload.get("roles", [])
        permissions: List[Dict[str, str]] = payload.get("permissions", [])
        exp: datetime = datetime.fromtimestamp(payload.get("exp"))
        
        if datetime.utcnow() > exp:
            raise TokenExpiredException()
        
        return TokenData(
            user_id=user_id,
            username=username,
            roles=roles,
            permissions=permissions,
            exp=exp
        )
    except JWTError:
        raise InvalidTokenException()
    except (KeyError, ValueError):
        raise InvalidTokenException()


def has_permission(token_data: TokenData, resource: str, action: str) -> bool:
    """
    Kiểm tra xem người dùng có quyền với tài nguyên và hành động cụ thể không.
    
    Args:
        token_data: Dữ liệu token của người dùng
        resource: Tài nguyên cần kiểm tra (e.g. file, document, user)
        action: Hành động cần kiểm tra (e.g. read, write, delete)
    
    Returns:
        True nếu có quyền, ngược lại False
    """
    for permission in token_data.permissions:
        if (permission["resource"] == resource or permission["resource"] == "*") and \
           (permission["action"] == action or permission["action"] == "*"):
            return True
    
    return False 