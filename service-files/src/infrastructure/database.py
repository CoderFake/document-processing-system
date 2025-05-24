from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, update, delete
from sqlalchemy.future import select
from core.config import settings
from domain.models import DBDocument
from typing import List, Optional

engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    echo=settings.DEBUG,
    future=True
)

async_session_factory = sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

async def get_db_session() -> AsyncSession:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def init_db():
    pass

async def get_documents_by_user(session: AsyncSession, user_id: str, category: Optional[str] = "files") -> List[DBDocument]:
    """
    Lấy danh sách tài liệu theo user_id và loại tài liệu.
    
    Args:
        session: Session database
        user_id: ID của người dùng
        category: Loại tài liệu (pdf, excel, word, files), nếu None thì lấy tất cả
        
    Returns:
        Danh sách tài liệu
    """
    if category:
        query = select(DBDocument).where(DBDocument.user_id == user_id, DBDocument.document_category == category)
    else:
        query = select(DBDocument).where(DBDocument.user_id == user_id)
    
    result = await session.execute(query)
    return result.scalars().all()

async def get_all_documents_by_user(session: AsyncSession, user_id: str) -> List[DBDocument]:
    """
    Lấy tất cả tài liệu của người dùng bất kể loại tài liệu.
    
    Args:
        session: Session database
        user_id: ID của người dùng
        
    Returns:
        Danh sách tất cả tài liệu
    """
    return await get_documents_by_user(session, user_id, category=None)

async def get_document_by_id(session: AsyncSession, document_id: str) -> Optional[DBDocument]:
    """
    Lấy tài liệu theo ID.
    
    Args:
        session: Session database
        document_id: ID của tài liệu
        
    Returns:
        Tài liệu hoặc None nếu không tìm thấy
    """
    query = select(DBDocument).where(DBDocument.id == document_id)
    result = await session.execute(query)
    return result.scalars().first()

async def save_document(session: AsyncSession, document: DBDocument) -> DBDocument:
    """
    Lưu tài liệu vào database.
    
    Args:
        session: Session database
        document: Đối tượng tài liệu cần lưu
        
    Returns:
        Tài liệu đã lưu
    """
    session.add(document)
    await session.flush()
    await session.refresh(document)
    return document 