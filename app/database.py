"""
database.py — Database connection and session management.
"""
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text
import os

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


async def check_db_health():
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"connected": True, "message": "OK"}
    except Exception as e:
        return {"connected": False, "message": str(e)}
