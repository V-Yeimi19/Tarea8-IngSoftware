import math
from decimal import Decimal

import pytest

from rewards_service.domain.reward_calculator import (
    RewardCalculator,
    RewardResult,
    InvalidAmountError,
    AmountExceedsLimitError,
)


@pytest.fixture
def calculator() -> RewardCalculator:
    return RewardCalculator()


class TestStandardTier:
    def test_standard_tier_calculation(self, calculator: RewardCalculator):
        """amount=45.00 falls below 50 threshold — standard tier."""
        result = calculator.calculate(Decimal("45.00"))

        assert result.tier == "standard"
        # points = floor(45.00 * 0.5) = 22
        assert result.points == 22
        # cashback = 45.00 * 0.025 = 1.125 → rounds to 1.13
        assert result.cashback == Decimal("1.13")


class TestSilverTier:
    def test_silver_tier_calculation(self, calculator: RewardCalculator):
        """amount=100.00 is in silver tier (50 <= amount < 150)."""
        result = calculator.calculate(Decimal("100.00"))

        assert result.tier == "silver"
        # points = floor(100.00 * 1.0) = 100
        assert result.points == 100
        # cashback = 100.00 * 0.03 = 3.00
        assert result.cashback == Decimal("3.00")


class TestGoldTier:
    def test_gold_tier_calculation(self, calculator: RewardCalculator):
        """amount=200.00 is in gold tier (150 <= amount < 300)."""
        result = calculator.calculate(Decimal("200.00"))

        assert result.tier == "gold"
        # points = floor(200.00 * 1.5) = 300
        assert result.points == 300
        # cashback = 200.00 * 0.04 = 8.00
        assert result.cashback == Decimal("8.00")


class TestPlatinumTier:
    def test_platinum_tier_calculation(self, calculator: RewardCalculator):
        """amount=500.00 is in platinum tier (amount >= 300)."""
        result = calculator.calculate(Decimal("500.00"))

        assert result.tier == "platinum"
        # points = floor(500.00 * 2.0) = 1000
        assert result.points == 1000
        # cashback = 500.00 * 0.05 = 25.00
        assert result.cashback == Decimal("25.00")


class TestPointsFloor:
    def test_points_are_floored_not_rounded(self, calculator: RewardCalculator):
        """Ensure floor() is used: 51.9 * 1.0 = 51.9 → floor = 51, not 52."""
        result = calculator.calculate(Decimal("51.9"))  # silver tier, rate 1.0

        assert result.tier == "silver"
        assert result.points == 51  # floor(51.9), NOT round(51.9) = 52


class TestCashbackRounding:
    def test_cashback_rounded_to_2_decimal_places(self, calculator: RewardCalculator):
        """Cashback is quantized to 2 decimal places using ROUND_HALF_UP."""
        # 45.00 * 0.025 = 1.125 → ROUND_HALF_UP → 1.13
        result = calculator.calculate(Decimal("45.00"))

        assert result.cashback == Decimal("1.13")
        assert result.cashback.as_tuple().exponent == -2


class TestTierNameInResult:
    def test_tier_name_in_result(self, calculator: RewardCalculator):
        """RewardResult carries the correct tier name string."""
        result = calculator.calculate(Decimal("300.00"))
        assert isinstance(result, RewardResult)
        assert result.tier == "platinum"

    def test_result_is_frozen_dataclass(self, calculator: RewardCalculator):
        """RewardResult is immutable (frozen=True)."""
        result = calculator.calculate(Decimal("100.00"))
        with pytest.raises((AttributeError, TypeError)):
            result.tier = "custom"  # type: ignore[misc]
