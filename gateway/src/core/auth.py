import jwt
from typing import Dict, Any, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import PyJWTError

from core.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

def decode_jwt_token(token: str) -> Dict[str, Any]:
    """
    Giải mã JWT token để lấy thông tin người dùng
    """
    try:
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ hoặc hết hạn",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_user_id(token: str = Depends(oauth2_scheme)) -> str:
    """
    Lấy user_id từ token hiện tại
    """
    try:
        payload = decode_jwt_token(token)
        user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token không chứa thông tin người dùng",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return str(user_id)
    except PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Không thể xác thực token",
            headers={"WWW-Authenticate": "Bearer"},
        ) 