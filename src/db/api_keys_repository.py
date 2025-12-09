"""
Repository Pattern for Database Operations
Provides clean data access layer
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.base_repository import BaseRepository
from src.models.api_key_model import APIKey


class APIKeyRepository(BaseRepository[APIKey]):
    """Repository for API Key operations"""

    async def get_by_key_hash(self, key_hash: str) -> Optional[APIKey]:
        """Get API key by hash"""
        result = await self.db.execute(
            select(APIKey).where(APIKey.key_hash == key_hash)
        )
        return result.scalar_one_or_none()

    async def get_by_id_and_user(self, key_id: str, user_id: str) -> Optional[APIKey]:
        """Get API key by ID and user"""
        result = await self.db.execute(
            select(APIKey).where(and_(APIKey.id == key_id, APIKey.user_id == user_id))
        )
        return result.scalar_one_or_none()

    async def count_active_keys(self, user_id: str) -> int:
        """Count active API keys for user"""
        result = await self.db.execute(
            select(func.count(APIKey.id)).where(
                and_(
                    APIKey.user_id == user_id,
                    APIKey.is_active,
                    APIKey.is_revoked,
                    APIKey.expires_at > datetime.utcnow(),
                )
            )
        )
        return result.scalar()

    async def get_user_keys(
        self, user_id: str, include_expired: bool = False
    ) -> List[APIKey]:
        """Get all API keys for user"""
        query = select(APIKey).where(APIKey.user_id == user_id)

        if not include_expired:
            query = query.where(
                and_(
                    APIKey.is_active,
                    APIKey.is_revoked,
                    APIKey.expires_at > datetime.utcnow(),
                )
            )

        result = await self.db.execute(query.order_by(APIKey.created_at.desc()))
        return result.scalars().all()


def get_api_key_repository(db: AsyncSession) -> APIKeyRepository:
    """Get APIKeyRepository instance"""
    return APIKeyRepository(APIKey, db)
