"""
Authentication Routes - Google OAuth
Returns JSON responses with redirect URLs instead of performing redirects
"""

import logging

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.routes.docs.auth_routes_docs import (
    google_callback_custom_errors,
    google_callback_custom_success,
    google_callback_responses,
    google_login_custom_errors,
    google_login_custom_success,
    google_login_responses,
    test_token_custom_errors,
    test_token_custom_success,
    test_token_responses,
)
from src.schemas.auth_schemas import TokenResponse
from src.services.auth_service import auth_service
from src.utils.auth import get_current_user
from src.utils.responses import error_response, success_response

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/google", responses=google_login_responses)
async def google_login(
    state: str = Query(None, description="Optional CSRF state parameter"),
):
    """
    Get Google OAuth authorization URL

    **Response:**
    ```json
    {
        "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?...",
        "state": "random_state_string",
    }
    ```
    """
    try:
        oauth_data = auth_service.get_google_oauth_url(state)

        return oauth_data

    except ValueError as e:
        logger.error(f"OAuth configuration error: {str(e)}")
        return error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Google OAuth configuration error",
            error="CONFIGURATION_ERROR",
            errors={"details": [str(e)]},
        )
    except Exception as e:
        logger.error(f"Failed to generate OAuth URL: {str(e)}", exc_info=True)
        return error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Authentication service temporarily unavailable",
            error="SERVER_ERROR",
        )


google_login._custom_errors = google_login_custom_errors
google_login._custom_success = google_login_custom_success


@router.get(
    "/google/callback",
    response_model=TokenResponse,
    responses=google_callback_responses,
)
async def google_callback(
    code: str = Query(
        ..., description="Authorization code from Google (from redirect URL)"
    ),
    state: str = Query(
        None, description="CSRF state parameter (optional verification)"
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Exchange Google authorization code for JWT token

    **Response:**
    ```json
    {
        "access_token": "eyJhbGciOiJIUzI1NiIs...",
        "token_type": "bearer"
    }
    ```
    """
    try:
        token_response = auth_service.handle_google_callback(code, db)
        logger.info("Google OAuth callback successful - returning JWT token")
        return token_response

    except ValueError as e:
        logger.warning(f"Invalid OAuth callback: {str(e)}")
        return error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Invalid authentication request",
            error="INVALID_REQUEST",
            errors={"details": [str(e)]},
        )
    except Exception as e:
        logger.error(f"Authentication callback failed: {str(e)}", exc_info=True)
        return error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Authentication failed. Please try again",
            error="SERVER_ERROR",
        )


google_callback._custom_errors = google_callback_custom_errors
google_callback._custom_success = google_callback_custom_success


@router.get("/test-token", responses=test_token_responses)
async def test_token(current_user: dict = Depends(get_current_user)):
    """
    Test endpoint to verify your JWT token is working.

    **Response:**
    ```json
    {
        "message": "Token is valid!",
        "user": {
            "id": "user_id",
            "email": "user@example.com",
            "name": "User Name"
        }
    }
    ```
    """
    try:
        return success_response(
            status_code=status.HTTP_200_OK,
            message="Token is valid!",
            data={"user": current_user},
        )
    except Exception as e:
        logger.error(f"Token test failed: {str(e)}", exc_info=True)
        return error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to validate token",
            error="VALIDATION_ERROR",
        )


test_token._custom_errors = test_token_custom_errors
test_token._custom_success = test_token_custom_success
