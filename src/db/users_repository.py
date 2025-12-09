"""
Repository Pattern for Database Operations
Provides clean data access layer
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.base_repository import BaseRepository
from src.models.user_model import User


class UserRepository(BaseRepository[User]):
    """Repository for User operations"""

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_google_id(self, google_id: str) -> Optional[User]:
        """Get user by Google ID"""
        result = await self.db.execute(select(User).where(User.google_id == google_id))
        return result.scalar_one_or_none()


def get_user_repository(db: AsyncSession) -> UserRepository:
    """Get UserRepository instance"""
    return UserRepository(User, db)
