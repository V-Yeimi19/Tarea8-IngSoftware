from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from shared.events.schemas import MealTransactionEvent
from restaurant_service.domain.entities import MealTransaction
from restaurant_service.domain.ports import IEventPublisher, ITransactionRepository


@dataclass
class RegisterMealCommand:
    card_number: str
    restaurant_code: str
    amount: Decimal
    customer_email: str = ""


class DuplicateTransactionError(Exception):
    pass


class RegisterMealUseCase:
    def __init__(self, publisher: IEventPublisher, repository: ITransactionRepository):
        self._publisher = publisher
        self._repository = repository

    def execute(self, command: RegisterMealCommand) -> MealTransactionEvent:
        transaction = MealTransaction(
            card_number=command.card_number,
            restaurant_code=command.restaurant_code,
            amount=command.amount,
        )
        self._repository.save(transaction)
        event = MealTransactionEvent(
            transaction_id=transaction.transaction_id,
            card_number=transaction.card_number,
            restaurant_code=transaction.restaurant_code,
            amount=transaction.amount,
            timestamp=transaction.timestamp,
            currency=transaction.currency,
            customer_email=command.customer_email,
        )
        self._publisher.publish_meal_transaction(event)
        return event
