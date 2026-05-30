from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import MagicMock, call
from uuid import uuid4

import pytest

from rewards_service.application.use_cases import ProcessMealEventUseCase
from rewards_service.domain.entities import CustomerAccount
from rewards_service.domain.reward_calculator import RewardCalculator
from shared.events.schemas import MealTransactionEvent, RewardProcessedEvent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_use_case(mock_account_repo, mock_publisher):
    return ProcessMealEventUseCase(
        calculator=RewardCalculator(),
        account_repo=mock_account_repo,
        publisher=mock_publisher,
        default_email="default@rewards.com",
    )


def make_event(amount: Decimal = Decimal("100.00"), card_number: str = "CARD-001") -> MealTransactionEvent:
    return MealTransactionEvent(
        transaction_id=uuid4(),
        card_number=card_number,
        restaurant_code="REST-01",
        amount=amount,
        timestamp=datetime.now(timezone.utc),
        currency="PEN",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCreateNewAccount:
    def test_execute_creates_new_account_when_none_exists(
        self, mock_account_repo, mock_publisher
    ):
        mock_account_repo.get_by_card.return_value = None
        mock_account_repo.transaction_exists.return_value = False
        use_case = make_use_case(mock_account_repo, mock_publisher)
        event = make_event(amount=Decimal("100.00"))

        result = use_case.execute(event)

        # save_account must be called once with a CustomerAccount
        mock_account_repo.save_account.assert_called_once()
        saved_account: CustomerAccount = mock_account_repo.save_account.call_args[0][0]
        assert saved_account.card_number == event.card_number
        assert saved_account.email == "default@rewards.com"
        assert result is not None


class TestUpdateExistingAccount:
    def test_execute_updates_existing_account(
        self, mock_account_repo, mock_publisher
    ):
        existing = CustomerAccount(
            card_number="CARD-002",
            email="existing@user.com",
            points_balance=50,
            cashback_balance=Decimal("2.00"),
            tier="standard",
        )
        mock_account_repo.get_by_card.return_value = existing
        mock_account_repo.transaction_exists.return_value = False
        use_case = make_use_case(mock_account_repo, mock_publisher)
        event = make_event(amount=Decimal("100.00"), card_number="CARD-002")

        result = use_case.execute(event)

        # Points should increase from 50 by silver tier (100 pts for 100.00)
        assert existing.points_balance == 150
        assert existing.tier == "silver"
        assert result is not None
        mock_account_repo.save_account.assert_called_once_with(existing)


class TestIdempotency:
    def test_execute_idempotency_skips_duplicate_transaction(
        self, mock_account_repo, mock_publisher
    ):
        mock_account_repo.transaction_exists.return_value = True
        use_case = make_use_case(mock_account_repo, mock_publisher)
        event = make_event()

        result = use_case.execute(event)

        assert result is None
        mock_publisher.publish_reward_processed.assert_not_called()
        mock_account_repo.save_account.assert_not_called()

    def test_execute_returns_none_for_duplicate(
        self, mock_account_repo, mock_publisher
    ):
        mock_account_repo.transaction_exists.return_value = True
        use_case = make_use_case(mock_account_repo, mock_publisher)

        result = use_case.execute(make_event())

        assert result is None


class TestEventPublishing:
    def test_execute_publishes_reward_processed_event(
        self, mock_account_repo, mock_publisher
    ):
        mock_account_repo.get_by_card.return_value = None
        mock_account_repo.transaction_exists.return_value = False
        use_case = make_use_case(mock_account_repo, mock_publisher)
        event = make_event(amount=Decimal("100.00"))

        result = use_case.execute(event)

        mock_publisher.publish_reward_processed.assert_called_once()
        published: RewardProcessedEvent = mock_publisher.publish_reward_processed.call_args[0][0]
        assert published.card_number == event.card_number
        assert published.transaction_id == event.transaction_id
        assert published.points_earned == 100  # silver: floor(100 * 1.0)
        assert published.cashback_amount == Decimal("3.00")  # 100 * 0.03


class TestSaveRewardTransaction:
    def test_execute_saves_reward_transaction(
        self, mock_account_repo, mock_publisher
    ):
        mock_account_repo.get_by_card.return_value = None
        mock_account_repo.transaction_exists.return_value = False
        use_case = make_use_case(mock_account_repo, mock_publisher)
        event = make_event(amount=Decimal("200.00"))

        use_case.execute(event)

        mock_account_repo.save_reward_transaction.assert_called_once()
        saved_tx = mock_account_repo.save_reward_transaction.call_args[0][0]
        assert saved_tx.transaction_id == event.transaction_id
        assert saved_tx.card_number == event.card_number
        assert saved_tx.points_earned == 300  # gold: floor(200 * 1.5)
        assert saved_tx.tier == "gold"
