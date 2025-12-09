from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.auth_service import AuthService


class TestAuthService:
    """Test Google OAuth & JWT Authentication"""

    @pytest.fixture
    def auth_service(self):
        service = AuthService()
        service.google_client_id = "test_client_id"
        service.google_client_secret = "test_client_secret"
        return service

    def test_get_google_oauth_url(self, auth_service):
        """Test Google OAuth URL generation"""
        result = auth_service.get_google_oauth_url()

        assert "authorization_url" in result
        assert "state" in result
        assert "accounts.google.com" in result["authorization_url"]
        assert "test_client_id" in result["authorization_url"]

    @pytest.mark.asyncio
    async def test_exchange_code_for_token_success(self, auth_service):
        """Test successful token exchange"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "test_token",
            "token_type": "Bearer",
        }
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            result = await auth_service.exchange_code_for_token("test_code")

            assert result["access_token"] == "test_token"

    @pytest.mark.asyncio
    async def test_get_user_info_success(self, auth_service):
        """Test fetching user info from Google"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "email": "test@example.com",
            "id": "google123",
            "name": "Test User",
            "picture": "https://example.com/pic.jpg",
        }
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await auth_service.get_user_info("test_token")

            assert result["email"] == "test@example.com"
            assert result["id"] == "google123"

    @pytest.mark.asyncio
    async def test_handle_google_callback_new_user(self, auth_service):
        """Test callback creates new user and wallet"""
        db = AsyncMock(spec=AsyncSession)

        # Mock no existing user
        user_result = Mock()
        user_result.scalar_one_or_none.return_value = None
        db.execute.return_value = user_result

        with patch.object(auth_service, "exchange_code_for_token") as mock_exchange:
            with patch.object(auth_service, "get_user_info") as mock_user_info:
                mock_exchange.return_value = {"access_token": "test_token"}
                mock_user_info.return_value = {
                    "email": "newuser@example.com",
                    "id": "google456",
                    "name": "New User",
                }

                result = await auth_service.handle_google_callback("code123", db)

                assert result.token_type == "bearer"
                assert db.add.called
                assert db.commit.called
