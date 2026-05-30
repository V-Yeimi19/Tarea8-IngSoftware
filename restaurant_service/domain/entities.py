from dataclasses import dataclass, field
from decimal import Decimal
from datetime import datetime, timezone
from uuid import UUID, uuid4


class InvalidAmountError(ValueError):
    pass


class InvalidCardNumberError(ValueError):
    pass


@dataclass
class MealTransaction:
    card_number: str
    restaurant_code: str
    amount: Decimal
    transaction_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    currency: str = "PEN"

    def __post_init__(self):
        if self.amount <= Decimal("0"):
            raise InvalidAmountError(f"Amount must be positive, got {self.amount}")
        if self.amount > Decimal("10000"):
            raise InvalidAmountError(f"Amount exceeds maximum limit of 10000, got {self.amount}")
        if not self.card_number or not self.card_number.strip():
            raise InvalidCardNumberError("Card number cannot be empty")
        if not self.restaurant_code or not self.restaurant_code.strip():
            raise ValueError("Restaurant code cannot be empty")
