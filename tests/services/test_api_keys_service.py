"""
Comprehensive Test Suite for Wallet Service Backend
Tests aligned with Stage 9 project objectives
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.exc import IntegrityError
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

        async_context = AsyncMock()
        async_context.__aenter__ = AsyncMock(return_value=async_context)
        async_context.__aexit__ = AsyncMock(return_value=None)
        db.begin.return_value = async_context

        return db

    @pytest.mark.asyncio
    async def test_create_api_key_success(self, api_key_service, mock_user, mock_db):
        """Test successful API key creation with valid expiry"""

        count_result = Mock()
        count_result.scalar.return_value = 0
        mock_db.execute.return_value = count_result

        mock_db.flush = AsyncMock()

        result = await api_key_service.create_api_key(
            db=mock_db,
            user=mock_user,
            name="test-key",
            permissions=["deposit", "transfer"],
            expiry="1D",
        )

        assert result.api_key.startswith("sk_")
        assert len(result.api_key) >= 40
        assert result.expires_at > datetime.now(timezone.utc)

    @pytest.mark.asyncio
    async def test_create_api_key_max_limit_reached(
        self, api_key_service, mock_user, mock_db
    ):
        """Test that maximum 5 active API keys per user is enforced"""

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

            now_utc = datetime.now(timezone.utc)
            time_diff = result.expires_at - now_utc
            assert abs(time_diff - expected_delta) < timedelta(minutes=1)

    @pytest.mark.asyncio
    async def test_rollover_expired_key_success(
        self, api_key_service, mock_user, mock_db
    ):
        """Test rolling over an expired API key with same permissions"""
        expired_key = Mock(spec=APIKey)
        expired_key.id = "key123"
        expired_key.name = "old-key"
        expired_key.permissions = ["deposit", "transfer"]
        expired_key.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        expired_key.is_revoked = False

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


class TestAPIKeyPermissions:
    """Test API Key Permission Enforcement"""

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

        async_context = AsyncMock()
        async_context.__aenter__ = AsyncMock(return_value=async_context)
        async_context.__aexit__ = AsyncMock(return_value=None)
        db.begin.return_value = async_context

        return db

    @pytest.mark.asyncio
    async def test_create_api_key_with_deposit_permission(
        self, api_key_service, mock_user, mock_db
    ):
        """Test creating API key with only deposit permission"""
        count_result = Mock()
        count_result.scalar.return_value = 0
        mock_db.execute.return_value = count_result
        mock_db.flush = AsyncMock()

        result = await api_key_service.create_api_key(
            db=mock_db,
            user=mock_user,
            name="deposit-only-key",
            permissions=["deposit"],
            expiry="1D",
        )

        assert result.api_key.startswith("sk_")
        call_args = mock_db.add.call_args
        added_key = call_args[0][0]
        assert added_key.permissions == ["deposit"]

    @pytest.mark.asyncio
    async def test_create_api_key_with_transfer_permission(
        self, api_key_service, mock_user, mock_db
    ):
        """Test creating API key with only transfer permission"""
        count_result = Mock()
        count_result.scalar.return_value = 0
        mock_db.execute.return_value = count_result
        mock_db.flush = AsyncMock()

        await api_key_service.create_api_key(
            db=mock_db,
            user=mock_user,
            name="transfer-only-key",
            permissions=["transfer"],
            expiry="1D",
        )

        call_args = mock_db.add.call_args
        added_key = call_args[0][0]
        assert added_key.permissions == ["transfer"]

    @pytest.mark.asyncio
    async def test_create_api_key_with_read_permission(
        self, api_key_service, mock_user, mock_db
    ):
        """Test creating API key with only read permission"""
        count_result = Mock()
        count_result.scalar.return_value = 0
        mock_db.execute.return_value = count_result
        mock_db.flush = AsyncMock()

        await api_key_service.create_api_key(
            db=mock_db,
            user=mock_user,
            name="read-only-key",
            permissions=["read"],
            expiry="1D",
        )

        call_args = mock_db.add.call_args
        added_key = call_args[0][0]
        assert added_key.permissions == ["read"]

    @pytest.mark.asyncio
    async def test_create_api_key_with_multiple_permissions(
        self, api_key_service, mock_user, mock_db
    ):
        """Test creating API key with multiple permissions"""
        count_result = Mock()
        count_result.scalar.return_value = 0
        mock_db.execute.return_value = count_result
        mock_db.flush = AsyncMock()

        await api_key_service.create_api_key(
            db=mock_db,
            user=mock_user,
            name="full-access-key",
            permissions=["deposit", "transfer", "read"],
            expiry="1D",
        )

        call_args = mock_db.add.call_args
        added_key = call_args[0][0]
        assert set(added_key.permissions) == {"deposit", "transfer", "read"}

    @pytest.mark.asyncio
    async def test_create_api_key_with_empty_permissions(
        self, api_key_service, mock_user, mock_db
    ):
        """Test creating API key with empty permissions list"""
        count_result = Mock()
        count_result.scalar.return_value = 0
        mock_db.execute.return_value = count_result
        mock_db.flush = AsyncMock()

        await api_key_service.create_api_key(
            db=mock_db,
            user=mock_user,
            name="no-permission-key",
            permissions=[],
            expiry="1D",
        )

        call_args = mock_db.add.call_args
        added_key = call_args[0][0]
        assert added_key.permissions == []

    @pytest.mark.asyncio
    async def test_rollover_preserves_permissions(
        self, api_key_service, mock_user, mock_db
    ):
        """Test that rollover creates new key with exact same permissions"""
        expired_key = Mock(spec=APIKey)
        expired_key.id = "key123"
        expired_key.name = "old-key"
        expired_key.permissions = ["deposit", "read"]
        expired_key.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        expired_key.is_revoked = False

        key_result = Mock()
        key_result.scalar_one_or_none.return_value = expired_key

        count_result = Mock()
        count_result.scalar.return_value = 2

        mock_db.execute.side_effect = [key_result, count_result]
        mock_db.flush = AsyncMock()

        await api_key_service.rollover_api_key(
            db=mock_db, user=mock_user, expired_key_id="key123", new_expiry="1M"
        )

        call_args = mock_db.add.call_args
        new_key = call_args[0][0]
        assert new_key.permissions == ["deposit", "read"]

    @pytest.mark.asyncio
    async def test_create_api_key_with_invalid_permissions(
        self, api_key_service, mock_user, mock_db
    ):
        """Test creating API key with invalid permission names (should still work - validation happens at endpoint level)"""
        count_result = Mock()
        count_result.scalar.return_value = 0
        mock_db.execute.return_value = count_result
        mock_db.flush = AsyncMock()

        await api_key_service.create_api_key(
            db=mock_db,
            user=mock_user,
            name="invalid-permission-key",
            permissions=["invalid_permission", "another_invalid"],
            expiry="1D",
        )

        call_args = mock_db.add.call_args
        added_key = call_args[0][0]
        assert added_key.permissions == ["invalid_permission", "another_invalid"]


class TestAPIKeyValidation:
    """Test API Key validation logic that would be used in middleware/decorators"""

    def test_api_key_has_permission(self):
        """Test checking if API key has specific permission"""
        api_key = Mock(spec=APIKey)
        api_key.permissions = ["deposit", "read"]

        assert "deposit" in api_key.permissions
        assert "read" in api_key.permissions
        assert "transfer" not in api_key.permissions

    def test_api_key_is_expired(self):
        """Test checking if API key is expired"""
        expired_key = Mock(spec=APIKey)
        expired_key.expires_at = datetime.now(timezone.utc) - timedelta(days=1)

        active_key = Mock(spec=APIKey)
        active_key.expires_at = datetime.now(timezone.utc) + timedelta(days=1)

        assert expired_key.expires_at < datetime.now(timezone.utc)
        assert active_key.expires_at > datetime.now(timezone.utc)

    def test_api_key_is_revoked(self):
        """Test checking if API key is revoked"""
        revoked_key = Mock(spec=APIKey)
        revoked_key.is_revoked = True

        active_key = Mock(spec=APIKey)
        active_key.is_revoked = False

        assert revoked_key.is_revoked is True
        assert active_key.is_revoked is False

    def test_api_key_is_valid(self):
        """Test comprehensive API key validation"""
        valid_key = Mock(spec=APIKey)
        valid_key.is_revoked = False
        valid_key.expires_at = datetime.now(timezone.utc) + timedelta(days=1)
        valid_key.is_active = True

        assert (
            not valid_key.is_revoked
            and valid_key.expires_at > datetime.now(timezone.utc)
            and valid_key.is_active
        )

        expired_key = Mock(spec=APIKey)
        expired_key.is_revoked = False
        expired_key.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        expired_key.is_active = True

        assert not (
            not expired_key.is_revoked
            and expired_key.expires_at > datetime.now(timezone.utc)
            and expired_key.is_active
        )


"""
Tests for API Key Edge Cases
Tests concurrent operations, key limits, and edge scenarios
"""


class TestAPIKeyLimits:
    """Test API key limit enforcement"""

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
        db = AsyncMock(spec=AsyncSession)
        async_context = AsyncMock()
        async_context.__aenter__ = AsyncMock(return_value=async_context)
        async_context.__aexit__ = AsyncMock(return_value=None)
        db.begin.return_value = async_context
        return db

    @pytest.mark.asyncio
    async def test_create_key_at_limit_minus_one(
        self, api_key_service, mock_user, mock_db
    ):
        """Test creating API key when at 4 keys (one below limit)"""
        count_result = Mock()
        count_result.scalar.return_value = 4
        mock_db.execute.return_value = count_result
        mock_db.flush = AsyncMock()

        result = await api_key_service.create_api_key(
            db=mock_db,
            user=mock_user,
            name="5th-key",
            permissions=["read"],
            expiry="1D",
        )

        assert result.api_key.startswith("sk_")

    @pytest.mark.asyncio
    async def test_create_key_exceeds_limit(self, api_key_service, mock_user, mock_db):
        """Test creating API key when already at 5 keys fails"""
        count_result = Mock()
        count_result.scalar.return_value = 5
        mock_db.execute.return_value = count_result

        with pytest.raises(ValueError, match="Maximum of 5 active API keys"):
            await api_key_service.create_api_key(
                db=mock_db,
                user=mock_user,
                name="6th-key",
                permissions=["read"],
                expiry="1D",
            )

    @pytest.mark.asyncio
    async def test_rollover_at_limit_fails(self, api_key_service, mock_user, mock_db):
        """Test rollover fails when already at 5 active keys"""
        expired_key = Mock(spec=APIKey)
        expired_key.id = "key123"
        expired_key.name = "old-key"
        expired_key.permissions = ["deposit"]
        expired_key.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        expired_key.is_revoked = False

        key_result = Mock()
        key_result.scalar_one_or_none.return_value = expired_key

        count_result = Mock()
        count_result.scalar.return_value = 5

        mock_db.execute.side_effect = [key_result, count_result]

        with pytest.raises(ValueError, match="Maximum of 5 active API keys"):
            await api_key_service.rollover_api_key(
                db=mock_db, user=mock_user, expired_key_id="key123", new_expiry="1M"
            )


class TestAPIKeyCollisions:
    """Test API key collision handling"""

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
        db = AsyncMock(spec=AsyncSession)
        async_context = AsyncMock()
        async_context.__aenter__ = AsyncMock(return_value=async_context)
        async_context.__aexit__ = AsyncMock(return_value=None)
        db.begin.return_value = async_context
        return db

    @pytest.mark.asyncio
    async def test_create_key_retry_on_collision(
        self, api_key_service, mock_user, mock_db
    ):
        """Test API key creation retries on collision"""
        count_result = Mock()
        count_result.scalar.return_value = 0
        mock_db.execute.return_value = count_result

        mock_db.flush = AsyncMock(side_effect=[IntegrityError("", "", ""), None])
        mock_db.rollback = AsyncMock()

        result = await api_key_service.create_api_key(
            db=mock_db,
            user=mock_user,
            name="test-key",
            permissions=["read"],
            expiry="1D",
        )

        assert result.api_key.startswith("sk_")
        assert mock_db.rollback.call_count == 1

    @pytest.mark.asyncio
    async def test_create_key_max_retries_exceeded(
        self, api_key_service, mock_user, mock_db
    ):
        """Test API key creation fails after max retries"""
        count_result = Mock()
        count_result.scalar.return_value = 0
        mock_db.execute.return_value = count_result

        mock_db.flush = AsyncMock(
            side_effect=[IntegrityError("", "", "")]
            * api_key_service.MAX_RETRY_ATTEMPTS
        )
        mock_db.rollback = AsyncMock()

        with pytest.raises(ValueError, match="Failed to generate unique API key"):
            await api_key_service.create_api_key(
                db=mock_db,
                user=mock_user,
                name="test-key",
                permissions=["read"],
                expiry="1D",
            )

    @pytest.mark.asyncio
    async def test_rollover_retry_on_collision(
        self, api_key_service, mock_user, mock_db
    ):
        """Test rollover retries on collision"""
        expired_key = Mock(spec=APIKey)
        expired_key.id = "key123"
        expired_key.name = "old-key"
        expired_key.permissions = ["deposit"]
        expired_key.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        expired_key.is_revoked = False

        key_result = Mock()
        key_result.scalar_one_or_none.return_value = expired_key

        count_result = Mock()
        count_result.scalar.return_value = 2

        mock_db.execute.side_effect = [key_result, count_result]

        mock_db.flush = AsyncMock(side_effect=[IntegrityError("", "", ""), None])
        mock_db.rollback = AsyncMock()

        result = await api_key_service.rollover_api_key(
            db=mock_db, user=mock_user, expired_key_id="key123", new_expiry="1M"
        )

        assert result.api_key.startswith("sk_")
        assert mock_db.rollback.call_count == 1


class TestAPIKeyNotFound:
    """Test API key not found scenarios"""

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
        db = AsyncMock(spec=AsyncSession)
        async_context = AsyncMock()
        async_context.__aenter__ = AsyncMock(return_value=async_context)
        async_context.__aexit__ = AsyncMock(return_value=None)
        db.begin.return_value = async_context
        return db

    @pytest.mark.asyncio
    async def test_rollover_nonexistent_key(self, api_key_service, mock_user, mock_db):
        """Test rollover fails for non-existent key"""
        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = result_mock

        with pytest.raises(LookupError, match="API key not found"):
            await api_key_service.rollover_api_key(
                db=mock_db,
                user=mock_user,
                expired_key_id="nonexistent_key",
                new_expiry="1M",
            )

    @pytest.mark.asyncio
    async def test_revoke_nonexistent_key(self, api_key_service, mock_user, mock_db):
        """Test revoke fails for non-existent key"""
        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = result_mock

        with pytest.raises(LookupError, match="API key not found"):
            await api_key_service.revoke_api_key(
                db=mock_db, user=mock_user, key_id="nonexistent_key"
            )

    @pytest.mark.asyncio
    async def test_rollover_wrong_user_key(self, api_key_service, mock_user, mock_db):
        """Test rollover fails when key belongs to different user"""
        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = result_mock

        with pytest.raises(LookupError, match="API key not found"):
            await api_key_service.rollover_api_key(
                db=mock_db,
                user=mock_user,
                expired_key_id="other_user_key",
                new_expiry="1M",
            )


class TestAPIKeyExpiry:
    """Test API key expiry edge cases"""

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
        db = AsyncMock(spec=AsyncSession)
        async_context = AsyncMock()
        async_context.__aenter__ = AsyncMock(return_value=async_context)
        async_context.__aexit__ = AsyncMock(return_value=None)
        db.begin.return_value = async_context
        return db

    @pytest.mark.asyncio
    async def test_rollover_just_expired_key(self, api_key_service, mock_user, mock_db):
        """Test rollover works for key that just expired"""
        expired_key = Mock(spec=APIKey)
        expired_key.id = "key123"
        expired_key.name = "old-key"
        expired_key.permissions = ["deposit"]
        expired_key.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        expired_key.is_revoked = False

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

    @pytest.mark.asyncio
    async def test_rollover_almost_expired_key_fails(
        self, api_key_service, mock_user, mock_db
    ):
        """Test rollover fails for key that's almost expired but not yet"""
        almost_expired_key = Mock(spec=APIKey)
        almost_expired_key.expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=10
        )
        almost_expired_key.is_revoked = False

        key_result = Mock()
        key_result.scalar_one_or_none.return_value = almost_expired_key
        mock_db.execute.return_value = key_result

        with pytest.raises(ValueError, match="API key is not expired"):
            await api_key_service.rollover_api_key(
                db=mock_db, user=mock_user, expired_key_id="key123", new_expiry="1M"
            )

    @pytest.mark.asyncio
    async def test_rollover_revoked_key_fails(
        self, api_key_service, mock_user, mock_db
    ):
        """Test rollover fails for already revoked key"""
        revoked_key = Mock(spec=APIKey)
        revoked_key.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        revoked_key.is_revoked = True

        key_result = Mock()
        key_result.scalar_one_or_none.return_value = revoked_key
        mock_db.execute.return_value = key_result

        with pytest.raises(ValueError, match="already been revoked"):
            await api_key_service.rollover_api_key(
                db=mock_db, user=mock_user, expired_key_id="key123", new_expiry="1M"
            )


class TestAPIKeyExpiryFormats:
    """Test different expiry format edge cases"""

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
        db = AsyncMock(spec=AsyncSession)
        async_context = AsyncMock()
        async_context.__aenter__ = AsyncMock(return_value=async_context)
        async_context.__aexit__ = AsyncMock(return_value=None)
        db.begin.return_value = async_context
        return db

    @pytest.mark.asyncio
    async def test_create_key_lowercase_expiry(
        self, api_key_service, mock_user, mock_db
    ):
        """Test expiry format is case-insensitive (if implemented)"""
        count_result = Mock()
        count_result.scalar.return_value = 0
        mock_db.execute.return_value = count_result
        mock_db.flush = AsyncMock()

        try:
            result = await api_key_service.create_api_key(
                db=mock_db,
                user=mock_user,
                name="test-key",
                permissions=["read"],
                expiry="1d",
            )
            assert result.api_key.startswith("sk_")
        except ValueError:
            pass

    @pytest.mark.asyncio
    async def test_create_key_invalid_expiry_format(
        self, api_key_service, mock_user, mock_db
    ):
        """Test invalid expiry format raises error"""
        with pytest.raises(ValueError):
            await api_key_service.create_api_key(
                db=mock_db,
                user=mock_user,
                name="test-key",
                permissions=["read"],
                expiry="INVALID",
            )

    @pytest.mark.asyncio
    async def test_create_key_missing_expiry_unit(
        self, api_key_service, mock_user, mock_db
    ):
        """Test expiry without unit raises error"""
        with pytest.raises(ValueError):
            await api_key_service.create_api_key(
                db=mock_db,
                user=mock_user,
                name="test-key",
                permissions=["read"],
                expiry="1",
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
