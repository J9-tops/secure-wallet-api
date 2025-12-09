"""
Authentication Service - Google OAuth Business Logic
Refactored to use httpx and return redirect URLs instead of performing redirects
"""

import logging
import os
import secrets
from urllib.parse import urlencode

import httpx
from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user_model import User
from src.models.wallet_model import Wallet
from src.schemas.auth_schemas import TokenResponse
from src.utils.security import create_jwt_token

load_dotenv()
logger = logging.getLogger(__name__)


class AuthService:
    """Service for handling authentication operations"""

    def __init__(self):
        self.google_client_id = os.getenv("GOOGLE_CLIENT_ID")
        self.google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        self.redirect_uri = os.getenv(
            "GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback"
        )

        # Google OAuth endpoints
        self.google_auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
        self.google_token_url = "https://oauth2.googleapis.com/token"
        self.google_userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"

        if self.google_client_id and self.google_client_secret:
            logger.info("Google OAuth configured successfully")
        else:
            logger.warning(
                "Google OAuth credentials not configured - OAuth endpoints will not work"
            )

    def get_google_oauth_url(self, state: str = None) -> dict:
        """
        Generate Google OAuth authorization URL

        Args:
            state: Optional CSRF state parameter

        Returns:
            dict with authorization_url and state
        """
        if not self.google_client_id:
            raise ValueError(
                "Google OAuth not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET"
            )

        # Generate state for CSRF protection if not provided
        if not state:
            state = secrets.token_urlsafe(32)

        params = {
            "client_id": self.google_client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }

        authorization_url = f"{self.google_auth_url}?{urlencode(params)}"

        return {"authorization_url": authorization_url, "state": state}

    async def exchange_code_for_token(self, code: str) -> dict:
        """
        Exchange authorization code for access token

        Args:
            code: Authorization code from Google

        Returns:
            dict containing access_token and other token info

        Raises:
            ValueError: If token exchange fails
        """
        if not self.google_client_id or not self.google_client_secret:
            raise ValueError("Google OAuth not configured")

        token_data = {
            "code": code,
            "client_id": self.google_client_id,
            "client_secret": self.google_client_secret,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.google_token_url,
                    data=token_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Failed to exchange code for token: {str(e)}")
                raise ValueError(f"Failed to exchange authorization code: {str(e)}")

    async def get_user_info(self, access_token: str) -> dict:
        """
        Get user information from Google

        Args:
            access_token: Google access token

        Returns:
            dict containing user info (email, sub, name, picture)

        Raises:
            ValueError: If fetching user info fails
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    self.google_userinfo_url,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Failed to get user info: {str(e)}")
                raise ValueError(f"Failed to get user information: {str(e)}")

    async def handle_google_callback(
        self, code: str, db: AsyncSession
    ) -> TokenResponse:
        """
        Handle Google OAuth callback and create/login user

        Args:
            code: OAuth authorization code
            db: Database session

        Returns:
            TokenResponse with JWT token

        Raises:
            ValueError: If authentication fails
        """
        # Exchange code for access token
        token_data = await self.exchange_code_for_token(code)
        access_token = token_data.get("access_token")

        if not access_token:
            raise ValueError("Failed to get access token from Google")

        # Get user info
        user_info = await self.get_user_info(access_token)
        logger.info(f"Google user info: {user_info}")

        email = user_info.get("email")
        google_id = user_info.get("id")
        name = user_info.get("name")
        picture = user_info.get("picture")

        if not email or not google_id:
            raise ValueError("Invalid user info from Google")

        logger.info(f"Google OAuth callback for email: {email}")

        # Get or create user
        user = await self._get_or_create_user(
            db=db, email=email, google_id=google_id, name=name, picture=picture
        )

        # Generate JWT
        jwt_token = create_jwt_token(user.id, user.email)

        logger.info(f"Successfully authenticated user: {email}")

        return TokenResponse(access_token=jwt_token, token_type="bearer")

    async def _get_or_create_user(
        self,
        db: AsyncSession,
        email: str,
        google_id: str,
        name: str = None,
        picture: str = None,
    ) -> User:
        """
        Get existing user or create new one with wallet

        Args:
            db: Database session
            email: User email
            google_id: Google user ID
            name: User name
            picture: User picture URL

        Returns:
            User object
        """
        # Check if user exists by google_id first
        result = await db.execute(select(User).where(User.google_id == google_id))
        user = result.scalar_one_or_none()

        # If not found by google_id, check by email
        if not user:
            result = await db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()

            # Update google_id if user exists with email
            if user:
                user.google_id = google_id
                if name:
                    user.name = name
                if picture:
                    user.picture = picture
                await db.commit()
                logger.info(f"Updated existing user with Google ID: {email}")
                return user

        # User exists, return it
        if user:
            logger.info(f"Existing user logged in: {email}")
            return user

        # Create new user
        user = User(
            email=email,
            google_id=google_id,
            name=name or email.split("@")[0],
            picture=picture,
        )
        db.add(user)
        await db.flush()

        # Create wallet for new user
        wallet = Wallet(user_id=user.id)
        db.add(wallet)
        await db.commit()
        await db.refresh(user)

        logger.info(f"Created new user: {email}")

        return user


# Singleton instance
auth_service = AuthService()
