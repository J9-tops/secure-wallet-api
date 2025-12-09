import json
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.transaction_model import Transaction, TransactionStatus
from src.models.wallet_model import Wallet
from src.services.webhook_service import WebhookService


class TestWebhookService:
    """Test Paystack Webhook Processing - Objective: webhook handling"""

    @pytest.fixture
    def webhook_service(self):
        return WebhookService()

    @pytest.mark.asyncio
    async def test_process_webhook_success(self, webhook_service):
        """Test successful webhook processing credits wallet"""
        db = AsyncMock(spec=AsyncSession)

        transaction = Mock(spec=Transaction)
        transaction.user_id = "user123"
        transaction.amount = Decimal("5000.00")
        transaction.status = TransactionStatus.PENDING

        wallet = Mock(spec=Wallet)
        wallet.balance = Decimal("10000.00")

        txn_result = Mock()
        txn_result.scalar_one_or_none.return_value = transaction

        wallet_result = Mock()
        wallet_result.scalar_one.return_value = wallet

        db.execute.side_effect = [txn_result, wallet_result]

        webhook_data = {
            "event": "charge.success",
            "data": {
                "reference": "TXN_123",
                "amount": 500000,
                "status": "success",
            },
        }
        body = json.dumps(webhook_data).encode()

        with patch(
            "src.services.webhook_service.verify_paystack_signature", return_value=True
        ):
            result = await webhook_service.process_paystack_webhook(
                db=db, body=body, signature="valid_signature"
            )

            assert result is True
            assert transaction.status == TransactionStatus.SUCCESS
            assert wallet.balance == Decimal("15000.00")

    @pytest.mark.asyncio
    async def test_process_webhook_invalid_signature(self, webhook_service):
        """Test webhook rejects invalid signature"""
        db = AsyncMock(spec=AsyncSession)

        body = b'{"event": "charge.success"}'

        with patch(
            "src.services.webhook_service.verify_paystack_signature", return_value=False
        ):
            with pytest.raises(ValueError, match="Invalid Paystack signature"):
                await webhook_service.process_paystack_webhook(
                    db=db, body=body, signature="invalid_signature"
                )

    @pytest.mark.asyncio
    async def test_process_webhook_idempotency(self, webhook_service):
        """Test webhook is idempotent - no double credit"""
        db = AsyncMock(spec=AsyncSession)

        transaction = Mock(spec=Transaction)
        transaction.status = TransactionStatus.SUCCESS

        txn_result = Mock()
        txn_result.scalar_one_or_none.return_value = transaction
        db.execute.return_value = txn_result

        webhook_data = {
            "event": "charge.success",
            "data": {"reference": "TXN_123", "amount": 500000, "status": "success"},
        }
        body = json.dumps(webhook_data).encode()

        with patch(
            "src.services.webhook_service.verify_paystack_signature", return_value=True
        ):
            result = await webhook_service.process_paystack_webhook(
                db=db, body=body, signature="valid_signature"
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_process_webhook_amount_mismatch(self, webhook_service):
        """Test webhook fails on amount mismatch"""
        db = AsyncMock(spec=AsyncSession)

        transaction = Mock(spec=Transaction)
        transaction.amount = Decimal("5000.00")
        transaction.status = TransactionStatus.PENDING

        txn_result = Mock()
        txn_result.scalar_one_or_none.return_value = transaction
        db.execute.return_value = txn_result

        webhook_data = {
            "event": "charge.success",
            "data": {
                "reference": "TXN_123",
                "amount": 300000,
                "status": "success",
            },
        }
        body = json.dumps(webhook_data).encode()

        with patch(
            "src.services.webhook_service.verify_paystack_signature", return_value=True
        ):
            with pytest.raises(ValueError, match="Amount mismatch"):
                await webhook_service.process_paystack_webhook(
                    db=db, body=body, signature="valid_signature"
                )


class TestWebhookSecurity:
    """Test webhook security and signature verification"""

    @pytest.fixture
    def webhook_service(self):
        return WebhookService()

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock(spec=AsyncSession)
        return db

    @pytest.mark.asyncio
    async def test_webhook_missing_signature(self, webhook_service, mock_db):
        """Test webhook rejects request with no signature"""
        body = b'{"event": "charge.success"}'

        with pytest.raises(ValueError, match="Missing Paystack signature"):
            await webhook_service.process_paystack_webhook(
                db=mock_db, body=body, signature=""
            )

    @pytest.mark.asyncio
    async def test_webhook_none_signature(self, webhook_service, mock_db):
        """Test webhook rejects request with None signature"""
        body = b'{"event": "charge.success"}'

        with pytest.raises(ValueError, match="Missing Paystack signature"):
            await webhook_service.process_paystack_webhook(
                db=mock_db, body=body, signature=None
            )

    @pytest.mark.asyncio
    async def test_webhook_invalid_signature(self, webhook_service, mock_db):
        """Test webhook rejects invalid signature"""
        body = b'{"event": "charge.success", "data": {"reference": "TXN_123"}}'

        with patch(
            "src.services.webhook_service.verify_paystack_signature", return_value=False
        ):
            with pytest.raises(ValueError, match="Invalid Paystack signature"):
                await webhook_service.process_paystack_webhook(
                    db=mock_db, body=body, signature="invalid_signature_123"
                )

    @pytest.mark.asyncio
    async def test_webhook_malformed_json(self, webhook_service, mock_db):
        """Test webhook handles malformed JSON"""
        body = b'{"event": "charge.success", invalid json}'

        with patch(
            "src.services.webhook_service.verify_paystack_signature", return_value=True
        ):
            with pytest.raises(json.JSONDecodeError):
                await webhook_service.process_paystack_webhook(
                    db=mock_db, body=body, signature="valid_signature"
                )


class TestWebhookEventTypes:
    """Test different webhook event types"""

    @pytest.fixture
    def webhook_service(self):
        return WebhookService()

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock(spec=AsyncSession)
        return db

    @pytest.mark.asyncio
    async def test_webhook_charge_success_event(self, webhook_service, mock_db):
        """Test webhook processes charge.success event"""
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
            "data": {"reference": "TXN_123", "amount": 500000, "status": "success"},
        }
        body = json.dumps(webhook_data).encode()

        with patch(
            "src.services.webhook_service.verify_paystack_signature", return_value=True
        ):
            result = await webhook_service.process_paystack_webhook(
                db=mock_db, body=body, signature="valid_sig"
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_webhook_ignores_charge_failed(self, webhook_service, mock_db):
        """Test webhook ignores charge.failed event"""
        webhook_data = {
            "event": "charge.failed",
            "data": {"reference": "TXN_123", "amount": 500000, "status": "failed"},
        }
        body = json.dumps(webhook_data).encode()

        with patch(
            "src.services.webhook_service.verify_paystack_signature", return_value=True
        ):
            result = await webhook_service.process_paystack_webhook(
                db=mock_db, body=body, signature="valid_sig"
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_webhook_ignores_transfer_success(self, webhook_service, mock_db):
        """Test webhook ignores transfer.success event"""
        webhook_data = {
            "event": "transfer.success",
            "data": {"reference": "TXN_123", "amount": 500000},
        }
        body = json.dumps(webhook_data).encode()

        with patch(
            "src.services.webhook_service.verify_paystack_signature", return_value=True
        ):
            result = await webhook_service.process_paystack_webhook(
                db=mock_db, body=body, signature="valid_sig"
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_webhook_ignores_unknown_event(self, webhook_service, mock_db):
        """Test webhook ignores unknown event types"""
        webhook_data = {"event": "unknown.event", "data": {}}
        body = json.dumps(webhook_data).encode()

        with patch(
            "src.services.webhook_service.verify_paystack_signature", return_value=True
        ):
            result = await webhook_service.process_paystack_webhook(
                db=mock_db, body=body, signature="valid_sig"
            )

            assert result is False


class TestWebhookIdempotency:
    """Test webhook idempotency - no double crediting"""

    @pytest.fixture
    def webhook_service(self):
        return WebhookService()

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock(spec=AsyncSession)
        return db

    @pytest.mark.asyncio
    async def test_webhook_double_processing_prevented(self, webhook_service, mock_db):
        """Test same webhook processed twice doesn't double credit"""
        transaction = Mock(spec=Transaction)
        transaction.status = TransactionStatus.SUCCESS
        transaction.amount = Decimal("5000.00")

        txn_result = Mock()
        txn_result.scalar_one_or_none.return_value = transaction
        mock_db.execute.return_value = txn_result

        webhook_data = {
            "event": "charge.success",
            "data": {"reference": "TXN_123", "amount": 500000, "status": "success"},
        }
        body = json.dumps(webhook_data).encode()

        with patch(
            "src.services.webhook_service.verify_paystack_signature", return_value=True
        ):
            result = await webhook_service.process_paystack_webhook(
                db=mock_db, body=body, signature="valid_sig"
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_webhook_multiple_references_independent(
        self, webhook_service, mock_db
    ):
        """Test different transaction references are processed independently"""

        transaction1 = Mock(spec=Transaction)
        transaction1.status = TransactionStatus.PENDING
        transaction1.amount = Decimal("5000.00")
        transaction1.user_id = "user123"

        wallet = Mock(spec=Wallet)
        wallet.balance = Decimal("0.00")

        txn_result = Mock()
        txn_result.scalar_one_or_none.return_value = transaction1

        wallet_result = Mock()
        wallet_result.scalar_one.return_value = wallet

        mock_db.execute.side_effect = [txn_result, wallet_result]

        webhook_data = {
            "event": "charge.success",
            "data": {
                "reference": "TXN_UNIQUE_123",
                "amount": 500000,
                "status": "success",
            },
        }
        body = json.dumps(webhook_data).encode()

        with patch(
            "src.services.webhook_service.verify_paystack_signature", return_value=True
        ):
            result = await webhook_service.process_paystack_webhook(
                db=mock_db, body=body, signature="valid_sig"
            )

            assert result is True


class TestWebhookDataValidation:
    """Test webhook data validation"""

    @pytest.fixture
    def webhook_service(self):
        return WebhookService()

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock(spec=AsyncSession)
        return db

    @pytest.mark.asyncio
    async def test_webhook_missing_reference(self, webhook_service, mock_db):
        """Test webhook fails with missing reference"""
        webhook_data = {
            "event": "charge.success",
            "data": {"amount": 500000, "status": "success"},
        }
        body = json.dumps(webhook_data).encode()

        with patch(
            "src.services.webhook_service.verify_paystack_signature", return_value=True
        ):
            with pytest.raises(ValueError, match="Missing required webhook data"):
                await webhook_service.process_paystack_webhook(
                    db=mock_db, body=body, signature="valid_sig"
                )

    @pytest.mark.asyncio
    async def test_webhook_missing_amount(self, webhook_service, mock_db):
        """Test webhook fails with missing amount"""
        webhook_data = {
            "event": "charge.success",
            "data": {"reference": "TXN_123", "status": "success"},
        }
        body = json.dumps(webhook_data).encode()

        with patch(
            "src.services.webhook_service.verify_paystack_signature", return_value=True
        ):
            with pytest.raises(ValueError, match="Missing required webhook data"):
                await webhook_service.process_paystack_webhook(
                    db=mock_db, body=body, signature="valid_sig"
                )

    @pytest.mark.asyncio
    async def test_webhook_transaction_not_found(self, webhook_service, mock_db):
        """Test webhook fails when transaction doesn't exist"""
        txn_result = Mock()
        txn_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = txn_result

        webhook_data = {
            "event": "charge.success",
            "data": {
                "reference": "TXN_NONEXISTENT",
                "amount": 500000,
                "status": "success",
            },
        }
        body = json.dumps(webhook_data).encode()

        with patch(
            "src.services.webhook_service.verify_paystack_signature", return_value=True
        ):
            with pytest.raises(LookupError, match="Transaction not found"):
                await webhook_service.process_paystack_webhook(
                    db=mock_db, body=body, signature="valid_sig"
                )

    @pytest.mark.asyncio
    async def test_webhook_amount_mismatch(self, webhook_service, mock_db):
        """Test webhook fails when amount doesn't match"""
        transaction = Mock(spec=Transaction)
        transaction.amount = Decimal("5000.00")
        transaction.status = TransactionStatus.PENDING

        txn_result = Mock()
        txn_result.scalar_one_or_none.return_value = transaction
        mock_db.execute.return_value = txn_result

        webhook_data = {
            "event": "charge.success",
            "data": {
                "reference": "TXN_123",
                "amount": 300000,
                "status": "success",
            },
        }
        body = json.dumps(webhook_data).encode()

        with patch(
            "src.services.webhook_service.verify_paystack_signature", return_value=True
        ):
            with pytest.raises(ValueError, match="Amount mismatch"):
                await webhook_service.process_paystack_webhook(
                    db=mock_db, body=body, signature="valid_sig"
                )

    @pytest.mark.asyncio
    async def test_webhook_failed_status(self, webhook_service, mock_db):
        """Test webhook handles failed payment status"""
        transaction = Mock(spec=Transaction)
        transaction.amount = Decimal("5000.00")
        transaction.status = TransactionStatus.PENDING

        txn_result = Mock()
        txn_result.scalar_one_or_none.return_value = transaction
        mock_db.execute.return_value = txn_result

        webhook_data = {
            "event": "charge.success",
            "data": {
                "reference": "TXN_123",
                "amount": 500000,
                "status": "failed",
            },
        }
        body = json.dumps(webhook_data).encode()

        with patch(
            "src.services.webhook_service.verify_paystack_signature", return_value=True
        ):
            result = await webhook_service.process_paystack_webhook(
                db=mock_db, body=body, signature="valid_sig"
            )

            assert result is False
            assert transaction.status == TransactionStatus.FAILED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
