"""
Database Session Management and Configuration with PostgreSQL (Synchronous)
"""

import os
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/wallet_service",
)
DEBUG = os.getenv("DEBUG", "True").lower() == "true"


if DATABASE_URL.startswith("postgresql://"):
    # Already correct format for psycopg2
    pass

DB_NAME = DATABASE_URL.rsplit("/", 1)[-1]
DB_ROOT_URL = DATABASE_URL.rsplit("/", 1)[0] + "/postgres"

engine = create_engine(
    DATABASE_URL,
    echo=DEBUG,
    future=True,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Dependency to get database session"""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def create_database_if_not_exists():
    root_engine = create_engine(DB_ROOT_URL, isolation_level="AUTOCOMMIT")

    with root_engine.begin() as conn:
        result = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": DB_NAME},
        )
        exists = result.scalar() is not None

        if not exists:
            print(f"Database '{DB_NAME}' does not exist. Creating...")
            conn.execute(text(f'CREATE DATABASE "{DB_NAME}"'))
        else:
            print(f"Database '{DB_NAME}' already exists.")

    root_engine.dispose()


def init_db():
    """Initialize database and create tables"""
    create_database_if_not_exists()

    from src.models.api_key_model import APIKey  # noqa: F401
    from src.models.transaction_model import Transaction  # noqa: F401
    from src.models.user_model import User  # noqa: F401
    from src.models.wallet_model import Wallet  # noqa: F401

    Base.metadata.create_all(bind=engine)

    print("Database tables created successfully")


def close_db():
    """Close database connection"""
    engine.dispose()
