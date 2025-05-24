from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
import json

from domain.models import TokenData, User, Role, Permission, RefreshToken, UserProfile, Document, DocumentCategory
from infrastructure.repository import UserRepository, RoleRepository, RefreshTokenRepository, DocumentRepository, DocumentCategoryRepository
from application.dto import UserCreateDTO, UserUpdateDTO, RoleCreateDTO, RoleUpdateDTO
from application.security import verify_password, get_password_hash, create_access_token, create_refresh_token
from domain.exceptions import UserNotFoundException, RoleNotFoundException

logger = logging.getLogger(__name__)


class UserService:
    """Service cho các hoạt động liên quan đến User."""
    
    def __init__(self, repository: UserRepository, token_repository: RefreshTokenRepository):
        self.repository = repository
        self.token_repository = token_repository
    
    async def get_user(self, user_id: str) -> Optional[User]:
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
    
    async def create_user(self, user_data: UserCreateDTO) -> Optional[User]:
        """Tạo user mới."""
        existing_user = await self.repository.get_user_by_username(user_data.username)
        if existing_user:
            logger.warning(f"Tên đăng nhập đã tồn tại: {user_data.username}")
            return None

        existing_email = await self.repository.get_user_by_email(user_data.email)
        if existing_email:
            logger.warning(f"Email đã tồn tại: {user_data.email}")
            return None

        try:
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
        except Exception as e:
            logger.error(f"Lỗi khi tạo người dùng: {str(e)}")
            return None
    
    async def update_user(self, user_id: str, user_data: UserUpdateDTO) -> Optional[User]:
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
    
    async def delete_user(self, user_id: str) -> bool:
        """Xóa user."""
        user = await self.repository.get_user_by_id(user_id)
        if not user:
            return False

        return await self.repository.delete_user(user_id)
    
    async def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Xác thực user với username và password."""
        user = await self.repository.get_user_by_username(username)
        if not user:
            return None
        
        if not verify_password(password, user.hashed_password):
            return None
        
        await self.repository.update_user(user.id, {"last_login": datetime.utcnow()})

        access_token = create_access_token(
            user_or_id=user
        )
        
        token_str = create_refresh_token()
        expires_at = datetime.utcnow() + timedelta(days=30)
        
        refresh_token_obj = RefreshToken(
            token=token_str,
            user_id=user.id,
            expires_at=expires_at,
            created_at=datetime.utcnow()
        )
        
        refresh_token = await self.token_repository.create_refresh_token(refresh_token_obj)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token.token,
            "token_type": "bearer"
        }


class RoleService:
    """Service cho các hoạt động liên quan đến Role."""
    
    def __init__(self, repository: RoleRepository):
        self.repository = repository
    
    async def get_role(self, role_id: str) -> Optional[Role]:
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
    
    async def update_role(self, role_id: str, role_data: RoleUpdateDTO) -> Optional[Role]:
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
    
    async def delete_role(self, role_id: str) -> bool:
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
    
    async def assign_role_to_user(self, user_id: str, role_id: str) -> bool:
        """Gán role cho user."""
        user = await self.user_repository.get_user_by_id(user_id)
        if not user:
            raise UserNotFoundException(f"User with ID {user_id} not found")
        
        role = await self.role_repository.get_role_by_id(role_id)
        if not role:
            raise RoleNotFoundException(f"Role with ID {role_id} not found")
        
        await self.user_repository.assign_role_to_user(user, role)
        return True
    
    async def remove_role_from_user(self, user_id: str, role_id: str) -> bool:
        """Xóa role khỏi user."""
        user = await self.user_repository.get_user_by_id(user_id)
        if not user:
            raise UserNotFoundException(f"User with ID {user_id} not found")
        
        role = await self.role_repository.get_role_by_id(role_id)
        if not role:
            raise RoleNotFoundException(f"Role with ID {role_id} not found")
        
        await self.user_repository.remove_role_from_user(user, role)
        return True
        
    async def create_refresh_token(self, user_id: str) -> str:
        """Tạo refresh token mới cho user.
        
        Args:
            user_id: ID của người dùng
            
        Returns:
            Chuỗi refresh token
        """
        from application.security import create_refresh_token as create_token
        from datetime import datetime, timedelta
        
        token_str = create_token()
        expires_at = datetime.utcnow() + timedelta(days=30) 
        refresh_token = RefreshToken(
            token=token_str,
            user_id=user_id,
            expires_at=expires_at,
            created_at=datetime.utcnow()
        )
        
        await self.token_repository.create_refresh_token(refresh_token)
        
        return token_str
        
    async def verify_refresh_token(self, token_str: str):
        """Xác minh refresh token.
        
        Args:
            token_str: Chuỗi refresh token
            
        Returns:
            TokenData nếu refresh token hợp lệ
            
        Raises:
            ValueError: Nếu refresh token không hợp lệ hoặc đã hết hạn
        """
        refresh_token = await self.token_repository.get_refresh_token(token_str)
        if not refresh_token:
            raise ValueError("Invalid refresh token")
            
        if refresh_token.expires_at < datetime.utcnow():
            await self.token_repository.revoke_refresh_token(token_str)
            raise ValueError("Refresh token expired")
        
        return TokenData(
            user_id=refresh_token.user_id,
            username="", 
            roles=[],
            permissions=[], 
            exp=refresh_token.expires_at
        )
        
    async def revoke_refresh_token(self, token_str: str) -> bool:
        """Thu hồi refresh token.
        
        Args:
            token_str: Chuỗi refresh token
            
        Returns:
            True nếu thu hồi thành công, ngược lại False
        """
        return await self.token_repository.revoke_refresh_token(token_str)
        
    async def revoke_all_user_tokens(self, user_id: str) -> int:
        """Thu hồi tất cả refresh token của user.
        
        Args:
            user_id: ID của người dùng
            
        Returns:
            Số lượng refresh token đã thu hồi
        """
        return await self.token_repository.revoke_all_user_tokens(user_id)


class DocumentService:
    """
    Service xử lý nghiệp vụ liên quan đến Document.
    """

    def __init__(self, document_repository: DocumentRepository, category_repository: DocumentCategoryRepository):
        self.document_repository = document_repository
        self.category_repository = category_repository

    async def create_document(self, user_id: str, document_data: Dict[str, Any]) -> Optional[Document]:
        """
        Tạo tài liệu mới.
        """
        try:
            document_data["user_id"] = user_id
            
            if "metadata" in document_data and isinstance(document_data["metadata"], dict):
                document_data["metadata"] = json.dumps(document_data["metadata"])
                
            return await self.document_repository.create(document_data)
        except Exception as e:
            logger.error(f"Lỗi khi tạo tài liệu mới: {str(e)}")
            return None

    async def get_document_by_id(self, document_id: str, user_id: Optional[str] = None) -> Optional[Document]:
        """
        Lấy thông tin tài liệu theo ID.
        """
        try:
            document = await self.document_repository.get_by_id(document_id)
          
            if document and user_id is not None and document.user_id != user_id:
                return None
                
            return document
        except Exception as e:
            logger.error(f"Lỗi khi lấy thông tin tài liệu (ID: {document_id}): {str(e)}")
            return None

    async def get_document_by_storage_id(self, storage_id: str, user_id: Optional[str] = None) -> Optional[Document]:
        """
        Lấy thông tin tài liệu theo ID lưu trữ.
        """
        try:
            document = await self.document_repository.get_by_storage_id(storage_id)
            
            if document and user_id is not None and document.user_id != user_id:
                return None
                
            return document
        except Exception as e:
            logger.error(f"Lỗi khi lấy thông tin tài liệu (Storage ID: {storage_id}): {str(e)}")
            return None

    async def get_user_documents(self, user_id: str, skip: int = 0, limit: int = 100, 
                                file_type: Optional[str] = None,
                                service_name: Optional[str] = None,
                                category_id: Optional[int] = None) -> List[Document]:
        """
        Lấy danh sách tài liệu của người dùng.
        """
        try:
            return await self.document_repository.get_by_user_id(
                user_id, skip, limit, file_type, service_name, category_id
            )
        except Exception as e:
            logger.error(f"Lỗi khi lấy danh sách tài liệu của người dùng (ID: {user_id}): {str(e)}")
            return []

    async def get_all_documents(self, skip: int = 0, limit: int = 100, 
                               file_type: Optional[str] = None,
                               service_name: Optional[str] = None,
                               category_id: Optional[int] = None) -> List[Document]:
        """
        Lấy tất cả tài liệu.
        """
        try:
            return await self.document_repository.get_all(
                skip, limit, file_type, service_name, category_id
            )
        except Exception as e:
            logger.error(f"Lỗi khi lấy tất cả tài liệu: {str(e)}")
            return []

    async def update_document(self, document_id: str, document_data: Dict[str, Any], user_id: Optional[str] = None) -> Optional[Document]:
        """
        Cập nhật thông tin tài liệu.
        """
        try:
            # Kiểm tra quyền truy cập
            document = await self.document_repository.get_by_id(document_id)
            if not document:
                return None
                
            if user_id is not None and document.user_id != user_id:
                logger.warning(f"Người dùng không có quyền cập nhật tài liệu: User ID {user_id}, Document ID {document_id}")
                return None
            
            if "metadata" in document_data and isinstance(document_data["metadata"], dict):
                document_data["metadata"] = json.dumps(document_data["metadata"])
                
            return await self.document_repository.update(document_id, document_data)
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật thông tin tài liệu (ID: {document_id}): {str(e)}")
            return None

    async def delete_document(self, document_id: str, user_id: Optional[str] = None, hard_delete: bool = False) -> bool:
        """
        Xóa tài liệu.
        """
        try:
            document = await self.document_repository.get_by_id(document_id)
            if not document:
                return False
                
            if user_id is not None and document.user_id != user_id:
                logger.warning(f"Người dùng không có quyền xóa tài liệu: User ID {user_id}, Document ID {document_id}")
                return False
                
            return await self.document_repository.delete(document_id, hard_delete)
        except Exception as e:
            logger.error(f"Lỗi khi xóa tài liệu (ID: {document_id}): {str(e)}")
            return False

    async def count_user_documents(self, user_id: str, 
                                  file_type: Optional[str] = None,
                                  service_name: Optional[str] = None,
                                  category_id: Optional[int] = None) -> int:
        """
        Đếm số lượng tài liệu của người dùng.
        """
        try:
            return await self.document_repository.count_by_user_id(
                user_id, file_type, service_name, category_id
            )
        except Exception as e:
            logger.error(f"Lỗi khi đếm số lượng tài liệu của người dùng (ID: {user_id}): {str(e)}")
            return 0

    async def count_all_documents(self, 
                                 file_type: Optional[str] = None,
                                 service_name: Optional[str] = None,
                                 category_id: Optional[int] = None) -> int:
        """
        Đếm tổng số tài liệu.
        """
        try:
            return await self.document_repository.count_all(
                file_type, service_name, category_id
            )
        except Exception as e:
            logger.error(f"Lỗi khi đếm tổng số tài liệu: {str(e)}")
            return 0


class DocumentCategoryService:
    """
    Service xử lý nghiệp vụ liên quan đến DocumentCategory.
    """

    def __init__(self, category_repository: DocumentCategoryRepository):
        self.category_repository = category_repository

    async def create_category(self, category_data: Dict[str, Any]) -> Optional[DocumentCategory]:
        """
        Tạo danh mục tài liệu mới.
        """
        try:
            existing_category = await self.category_repository.get_by_name(category_data["name"])
            if existing_category:
                logger.warning(f"Tên danh mục đã tồn tại: {category_data['name']}")
                return None
                
            return await self.category_repository.create(category_data)
        except Exception as e:
            logger.error(f"Lỗi khi tạo danh mục tài liệu mới: {str(e)}")
            return None

    async def get_category_by_id(self, category_id: int) -> Optional[DocumentCategory]:
        """
        Lấy thông tin danh mục theo ID.
        """
        try:
            return await self.category_repository.get_by_id(category_id)
        except Exception as e:
            logger.error(f"Lỗi khi lấy thông tin danh mục (ID: {category_id}): {str(e)}")
            return None

    async def get_category_by_name(self, name: str) -> Optional[DocumentCategory]:
        """
        Lấy thông tin danh mục theo tên.
        """
        try:
            return await self.category_repository.get_by_name(name)
        except Exception as e:
            logger.error(f"Lỗi khi lấy thông tin danh mục (Tên: {name}): {str(e)}")
            return None

    async def get_all_categories(self, skip: int = 0, limit: int = 100) -> List[DocumentCategory]:
        """
        Lấy tất cả danh mục.
        """
        try:
            return await self.category_repository.get_all(skip, limit)
        except Exception as e:
            logger.error(f"Lỗi khi lấy tất cả danh mục: {str(e)}")
            return []

    async def update_category(self, category_id: int, category_data: Dict[str, Any]) -> Optional[DocumentCategory]:
        """
        Cập nhật thông tin danh mục.
        """
        try:
            if "name" in category_data:
                existing_category = await self.category_repository.get_by_name(category_data["name"])
                if existing_category and existing_category.id != category_id:
                    logger.warning(f"Tên danh mục đã tồn tại: {category_data['name']}")
                    return None
                    
            return await self.category_repository.update(category_id, category_data)
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật thông tin danh mục (ID: {category_id}): {str(e)}")
            return None

    async def delete_category(self, category_id: int) -> bool:
        """
        Xóa danh mục.
        """
        try:
            return await self.category_repository.delete(category_id)
        except Exception as e:
            logger.error(f"Lỗi khi xóa danh mục (ID: {category_id}): {str(e)}")
            return False

    async def count_categories(self) -> int:
        """
        Đếm số lượng danh mục.
        """
        try:
            return await self.category_repository.count()
        except Exception as e:
            logger.error(f"Lỗi khi đếm số lượng danh mục: {str(e)}")
            return 0 