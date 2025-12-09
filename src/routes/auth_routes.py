"""
Authentication Routes - Google OAuth
Returns JSON responses with redirect URLs instead of performing redirects
"""

import logging

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.schemas.auth_schemas import TokenResponse
from src.services.auth_service import auth_service
from src.utils.auth import get_current_user
from src.utils.responses import error_response, success_response

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/google")
async def google_login(
    state: str = Query(None, description="Optional CSRF state parameter"),
):
    """
    Get Google OAuth authorization URL

    **For FastAPI Docs Testing:**
    1. Click "Try it out" and "Execute"
    2. Copy the `authorization_url` from the response
    3. Paste it in your browser and press Enter
    4. Complete Google sign-in
    5. You'll be redirected back with a `code` parameter
    6. Copy that code and use it in the `/auth/google/callback` endpoint

    **Response:**
    ```json
    {
        "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?...",
        "state": "random_state_string",
        "instructions": "Open the authorization_url in your browser to sign in with Google"
    }
    ```
    """
    try:
        oauth_data = auth_service.get_google_oauth_url(state)

        return (
            {
                "authorization_url": oauth_data["authorization_url"],
                "state": oauth_data["state"],
            },
        )

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


@router.get("/google/callback", response_model=TokenResponse)
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

    **How to use:**
    1. After signing in with Google, you'll be redirected to a URL like:
       `http://localhost:8000/auth/google/callback?code=4/0AY0e-g7...&state=...`
    2. Copy the `code` parameter value from that URL
    3. Paste it in the `code` field below
    4. Click "Execute"
    5. You'll receive your JWT token!

    **Using the token:**
    1. Copy the `access_token` from the response
    2. Click "Authorize" button at the top of Swagger UI
    3. Enter: `Bearer YOUR_TOKEN_HERE`
    4. Now you can test protected endpoints!

    **Response:**
    ```json
    {
        "access_token": "eyJhbGciOiJIUzI1NiIs...",
        "token_type": "bearer"
    }
    ```
    """
    try:
        token_response = await auth_service.handle_google_callback(code, db)
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


@router.get("/test-token")
async def test_token(current_user: dict = Depends(get_current_user)):
    """
    Test endpoint to verify your JWT token is working.

    **How to test:**
    1. Get your token from `/auth/google/callback`
    2. Click "Authorize" in Swagger UI and enter: `Bearer YOUR_TOKEN_HERE`
    3. Try this endpoint - it should return success!

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
