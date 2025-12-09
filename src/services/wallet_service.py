"""
Wallet Service - Business Logic for Wallet Operations
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import List

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

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

    def get_or_create_wallet(self, db: Session, user: User) -> Wallet:
        result = db.execute(select(Wallet).where(Wallet.user_id == user.id))
        wallet = result.scalar_one_or_none()

        if not wallet:
            wallet = Wallet(user_id=user.id)
            db.add(wallet)
            db.flush()

        return wallet

    def initiate_deposit(
        self, db: Session, user: User, amount: Decimal
    ) -> DepositResponse:
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
        db.flush()

        paystack_data = paystack_service.initialize_transaction(
            email=user.email, amount=amount, reference=reference
        )

        transaction.authorization_url = paystack_data["authorization_url"]
        db.commit()

        return DepositResponse(
            reference=reference, authorization_url=paystack_data["authorization_url"]
        )

    def get_deposit_status(
        self, db: Session, reference: str, user: User
    ) -> DepositStatusResponse:
        result = db.execute(
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

    def transfer_funds(
        self,
        db: Session,
        sender: User,
        recipient_wallet_number: str,
        amount: Decimal,
    ) -> TransferResponse:
        if amount <= 0:
            raise ValueError("Transfer amount must be greater than zero")

        sender_wallet_result = db.execute(
            select(Wallet).where(Wallet.user_id == sender.id)
        )
        sender_wallet = sender_wallet_result.scalar_one_or_none()

        if not sender_wallet:
            raise ValueError("Sender wallet not found")

        if sender_wallet.balance < amount:
            raise ValueError("Insufficient balance")

        recipient_wallet_result = db.execute(
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

        db.commit()

        return TransferResponse(status="success", message="Transfer completed")

    def get_balance(self, db: Session, user: User) -> Decimal:
        wallet = self.get_or_create_wallet(db, user)
        return wallet.balance

    def get_transactions(self, db: Session, user: User) -> List[Transaction]:
        result = db.execute(
            select(Transaction)
            .where(Transaction.user_id == user.id)
            .order_by(Transaction.created_at.desc())
        )
        return result.scalars().all()


wallet_service = WalletService()
