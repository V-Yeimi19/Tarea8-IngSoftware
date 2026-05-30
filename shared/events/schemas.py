import json
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class MealTransactionEvent(BaseModel):
    model_config = ConfigDict(json_encoders={Decimal: str, UUID: str})

    transaction_id: UUID
    card_number: str
    restaurant_code: str
    amount: Decimal
    timestamp: datetime
    currency: str = "PEN"
    customer_email: str = ""  # Email del cliente para notificaciones

    @classmethod
    def from_json(cls, data: str | bytes | dict) -> "MealTransactionEvent":
        if isinstance(data, (str, bytes)):
            return cls.model_validate_json(data)
        return cls.model_validate(data)


class RewardProcessedEvent(BaseModel):
    model_config = ConfigDict(json_encoders={Decimal: str, UUID: str})

    event_id: UUID
    transaction_id: UUID
    card_number: str
    customer_email: EmailStr
    points_earned: int
    cashback_amount: Decimal
    total_points_balance: int
    total_cashback_balance: Decimal
    restaurant_code: str
    processed_at: datetime

    @classmethod
    def from_json(cls, data: str | bytes | dict) -> "RewardProcessedEvent":
        if isinstance(data, (str, bytes)):
            return cls.model_validate_json(data)
        return cls.model_validate(data)


class DLQEvent(BaseModel):
    model_config = ConfigDict(json_encoders={Decimal: str, UUID: str})

    original_topic: str
    original_message: dict
    error: str
    retry_count: int
    failed_at: datetime

    @classmethod
    def from_json(cls, data: str | bytes | dict) -> "DLQEvent":
        if isinstance(data, (str, bytes)):
            return cls.model_validate_json(data)
        return cls.model_validate(data)
