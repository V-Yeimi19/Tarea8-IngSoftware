import pytest
from decimal import Decimal
from uuid import UUID
from datetime import datetime

from restaurant_service.domain.entities import (
    MealTransaction,
    InvalidAmountError,
    InvalidCardNumberError,
)


def test_valid_transaction_creates_successfully():
    """A MealTransaction with a positive amount, non-empty card number and restaurant code
    should be created without raising any exception."""
    tx = MealTransaction(
        card_number="1234-5678-9012",
        restaurant_code="REST-100",
        amount=Decimal("50.00"),
    )
    assert tx.card_number == "1234-5678-9012"
    assert tx.restaurant_code == "REST-100"
    assert tx.amount == Decimal("50.00")


def test_negative_amount_raises_invalid_amount_error():
    """Constructing a MealTransaction with a negative amount must raise InvalidAmountError."""
    with pytest.raises(InvalidAmountError):
        MealTransaction(
            card_number="1234-5678",
            restaurant_code="REST-001",
            amount=Decimal("-10.00"),
        )


def test_zero_amount_raises_invalid_amount_error():
    """Constructing a MealTransaction with amount == 0 must raise InvalidAmountError
    because zero is not a positive value."""
    with pytest.raises(InvalidAmountError):
        MealTransaction(
            card_number="1234-5678",
            restaurant_code="REST-001",
            amount=Decimal("0"),
        )


def test_empty_card_number_raises_error():
    """An empty string as card_number must raise InvalidCardNumberError."""
    with pytest.raises(InvalidCardNumberError):
        MealTransaction(
            card_number="",
            restaurant_code="REST-001",
            amount=Decimal("20.00"),
        )


def test_transaction_id_auto_generated():
    """transaction_id should be automatically assigned a valid UUID when not provided."""
    tx = MealTransaction(
        card_number="CARD-001",
        restaurant_code="REST-001",
        amount=Decimal("30.00"),
    )
    assert isinstance(tx.transaction_id, UUID)


def test_timestamp_auto_generated():
    """timestamp should be automatically set to a timezone-aware datetime when not provided."""
    tx = MealTransaction(
        card_number="CARD-001",
        restaurant_code="REST-001",
        amount=Decimal("30.00"),
    )
    assert isinstance(tx.timestamp, datetime)
    assert tx.timestamp.tzinfo is not None


def test_currency_defaults_to_pen():
    """currency field should default to 'PEN' when not explicitly provided."""
    tx = MealTransaction(
        card_number="CARD-001",
        restaurant_code="REST-001",
        amount=Decimal("30.00"),
    )
    assert tx.currency == "PEN"


def test_valid_decimal_amount():
    """A MealTransaction should accept Decimal amounts with fractional parts correctly."""
    tx = MealTransaction(
        card_number="CARD-001",
        restaurant_code="REST-001",
        amount=Decimal("99.99"),
    )
    assert tx.amount == Decimal("99.99")
