from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
from jose import JWTError, jwt
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from domain.models import User
from infrastructure.repository import UserRepository, RoleRepository, RefreshTokenRepository
from application.services import UserService, AuthService
from infrastructure.database import get_db_session

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

async def get_user_repository(session: AsyncSession = Depends(get_db_session)):
    """
    Dependency để lấy UserRepository.
    """
    return UserRepository(session)

async def get_role_repository(session: AsyncSession = Depends(get_db_session)):
    """
    Dependency để lấy RoleRepository.
    """
    return RoleRepository(session)

async def get_token_repository(session: AsyncSession = Depends(get_db_session)):
    """
    Dependency để lấy RefreshTokenRepository.
    """
    return RefreshTokenRepository(session)

async def get_user_service(
    repository: UserRepository = Depends(get_user_repository)
):
    """
    Dependency để lấy UserService.
    """
    return UserService(repository)

async def get_auth_service(
    user_repo: UserRepository = Depends(get_user_repository),
    role_repo: RoleRepository = Depends(get_role_repository),
    token_repo: RefreshTokenRepository = Depends(get_token_repository)
):
    """
    Dependency để lấy AuthService.
    """
    return AuthService(user_repo, role_repo, token_repo)

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    user_repo: UserRepository = Depends(get_user_repository)
) -> User:
    """
    Dependency để lấy người dùng hiện tại từ token JWT.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = await user_repo.get_user_by_id(user_id)
    if user is None:
        raise credentials_exception
        
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
        
    return user

async def get_current_active_superuser(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency để xác minh rằng người dùng hiện tại là superuser.
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have sufficient privileges"
        )
    return current_user 