"""
Integration tests for SQLAlchemyAccountRepository using an in-memory SQLite database.
"""
from decimal import Decimal
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from rewards_service.infrastructure.database import Base
from rewards_service.infrastructure.models import CustomerAccountModel, RewardTransactionModel  # noqa: F401
from rewards_service.infrastructure.repository import SQLAlchemyAccountRepository
from rewards_service.domain.entities import CustomerAccount, RewardTransaction


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def engine():
    """In-memory SQLite engine, fresh for each test function."""
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)
    eng.dispose()


@pytest.fixture(scope="function")
def session(engine):
    SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    sess = SessionFactory()
    yield sess
    sess.close()


@pytest.fixture(scope="function")
def repo(session) -> SQLAlchemyAccountRepository:
    return SQLAlchemyAccountRepository(session)


def make_account(card_number: str = "TEST-CARD-001", email: str = "user@test.com") -> CustomerAccount:
    return CustomerAccount(card_number=card_number, email=email)


def make_reward_tx(card_number: str = "TEST-CARD-001") -> RewardTransaction:
    return RewardTransaction(
        transaction_id=uuid4(),
        card_number=card_number,
        amount=Decimal("100.00"),
        points_earned=100,
        cashback_amount=Decimal("3.00"),
        tier="silver",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSaveAndGetAccount:
    def test_save_and_get_account_by_card(self, repo):
        account = make_account(card_number="CARD-SAVE-001")
        repo.save_account(account)

        retrieved = repo.get_by_card("CARD-SAVE-001")

        assert retrieved is not None
        assert retrieved.card_number == "CARD-SAVE-001"
        assert retrieved.email == "user@test.com"
        assert retrieved.points_balance == 0
        assert retrieved.cashback_balance == Decimal("0.00")
        assert retrieved.tier == "standard"

    def test_get_by_card_returns_none_for_unknown(self, repo):
        result = repo.get_by_card("DOES-NOT-EXIST")
        assert result is None


class TestTransactionExists:
    def test_transaction_exists_returns_false_for_unknown(self, repo):
        unknown_id = uuid4()
        assert repo.transaction_exists(unknown_id) is False

    def test_transaction_exists_returns_true_after_save(self, repo):
        tx = make_reward_tx()
        repo.save_reward_transaction(tx)

        assert repo.transaction_exists(tx.transaction_id) is True

    def test_transaction_exists_does_not_collide_across_ids(self, repo):
        tx1 = make_reward_tx()
        tx2 = make_reward_tx()
        repo.save_reward_transaction(tx1)

        assert repo.transaction_exists(tx1.transaction_id) is True
        assert repo.transaction_exists(tx2.transaction_id) is False


class TestUpdateExistingAccount:
    def test_save_account_updates_existing(self, repo):
        account = make_account(card_number="CARD-UPDATE-001")
        repo.save_account(account)

        # Modify and save again
        account.add_rewards(points=150, cashback=Decimal("4.50"), tier="gold")
        repo.save_account(account)

        updated = repo.get_by_card("CARD-UPDATE-001")
        assert updated is not None
        assert updated.points_balance == 150
        assert updated.cashback_balance == Decimal("4.50")
        assert updated.tier == "gold"

    def test_save_account_multiple_updates_accumulate(self, repo):
        account = make_account(card_number="CARD-ACCUM-001")
        repo.save_account(account)

        account.add_rewards(points=100, cashback=Decimal("3.00"), tier="silver")
        repo.save_account(account)

        account.add_rewards(points=200, cashback=Decimal("8.00"), tier="gold")
        repo.save_account(account)

        final = repo.get_by_card("CARD-ACCUM-001")
        assert final is not None
        assert final.points_balance == 300
        assert final.cashback_balance == Decimal("11.00")
        assert final.tier == "gold"


class TestRewardTransactionPersisted:
    def test_reward_transaction_persisted(self, repo, session):
        tx = make_reward_tx(card_number="CARD-TX-001")
        repo.save_reward_transaction(tx)

        # Query directly to verify persistence
        model = (
            session.query(RewardTransactionModel)
            .filter(RewardTransactionModel.transaction_id == str(tx.transaction_id))
            .first()
        )
        assert model is not None
        assert model.card_number == "CARD-TX-001"
        assert model.points_earned == 100
        assert Decimal(str(model.cashback_amount)) == Decimal("3.00")
        assert model.tier == "silver"

    def test_reward_transaction_entity_round_trip(self, repo, session):
        tx = make_reward_tx()
        repo.save_reward_transaction(tx)

        model = (
            session.query(RewardTransactionModel)
            .filter(RewardTransactionModel.transaction_id == str(tx.transaction_id))
            .first()
        )
        entity = model.to_entity()
        assert entity.transaction_id == tx.transaction_id
        assert entity.amount == tx.amount
        assert entity.points_earned == tx.points_earned
