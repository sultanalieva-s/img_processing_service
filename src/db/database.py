from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.config import settings

# async: for `async def` endpoints
async_engine = create_async_engine(settings.database_url, pool_pre_ping=True)
AsyncSessionFactory = async_sessionmaker(async_engine, expire_on_commit=False)

# sync: for Celery tasks and `def` endpoints
sync_engine = create_engine(settings.database_url, pool_pre_ping=True)
SyncSessionFactory = sessionmaker(sync_engine, expire_on_commit=False)
