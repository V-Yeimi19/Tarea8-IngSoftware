from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID
from shared.events.schemas import RewardProcessedEvent
from rewards_service.domain.entities import CustomerAccount, RewardTransaction


class IAccountRepository(ABC):
    @abstractmethod
    def get_by_card(self, card_number: str) -> Optional[CustomerAccount]: ...

    @abstractmethod
    def save_account(self, account: CustomerAccount) -> None: ...

    @abstractmethod
    def save_reward_transaction(self, reward_tx: RewardTransaction) -> None: ...

    @abstractmethod
    def transaction_exists(self, transaction_id: UUID) -> bool: ...


class IRewardEventPublisher(ABC):
    @abstractmethod
    def publish_reward_processed(self, event: RewardProcessedEvent) -> None: ...
