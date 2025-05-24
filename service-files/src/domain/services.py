from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from infrastructure.database import get_all_documents_by_user, get_documents_by_user, get_document_by_id
from domain.models import DBDocument, ArchiveInfo

class DocumentAccessService:
    """
    Service để truy cập tài liệu từ tất cả các service
    """
    
    @staticmethod
    async def get_all_user_documents(db_session: AsyncSession, user_id: str) -> List[DBDocument]:
        """
        Lấy tất cả tài liệu của người dùng từ tất cả các service
        
        Args:
            db_session: Session database
            user_id: ID của người dùng
            
        Returns:
            Danh sách tất cả tài liệu
        """
        return await get_all_documents_by_user(db_session, user_id)
    
    @staticmethod
    async def get_documents_by_category(db_session: AsyncSession, user_id: str, category: str) -> List[DBDocument]:
        """
        Lấy tài liệu của người dùng theo loại
        
        Args:
            db_session: Session database
            user_id: ID của người dùng
            category: Loại tài liệu (pdf, excel, word, files)
            
        Returns:
            Danh sách tài liệu theo loại
        """
        return await get_documents_by_user(db_session, user_id, category)
    
    @staticmethod
    async def get_document(db_session: AsyncSession, document_id: str) -> Optional[DBDocument]:
        """
        Lấy thông tin tài liệu theo ID
        
        Args:
            db_session: Session database
            document_id: ID của tài liệu
            
        Returns:
            Thông tin tài liệu hoặc None nếu không tìm thấy
        """
        return await get_document_by_id(db_session, document_id)
    
    @staticmethod
    async def prepare_documents_for_archive(
        db_session: AsyncSession, user_id: str, document_ids: List[int] = None, categories: List[str] = None
    ) -> List[DBDocument]:
        """
        Chuẩn bị danh sách tài liệu để nén
        
        Args:
            db_session: Session database
            user_id: ID của người dùng
            document_ids: Danh sách ID tài liệu cần nén, nếu None thì lấy theo categories
            categories: Danh sách loại tài liệu cần nén, nếu None thì lấy tất cả
            
        Returns:
            Danh sách tài liệu để nén
        """
        if document_ids:
            documents = []
            for doc_id in document_ids:
                doc = await get_document_by_id(db_session, doc_id)
                if doc and doc.user_id == user_id:
                    documents.append(doc)
            return documents
            
        if categories:
            all_documents = []
            for category in categories:
                docs = await get_documents_by_user(db_session, user_id, category)
                all_documents.extend(docs)
            return all_documents
            
        # Lấy tất cả tài liệu nếu không chỉ định
        return await get_all_documents_by_user(db_session, user_id) 