from dataclasses import dataclass, field
from decimal import Decimal
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass
class CustomerAccount:
    card_number: str
    email: str
    points_balance: int = 0
    cashback_balance: Decimal = field(default_factory=lambda: Decimal("0.00"))
    tier: str = "standard"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def add_rewards(self, points: int, cashback: Decimal, tier: str) -> None:
        self.points_balance += points
        self.cashback_balance += cashback
        self.tier = tier
        self.updated_at = datetime.now(timezone.utc)


@dataclass
class RewardTransaction:
    transaction_id: UUID
    card_number: str
    amount: Decimal
    points_earned: int
    cashback_amount: Decimal
    tier: str
    id: int = field(default=0)
    processed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
