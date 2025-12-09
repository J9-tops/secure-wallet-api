"""
Integration Tests for Complete Wallet Flows
Tests end-to-end scenarios with multiple services working together
"""

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.api_key_model import APIKey
from src.models.transaction_model import Transaction, TransactionStatus
from src.models.user_model import User
from src.models.wallet_model import Wallet
from src.services.api_keys_service import APIKeyService
from src.services.auth_service import AuthService
from src.services.wallet_service import WalletService
from src.services.webhook_service import WebhookService


class TestCompleteDepositFlow:
    """Test complete deposit flow from initiation to webhook to balance update"""

    @pytest.fixture
    def wallet_service(self):
        return WalletService()

    @pytest.fixture
    def webhook_service(self):
        return WebhookService()

    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = "user123"
        user.email = "test@example.com"
        return user

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock(spec=AsyncSession)
        return db

    @pytest.mark.asyncio
    async def test_complete_deposit_flow_success(
        self, wallet_service, webhook_service, mock_user, mock_db
    ):
        """
        Test complete flow:
        1. User initiates deposit
        2. Transaction created with PENDING status
        3. Webhook arrives with success
        4. Wallet is credited
        5. Transaction status updated to SUCCESS
        """

        with patch(
            "src.services.wallet_service.paystack_service.initialize_transaction"
        ) as mock_paystack:
            mock_paystack.return_value = {
                "authorization_url": "https://paystack.co/pay/test123",
                "access_code": "test123",
            }

            deposit_response = await wallet_service.initiate_deposit(
                db=mock_db, user=mock_user, amount=Decimal("5000.00")
            )

            reference = deposit_response.reference
            assert reference.startswith("TXN_")

        transaction = Mock(spec=Transaction)
        transaction.user_id = "user123"
        transaction.amount = Decimal("5000.00")
        transaction.status = TransactionStatus.PENDING
        transaction.reference = reference

        wallet = Mock(spec=Wallet)
        wallet.balance = Decimal("1000.00")
        wallet.user_id = "user123"

        txn_result = Mock()
        txn_result.scalar_one_or_none.return_value = transaction

        wallet_result = Mock()
        wallet_result.scalar_one.return_value = wallet

        mock_db.execute.side_effect = [txn_result, wallet_result]

        webhook_data = {
            "event": "charge.success",
            "data": {
                "reference": reference,
                "amount": 500000,
                "status": "success",
            },
        }
        body = json.dumps(webhook_data).encode()

        with patch(
            "src.services.webhook_service.verify_paystack_signature", return_value=True
        ):
            webhook_processed = await webhook_service.process_paystack_webhook(
                db=mock_db, body=body, signature="valid_signature"
            )

        assert webhook_processed is True
        assert transaction.status == TransactionStatus.SUCCESS
        assert wallet.balance == Decimal("6000.00")

    @pytest.mark.asyncio
    async def test_deposit_webhook_idempotency(self, webhook_service, mock_db):
        """
        Test that processing the same webhook twice doesn't double credit
        """
        reference = "TXN_TEST_123"

        transaction = Mock(spec=Transaction)
        transaction.user_id = "user123"
        transaction.amount = Decimal("5000.00")
        transaction.status = TransactionStatus.PENDING

        wallet = Mock(spec=Wallet)
        wallet.balance = Decimal("0.00")

        txn_result = Mock()
        txn_result.scalar_one_or_none.return_value = transaction

        wallet_result = Mock()
        wallet_result.scalar_one.return_value = wallet

        mock_db.execute.side_effect = [txn_result, wallet_result]

        webhook_data = {
            "event": "charge.success",
            "data": {"reference": reference, "amount": 500000, "status": "success"},
        }
        body = json.dumps(webhook_data).encode()

        with patch(
            "src.services.webhook_service.verify_paystack_signature", return_value=True
        ):
            first_result = await webhook_service.process_paystack_webhook(
                db=mock_db, body=body, signature="valid_sig"
            )

        assert first_result is True
        assert wallet.balance == Decimal("5000.00")

        transaction.status = TransactionStatus.SUCCESS

        txn_result2 = Mock()
        txn_result2.scalar_one_or_none.return_value = transaction
        mock_db.execute.side_effect = [txn_result2]

        with patch(
            "src.services.webhook_service.verify_paystack_signature", return_value=True
        ):
            second_result = await webhook_service.process_paystack_webhook(
                db=mock_db, body=body, signature="valid_sig"
            )

        assert second_result is False
        assert wallet.balance == Decimal("5000.00")


class TestCompleteTransferFlow:
    """Test complete transfer flow with balance checks"""

    @pytest.fixture
    def wallet_service(self):
        return WalletService()

    @pytest.fixture
    def sender_user(self):
        user = Mock(spec=User)
        user.id = "sender123"
        user.email = "sender@example.com"
        return user

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock(spec=AsyncSession)
        return db

    @pytest.mark.asyncio
    async def test_complete_transfer_updates_both_wallets(
        self, wallet_service, sender_user, mock_db
    ):
        """
        Test complete transfer flow:
        1. Check sender balance
        2. Verify recipient exists
        3. Deduct from sender
        4. Add to recipient
        5. Create transaction record
        """
        sender_wallet = Mock(spec=Wallet)
        sender_wallet.id = "wallet1"
        sender_wallet.user_id = "sender123"
        sender_wallet.balance = Decimal("10000.00")

        recipient_wallet = Mock(spec=Wallet)
        recipient_wallet.id = "wallet2"
        recipient_wallet.user_id = "recipient456"
        recipient_wallet.wallet_number = "9876543210"
        recipient_wallet.balance = Decimal("5000.00")

        sender_result = Mock()
        sender_result.scalar_one_or_none.return_value = sender_wallet

        recipient_result = Mock()
        recipient_result.scalar_one_or_none.return_value = recipient_wallet

        mock_db.execute.side_effect = [sender_result, recipient_result]

        result = await wallet_service.transfer_funds(
            db=mock_db,
            sender=sender_user,
            recipient_wallet_number="9876543210",
            amount=Decimal("3000.00"),
        )

        assert result.status == "success"
        assert sender_wallet.balance == Decimal("7000.00")
        assert recipient_wallet.balance == Decimal("8000.00")
        assert mock_db.add.called

    @pytest.mark.asyncio
    async def test_transfer_atomicity_on_failure(
        self, wallet_service, sender_user, mock_db
    ):
        """
        Test that if transfer fails, no balances are changed
        """
        sender_wallet = Mock(spec=Wallet)
        sender_wallet.balance = Decimal("1000.00")

        sender_result = Mock()
        sender_result.scalar_one_or_none.return_value = sender_wallet

        mock_db.execute.return_value = sender_result

        original_balance = sender_wallet.balance

        try:
            await wallet_service.transfer_funds(
                db=mock_db,
                sender=sender_user,
                recipient_wallet_number="9876543210",
                amount=Decimal("5000.00"),
            )
        except ValueError:
            pass

        assert sender_wallet.balance == original_balance


class TestAPIKeyAccessControl:
    """Test API key permissions enforcement across services"""

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
    async def test_create_multiple_keys_with_different_permissions(
        self, api_key_service, mock_user, mock_db
    ):
        """
        Test creating multiple API keys with different permissions
        """
        count_result = Mock()
        count_result.scalar.return_value = 0
        mock_db.execute.return_value = count_result
        mock_db.flush = AsyncMock()

        deposit_key = await api_key_service.create_api_key(
            db=mock_db,
            user=mock_user,
            name="deposit-key",
            permissions=["deposit"],
            expiry="1D",
        )

        count_result.scalar.return_value = 1

        transfer_key = await api_key_service.create_api_key(
            db=mock_db,
            user=mock_user,
            name="transfer-key",
            permissions=["transfer"],
            expiry="1D",
        )

        count_result.scalar.return_value = 2

        read_key = await api_key_service.create_api_key(
            db=mock_db,
            user=mock_user,
            name="read-key",
            permissions=["read"],
            expiry="1D",
        )

        assert deposit_key.api_key != transfer_key.api_key != read_key.api_key

    @pytest.mark.asyncio
    async def test_api_key_lifecycle(self, api_key_service, mock_user, mock_db):
        """
        Test complete API key lifecycle:
        1. Create key
        2. Use key (expires)
        3. Rollover to new key
        4. Revoke key
        """
        count_result = Mock()
        count_result.scalar.return_value = 0
        mock_db.execute.return_value = count_result
        mock_db.flush = AsyncMock()

        created_key = await api_key_service.create_api_key(
            db=mock_db,
            user=mock_user,
            name="lifecycle-key",
            permissions=["deposit", "transfer"],
            expiry="1H",
        )

        assert created_key.api_key.startswith("sk_")

        expired_key = Mock(spec=APIKey)
        expired_key.id = "old_key_id"
        expired_key.name = "lifecycle-key"
        expired_key.permissions = ["deposit", "transfer"]
        expired_key.expires_at = datetime.now(timezone.utc) - timedelta(hours=2)
        expired_key.is_revoked = False

        key_result = Mock()
        key_result.scalar_one_or_none.return_value = expired_key

        count_result_rollover = Mock()
        count_result_rollover.scalar.return_value = 0

        mock_db.execute.side_effect = [key_result, count_result_rollover]

        rolled_key = await api_key_service.rollover_api_key(
            db=mock_db, user=mock_user, expired_key_id="old_key_id", new_expiry="1M"
        )

        assert rolled_key.api_key.startswith("sk_")
        assert expired_key.is_revoked is True

        new_key = Mock(spec=APIKey)
        new_key.is_revoked = False

        revoke_result = Mock()
        revoke_result.scalar_one_or_none.return_value = new_key
        mock_db.execute.side_effect = [revoke_result]

        async_context = AsyncMock()
        async_context.__aenter__ = AsyncMock(return_value=async_context)
        async_context.__aexit__ = AsyncMock(return_value=None)
        mock_db.begin.return_value = async_context

        revoked = await api_key_service.revoke_api_key(
            db=mock_db, user=mock_user, key_id="new_key_id"
        )

        assert revoked is True
        assert new_key.is_revoked is True


class TestUserOnboardingFlow:
    """Test complete user onboarding with Google OAuth"""

    @pytest.fixture
    def auth_service(self):
        service = AuthService()
        service.google_client_id = "test_client_id"
        service.google_client_secret = "test_client_secret"
        return service

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock(spec=AsyncSession)
        return db

    @pytest.mark.asyncio
    async def test_new_user_onboarding_creates_wallet(self, auth_service, mock_db):
        """
        Test that new user gets:
        1. User account created
        2. Wallet automatically created
        3. JWT token returned
        """
        user_result = Mock()
        user_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = user_result

        with patch.object(auth_service, "exchange_code_for_token") as mock_exchange:
            with patch.object(auth_service, "get_user_info") as mock_user_info:
                mock_exchange.return_value = {"access_token": "test_token"}
                mock_user_info.return_value = {
                    "email": "newuser@example.com",
                    "id": "google_new_123",
                    "name": "New User",
                    "picture": "https://example.com/pic.jpg",
                }

                token_response = await auth_service.handle_google_callback(
                    "auth_code", mock_db
                )

                assert token_response.token_type == "bearer"
                assert token_response.access_token is not None

                assert mock_db.add.call_count == 2
                assert mock_db.commit.called


class TestConcurrentOperations:
    """Test handling of concurrent operations"""

    @pytest.fixture
    def wallet_service(self):
        return WalletService()

    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = "user123"
        user.email = "test@example.com"
        return user

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock(spec=AsyncSession)
        return db

    @pytest.mark.asyncio
    async def test_multiple_transfers_from_same_wallet(
        self, wallet_service, mock_user, mock_db
    ):
        """
        Test that multiple transfers check balance correctly
        This simulates race condition scenarios
        """
        sender_wallet = Mock(spec=Wallet)
        sender_wallet.id = "wallet1"
        sender_wallet.user_id = "user123"
        sender_wallet.balance = Decimal("5000.00")

        recipient_wallet = Mock(spec=Wallet)
        recipient_wallet.id = "wallet2"
        recipient_wallet.wallet_number = "1234567890"
        recipient_wallet.balance = Decimal("0.00")

        sender_result = Mock()
        sender_result.scalar_one_or_none.return_value = sender_wallet

        recipient_result = Mock()
        recipient_result.scalar_one_or_none.return_value = recipient_wallet

        mock_db.execute.side_effect = [sender_result, recipient_result]

        result1 = await wallet_service.transfer_funds(
            db=mock_db,
            sender=mock_user,
            recipient_wallet_number="1234567890",
            amount=Decimal("3000.00"),
        )

        assert result1.status == "success"
        assert sender_wallet.balance == Decimal("2000.00")

        sender_result2 = Mock()
        sender_result2.scalar_one_or_none.return_value = sender_wallet
        mock_db.execute.side_effect = [sender_result2]

        with pytest.raises(ValueError, match="Insufficient balance"):
            await wallet_service.transfer_funds(
                db=mock_db,
                sender=mock_user,
                recipient_wallet_number="1234567890",
                amount=Decimal("3000.00"),
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
