from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from domain.models import User, Role, Permission, RefreshToken
from infrastructure.repository import UserRepository, RoleRepository, RefreshTokenRepository
from application.dto import UserCreateDTO, UserUpdateDTO, RoleCreateDTO, RoleUpdateDTO
from application.security import verify_password, get_password_hash
from domain.exceptions import UserNotFoundException, RoleNotFoundException

logger = logging.getLogger(__name__)


class UserService:
    """Service cho các hoạt động liên quan đến User."""
    
    def __init__(self, repository: UserRepository):
        self.repository = repository
    
    async def get_user(self, user_id: int) -> Optional[User]:
        """Lấy thông tin user theo ID."""
        user = await self.repository.get_user_by_id(user_id)
        if not user:
            logger.info(f"User with ID {user_id} not found")
            return None
        return user
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Lấy thông tin user theo username."""
        return await self.repository.get_user_by_username(username)
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Lấy thông tin user theo email."""
        return await self.repository.get_user_by_email(email)
    
    async def get_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Lấy danh sách users."""
        return await self.repository.get_users(skip, limit)
    
    async def create_user(self, user_data: UserCreateDTO) -> User:
        """Tạo user mới."""
        existing_user = await self.repository.get_user_by_username(user_data.username)
        if existing_user:
            raise ValueError(f"Username '{user_data.username}' already exists")
        
        existing_user = await self.repository.get_user_by_email(user_data.email)
        if existing_user:
            raise ValueError(f"Email '{user_data.email}' already exists")
        
        hashed_password = get_password_hash(user_data.password)
        
        user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password,
            full_name=user_data.full_name,
            is_active=user_data.is_active if user_data.is_active is not None else True,
            is_verified=user_data.is_verified if user_data.is_verified is not None else False,
        )
        
        return await self.repository.create_user(user)
    
    async def update_user(self, user_id: int, user_data: UserUpdateDTO) -> Optional[User]:
        """Cập nhật thông tin user."""
        user = await self.repository.get_user_by_id(user_id)
        if not user:
            return None
        
        update_data = {}
        
        if user_data.email is not None and user_data.email != user.email:
            existing_user = await self.repository.get_user_by_email(user_data.email)
            if existing_user and existing_user.id != user_id:
                raise ValueError(f"Email '{user_data.email}' already exists")
            update_data["email"] = user_data.email
        
        if user_data.full_name is not None:
            update_data["full_name"] = user_data.full_name
        
        if user_data.is_active is not None:
            update_data["is_active"] = user_data.is_active
        
        if user_data.is_verified is not None:
            update_data["is_verified"] = user_data.is_verified
        
        if user_data.profile_image is not None:
            update_data["profile_image"] = user_data.profile_image
        
        if user_data.password is not None:
            update_data["hashed_password"] = get_password_hash(user_data.password)
        
        if not update_data:
            return user
        
        update_data["updated_at"] = datetime.utcnow()
        
        return await self.repository.update_user(user_id, update_data)
    
    async def delete_user(self, user_id: int) -> bool:
        """Xóa user."""
        user = await self.repository.get_user_by_id(user_id)
        if not user:
            return False

        return await self.repository.delete_user(user_id)
    
    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Xác thực user với username và password."""
        user = await self.repository.get_user_by_username(username)
        if not user:
            return None
        
        if not verify_password(password, user.hashed_password):
            return None
        
        return user


class RoleService:
    """Service cho các hoạt động liên quan đến Role."""
    
    def __init__(self, repository: RoleRepository):
        self.repository = repository
    
    async def get_role(self, role_id: int) -> Optional[Role]:
        """Lấy thông tin role theo ID."""
        role = await self.repository.get_role_by_id(role_id)
        if not role:
            logger.info(f"Role with ID {role_id} not found")
            return None
        return role
    
    async def get_role_by_name(self, name: str) -> Optional[Role]:
        """Lấy thông tin role theo tên."""
        return await self.repository.get_role_by_name(name)
    
    async def get_roles(self) -> List[Role]:
        """Lấy danh sách roles."""
        return await self.repository.get_roles()
    
    async def create_role(self, role_data: RoleCreateDTO) -> Role:
        """Tạo role mới."""
        existing_role = await self.repository.get_role_by_name(role_data.name)
        if existing_role:
            raise ValueError(f"Role '{role_data.name}' already exists")
        
        role = Role(
            name=role_data.name,
            description=role_data.description
        )
        
        return await self.repository.create_role(role)
    
    async def update_role(self, role_id: int, role_data: RoleUpdateDTO) -> Optional[Role]:
        """Cập nhật thông tin role."""
        role = await self.repository.get_role_by_id(role_id)
        if not role:
            return None
        
        update_data = {}
        
        if role_data.name is not None and role_data.name != role.name:
            existing_role = await self.repository.get_role_by_name(role_data.name)
            if existing_role and existing_role.id != role_id:
                raise ValueError(f"Role '{role_data.name}' already exists")
            update_data["name"] = role_data.name
        
        if role_data.description is not None:
            update_data["description"] = role_data.description
        
        if not update_data:
            return role
        
        update_data["updated_at"] = datetime.utcnow()
        
        return await self.repository.update_role(role_id, update_data)
    
    async def delete_role(self, role_id: int) -> bool:
        """Xóa role."""
        role = await self.repository.get_role_by_id(role_id)
        if not role:
            return False
        
        return await self.repository.delete_role(role_id)


class AuthService:
    """Service cho các hoạt động liên quan đến xác thực."""
    
    def __init__(
        self, 
        user_repository: UserRepository,
        role_repository: RoleRepository,
        token_repository: RefreshTokenRepository
    ):
        self.user_repository = user_repository
        self.role_repository = role_repository
        self.token_repository = token_repository
    
    async def assign_role_to_user(self, user_id: int, role_id: int) -> bool:
        """Gán role cho user."""
        user = await self.user_repository.get_user_by_id(user_id)
        if not user:
            raise UserNotFoundException(f"User with ID {user_id} not found")
        
        role = await self.role_repository.get_role_by_id(role_id)
        if not role:
            raise RoleNotFoundException(f"Role with ID {role_id} not found")
        
        await self.user_repository.assign_role_to_user(user, role)
        return True
    
    async def remove_role_from_user(self, user_id: int, role_id: int) -> bool:
        """Xóa role khỏi user."""
        user = await self.user_repository.get_user_by_id(user_id)
        if not user:
            raise UserNotFoundException(f"User with ID {user_id} not found")
        
        role = await self.role_repository.get_role_by_id(role_id)
        if not role:
            raise RoleNotFoundException(f"Role with ID {role_id} not found")
        
        await self.user_repository.remove_role_from_user(user, role)
        return True 