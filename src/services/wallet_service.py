"""
Wallet Service - Business Logic for Wallet Operations
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import List

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.transaction_model import Transaction, TransactionStatus, TransactionType
from src.models.user_model import User
from src.models.wallet_model import Wallet
from src.schemas.wallet_schemas import (
    DepositResponse,
    DepositStatusResponse,
    TransferResponse,
)
from src.services.paystack_service import paystack_service
from src.utils.security import generate_transaction_reference


class WalletService:
    """Service for wallet operations"""

    async def get_or_create_wallet(self, db: AsyncSession, user: User) -> Wallet:
        """
        Get or create wallet for user

        Args:
            db: Database session
            user: User object

        Returns:
            Wallet object
        """
        result = await db.execute(select(Wallet).where(Wallet.user_id == user.id))
        wallet = result.scalar_one_or_none()

        if not wallet:
            wallet = Wallet(user_id=user.id)
            db.add(wallet)
            await db.flush()

        return wallet

    async def initiate_deposit(
        self, db: AsyncSession, user: User, amount: Decimal
    ) -> DepositResponse:
        """
        Initiate a Paystack deposit transaction

        Args:
            db: Database session
            user: User object
            amount: Deposit amount

        Returns:
            DepositResponse with reference and authorization URL

        Raises:
            ValueError: If amount is invalid
        """
        if amount <= 0:
            raise ValueError("Amount must be greater than zero")

        reference = generate_transaction_reference()

        transaction = Transaction(
            user_id=user.id,
            reference=reference,
            type=TransactionType.DEPOSIT,
            amount=amount,
            status=TransactionStatus.PENDING,
            paystack_reference=reference,
        )
        db.add(transaction)
        await db.flush()

        paystack_data = await paystack_service.initialize_transaction(
            email=user.email, amount=amount, reference=reference
        )

        transaction.authorization_url = paystack_data["authorization_url"]
        await db.commit()

        return DepositResponse(
            reference=reference, authorization_url=paystack_data["authorization_url"]
        )

    async def get_deposit_status(
        self, db: AsyncSession, reference: str, user: User
    ) -> DepositStatusResponse:
        """
        Get deposit transaction status (read-only)

        Args:
            db: Database session
            reference: Transaction reference
            user: User object

        Returns:
            DepositStatusResponse

        Raises:
            LookupError: If transaction not found
        """
        result = await db.execute(
            select(Transaction).where(
                and_(
                    Transaction.reference == reference,
                    Transaction.user_id == user.id,
                    Transaction.type == TransactionType.DEPOSIT,
                )
            )
        )
        transaction = result.scalar_one_or_none()

        if not transaction:
            raise LookupError(f"Transaction not found: {reference}")

        return DepositStatusResponse(
            reference=transaction.reference,
            status=transaction.status.value,
            amount=transaction.amount,
        )

    async def transfer_funds(
        self,
        db: AsyncSession,
        sender: User,
        recipient_wallet_number: str,
        amount: Decimal,
    ) -> TransferResponse:
        """
        Transfer funds between wallets (ATOMIC operation)

        Args:
            db: Database session
            sender: Sender user object
            recipient_wallet_number: Recipient wallet number
            amount: Transfer amount

        Returns:
            TransferResponse

        Raises:
            ValueError: If validation fails
            LookupError: If recipient not found
        """
        if amount <= 0:
            raise ValueError("Transfer amount must be greater than zero")

        sender_wallet_result = await db.execute(
            select(Wallet).where(Wallet.user_id == sender.id)
        )
        sender_wallet = sender_wallet_result.scalar_one_or_none()

        if not sender_wallet:
            raise ValueError("Sender wallet not found")

        if sender_wallet.balance < amount:
            raise ValueError("Insufficient balance")

        recipient_wallet_result = await db.execute(
            select(Wallet).where(Wallet.wallet_number == recipient_wallet_number)
        )
        recipient_wallet = recipient_wallet_result.scalar_one_or_none()

        if not recipient_wallet:
            raise LookupError("Recipient wallet not found")

        if sender_wallet.id == recipient_wallet.id:
            raise ValueError("Cannot transfer to your own wallet")

        reference = generate_transaction_reference()

        sender_wallet.balance -= amount
        sender_wallet.updated_at = datetime.now(timezone.utc)

        recipient_wallet.balance += amount
        recipient_wallet.updated_at = datetime.now(timezone.utc)

        transaction = Transaction(
            user_id=sender.id,
            reference=reference,
            type=TransactionType.TRANSFER,
            amount=amount,
            status=TransactionStatus.SUCCESS,
            recipient_wallet_number=recipient_wallet_number,
            recipient_user_id=recipient_wallet.user_id,
        )
        db.add(transaction)

        await db.commit()

        return TransferResponse(status="success", message="Transfer completed")

    async def get_balance(self, db: AsyncSession, user: User) -> Decimal:
        """
        Get wallet balance

        Args:
            db: Database session
            user: User object

        Returns:
            Balance as Decimal
        """
        wallet = await self.get_or_create_wallet(db, user)
        return wallet.balance

    async def get_transactions(self, db: AsyncSession, user: User) -> List[Transaction]:
        """
        Get user transaction history

        Args:
            db: Database session
            user: User object

        Returns:
            List of Transaction objects
        """
        result = await db.execute(
            select(Transaction)
            .where(Transaction.user_id == user.id)
            .order_by(Transaction.created_at.desc())
        )
        return result.scalars().all()


wallet_service = WalletService()
