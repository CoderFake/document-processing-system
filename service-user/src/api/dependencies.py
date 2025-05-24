import logging
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
import jwt
from jwt.exceptions import PyJWTError

from domain.models import User, TokenData
from infrastructure.database import get_db_session
from infrastructure.repository import UserRepository, RoleRepository, RefreshTokenRepository, DocumentRepository, DocumentCategoryRepository
from application.services import UserService, AuthService, DocumentService, DocumentCategoryService
from application.security import verify_token
from core.config import settings

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/token")


def get_user_repository(session: AsyncSession = Depends(get_db_session)) -> UserRepository:
    """
    Dependency để lấy UserRepository.
    """
    return UserRepository(session)


def get_role_repository(session: AsyncSession = Depends(get_db_session)) -> RoleRepository:
    """
    Dependency để lấy RoleRepository.
    """
    return RoleRepository(session)


def get_refresh_token_repository(session: AsyncSession = Depends(get_db_session)) -> RefreshTokenRepository:
    """
    Dependency để lấy RefreshTokenRepository.
    """
    return RefreshTokenRepository(session)


def get_document_repository(session: AsyncSession = Depends(get_db_session)) -> DocumentRepository:
    """
    Dependency để lấy DocumentRepository.
    """
    return DocumentRepository(session)


def get_document_category_repository(session: AsyncSession = Depends(get_db_session)) -> DocumentCategoryRepository:
    """
    Dependency để lấy DocumentCategoryRepository.
    """
    return DocumentCategoryRepository(session)


def get_user_service(
    user_repository: UserRepository = Depends(get_user_repository),
    token_repository: RefreshTokenRepository = Depends(get_refresh_token_repository)
) -> UserService:
    """
    Dependency để lấy UserService.
    """
    return UserService(user_repository, token_repository)


def get_auth_service(
    user_repository: UserRepository = Depends(get_user_repository),
    role_repository: RoleRepository = Depends(get_role_repository),
    token_repository: RefreshTokenRepository = Depends(get_refresh_token_repository)
) -> AuthService:
    """
    Dependency để lấy AuthService.
    """
    return AuthService(user_repository, role_repository, token_repository)


def get_document_service(
    document_repository: DocumentRepository = Depends(get_document_repository),
    category_repository: DocumentCategoryRepository = Depends(get_document_category_repository)
) -> DocumentService:
    """
    Dependency để lấy DocumentService.
    """
    return DocumentService(document_repository, category_repository)


def get_document_category_service(
    category_repository: DocumentCategoryRepository = Depends(get_document_category_repository)
) -> DocumentCategoryService:
    """
    Dependency để lấy DocumentCategoryService.
    """
    return DocumentCategoryService(category_repository)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    user_service: UserService = Depends(get_user_service)
) -> User:
    """
    Dependency để lấy người dùng hiện tại từ token.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Không thể xác thực thông tin đăng nhập",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token_data = verify_token(token)
        if token_data is None:
            raise credentials_exception
        
        user = await user_service.get_user(token_data.user_id)
        if user is None:
            raise credentials_exception
            
        return user
    except PyJWTError:
        raise credentials_exception


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency để lấy người dùng đang hoạt động hiện tại.
    """
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Người dùng không hoạt động")
    return current_user


async def get_optional_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    user_service: UserService = Depends(get_user_service)
) -> Optional[User]:
    """
    Dependency để lấy người dùng hiện tại từ token (không bắt buộc).
    """
    if not token:
        return None
        
    try:
        token_data = verify_token(token)
        if token_data is None:
            return None
        
        user = await user_service.get_user(token_data.user_id)
        return user
    except PyJWTError:
        return None 