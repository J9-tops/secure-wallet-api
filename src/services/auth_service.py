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
from sqlalchemy.orm import Session

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
        if not self.google_client_id:
            raise ValueError(
                "Google OAuth not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET"
            )

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

    def exchange_code_for_token(self, code: str) -> dict:
        if not self.google_client_id or not self.google_client_secret:
            raise ValueError("Google OAuth not configured")

        token_data = {
            "code": code,
            "client_id": self.google_client_id,
            "client_secret": self.google_client_secret,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
        }

        try:
            response = httpx.post(
                self.google_token_url,
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()

            result_json = response.json()
            result = {
                "authorization_url": result_json["authorization_url"],
                "state": result_json["state"],
            }
            return result
        except httpx.HTTPError as e:
            logger.error(f"Failed to exchange code for token: {str(e)}")
            raise ValueError(f"Failed to exchange authorization code: {str(e)}")

    def get_user_info(self, access_token: str) -> dict:
        try:
            response = httpx.get(
                self.google_userinfo_url,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to get user info: {str(e)}")
            raise ValueError(f"Failed to get user information: {str(e)}")

    def handle_google_callback(self, code: str, db: Session) -> TokenResponse:
        token_data = self.exchange_code_for_token(code)
        access_token = token_data.get("access_token")

        if not access_token:
            raise ValueError("Failed to get access token from Google")

        user_info = self.get_user_info(access_token)
        logger.info(f"Google user info: {user_info}")

        email = user_info.get("email")
        google_id = user_info.get("id")
        name = user_info.get("name")
        picture = user_info.get("picture")

        if not email or not google_id:
            raise ValueError("Invalid user info from Google")

        logger.info(f"Google OAuth callback for email: {email}")

        user = self._get_or_create_user(
            db=db, email=email, google_id=google_id, name=name, picture=picture
        )

        jwt_token = create_jwt_token(user.id, user.email)

        logger.info(f"Successfully authenticated user: {email}")

        return TokenResponse(access_token=jwt_token, token_type="bearer")

    def _get_or_create_user(
        self,
        db: Session,
        email: str,
        google_id: str,
        name: str = None,
        picture: str = None,
    ) -> User:
        result = db.execute(select(User).where(User.google_id == google_id))
        user = result.scalar_one_or_none()

        if not user:
            result = db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()

            if user:
                user.google_id = google_id
                if name:
                    user.name = name
                if picture:
                    user.picture = picture
                db.commit()
                logger.info(f"Updated existing user with Google ID: {email}")
                return user

        if user:
            logger.info(f"Existing user logged in: {email}")
            return user

        user = User(
            email=email,
            google_id=google_id,
            name=name or email.split("@")[0],
            picture=picture,
        )
        db.add(user)
        db.flush()

        wallet = Wallet(user_id=user.id)
        db.add(wallet)
        db.commit()
        db.refresh(user)

        logger.info(f"Created new user: {email}")

        return user


auth_service = AuthService()
