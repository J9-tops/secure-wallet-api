"""
Repository Pattern for Database Operations
Provides clean data access layer
"""

from typing import Generic, List, Optional, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Base repository with common CRUD operations"""

    def __init__(self, model: Type[T], db: AsyncSession):
        self.model = model
        self.db = db

    async def get_by_id(self, id: str) -> Optional[T]:
        """Get record by ID"""
        result = await self.db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """Get all records with pagination"""
        result = await self.db.execute(select(self.model).limit(limit).offset(offset))
        return result.scalars().all()

    async def create(self, **kwargs) -> T:
        """Create new record"""
        instance = self.model(**kwargs)
        self.db.add(instance)
        await self.db.flush()
        return instance

    async def update(self, instance: T, **kwargs) -> T:
        """Update existing record"""
        for key, value in kwargs.items():
            setattr(instance, key, value)
        await self.db.flush()
        return instance

    async def delete(self, instance: T) -> None:
        """Delete record"""
        await self.db.delete(instance)
        await self.db.flush()
