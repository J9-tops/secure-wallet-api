"""
Pydantic Schemas for Request/Response Validation
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class DepositRequest(BaseModel):
    amount: Decimal = Field(..., gt=0, decimal_places=2)


class DepositResponse(BaseModel):
    reference: str
    authorization_url: str


class TransferRequest(BaseModel):
    wallet_number: str = Field(..., min_length=13, max_length=13)
    amount: Decimal = Field(..., gt=0, decimal_places=2)


class TransferResponse(BaseModel):
    status: str
    message: str


class BalanceResponse(BaseModel):
    balance: Decimal


class TransactionResponse(BaseModel):
    type: str
    amount: Decimal
    status: str
    reference: Optional[str] = None
    recipient_wallet_number: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DepositStatusResponse(BaseModel):
    reference: str
    status: str
    amount: Decimal


class PaystackWebhookData(BaseModel):
    reference: str
    amount: int
    status: str
    paid_at: Optional[str] = None


class PaystackWebhook(BaseModel):
    event: str
    data: PaystackWebhookData
