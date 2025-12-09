"""
Wallet Model
"""

import random
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import relationship

from src.db.session import Base


def generate_wallet_number():
    """Generate a unique 13-digit wallet number"""
    prefix = "34"
    timestamp = datetime.now().strftime("%y%m%d%H%M")
    suffix = str(random.randint(100, 999))
    return prefix + timestamp + suffix


class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False)
    wallet_number = Column(
        String(15),
        unique=True,
        nullable=False,
        index=True,
        default=generate_wallet_number,
    )
    balance = Column(Numeric(precision=15, scale=2), default=0.00, nullable=False)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
    )

    user = relationship("User", back_populates="wallet")
