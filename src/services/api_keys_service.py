"""
API Key Service - Business Logic for API Key Management
FIXED: Corrected logical errors in active key counting
"""

from datetime import datetime, timezone
from typing import List

from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.models.api_key_model import APIKey
from src.models.user_model import User
from src.schemas.api_keys_schemas import APIKeyResponse
from src.utils.security import generate_api_key, hash_api_key, parse_expiry


class APIKeyService:
    """Service for API key operations"""

    MAX_ACTIVE_KEYS = 5
    MAX_RETRY_ATTEMPTS = 5

    def create_api_key(
        self,
        db: Session,
        user: User,
        name: str,
        permissions: List[str],
        expiry: str,
    ) -> APIKeyResponse:
        expires_at = parse_expiry(expiry)

        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        active_keys = (
            db.execute(
                select(APIKey)
                .where(
                    and_(
                        APIKey.user_id == user.id,
                        APIKey.is_active,
                        APIKey.is_revoked == False,  # noqa: E712
                        APIKey.expires_at > datetime.now(timezone.utc),
                    )
                )
                .with_for_update()
            )
            .scalars()
            .all()
        )

        active_count = len(active_keys)

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
                db.flush()
                break
            except IntegrityError:
                db.rollback()
                if attempt == self.MAX_RETRY_ATTEMPTS - 1:
                    raise ValueError(
                        "Failed to generate unique API key after multiple attempts"
                    )

        db.commit()
        return APIKeyResponse(api_key=api_key, expires_at=expires_at)

    def rollover_api_key(
        self, db: Session, user: User, expired_key_id: str, new_expiry: str
    ) -> APIKeyResponse:
        new_expires_at = parse_expiry(new_expiry)
        if new_expires_at.tzinfo is None:
            new_expires_at = new_expires_at.replace(tzinfo=timezone.utc)

        result = db.execute(
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

        result = db.execute(
            select(func.count(APIKey.id))
            .where(
                and_(
                    APIKey.user_id == user.id,
                    APIKey.is_active,
                    APIKey.is_revoked == False,  # noqa: E712
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
                db.flush()
                break
            except IntegrityError:
                db.rollback()
                if attempt == self.MAX_RETRY_ATTEMPTS - 1:
                    raise ValueError(
                        "Failed to generate unique API key after multiple attempts"
                    )

        expired_key.is_revoked = True
        db.commit()

        return APIKeyResponse(api_key=new_api_key, expires_at=new_expires_at)

    def revoke_api_key(self, db: Session, user: User, key_id: str) -> bool:
        result = db.execute(
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
        db.commit()

        return True

    def _count_active_keys(self, db: Session, user_id: str) -> int:
        result = db.execute(
            select(func.count(APIKey.id)).where(
                and_(
                    APIKey.user_id == user_id,
                    APIKey.is_active,
                    APIKey.is_revoked == False,  # noqa: E712
                    APIKey.expires_at > datetime.now(timezone.utc),
                )
            )
        )
        return result.scalar()

    def _get_api_key(self, db: Session, key_id: str, user_id: str) -> APIKey:
        result = db.execute(
            select(APIKey).where(and_(APIKey.id == key_id, APIKey.user_id == user_id))
        )
        return result.scalar_one_or_none()

    def list_api_keys(self, db: Session, user: User):
        result = db.execute(
            select(APIKey)
            .where(APIKey.user_id == user.id)
            .order_by(APIKey.created_at.desc())
        )
        api_keys = result.scalars().all()

        return api_keys


api_key_service = APIKeyService()
