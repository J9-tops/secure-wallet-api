"""
Webhook Service - Paystack Webhook Processing
"""

import json
import logging
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.transaction_model import Transaction, TransactionStatus
from src.models.wallet_model import Wallet
from src.utils.security import verify_paystack_signature

logger = logging.getLogger(__name__)


class WebhookService:
    """Service for processing Paystack webhooks"""

    def process_paystack_webhook(
        self, db: Session, body: bytes, signature: str
    ) -> bool:
        if not signature:
            raise ValueError("Missing Paystack signature")

        if not verify_paystack_signature(body, signature):
            raise ValueError("Invalid Paystack signature")

        webhook_data = json.loads(body.decode("utf-8"))

        event = webhook_data.get("event")
        if event != "charge.success":
            logger.info(f"Ignoring webhook event: {event}")
            return False

        data = webhook_data.get("data", {})
        reference = data.get("reference")
        amount_in_kobo = data.get("amount")
        paystack_status = data.get("status")

        if not reference or not amount_in_kobo:
            raise ValueError("Missing required webhook data")

        processed = self._process_deposit(
            db=db,
            reference=reference,
            amount_in_kobo=amount_in_kobo,
            paystack_status=paystack_status,
        )

        return processed

    def _process_deposit(
        self,
        db: Session,
        reference: str,
        amount_in_kobo: int,
        paystack_status: str,
    ) -> bool:
        result = db.execute(
            select(Transaction).where(Transaction.reference == reference)
        )
        transaction = result.scalar_one_or_none()

        if not transaction:
            raise LookupError(f"Transaction not found: {reference}")

        if transaction.status == TransactionStatus.SUCCESS:
            logger.info(f"Transaction already processed: {reference}")
            return False

        amount = Decimal(amount_in_kobo) / 100

        if amount != transaction.amount:
            transaction.status = TransactionStatus.FAILED
            db.commit()
            raise ValueError(
                f"Amount mismatch for {reference}: expected {transaction.amount}, got {amount}"
            )

        if paystack_status == "success":
            transaction.status = TransactionStatus.SUCCESS

            wallet_result = db.execute(
                select(Wallet).where(Wallet.user_id == transaction.user_id)
            )
            wallet = wallet_result.scalar_one()

            wallet.balance += amount
            wallet.updated_at = datetime.now(timezone.utc)

            db.commit()

            logger.info(
                f"Successfully credited wallet for transaction {reference}: "
                f"User {transaction.user_id}, Amount {amount}"
            )
            return True
        else:
            transaction.status = TransactionStatus.FAILED
            db.commit()

            logger.warning(
                f"Transaction failed from Paystack: {reference}, Status: {paystack_status}"
            )
            return False


webhook_service = WebhookService()
