"""
White-box branch coverage tests for RewardCalculator.

Decision points covered:
  1. amount <= 0  → InvalidAmountError
  2. amount > MAX_AMOUNT → AmountExceedsLimitError
  3. Tier boundaries: standard / silver / gold / platinum
  4. Floor vs round for points
  5. ROUND_HALF_UP for cashback
"""
import math
from decimal import Decimal

import pytest

from rewards_service.domain.reward_calculator import (
    AmountExceedsLimitError,
    InvalidAmountError,
    RewardCalculator,
)


@pytest.fixture
def calc() -> RewardCalculator:
    return RewardCalculator()


# ---------------------------------------------------------------------------
# Guard clauses
# ---------------------------------------------------------------------------

class TestAmountGuards:
    def test_zero_amount_raises_invalid_amount_error(self, calc):
        with pytest.raises(InvalidAmountError):
            calc.calculate(Decimal("0"))

    def test_negative_amount_raises_invalid_amount_error(self, calc):
        with pytest.raises(InvalidAmountError):
            calc.calculate(Decimal("-1.00"))

    def test_amount_exceeds_10000_raises_limit_error(self, calc):
        with pytest.raises(AmountExceedsLimitError):
            calc.calculate(Decimal("10000.01"))

    def test_exactly_10000_is_valid(self, calc):
        """Boundary: 10000 is exactly at the limit, must NOT raise."""
        result = calc.calculate(Decimal("10000"))
        assert result.tier == "platinum"
        assert result.points == math.floor(float(Decimal("10000") * Decimal("2.0")))


# ---------------------------------------------------------------------------
# Tier boundaries
# ---------------------------------------------------------------------------

class TestTierBoundaries:
    def test_boundary_at_50_is_silver_not_standard(self, calc):
        """50 is the exact lower boundary for silver."""
        result = calc.calculate(Decimal("50"))
        assert result.tier == "silver"

    def test_boundary_at_149_99_is_silver(self, calc):
        """149.99 is just below gold — should be silver."""
        result = calc.calculate(Decimal("149.99"))
        assert result.tier == "silver"

    def test_boundary_at_150_is_gold(self, calc):
        """150 is the exact lower boundary for gold."""
        result = calc.calculate(Decimal("150"))
        assert result.tier == "gold"

    def test_boundary_at_299_99_is_gold(self, calc):
        """299.99 is just below platinum — should be gold."""
        result = calc.calculate(Decimal("299.99"))
        assert result.tier == "gold"

    def test_boundary_at_300_is_platinum(self, calc):
        """300 is the exact lower boundary for platinum."""
        result = calc.calculate(Decimal("300"))
        assert result.tier == "platinum"

    def test_very_small_amount_standard_tier(self, calc):
        """0.01 is the minimum positive amount, falls to standard tier."""
        result = calc.calculate(Decimal("0.01"))
        assert result.tier == "standard"
        # points = floor(0.01 * 0.5) = floor(0.005) = 0
        assert result.points == 0


# ---------------------------------------------------------------------------
# Points floor behavior
# ---------------------------------------------------------------------------

class TestPointsFloorBehavior:
    def test_points_calculation_floor_behavior(self, calc):
        """amount=51.1, silver rate=1.0 → floor(51.1 * 1.0) = 51 (not 52)."""
        result = calc.calculate(Decimal("51.1"))
        assert result.tier == "silver"
        assert result.points == 51

    def test_points_floor_with_gold_fractional(self, calc):
        """amount=151.7, gold rate=1.5 → floor(151.7 * 1.5) = floor(227.55) = 227."""
        result = calc.calculate(Decimal("151.7"))
        assert result.tier == "gold"
        assert result.points == 227

    def test_points_floor_with_platinum_fractional(self, calc):
        """amount=301.3, platinum rate=2.0 → floor(301.3 * 2.0) = floor(602.6) = 602."""
        result = calc.calculate(Decimal("301.3"))
        assert result.tier == "platinum"
        assert result.points == 602


# ---------------------------------------------------------------------------
# Cashback rounding (ROUND_HALF_UP)
# ---------------------------------------------------------------------------

class TestCashbackRounding:
    def test_cashback_rounding(self, calc):
        """45.00 * 0.025 = 1.125 → ROUND_HALF_UP gives 1.13 (not 1.12)."""
        result = calc.calculate(Decimal("45.00"))
        assert result.cashback == Decimal("1.13")

    def test_cashback_exactly_2_decimals(self, calc):
        """100.00 * 0.03 = 3.00 — already 2 decimals, no rounding needed."""
        result = calc.calculate(Decimal("100.00"))
        assert result.cashback == Decimal("3.00")
        # Verify it's stored as proper 2-decimal Decimal
        assert result.cashback.as_tuple().exponent == -2

    def test_cashback_standard_rounding_down(self, calc):
        """10.00 * 0.025 = 0.25 — no rounding needed."""
        result = calc.calculate(Decimal("10.00"))
        assert result.tier == "standard"
        assert result.cashback == Decimal("0.25")
