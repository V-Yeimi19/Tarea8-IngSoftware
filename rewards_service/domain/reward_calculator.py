import math
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


class InvalidAmountError(ValueError):
    pass


class AmountExceedsLimitError(ValueError):
    pass


@dataclass(frozen=True)
class RewardResult:
    points: int
    cashback: Decimal
    tier: str


class RewardCalculator:
    TIERS = [
        ("platinum", Decimal("300"), Decimal("2.0"), Decimal("0.05")),
        ("gold",     Decimal("150"), Decimal("1.5"), Decimal("0.04")),
        ("silver",   Decimal("50"),  Decimal("1.0"), Decimal("0.03")),
        ("standard", Decimal("0"),   Decimal("0.5"), Decimal("0.025")),
    ]
    MAX_AMOUNT = Decimal("10000")

    def calculate(self, amount: Decimal) -> RewardResult:
        if amount <= Decimal("0"):
            raise InvalidAmountError(f"Amount must be positive, got {amount}")
        if amount > self.MAX_AMOUNT:
            raise AmountExceedsLimitError(f"Amount {amount} exceeds limit of {self.MAX_AMOUNT}")

        tier_name, _, points_rate, cashback_rate = self._get_tier(amount)
        points = math.floor(float(amount * points_rate))
        cashback = (amount * cashback_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return RewardResult(points=points, cashback=cashback, tier=tier_name)

    def _get_tier(self, amount: Decimal):
        for tier in self.TIERS:
            if amount >= tier[1]:
                return tier
        return self.TIERS[-1]  # standard fallback
