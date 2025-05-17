from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any, Optional
from fastapi.security import OAuth2PasswordRequestForm
import jwt
from jwt.exceptions import PyJWTError

from application.services import UserService, AuthService
from application.dto import UserCreateDTO, UserUpdateDTO, UserRegisterDTO, TokenResponseDTO
from api.dependencies import get_user_service, get_current_user, get_auth_service
from domain.models import User
from application.security import create_access_token
from core.config import settings

router = APIRouter()

@router.post("/auth/register", response_model=UserCreateDTO, status_code=status.HTTP_201_CREATED, tags=["auth"])
async def register(
    user_data: UserRegisterDTO,
    user_service: UserService = Depends(get_user_service)
):
    """
    Đăng ký người dùng mới.
    """
    try:
        create_data = UserCreateDTO(
            username=user_data.username,
            email=user_data.email,
            password=user_data.password,
            full_name=user_data.full_name,
            is_active=True,
            is_verified=False
        )
        user = await user_service.create_user(create_data)
        return create_data
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/auth/login", response_model=TokenResponseDTO, tags=["auth"])
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service),
    user_service: UserService = Depends(get_user_service)
):
    """
    Đăng nhập và lấy token.
    """
    user = await user_service.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token = create_access_token(user)
    refresh_token = await auth_service.create_refresh_token(user.id)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": 3600
    }

@router.post("/auth/validate-token", tags=["auth"])
async def validate_token(
    token: Dict[str, str],
    user_service: UserService = Depends(get_user_service)
):
    """
    Xác thực token và trả về thông tin người dùng.
    """
    try:
        # Lấy token từ request body
        token_str = token.get("token")
        if not token_str:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token is required",
            )
            
        # Giải mã token
        try:
            payload = jwt.decode(
                token_str,
                settings.JWT_SECRET_KEY, 
                algorithms=[settings.JWT_ALGORITHM]
            )
        except PyJWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # Lấy user_id từ payload
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # Lấy thông tin user từ database
        user = await user_service.get_user(int(user_id))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User is inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        return user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token validation error: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

@router.post("/auth/refresh-token", response_model=TokenResponseDTO, tags=["auth"])
async def refresh_token(
    refresh_token: Dict[str, str],
    auth_service: AuthService = Depends(get_auth_service),
    user_service: UserService = Depends(get_user_service)
):
    """
    Làm mới token JWT bằng refresh token.
    """
    try:
        # Lấy refresh_token từ request body
        token_str = refresh_token.get("refresh_token")
        if not token_str:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Refresh token is required",
            )
            
        token_data = await auth_service.verify_refresh_token(token_str)
        user_id = token_data.user_id
        
        # Lấy thông tin người dùng từ ID
        user = await user_service.get_user(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        access_token = create_access_token(user)
        new_refresh_token = await auth_service.create_refresh_token(user_id)
        
        await auth_service.revoke_refresh_token(token_str)
        
        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "expires_in": 3600
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid refresh token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"}
        )

@router.post("/auth/logout", tags=["auth"])
async def logout(
    refresh_token: Dict[str, str],
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Đăng xuất người dùng bằng cách thu hồi refresh token.
    """
    try:
        # Lấy refresh_token từ request body
        token_str = refresh_token.get("refresh_token")
        if not token_str:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Refresh token is required",
            )
            
        success = await auth_service.revoke_refresh_token(token_str)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid refresh token"
            )
        return {"detail": "Successfully logged out"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Logout error: {str(e)}"
        )

@router.get("/users", tags=["users"])
async def get_users(
    skip: int = 0, 
    limit: int = 100,
    user_service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_user)
):
    """
    Lấy danh sách người dùng.
    """
    return await user_service.get_users(skip=skip, limit=limit)

@router.get("/users/{user_id}", tags=["users"])
async def get_user(
    user_id: int,
    user_service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_user)
):
    """
    Lấy thông tin người dùng theo ID.
    """
    user = await user_service.get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    return user

@router.post("/users", tags=["users"], status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreateDTO,
    user_service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_user)
):
    """
    Tạo người dùng mới.
    """
    return await user_service.create_user(user_data)

@router.put("/users/{user_id}", tags=["users"])
async def update_user(
    user_id: int,
    user_data: UserUpdateDTO,
    user_service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_user)
):
    """
    Cập nhật thông tin người dùng.
    """
    user = await user_service.update_user(user_id, user_data)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    return user

@router.delete("/users/{user_id}", tags=["users"], status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    user_service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_user)
):
    """
    Xóa người dùng.
    """
    success = await user_service.delete_user(user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    return None

@router.get("/me", tags=["users"])
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Lấy thông tin người dùng hiện tại.
    """
    return current_user 