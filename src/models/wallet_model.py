"""
Wallet Model
"""

import random
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import relationship

from src.db.session import Base


def generate_wallet_number():
    """Generate a unique 13-digit wallet number"""
    return "".join([str(random.randint(0, 9)) for _ in range(13)])


class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False)
    wallet_number = Column(
        String(13),
        unique=True,
        nullable=False,
        index=True,
        default=generate_wallet_number,
    )
    balance = Column(Numeric(precision=15, scale=2), default=0.00, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="wallet")
