from fastapi import APIRouter, HTTPException, Depends, status, Request, Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import Dict, Any, Optional
import httpx
from core.config import settings
from utils.client import ServiceClient

router = APIRouter()

user_service = ServiceClient(settings.USER_SERVICE_URL)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Lấy thông tin người dùng hiện tại từ token.

    Args:
        token: JWT token

    Returns:
        Thông tin người dùng
    
    Raises:
        HTTPException: Nếu token không hợp lệ hoặc người dùng không tồn tại
    """
    try:
        response = await user_service.post("/api/v1/auth/validate-token", {"token": token})
        return response
    except HTTPException as e:
        if e.status_code == 401:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token không hợp lệ hoặc đã hết hạn",
                headers={"WWW-Authenticate": "Bearer"}
            )
        raise e


@router.post("/register", summary="Đăng ký người dùng mới")
async def register(
    username: str,
    email: str,
    password: str,
    full_name: Optional[str] = None
):
    """
    Đăng ký người dùng mới.
    """
    try:
        response = await user_service.post("/api/v1/auth/register", {
            "username": username,
            "email": email,
            "password": password,
            "full_name": full_name
        })
        return response
    except HTTPException as e:
        raise e


@router.post("/login", summary="Đăng nhập và nhận token JWT")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Đăng nhập và nhận token JWT.
    """
    try:
        response = await user_service.post("/api/v1/auth/login", {
            "username": form_data.username,
            "password": form_data.password
        })
        return response
    except HTTPException as e:
        if e.status_code == 401:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Tên đăng nhập hoặc mật khẩu không đúng",
                headers={"WWW-Authenticate": "Bearer"}
            )
        raise e


@router.post("/refresh-token", summary="Làm mới token JWT")
async def refresh_token(refresh_token: str):
    """
    Làm mới token JWT bằng refresh token.
    """
    try:
        response = await user_service.post("/api/v1/auth/refresh-token", {"refresh_token": refresh_token})
        return response
    except HTTPException as e:
        if e.status_code == 401:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token không hợp lệ hoặc đã hết hạn",
                headers={"WWW-Authenticate": "Bearer"}
            )
        raise e


@router.post("/logout", summary="Đăng xuất")
async def logout(refresh_token: str):
    """
    Đăng xuất người dùng.
    """
    try:
        response = await user_service.post("/api/v1/auth/logout", {"refresh_token": refresh_token})
        return response
    except HTTPException as e:
        raise e


@router.get("/me", summary="Lấy thông tin người dùng hiện tại")
async def get_me(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Lấy thông tin người dùng hiện tại.
    """
    return current_user 