from abc import ABC, abstractmethod
from uuid import UUID
from typing import Optional

from shared.events.schemas import MealTransactionEvent
from restaurant_service.domain.entities import MealTransaction


class IEventPublisher(ABC):
    @abstractmethod
    def publish_meal_transaction(self, event: MealTransactionEvent) -> None: ...


class ITransactionRepository(ABC):
    @abstractmethod
    def save(self, transaction: MealTransaction) -> None: ...

    @abstractmethod
    def exists(self, transaction_id: UUID) -> bool: ...

    @abstractmethod
    def get_by_id(self, transaction_id: UUID) -> Optional[MealTransaction]: ...
