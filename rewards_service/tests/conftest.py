from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from rewards_service.domain.entities import CustomerAccount
from rewards_service.domain.ports import IAccountRepository, IRewardEventPublisher
from rewards_service.domain.reward_calculator import RewardCalculator
from shared.events.schemas import MealTransactionEvent


@pytest.fixture
def mock_account_repo() -> MagicMock:
    repo = MagicMock(spec=IAccountRepository)
    # Default: no existing account, no existing transaction
    repo.get_by_card.return_value = None
    repo.transaction_exists.return_value = False
    return repo


@pytest.fixture
def mock_publisher() -> MagicMock:
    return MagicMock(spec=IRewardEventPublisher)


@pytest.fixture
def reward_calculator() -> RewardCalculator:
    return RewardCalculator()


@pytest.fixture
def sample_meal_event() -> MealTransactionEvent:
    return MealTransactionEvent(
        transaction_id=uuid4(),
        card_number="CARD-001",
        restaurant_code="REST-42",
        amount=Decimal("100.00"),
        timestamp=datetime.now(timezone.utc),
        currency="PEN",
    )
