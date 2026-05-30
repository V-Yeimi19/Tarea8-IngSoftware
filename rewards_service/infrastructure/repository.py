from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from rewards_service.domain.entities import CustomerAccount, RewardTransaction
from rewards_service.domain.ports import IAccountRepository
from rewards_service.infrastructure.models import CustomerAccountModel, RewardTransactionModel


class SQLAlchemyAccountRepository(IAccountRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_card(self, card_number: str) -> Optional[CustomerAccount]:
        model = (
            self._session.query(CustomerAccountModel)
            .filter(CustomerAccountModel.card_number == card_number)
            .first()
        )
        if model is None:
            return None
        return model.to_entity()

    def save_account(self, account: CustomerAccount) -> None:
        existing = (
            self._session.query(CustomerAccountModel)
            .filter(CustomerAccountModel.card_number == account.card_number)
            .first()
        )
        if existing is not None:
            existing.email = account.email
            existing.points_balance = account.points_balance
            existing.cashback_balance = account.cashback_balance
            existing.tier = account.tier
            existing.updated_at = account.updated_at
        else:
            model = CustomerAccountModel.from_entity(account)
            self._session.add(model)
        self._session.commit()

    def save_reward_transaction(self, reward_tx: RewardTransaction) -> None:
        model = RewardTransactionModel.from_entity(reward_tx)
        self._session.add(model)
        self._session.commit()

    def transaction_exists(self, transaction_id: UUID) -> bool:
        count = (
            self._session.query(RewardTransactionModel)
            .filter(RewardTransactionModel.transaction_id == str(transaction_id))
            .count()
        )
        return count > 0
