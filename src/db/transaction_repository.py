"""
Repository Pattern for Database Operations
Provides clean data access layer
"""

from typing import List, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.base_repository import BaseRepository
from src.models.transaction_model import Transaction, TransactionType


class TransactionRepository(BaseRepository[Transaction]):
    """Repository for Transaction operations"""

    async def get_by_reference(self, reference: str) -> Optional[Transaction]:
        """Get transaction by reference"""
        result = await self.db.execute(
            select(Transaction).where(Transaction.reference == reference)
        )
        return result.scalar_one_or_none()

    async def get_by_user_id(
        self, user_id: str, limit: int = 100, offset: int = 0
    ) -> List[Transaction]:
        """Get transactions by user ID"""
        result = await self.db.execute(
            select(Transaction)
            .where(Transaction.user_id == user_id)
            .order_by(Transaction.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    async def get_user_deposit_by_reference(
        self, reference: str, user_id: str
    ) -> Optional[Transaction]:
        """Get deposit transaction by reference and user"""
        result = await self.db.execute(
            select(Transaction).where(
                and_(
                    Transaction.reference == reference,
                    Transaction.user_id == user_id,
                    Transaction.type == TransactionType.DEPOSIT,
                )
            )
        )
        return result.scalar_one_or_none()


def get_transaction_repository(db: AsyncSession) -> TransactionRepository:
    """Get TransactionRepository instance"""
    return TransactionRepository(Transaction, db)
