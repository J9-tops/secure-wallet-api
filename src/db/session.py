"""
Database Session Management and Configuration with PostgreSQL
"""

import os
from typing import AsyncGenerator

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:password@localhost:5432/wallet_service",
)

DB_NAME = DATABASE_URL.rsplit("/", 1)[-1]
DB_ROOT_URL = DATABASE_URL.rsplit("/", 1)[0] + "/postgres"

engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    future=True,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_database_if_not_exists():
    root_engine = create_async_engine(DB_ROOT_URL, isolation_level="AUTOCOMMIT")

    async with root_engine.begin() as conn:
        result = await conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": DB_NAME},
        )
        exists = result.scalar() is not None

        if not exists:
            print(f"Database '{DB_NAME}' does not exist. Creating...")
            await conn.execute(text(f'CREATE DATABASE "{DB_NAME}"'))
        else:
            print(f"Database '{DB_NAME}' already exists.")

    await root_engine.dispose()


async def init_db():
    """Initialize database and create tables"""
    await create_database_if_not_exists()

    async with engine.begin() as conn:
        from src.models.api_key_model import APIKey  # noqa: F401
        from src.models.transaction_model import Transaction  # noqa: F401
        from src.models.user_model import User  # noqa: F401
        from src.models.wallet_model import Wallet  # noqa: F401

        await conn.run_sync(Base.metadata.create_all)

    print("Database tables created successfully")


async def close_db():
    """Close database connection"""
    await engine.dispose()
