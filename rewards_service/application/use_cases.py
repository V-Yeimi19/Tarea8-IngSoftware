from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from shared.events.schemas import MealTransactionEvent, RewardProcessedEvent
from rewards_service.domain.entities import CustomerAccount, RewardTransaction
from rewards_service.domain.ports import IAccountRepository, IRewardEventPublisher
from rewards_service.domain.reward_calculator import RewardCalculator


class ProcessMealEventUseCase:
    def __init__(
        self,
        calculator: RewardCalculator,
        account_repo: IAccountRepository,
        publisher: IRewardEventPublisher,
        default_email: str = "customer@rewards.com",
    ):
        self._calculator = calculator
        self._repo = account_repo
        self._publisher = publisher
        self._default_email = default_email

    def execute(self, event: MealTransactionEvent) -> Optional[RewardProcessedEvent]:
        # Idempotency guard
        if self._repo.transaction_exists(event.transaction_id):
            return None

        result = self._calculator.calculate(event.amount)

        account = self._repo.get_by_card(event.card_number)
        if account is None:
            # Usar email del evento si está disponible, sino usar default
            customer_email = event.customer_email or self._default_email
            account = CustomerAccount(
                card_number=event.card_number,
                email=customer_email,
            )
        elif event.customer_email and event.customer_email != account.email:
            # Actualizar email si viene en el evento y es diferente
            account.email = event.customer_email

        account.add_rewards(result.points, result.cashback, result.tier)
        self._repo.save_account(account)

        reward_tx = RewardTransaction(
            transaction_id=event.transaction_id,
            card_number=event.card_number,
            amount=event.amount,
            points_earned=result.points,
            cashback_amount=result.cashback,
            tier=result.tier,
        )
        self._repo.save_reward_transaction(reward_tx)

        processed_event = RewardProcessedEvent(
            event_id=uuid4(),
            transaction_id=event.transaction_id,
            card_number=event.card_number,
            customer_email=account.email,
            points_earned=result.points,
            cashback_amount=result.cashback,
            total_points_balance=account.points_balance,
            total_cashback_balance=account.cashback_balance,
            restaurant_code=event.restaurant_code,
            processed_at=datetime.now(timezone.utc),
        )
        self._publisher.publish_reward_processed(processed_event)
        return processed_event
