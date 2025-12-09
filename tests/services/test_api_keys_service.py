"""
Comprehensive Test Suite for Wallet Service Backend
Tests aligned with Stage 9 project objectives
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.api_key_model import APIKey
from src.models.user_model import User
from src.services.api_keys_service import APIKeyService


class TestAPIKeyService:
    """Test API Key Management - Objectives: API keys, permissions, limits, expiry"""

    @pytest.fixture
    def api_key_service(self):
        return APIKeyService()

    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = "user123"
        user.email = "test@example.com"
        return user

    @pytest.fixture
    def mock_db(self):
        """Create properly configured async mock database session"""
        db = AsyncMock(spec=AsyncSession)

        # Create async context manager for db.begin()
        async_context = AsyncMock()
        async_context.__aenter__ = AsyncMock(return_value=async_context)
        async_context.__aexit__ = AsyncMock(return_value=None)
        db.begin.return_value = async_context

        return db

    @pytest.mark.asyncio
    async def test_create_api_key_success(self, api_key_service, mock_user, mock_db):
        """Test successful API key creation with valid expiry"""
        # Mock count query (0 existing keys)
        count_result = Mock()
        count_result.scalar.return_value = 0
        mock_db.execute.return_value = count_result

        # Mock flush (no collision)
        mock_db.flush = AsyncMock()

        result = await api_key_service.create_api_key(
            db=mock_db,
            user=mock_user,
            name="test-key",
            permissions=["deposit", "transfer"],
            expiry="1D",
        )

        assert result.api_key.startswith("sk_")
        assert len(result.api_key) >= 40  # API keys are at least 40 characters
        assert result.expires_at > datetime.now(timezone.utc)

    @pytest.mark.asyncio
    async def test_create_api_key_max_limit_reached(
        self, api_key_service, mock_user, mock_db
    ):
        """Test that maximum 5 active API keys per user is enforced"""
        # Mock count query (5 existing keys - at limit)
        count_result = Mock()
        count_result.scalar.return_value = 5
        mock_db.execute.return_value = count_result

        with pytest.raises(ValueError, match="Maximum of 5 active API keys"):
            await api_key_service.create_api_key(
                db=mock_db,
                user=mock_user,
                name="test-key",
                permissions=["deposit"],
                expiry="1D",
            )

    @pytest.mark.asyncio
    async def test_create_api_key_expiry_formats(
        self, api_key_service, mock_user, mock_db
    ):
        """Test all valid expiry formats: 1H, 1D, 1M, 1Y"""
        count_result = Mock()
        count_result.scalar.return_value = 0
        mock_db.execute.return_value = count_result
        mock_db.flush = AsyncMock()

        expiry_tests = [
            ("1H", timedelta(hours=1)),
            ("1D", timedelta(days=1)),
            ("1M", timedelta(days=30)),
            ("1Y", timedelta(days=365)),
        ]

        for expiry_str, expected_delta in expiry_tests:
            result = await api_key_service.create_api_key(
                db=mock_db,
                user=mock_user,
                name="test-key",
                permissions=["read"],
                expiry=expiry_str,
            )

            # Both datetimes must be timezone-aware for comparison
            now_utc = datetime.now(timezone.utc)
            time_diff = result.expires_at - now_utc
            assert abs(time_diff - expected_delta) < timedelta(minutes=1)

    @pytest.mark.asyncio
    async def test_rollover_expired_key_success(
        self, api_key_service, mock_user, mock_db
    ):
        """Test rolling over an expired API key with same permissions"""
        # Mock expired key
        expired_key = Mock(spec=APIKey)
        expired_key.id = "key123"
        expired_key.name = "old-key"
        expired_key.permissions = ["deposit", "transfer"]
        expired_key.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        expired_key.is_revoked = False

        # Mock queries
        key_result = Mock()
        key_result.scalar_one_or_none.return_value = expired_key

        count_result = Mock()
        count_result.scalar.return_value = 2

        mock_db.execute.side_effect = [key_result, count_result]
        mock_db.flush = AsyncMock()

        result = await api_key_service.rollover_api_key(
            db=mock_db, user=mock_user, expired_key_id="key123", new_expiry="1M"
        )

        assert result.api_key.startswith("sk_")
        assert expired_key.is_revoked is True

    @pytest.mark.asyncio
    async def test_rollover_not_expired_key_fails(
        self, api_key_service, mock_user, mock_db
    ):
        """Test that rollover fails if key is not actually expired"""
        # Mock non-expired key
        active_key = Mock(spec=APIKey)
        active_key.expires_at = datetime.now(timezone.utc) + timedelta(days=1)
        active_key.is_revoked = False

        key_result = Mock()
        key_result.scalar_one_or_none.return_value = active_key
        mock_db.execute.return_value = key_result

        with pytest.raises(ValueError, match="API key is not expired"):
            await api_key_service.rollover_api_key(
                db=mock_db, user=mock_user, expired_key_id="key123", new_expiry="1M"
            )

    @pytest.mark.asyncio
    async def test_revoke_api_key_success(self, api_key_service, mock_user, mock_db):
        """Test revoking an active API key"""
        active_key = Mock(spec=APIKey)
        active_key.is_revoked = False

        key_result = Mock()
        key_result.scalar_one_or_none.return_value = active_key
        mock_db.execute.return_value = key_result

        result = await api_key_service.revoke_api_key(
            db=mock_db, user=mock_user, key_id="key123"
        )

        assert result is True
        assert active_key.is_revoked is True

    @pytest.mark.asyncio
    async def test_revoke_already_revoked_key_fails(
        self, api_key_service, mock_user, mock_db
    ):
        """Test that revoking an already revoked key fails"""
        revoked_key = Mock(spec=APIKey)
        revoked_key.is_revoked = True

        key_result = Mock()
        key_result.scalar_one_or_none.return_value = revoked_key
        mock_db.execute.return_value = key_result

        with pytest.raises(ValueError, match="already revoked"):
            await api_key_service.revoke_api_key(
                db=mock_db, user=mock_user, key_id="key123"
            )

    @pytest.mark.asyncio
    async def test_create_api_key_invalid_expiry(
        self, api_key_service, mock_user, mock_db
    ):
        """Test that invalid expiry format raises error"""
        with pytest.raises(ValueError):
            await api_key_service.create_api_key(
                db=mock_db,
                user=mock_user,
                name="test-key",
                permissions=["deposit"],
                expiry="INVALID",
            )
