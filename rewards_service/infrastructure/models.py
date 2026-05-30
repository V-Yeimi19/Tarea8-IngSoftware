from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Column, Integer, String, Numeric, DateTime, UniqueConstraint
from sqlalchemy.dialects.sqlite import TEXT

from rewards_service.infrastructure.database import Base
from rewards_service.domain.entities import CustomerAccount, RewardTransaction


class CustomerAccountModel(Base):
    __tablename__ = "customer_accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    card_number = Column(String(64), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=False)
    points_balance = Column(Integer, nullable=False, default=0)
    cashback_balance = Column(Numeric(precision=12, scale=2), nullable=False, default=0)
    tier = Column(String(32), nullable=False, default="standard")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    def to_entity(self) -> CustomerAccount:
        return CustomerAccount(
            card_number=self.card_number,
            email=self.email,
            points_balance=self.points_balance,
            cashback_balance=Decimal(str(self.cashback_balance)),
            tier=self.tier,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_entity(cls, account: CustomerAccount) -> "CustomerAccountModel":
        return cls(
            card_number=account.card_number,
            email=account.email,
            points_balance=account.points_balance,
            cashback_balance=account.cashback_balance,
            tier=account.tier,
            created_at=account.created_at,
            updated_at=account.updated_at,
        )


class RewardTransactionModel(Base):
    __tablename__ = "reward_transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(String(36), nullable=False, unique=True, index=True)
    card_number = Column(String(64), nullable=False, index=True)
    amount = Column(Numeric(precision=12, scale=2), nullable=False)
    points_earned = Column(Integer, nullable=False)
    cashback_amount = Column(Numeric(precision=12, scale=2), nullable=False)
    tier = Column(String(32), nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    def to_entity(self) -> RewardTransaction:
        from uuid import UUID
        return RewardTransaction(
            id=self.id,
            transaction_id=UUID(self.transaction_id),
            card_number=self.card_number,
            amount=Decimal(str(self.amount)),
            points_earned=self.points_earned,
            cashback_amount=Decimal(str(self.cashback_amount)),
            tier=self.tier,
            processed_at=self.processed_at,
        )

    @classmethod
    def from_entity(cls, reward_tx: RewardTransaction) -> "RewardTransactionModel":
        return cls(
            transaction_id=str(reward_tx.transaction_id),
            card_number=reward_tx.card_number,
            amount=reward_tx.amount,
            points_earned=reward_tx.points_earned,
            cashback_amount=reward_tx.cashback_amount,
            tier=reward_tx.tier,
            processed_at=reward_tx.processed_at,
        )
