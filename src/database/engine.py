from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.config import settings
from src.database.models import B


E = create_async_engine(settings.db_url, pool_pre_ping=True)
ASL = async_sessionmaker(E, expire_on_commit=False)


async def init_db() -> None:
    async with E.begin() as conn:
        await conn.run_sync(B.metadata.create_all)


async def close_db() -> None:
    await E.dispose()
