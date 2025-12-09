"""
Transaction Model
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Numeric, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship

from src.db.session import Base


class TransactionType(str, enum.Enum):
    DEPOSIT = "deposit"
    TRANSFER = "transfer"


class TransactionStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    reference = Column(String, unique=True, nullable=False, index=True)
    type = Column(SQLEnum(TransactionType), nullable=False)
    amount = Column(Numeric(precision=15, scale=2), nullable=False)
    status = Column(
        SQLEnum(TransactionStatus), default=TransactionStatus.PENDING, nullable=False
    )

    # For transfers
    recipient_wallet_number = Column(String(13), nullable=True)
    recipient_user_id = Column(String, nullable=True)

    # Paystack specific
    paystack_reference = Column(String, nullable=True)
    authorization_url = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="transactions")
