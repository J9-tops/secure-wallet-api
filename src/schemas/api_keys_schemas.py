"""
Pydantic Schemas for Request/Response Validation
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


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


class APIKeyInfo(BaseModel):
    """Information about an API key (without the actual key value)"""

    id: str
    name: str
    key_prefix: str = Field(..., description="First 20 characters of the key")
    permissions: List[str]
    is_active: bool
    is_revoked: bool
    expires_at: datetime
    last_used_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
