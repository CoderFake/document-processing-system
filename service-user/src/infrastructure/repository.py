from typing import List, Optional, Dict, Any
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from domain.models import User, Role, Permission, RefreshToken


class UserRepository:
    """Repository để tương tác với database để quản lý User."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Lấy user theo ID."""
        query = select(User).options(
            selectinload(User.roles).selectinload(Role.permissions)
        ).where(User.id == user_id)
        
        result = await self.session.execute(query)
        return result.scalars().first()
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Lấy user theo username."""
        query = select(User).options(
            selectinload(User.roles).selectinload(Role.permissions)
        ).where(User.username == username)
        
        result = await self.session.execute(query)
        return result.scalars().first()
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Lấy user theo email."""
        query = select(User).options(
            selectinload(User.roles).selectinload(Role.permissions)
        ).where(User.email == email)
        
        result = await self.session.execute(query)
        return result.scalars().first()
    
    async def get_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Lấy danh sách users với phân trang."""
        query = select(User).options(
            selectinload(User.roles)
        ).offset(skip).limit(limit)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def create_user(self, user: User) -> User:
        """Tạo user mới."""
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user
    
    async def update_user(self, user_id: int, user_data: Dict[str, Any]) -> Optional[User]:
        """Cập nhật thông tin user."""
        query = update(User).where(User.id == user_id).values(**user_data).returning(User)
        result = await self.session.execute(query)
        await self.session.flush()
        return result.scalars().first()
    
    async def delete_user(self, user_id: int) -> bool:
        """Xóa user."""
        query = delete(User).where(User.id == user_id)
        result = await self.session.execute(query)
        return result.rowcount > 0
    
    async def assign_role_to_user(self, user: User, role: Role) -> None:
        """Gán role cho user."""
        user.roles.append(role)
        await self.session.flush()
    
    async def remove_role_from_user(self, user: User, role: Role) -> None:
        """Xóa role khỏi user."""
        user.roles.remove(role)
        await self.session.flush()


class RoleRepository:
    """Repository để tương tác với database để quản lý Role."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_role_by_id(self, role_id: int) -> Optional[Role]:
        """Lấy role theo ID."""
        query = select(Role).options(
            selectinload(Role.permissions)
        ).where(Role.id == role_id)
        
        result = await self.session.execute(query)
        return result.scalars().first()
    
    async def get_role_by_name(self, name: str) -> Optional[Role]:
        """Lấy role theo tên."""
        query = select(Role).options(
            selectinload(Role.permissions)
        ).where(Role.name == name)
        
        result = await self.session.execute(query)
        return result.scalars().first()
    
    async def get_roles(self) -> List[Role]:
        """Lấy danh sách roles."""
        query = select(Role).options(
            selectinload(Role.permissions)
        )
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def create_role(self, role: Role) -> Role:
        """Tạo role mới."""
        self.session.add(role)
        await self.session.flush()
        await self.session.refresh(role)
        return role
    
    async def update_role(self, role_id: int, role_data: Dict[str, Any]) -> Optional[Role]:
        """Cập nhật thông tin role."""
        query = update(Role).where(Role.id == role_id).values(**role_data).returning(Role)
        result = await self.session.execute(query)
        await self.session.flush()
        return result.scalars().first()
    
    async def delete_role(self, role_id: int) -> bool:
        """Xóa role."""
        query = delete(Role).where(Role.id == role_id)
        result = await self.session.execute(query)
        return result.rowcount > 0
    
    async def assign_permission_to_role(self, role: Role, permission: Permission) -> None:
        """Gán permission cho role."""
        role.permissions.append(permission)
        await self.session.flush()
    
    async def remove_permission_from_role(self, role: Role, permission: Permission) -> None:
        """Xóa permission khỏi role."""
        role.permissions.remove(permission)
        await self.session.flush()


class RefreshTokenRepository:
    """Repository để tương tác với database để quản lý RefreshToken."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_refresh_token(self, token: str) -> Optional[RefreshToken]:
        """Lấy refresh token."""
        query = select(RefreshToken).options(
            selectinload(RefreshToken.user)
        ).where(RefreshToken.token == token, RefreshToken.revoked == False)
        
        result = await self.session.execute(query)
        return result.scalars().first()
    
    async def create_refresh_token(self, refresh_token: RefreshToken) -> RefreshToken:
        """Tạo refresh token mới."""
        self.session.add(refresh_token)
        await self.session.flush()
        await self.session.refresh(refresh_token)
        return refresh_token
    
    async def revoke_refresh_token(self, token: str) -> bool:
        """Thu hồi refresh token."""
        query = update(RefreshToken).where(
            RefreshToken.token == token, 
            RefreshToken.revoked == False
        ).values(revoked=True)
        
        result = await self.session.execute(query)
        return result.rowcount > 0
    
    async def revoke_all_user_tokens(self, user_id: int) -> int:
        """Thu hồi tất cả refresh token của user."""
        query = update(RefreshToken).where(
            RefreshToken.user_id == user_id, 
            RefreshToken.revoked == False
        ).values(revoked=True)
        
        result = await self.session.execute(query)
        return result.rowcount 