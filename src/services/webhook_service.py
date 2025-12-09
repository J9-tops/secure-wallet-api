"""
Webhook Service - Paystack Webhook Processing
"""

import json
import logging
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.transaction_model import Transaction, TransactionStatus
from src.models.wallet_model import Wallet
from src.utils.security import verify_paystack_signature

logger = logging.getLogger(__name__)


class WebhookService:
    """Service for processing Paystack webhooks"""

    async def process_paystack_webhook(
        self, db: AsyncSession, body: bytes, signature: str
    ) -> bool:
        """
        Process Paystack webhook with signature verification
        This is the ONLY method that credits wallets

        Args:
            db: Database session
            body: Raw request body
            signature: Paystack signature header

        Returns:
            True if processed successfully

        Raises:
            ValueError: If signature is invalid or data is malformed
            LookupError: If transaction not found
        """
        # Verify signature
        if not signature:
            raise ValueError("Missing Paystack signature")

        if not verify_paystack_signature(body, signature):
            raise ValueError("Invalid Paystack signature")

        # Parse webhook data
        webhook_data = json.loads(body.decode("utf-8"))

        # Only process charge.success events
        event = webhook_data.get("event")
        if event != "charge.success":
            logger.info(f"Ignoring webhook event: {event}")
            return False

        # Extract data
        data = webhook_data.get("data", {})
        reference = data.get("reference")
        amount_in_kobo = data.get("amount")
        paystack_status = data.get("status")

        if not reference or not amount_in_kobo:
            raise ValueError("Missing required webhook data")

        # Process deposit
        processed = await self._process_deposit(
            db=db,
            reference=reference,
            amount_in_kobo=amount_in_kobo,
            paystack_status=paystack_status,
        )

        return processed

    async def _process_deposit(
        self,
        db: AsyncSession,
        reference: str,
        amount_in_kobo: int,
        paystack_status: str,
    ) -> bool:
        """
        Process deposit and credit wallet (ATOMIC operation)

        Args:
            db: Database session
            reference: Transaction reference
            amount_in_kobo: Amount in kobo (smallest currency unit)
            paystack_status: Paystack status

        Returns:
            True if processed, False if already processed (idempotent)

        Raises:
            LookupError: If transaction not found
            ValueError: If amount mismatch
        """
        # Get transaction
        result = await db.execute(
            select(Transaction).where(Transaction.reference == reference)
        )
        transaction = result.scalar_one_or_none()

        if not transaction:
            raise LookupError(f"Transaction not found: {reference}")

        # Idempotency check - if already processed, skip
        if transaction.status == TransactionStatus.SUCCESS:
            logger.info(f"Transaction already processed: {reference}")
            return False

        # Convert amount from kobo to naira
        amount = Decimal(amount_in_kobo) / 100

        # Verify amount matches
        if amount != transaction.amount:
            transaction.status = TransactionStatus.FAILED
            await db.commit()
            raise ValueError(
                f"Amount mismatch for {reference}: expected {transaction.amount}, got {amount}"
            )

        # Update transaction status based on Paystack status
        if paystack_status == "success":
            transaction.status = TransactionStatus.SUCCESS

            # Credit wallet - ATOMIC operation
            wallet_result = await db.execute(
                select(Wallet).where(Wallet.user_id == transaction.user_id)
            )
            wallet = wallet_result.scalar_one()

            wallet.balance += amount
            wallet.updated_at = datetime.utcnow()

            await db.commit()

            logger.info(
                f"Successfully credited wallet for transaction {reference}: "
                f"User {transaction.user_id}, Amount {amount}"
            )
            return True
        else:
            transaction.status = TransactionStatus.FAILED
            await db.commit()

            logger.warning(
                f"Transaction failed from Paystack: {reference}, Status: {paystack_status}"
            )
            return False


# Singleton instance
webhook_service = WebhookService()
