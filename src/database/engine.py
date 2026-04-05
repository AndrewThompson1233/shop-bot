from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from src.config import settings
from src.database.models import Base

engine = create_async_engine(settings.db_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)