import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from core.config import settings

logger = logging.getLogger(__name__)

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

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency để lấy session database.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database error: {str(e)}")
            raise
        finally:
            await session.close()

async def init_db():
    """
    Khởi tạo database nếu cần.
    """
    from domain.models import Base
    import sqlalchemy as sa
    from sqlalchemy.ext.asyncio import AsyncConnection
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
        try:
            await conn.execute(sa.text("ALTER TABLE users ADD COLUMN IF NOT EXISTS user_metadata TEXT"))
            print("Database được khởi tạo thành công hoặc đã sẵn sàng.")
        except Exception as e:
            print(f"Lỗi khi thêm cột user_metadata: {str(e)}")
            try:
                await conn.execute(sa.text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name='users' AND column_name='user_metadata'"
                ))
                result = await conn.fetchall()
                if not result:
                    await conn.execute(sa.text("ALTER TABLE users ADD COLUMN user_metadata TEXT"))
                    print("Đã thêm cột user_metadata.")
            except Exception as e2:
                print(f"Không thể thêm cột user_metadata: {str(e2)}")
                print("Vui lòng thêm cột thủ công nếu cần thiết.") 