from typing import List, Optional, Dict, Any
from sqlalchemy import select, update, delete, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from datetime import datetime

from domain.models import User, Role, Permission, RefreshToken, Document, DocumentCategory
from application.security import get_password_hash, verify_password


class UserRepository:
    """Repository để tương tác với database để quản lý User."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
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
    
    async def update_user(self, user_id: str, user_data: Dict[str, Any]) -> Optional[User]:
        """Cập nhật thông tin user."""
        query = update(User).where(User.id == user_id).values(**user_data).returning(User)
        result = await self.session.execute(query)
        await self.session.flush()
        return result.scalars().first()
    
    async def delete_user(self, user_id: str) -> bool:
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
    
    async def get_role_by_id(self, role_id: str) -> Optional[Role]:
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
    
    async def update_role(self, role_id: str, role_data: Dict[str, Any]) -> Optional[Role]:
        """Cập nhật thông tin role."""
        query = update(Role).where(Role.id == role_id).values(**role_data).returning(Role)
        result = await self.session.execute(query)
        await self.session.flush()
        return result.scalars().first()
    
    async def delete_role(self, role_id: str) -> bool:
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
    
    async def revoke_all_user_tokens(self, user_id: str) -> int:
        """Thu hồi tất cả refresh token của user."""
        query = update(RefreshToken).where(
            RefreshToken.user_id == user_id, 
            RefreshToken.revoked == False
        ).values(revoked=True)
        
        result = await self.session.execute(query)
        return result.rowcount 


class DocumentRepository:
    """
    Repository để làm việc với Document.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, document_data: Dict[str, Any]) -> Document:
        """
        Tạo tài liệu mới.
        """
        document = Document(**document_data)
        self.session.add(document)
        await self.session.commit()
        await self.session.refresh(document)
        return document

    async def get_by_id(self, document_id: str) -> Optional[Document]:
        """
        Lấy tài liệu theo ID.
        """
        query = select(Document).where(Document.id == document_id, Document.is_deleted == False)
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_by_storage_id(self, storage_id: str) -> Optional[Document]:
        """
        Lấy tài liệu theo ID lưu trữ.
        """
        query = select(Document).where(Document.storage_id == storage_id, Document.is_deleted == False)
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_by_user_id(self, user_id: str, skip: int = 0, limit: int = 100, 
                             file_type: Optional[str] = None,
                             service_name: Optional[str] = None,
                             category_id: Optional[int] = None) -> List[Document]:
        """
        Lấy danh sách tài liệu của người dùng.
        """
        conditions = [Document.user_id == user_id, Document.is_deleted == False]
        
        if file_type:
            conditions.append(Document.file_type == file_type)
            
        if service_name:
            conditions.append(Document.service_name == service_name)
            
        if category_id:
            conditions.append(Document.category_id == category_id)
            
        query = select(Document).where(and_(*conditions)).order_by(Document.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_all(self, skip: int = 0, limit: int = 100, 
                      file_type: Optional[str] = None,
                      service_name: Optional[str] = None,
                      category_id: Optional[int] = None) -> List[Document]:
        """
        Lấy tất cả tài liệu.
        """
        conditions = [Document.is_deleted == False]
        
        if file_type:
            conditions.append(Document.file_type == file_type)
            
        if service_name:
            conditions.append(Document.service_name == service_name)
            
        if category_id:
            conditions.append(Document.category_id == category_id)
            
        query = select(Document).where(and_(*conditions)).order_by(Document.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def update(self, document_id: str, document_data: Dict[str, Any]) -> Optional[Document]:
        """
        Cập nhật thông tin tài liệu.
        """
        document = await self.get_by_id(document_id)
        if not document:
            return None

        for key, value in document_data.items():
            if hasattr(document, key):
                setattr(document, key, value)

        await self.session.commit()
        await self.session.refresh(document)
        return document

    async def delete(self, document_id: str, hard_delete: bool = False) -> bool:
        """
        Xóa tài liệu.
        """
        document = await self.get_by_id(document_id)
        if not document:
            return False

        if hard_delete:
            await self.session.delete(document)
        else:
            document.is_deleted = True
            document.updated_at = datetime.utcnow()

        await self.session.commit()
        return True

    async def count_by_user_id(self, user_id: str, 
                              file_type: Optional[str] = None,
                              service_name: Optional[str] = None,
                              category_id: Optional[int] = None) -> int:
        """
        Đếm số lượng tài liệu của người dùng.
        """
        conditions = [Document.user_id == user_id, Document.is_deleted == False]
        
        if file_type:
            conditions.append(Document.file_type == file_type)
            
        if service_name:
            conditions.append(Document.service_name == service_name)
            
        if category_id:
            conditions.append(Document.category_id == category_id)
            
        query = select(func.count(Document.id)).where(and_(*conditions))
        result = await self.session.execute(query)
        return result.scalar_one()

    async def count_all(self, 
                       file_type: Optional[str] = None,
                       service_name: Optional[str] = None,
                       category_id: Optional[int] = None) -> int:
        """
        Đếm tổng số tài liệu.
        """
        conditions = [Document.is_deleted == False]
        
        if file_type:
            conditions.append(Document.file_type == file_type)
            
        if service_name:
            conditions.append(Document.service_name == service_name)
            
        if category_id:
            conditions.append(Document.category_id == category_id)
            
        query = select(func.count(Document.id)).where(and_(*conditions))
        result = await self.session.execute(query)
        return result.scalar_one()


class DocumentCategoryRepository:
    """
    Repository để làm việc với DocumentCategory.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, category_data: Dict[str, Any]) -> DocumentCategory:
        """
        Tạo danh mục tài liệu mới.
        """
        category = DocumentCategory(**category_data)
        self.session.add(category)
        await self.session.commit()
        await self.session.refresh(category)
        return category

    async def get_by_id(self, category_id: int) -> Optional[DocumentCategory]:
        """
        Lấy danh mục theo ID.
        """
        query = select(DocumentCategory).where(DocumentCategory.id == category_id)
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_by_name(self, name: str) -> Optional[DocumentCategory]:
        """
        Lấy danh mục theo tên.
        """
        query = select(DocumentCategory).where(DocumentCategory.name == name)
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[DocumentCategory]:
        """
        Lấy tất cả danh mục.
        """
        query = select(DocumentCategory).order_by(DocumentCategory.name).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def update(self, category_id: int, category_data: Dict[str, Any]) -> Optional[DocumentCategory]:
        """
        Cập nhật thông tin danh mục.
        """
        category = await self.get_by_id(category_id)
        if not category:
            return None

        for key, value in category_data.items():
            if hasattr(category, key):
                setattr(category, key, value)

        await self.session.commit()
        await self.session.refresh(category)
        return category

    async def delete(self, category_id: int) -> bool:
        """
        Xóa danh mục.
        """
        category = await self.get_by_id(category_id)
        if not category:
            return False

        await self.session.delete(category)
        await self.session.commit()
        return True

    async def count(self) -> int:
        """
        Đếm số lượng danh mục.
        """
        query = select(func.count(DocumentCategory.id))
        result = await self.session.execute(query)
        return result.scalar_one() 