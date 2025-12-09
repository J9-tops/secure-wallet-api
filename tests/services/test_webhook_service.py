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

        # Mock transaction
        transaction = Mock(spec=Transaction)
        transaction.user_id = "user123"
        transaction.amount = Decimal("5000.00")
        transaction.status = TransactionStatus.PENDING

        # Mock wallet
        wallet = Mock(spec=Wallet)
        wallet.balance = Decimal("10000.00")

        # Mock queries
        txn_result = Mock()
        txn_result.scalar_one_or_none.return_value = transaction

        wallet_result = Mock()
        wallet_result.scalar_one.return_value = wallet

        db.execute.side_effect = [txn_result, wallet_result]

        # Create webhook payload
        webhook_data = {
            "event": "charge.success",
            "data": {
                "reference": "TXN_123",
                "amount": 500000,  # 5000 naira in kobo
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

        # Mock already processed transaction
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

            # Should return False (already processed)
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
                "amount": 300000,  # Wrong amount
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
