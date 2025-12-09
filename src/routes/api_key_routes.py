"""
API Key Management Routes
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.schemas.api_keys_schemas import APIKeyCreate, APIKeyResponse, APIKeyRollover
from src.services.api_keys_service import api_key_service
from src.utils.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/create", response_model=APIKeyResponse)
async def create_api_key(
    request: APIKeyCreate,
    current_user_data: tuple = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new API key
    Maximum 5 active keys per user
    """
    user, _ = current_user_data

    try:
        result = await api_key_service.create_api_key(
            db=db,
            user=user,
            name=request.name,
            permissions=request.permissions,
            expiry=request.expiry,
        )
        return result
    except ValueError as e:
        logger.warning(
            f"API key creation validation failed for user {user.id}: {str(e)}"
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(
            f"Failed to create API key for user {user.id}: {str(e)}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create API key. Please try again",
        )


@router.post("/rollover", response_model=APIKeyResponse)
async def rollover_api_key(
    request: APIKeyRollover,
    current_user_data: tuple = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Rollover an expired API key
    Creates new key with same permissions
    """
    user, _ = current_user_data

    try:
        result = await api_key_service.rollover_api_key(
            db=db,
            user=user,
            expired_key_id=request.expired_key_id,
            new_expiry=request.expiry,
        )
        return result
    except ValueError as e:
        logger.warning(
            f"API key rollover validation failed for user {user.id}: {str(e)}"
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except LookupError as e:
        logger.warning(f"API key not found for rollover: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
        )
    except Exception as e:
        logger.error(
            f"Failed to rollover API key for user {user.id}: {str(e)}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to rollover API key. Please try again",
        )
