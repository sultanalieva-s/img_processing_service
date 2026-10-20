from collections.abc import AsyncIterator, Iterator

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from src.db.database import AsyncSessionFactory, SyncSessionFactory


async def get_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionFactory() as session:
        yield session


def get_sync_session() -> Iterator[Session]:
    with SyncSessionFactory() as session:
        yield session