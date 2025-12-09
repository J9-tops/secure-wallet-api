"""
Authentication Dependencies for FastAPI
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.models.api_key_model import APIKey
from src.models.user_model import User
from src.utils.security import decode_jwt_token, hash_api_key

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)


async def get_current_user_from_jwt(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
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

    return user


async def get_current_user_from_api_key(
    x_api_key: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)
) -> tuple[Optional[User], Optional[APIKey]]:
    """Get current user from API key"""
    if not x_api_key:
        return None, None

    key_hash = hash_api_key(x_api_key)

    result = db.execute(select(APIKey).where(APIKey.key_hash == key_hash))
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key"
        )

    if api_key.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="API key expired"
        )

    if api_key.is_revoked or not api_key.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key revoked or inactive",
        )

    result = await db.execute(select(User).where(User.id == api_key.user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    return user, api_key


async def get_current_user(
    jwt_user: Optional[User] = Depends(get_current_user_from_jwt),
    api_key_data: tuple = Depends(get_current_user_from_api_key),
) -> tuple[User, Optional[APIKey]]:
    """
    Get current user from either JWT or API key
    Returns: (User, Optional[APIKey])
    """
    api_user, api_key = api_key_data

    if jwt_user:
        logger.debug(f"Authenticated user {jwt_user.id} via JWT")
        return jwt_user, None

    if api_user:
        logger.debug(f"Authenticated user {api_user.id} via API key")
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
    """

    async def check_permission(current_user_data: tuple = Depends(get_current_user)):
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
                detail=f"API key does not have '{permission}' permission",
            )

        logger.debug(f"API key user {user.id} has '{permission}' permission")
        return user

    return check_permission
