"""Unit tests for InMemoryTransactionRepository — save, exists and get_by_id."""
from decimal import Decimal

from restaurant_service.domain.entities import MealTransaction
from restaurant_service.infrastructure.in_memory_repository import InMemoryTransactionRepository


def _make_transaction() -> MealTransaction:
    return MealTransaction(
        card_number="4532-TEST-1234",
        restaurant_code="REST-001",
        amount=Decimal("100.00"),
    )


def test_save_and_get_by_id_returns_transaction():
    """A saved transaction can be retrieved by its id."""
    repo = InMemoryTransactionRepository()
    tx = _make_transaction()
    repo.save(tx)
    fetched = repo.get_by_id(tx.transaction_id)
    assert fetched is tx


def test_get_by_id_returns_none_for_unknown():
    """get_by_id returns None when the transaction does not exist."""
    repo = InMemoryTransactionRepository()
    tx = _make_transaction()
    assert repo.get_by_id(tx.transaction_id) is None


def test_exists_reflects_saved_state():
    """exists() is False before save and True after."""
    repo = InMemoryTransactionRepository()
    tx = _make_transaction()
    assert repo.exists(tx.transaction_id) is False
    repo.save(tx)
    assert repo.exists(tx.transaction_id) is True
