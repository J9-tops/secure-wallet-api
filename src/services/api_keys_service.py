"""
API Key Service - Business Logic for API Key Management
"""

from datetime import datetime, timezone
from typing import List

from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.api_key_model import APIKey
from src.models.user_model import User
from src.schemas.api_keys_schemas import APIKeyResponse
from src.utils.security import generate_api_key, hash_api_key, parse_expiry


class APIKeyService:
    """Service for API key operations"""

    MAX_ACTIVE_KEYS = 5
    MAX_RETRY_ATTEMPTS = 5

    async def create_api_key(
        self,
        db: AsyncSession,
        user: User,
        name: str,
        permissions: List[str],
        expiry: str,
    ) -> APIKeyResponse:
        """
        Create a new API key for user

        Args:
            db: Database session
            user: User object
            name: Key name
            permissions: List of permissions
            expiry: Expiry string (1H, 1D, 1M, 1Y)

        Returns:
            APIKeyResponse with key and expiry

        Raises:
            ValueError: If validation fails
        """
        expires_at = parse_expiry(expiry)

        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        async with db.begin():
            result = await db.execute(
                select(func.count(APIKey.id))
                .where(
                    and_(
                        APIKey.user_id == user.id,
                        APIKey.is_active,
                        APIKey.is_revoked,
                        APIKey.expires_at > datetime.now(timezone.utc),
                    )
                )
                .with_for_update()
            )
            active_count = result.scalar()
            if active_count >= self.MAX_ACTIVE_KEYS:
                raise ValueError(
                    f"Maximum of {self.MAX_ACTIVE_KEYS} active API keys allowed per user"
                )

            for attempt in range(self.MAX_RETRY_ATTEMPTS):
                api_key = generate_api_key()
                key_hash = hash_api_key(api_key)
                key_prefix = api_key[:20]
                api_key_record = APIKey(
                    user_id=user.id,
                    name=name,
                    key_hash=key_hash,
                    key_prefix=key_prefix,
                    permissions=permissions,
                    expires_at=expires_at,
                )
                db.add(api_key_record)
                try:
                    await db.flush()
                    break
                except IntegrityError:
                    await db.rollback()
                    if attempt == self.MAX_RETRY_ATTEMPTS - 1:
                        raise ValueError(
                            "Failed to generate unique API key after multiple attempts"
                        )

        return APIKeyResponse(api_key=api_key, expires_at=expires_at)

    async def rollover_api_key(
        self, db: AsyncSession, user: User, expired_key_id: str, new_expiry: str
    ) -> APIKeyResponse:
        """
        Rollover an expired API key with same permissions

        Args:
            db: Database session
            user: User object
            expired_key_id: ID of expired key
            new_expiry: New expiry string (1H, 1D, 1M, 1Y)

        Returns:
            APIKeyResponse with new key and expiry

        Raises:
            LookupError: If key not found
            ValueError: If validation fails
        """
        new_expires_at = parse_expiry(new_expiry)
        if new_expires_at.tzinfo is None:
            new_expires_at = new_expires_at.replace(tzinfo=timezone.utc)

        async with db.begin():
            result = await db.execute(
                select(APIKey)
                .where(and_(APIKey.id == expired_key_id, APIKey.user_id == user.id))
                .with_for_update()
            )
            expired_key = result.scalar_one_or_none()

            if not expired_key:
                raise LookupError("API key not found")

            if expired_key.expires_at > datetime.now(timezone.utc):
                raise ValueError("API key is not expired yet")

            if expired_key.is_revoked:
                raise ValueError("API key has already been revoked")

            result = await db.execute(
                select(func.count(APIKey.id))
                .where(
                    and_(
                        APIKey.user_id == user.id,
                        APIKey.is_active,
                        APIKey.is_revoked,
                        APIKey.expires_at > datetime.now(timezone.utc),
                    )
                )
                .with_for_update()
            )
            active_count = result.scalar()

            if active_count >= self.MAX_ACTIVE_KEYS:
                raise ValueError(
                    f"Maximum of {self.MAX_ACTIVE_KEYS} active API keys allowed per user"
                )

            for attempt in range(self.MAX_RETRY_ATTEMPTS):
                new_api_key = generate_api_key()
                new_key_hash = hash_api_key(new_api_key)
                new_key_prefix = new_api_key[:20]

                new_api_key_record = APIKey(
                    user_id=user.id,
                    name=expired_key.name,
                    key_hash=new_key_hash,
                    key_prefix=new_key_prefix,
                    permissions=expired_key.permissions,
                    expires_at=new_expires_at,
                )

                db.add(new_api_key_record)

                try:
                    await db.flush()
                    break
                except IntegrityError:
                    await db.rollback()
                    if attempt == self.MAX_RETRY_ATTEMPTS - 1:
                        raise ValueError(
                            "Failed to generate unique API key after multiple attempts"
                        )

            expired_key.is_revoked = True

        return APIKeyResponse(api_key=new_api_key, expires_at=new_expires_at)

    async def revoke_api_key(self, db: AsyncSession, user: User, key_id: str) -> bool:
        """
        Revoke an API key

        Args:
            db: Database session
            user: User object
            key_id: ID of key to revoke

        Returns:
            True if revoked successfully

        Raises:
            LookupError: If key not found
            ValueError: If key already revoked
        """
        async with db.begin():
            result = await db.execute(
                select(APIKey)
                .where(and_(APIKey.id == key_id, APIKey.user_id == user.id))
                .with_for_update()
            )
            api_key = result.scalar_one_or_none()

            if not api_key:
                raise LookupError("API key not found")

            if api_key.is_revoked:
                raise ValueError("API key is already revoked")

            api_key.is_revoked = True

        return True

    async def _count_active_keys(self, db: AsyncSession, user_id: str) -> int:
        """
        Count active API keys for user

        Args:
            db: Database session
            user_id: User ID

        Returns:
            Count of active keys
        """
        result = await db.execute(
            select(func.count(APIKey.id)).where(
                and_(
                    APIKey.user_id == user_id,
                    APIKey.is_active,
                    APIKey.is_revoked,
                    APIKey.expires_at > datetime.now(timezone.utc),
                )
            )
        )
        return result.scalar()

    async def _get_api_key(self, db: AsyncSession, key_id: str, user_id: str) -> APIKey:
        """
        Get API key by ID and user

        Args:
            db: Database session
            key_id: API key ID
            user_id: User ID

        Returns:
            APIKey object or None
        """
        result = await db.execute(
            select(APIKey).where(and_(APIKey.id == key_id, APIKey.user_id == user_id))
        )
        return result.scalar_one_or_none()


api_key_service = APIKeyService()
