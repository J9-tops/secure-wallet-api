"""
Authentication Dependencies for FastAPI
Supports both JWT tokens and API keys with Swagger UI integration
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Tuple

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.models.api_key_model import APIKey
from src.models.user_model import User
from src.utils.security import decode_jwt_token, hash_api_key

logger = logging.getLogger(__name__)


bearer_scheme = HTTPBearer(
    auto_error=False,
    scheme_name="JWT Bearer Token",
    description="Enter your JWT token from Google OAuth",
)

api_key_scheme = APIKeyHeader(
    name="x-api-key",
    auto_error=False,
    scheme_name="API Key",
    description="Enter your API key (format: sk_live_...)",
)


def get_current_user_from_jwt(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Get current user from JWT token"""
    if not credentials:
        return None

    token = credentials.credentials
    payload = decode_jwt_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        )

    user_id = payload.get("user_id")
    result = db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    logger.debug(f"Authenticated user {user.id} via JWT")
    return user


def get_current_user_from_api_key(
    api_key_value: Optional[str] = Depends(api_key_scheme),
    db: Session = Depends(get_db),
) -> Tuple[Optional[User], Optional[APIKey]]:
    """Get current user from API key"""
    if not api_key_value:
        return None, None

    key_hash = hash_api_key(api_key_value)

    result = db.execute(
        select(APIKey).where(
            and_(
                APIKey.key_hash == key_hash,
                APIKey.is_active,
                APIKey.is_revoked == False,  # noqa: E712
            )
        )
    )
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key"
        )

    now = datetime.now(timezone.utc)
    expires_at = api_key.expires_at

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at <= now:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="API key expired"
        )

    result = db.execute(select(User).where(User.id == api_key.user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Update last_used_at timestamp
    api_key.last_used_at = datetime.now(timezone.utc)
    db.commit()

    logger.debug(f"Authenticated user {user.id} via API key")
    return user, api_key


def get_current_user(
    jwt_user: Optional[User] = Depends(get_current_user_from_jwt),
    api_key_data: Tuple[Optional[User], Optional[APIKey]] = Depends(
        get_current_user_from_api_key
    ),
) -> Tuple[User, Optional[APIKey]]:
    """
    Get current user from either JWT or API key
    Returns: (User, Optional[APIKey])

    Supports both authentication methods:
    - JWT Bearer Token (via Authorization header)
    - API Key (via X-API-Key header)
    """
    api_user, api_key = api_key_data

    if jwt_user:
        return jwt_user, None

    if api_user:
        return api_user, api_key

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Please provide a valid JWT token or API key.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_permission(permission: str):
    """
    Dependency to check if user has required permission

    JWT users have all permissions
    API key users must have the specific permission

    Available permissions:
    - read: View balance and transactions
    - deposit: Initiate deposits
    - transfer: Transfer funds
    """

    def check_permission(
        current_user_data: Tuple[User, Optional[APIKey]] = Depends(get_current_user),
    ) -> User:
        user, api_key = current_user_data

        if api_key is None:
            logger.debug(f"JWT user {user.id} has all permissions")
            return user

        if permission not in api_key.permissions:
            logger.warning(
                f"API key {api_key.id} missing permission '{permission}' "
                f"(has: {api_key.permissions})"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"API key does not have '{permission}' permission. "
                f"Required: {permission}, Have: {api_key.permissions}",
            )

        logger.debug(f"API key user {user.id} has '{permission}' permission")
        return user

    return check_permission
