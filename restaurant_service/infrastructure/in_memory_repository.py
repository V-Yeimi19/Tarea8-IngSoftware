import threading
from typing import Optional
from uuid import UUID

from restaurant_service.domain.entities import MealTransaction
from restaurant_service.domain.ports import ITransactionRepository


class InMemoryTransactionRepository(ITransactionRepository):
    """Thread-safe in-memory implementation of ITransactionRepository backed by a dict."""

    def __init__(self) -> None:
        self._store: dict[UUID, MealTransaction] = {}
        self._lock = threading.Lock()

    def save(self, transaction: MealTransaction) -> None:
        """Persist a MealTransaction in memory, keyed by its transaction_id."""
        with self._lock:
            self._store[transaction.transaction_id] = transaction

    def exists(self, transaction_id: UUID) -> bool:
        """Return True if a transaction with the given UUID already exists in the store."""
        with self._lock:
            return transaction_id in self._store

    def get_by_id(self, transaction_id: UUID) -> Optional[MealTransaction]:
        """Return the MealTransaction for the given UUID, or None if not found."""
        with self._lock:
            return self._store.get(transaction_id)
