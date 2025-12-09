"""
Repository Pattern for Database Operations
Provides clean data access layer
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.base_repository import BaseRepository
from src.models.wallet_model import Wallet


class WalletRepository(BaseRepository[Wallet]):
    """Repository for Wallet operations"""

    async def get_by_user_id(self, user_id: str) -> Optional[Wallet]:
        """Get wallet by user ID"""
        result = await self.db.execute(select(Wallet).where(Wallet.user_id == user_id))
        return result.scalar_one_or_none()

    async def get_by_wallet_number(self, wallet_number: str) -> Optional[Wallet]:
        """Get wallet by wallet number"""
        result = await self.db.execute(
            select(Wallet).where(Wallet.wallet_number == wallet_number)
        )
        return result.scalar_one_or_none()


def get_wallet_repository(db: AsyncSession) -> WalletRepository:
    """Get WalletRepository instance"""
    return WalletRepository(Wallet, db)
