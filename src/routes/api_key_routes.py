"""
API Key Management Routes
"""

import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.schemas.api_keys_schemas import (
    APIKeyCreate,
    APIKeyResponse,
    APIKeyRollover,
)
from src.services.api_keys_service import api_key_service
from src.utils.auth import get_current_user
from src.utils.responses import error_response, success_response

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/create", response_model=APIKeyResponse)
def create_api_key(
    request: APIKeyCreate,
    current_user_data: tuple = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new API key
    Maximum 5 active keys per user

    **Permissions available:**
    - `read`: View balance and transactions
    - `deposit`: Initiate deposits
    - `transfer`: Transfer funds to other wallets

    **Expiry formats:**
    - `1H` - 1 hour
    - `1D` - 1 day
    - `1M` - 1 month
    - `1Y` - 1 year
    """
    user, _ = current_user_data

    try:
        result = api_key_service.create_api_key(
            db=db,
            user=user,
            name=request.name,
            permissions=request.permissions,
            expiry=request.expiry,
        )
        logger.info(f"API key created for user {user.id}: {request.name}")
        return result
    except ValueError as e:
        logger.warning(
            f"API key creation validation failed for user {user.id}: {str(e)}"
        )
        return error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Invalid API key request",
            error="VALIDATION_ERROR",
            errors={"details": [str(e)]},
        )
    except Exception as e:
        logger.error(
            f"Failed to create API key for user {user.id}: {str(e)}", exc_info=True
        )
        return error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to create API key. Please try again",
            error="SERVER_ERROR",
        )


@router.get("/list")
def list_api_keys(
    current_user_data: tuple = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get all API keys for the current user
    Returns key metadata (NOT the actual keys)
    """
    user, _ = current_user_data

    try:
        api_keys = api_key_service.list_api_keys(db=db, user=user)
        return success_response(
            status_code=status.HTTP_200_OK,
            message="API keys retrieved successfully",
            data={"keys": api_keys, "count": len(api_keys)},
        )
    except Exception as e:
        logger.error(
            f"Failed to list API keys for user {user.id}: {str(e)}", exc_info=True
        )
        return error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to retrieve API keys",
            error="SERVER_ERROR",
        )


@router.post("/revoke/{key_id}")
def revoke_api_key(
    key_id: str,
    current_user_data: tuple = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Revoke an API key
    Once revoked, the key cannot be used anymore
    """
    user, _ = current_user_data

    try:
        api_key_service.revoke_api_key(db=db, user=user, key_id=key_id)
        logger.info(f"API key revoked for user {user.id}: {key_id}")
        return success_response(
            status_code=status.HTTP_200_OK,
            message="API key revoked successfully",
            data={"key_id": key_id},
        )
    except LookupError as e:
        logger.warning(f"API key not found for revocation: {str(e)}")
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="API key not found",
            error="NOT_FOUND",
        )
    except ValueError as e:
        logger.warning(f"API key revocation validation failed: {str(e)}")
        return error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Invalid revocation request",
            error="VALIDATION_ERROR",
            errors={"details": [str(e)]},
        )
    except Exception as e:
        logger.error(
            f"Failed to revoke API key for user {user.id}: {str(e)}", exc_info=True
        )
        return error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to revoke API key. Please try again",
            error="SERVER_ERROR",
        )


@router.post("/rollover", response_model=APIKeyResponse)
def rollover_api_key(
    request: APIKeyRollover,
    current_user_data: tuple = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Rollover an expired API key
    Creates new key with same permissions and revokes the old one
    """
    user, _ = current_user_data

    try:
        result = api_key_service.rollover_api_key(
            db=db,
            user=user,
            expired_key_id=request.expired_key_id,
            new_expiry=request.expiry,
        )
        logger.info(f"API key rolled over for user {user.id}")
        return result
    except ValueError as e:
        logger.warning(
            f"API key rollover validation failed for user {user.id}: {str(e)}"
        )
        return error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Invalid rollover request",
            error="VALIDATION_ERROR",
            errors={"details": [str(e)]},
        )
    except LookupError as e:
        logger.warning(f"API key not found for rollover: {str(e)}")
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="API key not found",
            error="NOT_FOUND",
        )
    except Exception as e:
        logger.error(
            f"Failed to rollover API key for user {user.id}: {str(e)}", exc_info=True
        )
        return error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to rollover API key. Please try again",
            error="SERVER_ERROR",
        )
