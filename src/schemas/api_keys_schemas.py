"""
Pydantic Schemas for Request/Response Validation
"""

from datetime import datetime
from typing import List

from pydantic import BaseModel, Field, field_validator


class APIKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    permissions: List[str] = Field(..., min_length=1)
    expiry: str = Field(..., pattern="^(1H|1D|1M|1Y)$")

    @field_validator("permissions")
    def validate_permissions(cls, v):
        valid_permissions = {"deposit", "transfer", "read"}
        for perm in v:
            if perm not in valid_permissions:
                raise ValueError(
                    f"Invalid permission: {perm}. Must be one of {valid_permissions}"
                )
        return v


class APIKeyResponse(BaseModel):
    api_key: str
    expires_at: datetime


class APIKeyRollover(BaseModel):
    expired_key_id: str
    expiry: str = Field(..., pattern="^(1H|1D|1M|1Y)$")
