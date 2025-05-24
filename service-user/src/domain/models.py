from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
import uuid
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Table, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

user_roles = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', UUID, ForeignKey('users.id')),
    Column('role_id', UUID, ForeignKey('roles.id'))
)

role_permissions = Table(
    'role_permissions',
    Base.metadata,
    Column('role_id', UUID, ForeignKey('roles.id')),
    Column('permission_id', UUID, ForeignKey('permissions.id'))
)


class User(Base):
    """Người dùng trong hệ thống."""
    __tablename__ = 'users'

    id = Column(UUID, primary_key=True, index=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(100), nullable=False)
    full_name = Column(String(100))
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    profile_image = Column(String(255), nullable=True)
    user_metadata = Column(Text, nullable=True)

    roles = relationship("Role", secondary=user_roles, back_populates="users")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="user")


class DocumentCategory(Base):
    """Danh mục tài liệu trong hệ thống."""
    __tablename__ = 'document_categories'

    id = Column(UUID, primary_key=True, index=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    documents = relationship("Document", back_populates="category")


class Document(Base):
    """Tài liệu trong hệ thống."""
    __tablename__ = 'documents'

    id = Column(UUID, primary_key=True, index=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    file_path = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False, default=0)
    file_type = Column(String(50), nullable=False)
    original_filename = Column(String(255), nullable=False)
    storage_id = Column(UUID, nullable=False, default=uuid.uuid4)
    service_name = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_deleted = Column(Boolean, default=False)
    doc_metadata = Column(Text, nullable=True)
    
    user_id = Column(UUID, ForeignKey('users.id'), nullable=False)
    category_id = Column(UUID, ForeignKey('document_categories.id'), nullable=True)
    
    user = relationship("User", back_populates="documents")
    category = relationship("DocumentCategory", back_populates="documents")


class Role(Base):
    """Vai trò người dùng trong hệ thống."""
    __tablename__ = 'roles'

    id = Column(UUID, primary_key=True, index=True, default=uuid.uuid4)
    name = Column(String(50), unique=True, index=True, nullable=False)
    description = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    users = relationship("User", secondary=user_roles, back_populates="roles")
    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles")


class Permission(Base):
    """Quyền trong hệ thống."""
    __tablename__ = 'permissions'

    id = Column(UUID, primary_key=True, index=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(String(255))
    resource = Column(String(50), nullable=False) 
    action = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")


class RefreshToken(Base):
    """Refresh token cho JWT."""
    __tablename__ = 'refresh_tokens'

    id = Column(UUID, primary_key=True, index=True, default=uuid.uuid4)
    token = Column(String(255), unique=True, index=True, nullable=False)
    user_id = Column(UUID, ForeignKey('users.id'))
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    revoked = Column(Boolean, default=False)
    revoked_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="refresh_tokens")


class UserProfile:
    """Thông tin hồ sơ người dùng."""
    id: str
    username: str
    email: str
    full_name: Optional[str]
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login: Optional[datetime]
    profile_image: Optional[str]
    roles: List[str]
    permissions: List[Dict[str, str]]

    def __init__(
        self,
        id: str,
        username: str,
        email: str,
        full_name: Optional[str] = None,
        is_active: bool = True,
        is_verified: bool = False,
        created_at: Optional[datetime] = None,
        last_login: Optional[datetime] = None,
        profile_image: Optional[str] = None,
        roles: Optional[List[str]] = None,
        permissions: Optional[List[Dict[str, str]]] = None
    ):
        self.id = id
        self.username = username
        self.email = email
        self.full_name = full_name
        self.is_active = is_active
        self.is_verified = is_verified
        self.created_at = created_at or datetime.utcnow()
        self.last_login = last_login
        self.profile_image = profile_image
        self.roles = roles or []
        self.permissions = permissions or []


class TokenData:
    """Dữ liệu từ token JWT."""
    user_id: str
    username: str
    roles: List[str]
    permissions: List[Dict[str, str]]
    exp: datetime

    def __init__(
        self,
        user_id: str,
        username: str,
        roles: List[str],
        permissions: List[Dict[str, str]],
        exp: datetime
    ):
        self.user_id = user_id
        self.username = username
        self.roles = roles
        self.permissions = permissions
        self.exp = exp 