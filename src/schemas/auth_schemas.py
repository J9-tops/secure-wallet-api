"""
Authentication Schemas
"""

from pydantic import BaseModel, Field


class TokenResponse(BaseModel):
    """JWT Token Response"""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(
        default="bearer", description="Token type (always 'bearer')"
    )


class GoogleAuthURLResponse(BaseModel):
    """Google OAuth Authorization URL Response"""

    authorization_url: str = Field(
        ..., description="URL to redirect user to for Google OAuth"
    )
    state: str = Field(..., description="CSRF state parameter for security")
    instructions: str = Field(..., description="Instructions for completing OAuth flow")


class UserTestResponse(BaseModel):
    """Test token response"""

    message: str
    user: dict
