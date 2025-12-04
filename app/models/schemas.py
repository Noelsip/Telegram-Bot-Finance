"""
================================================================================
FILE: app/models/schemas.py
DESKRIPSI: Pydantic Schemas untuk validasi data
ASSIGNEE: @Backend
PRIORITY: MEDIUM
SPRINT: 1
================================================================================
"""

from datetime import datetime
from typing import Optional, Dict, Any

from pydantic import BaseModel, field_validator, Field
from .enums import IntentType, InputSource

class LLMOutputSchema(BaseModel):
    intent: IntentType
    amount: int = Field(..., gt=0)
    currency: str = "IDR"
    date: Optional[str] = None  # ISO date string (YYYY-MM-DD)
    category: str
    note: str
    confidence: float = Field(..., ge=0.0, le=1.0)

    @field_validator("date")
    def validate_date(cls, v):
        if v is None:
            return v
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("date must be in ISO format YYYY-MM-DD")
        return v

class TransactionCreateSchema(BaseModel):
    user_id: int
    intent: IntentType
    amount: int = Field(..., gt=0)
    currency: str = "IDR"
    tx_date: Optional[datetime] = None
    category: str
    note: Optional[str] = None
    needs_review: bool = False
    llm_response_id: Optional[int] = None
    receipt_id: Optional[int] = None
    extra: Optional[Dict[str, Any]] = None

class TransactionResponseSchema(TransactionCreateSchema):
    id: int
    created_at: datetime

class WebhookPayloadSchema(BaseModel):
    source: InputSource
    raw_message: str
    timestamp: Optional[datetime] = None
