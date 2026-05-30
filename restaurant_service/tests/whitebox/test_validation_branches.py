"""
White-box tests for MealTransaction.__post_init__ validation branches.

Each test targets a specific conditional branch in the entity to ensure
100% branch coverage of the validation logic.
"""
import pytest
from decimal import Decimal

from restaurant_service.domain.entities import (
    MealTransaction,
    InvalidAmountError,
    InvalidCardNumberError,
)


# ---------------------------------------------------------------------------
# Amount boundary — lower bound
# ---------------------------------------------------------------------------

def test_amount_zero_raises_invalid_amount_error():
    """Branch: amount <= 0 (exactly 0) — must raise InvalidAmountError."""
    with pytest.raises(InvalidAmountError, match="must be positive"):
        MealTransaction(
            card_number="CARD-001",
            restaurant_code="REST-001",
            amount=Decimal("0"),
        )


def test_amount_negative_raises_invalid_amount_error():
    """Branch: amount <= 0 (negative value -1) — must raise InvalidAmountError."""
    with pytest.raises(InvalidAmountError, match="must be positive"):
        MealTransaction(
            card_number="CARD-001",
            restaurant_code="REST-001",
            amount=Decimal("-1"),
        )


def test_amount_minimum_positive_succeeds():
    """Branch: amount > 0 and amount <= 10000 (0.01, minimum valid value) — must succeed."""
    tx = MealTransaction(
        card_number="CARD-001",
        restaurant_code="REST-001",
        amount=Decimal("0.01"),
    )
    assert tx.amount == Decimal("0.01")


# ---------------------------------------------------------------------------
# Amount boundary — upper bound
# ---------------------------------------------------------------------------

def test_amount_exceeds_maximum_raises_invalid_amount_error():
    """Branch: amount > 10000 (10001) — must raise InvalidAmountError."""
    with pytest.raises(InvalidAmountError, match="exceeds maximum limit"):
        MealTransaction(
            card_number="CARD-001",
            restaurant_code="REST-001",
            amount=Decimal("10001"),
        )


def test_amount_at_maximum_limit_succeeds():
    """Branch: amount == 10000 (at upper limit) — must succeed without raising."""
    tx = MealTransaction(
        card_number="CARD-001",
        restaurant_code="REST-001",
        amount=Decimal("10000"),
    )
    assert tx.amount == Decimal("10000")


# ---------------------------------------------------------------------------
# Card number validation branches
# ---------------------------------------------------------------------------

def test_empty_card_number_raises_invalid_card_number_error():
    """Branch: card_number is an empty string — must raise InvalidCardNumberError."""
    with pytest.raises(InvalidCardNumberError, match="cannot be empty"):
        MealTransaction(
            card_number="",
            restaurant_code="REST-001",
            amount=Decimal("50.00"),
        )


def test_whitespace_only_card_number_raises_invalid_card_number_error():
    """Branch: card_number contains only spaces — strip() makes it falsy, must raise InvalidCardNumberError."""
    with pytest.raises(InvalidCardNumberError, match="cannot be empty"):
        MealTransaction(
            card_number="   ",
            restaurant_code="REST-001",
            amount=Decimal("50.00"),
        )


# ---------------------------------------------------------------------------
# Restaurant code validation branch
# ---------------------------------------------------------------------------

def test_empty_restaurant_code_raises_value_error():
    """Branch: restaurant_code is an empty string — must raise ValueError."""
    with pytest.raises(ValueError, match="Restaurant code cannot be empty"):
        MealTransaction(
            card_number="CARD-001",
            restaurant_code="",
            amount=Decimal("50.00"),
        )


# ---------------------------------------------------------------------------
# Valid transaction at each amount boundary (both branches passing)
# ---------------------------------------------------------------------------

def test_valid_transaction_at_lower_boundary():
    """Branch: all validations pass with amount at exact lower valid boundary (0.01)."""
    tx = MealTransaction(
        card_number="CARD-VALID",
        restaurant_code="REST-VALID",
        amount=Decimal("0.01"),
    )
    assert tx.card_number == "CARD-VALID"
    assert tx.restaurant_code == "REST-VALID"
    assert tx.amount == Decimal("0.01")


def test_valid_transaction_at_upper_boundary():
    """Branch: all validations pass with amount at exact upper valid boundary (10000)."""
    tx = MealTransaction(
        card_number="CARD-VALID",
        restaurant_code="REST-VALID",
        amount=Decimal("10000"),
    )
    assert tx.amount == Decimal("10000")


def test_valid_transaction_midrange():
    """Branch: all validations pass with a normal mid-range amount (500)."""
    tx = MealTransaction(
        card_number="CARD-VALID",
        restaurant_code="REST-VALID",
        amount=Decimal("500.00"),
    )
    assert tx.amount == Decimal("500.00")
