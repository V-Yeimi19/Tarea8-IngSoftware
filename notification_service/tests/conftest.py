import pytest
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4
from notification_service.domain.ports import IEmailSender
from shared.events.schemas import RewardProcessedEvent


@pytest.fixture
def mock_email_sender():
    return MagicMock(spec=IEmailSender)


@pytest.fixture
def sample_reward_event():
    return RewardProcessedEvent(
        event_id=uuid4(),
        transaction_id=uuid4(),
        card_number="4532-TEST-1234",
        customer_email="cliente@test.com",
        points_earned=100,
        cashback_amount=Decimal("3.00"),
        total_points_balance=1100,
        total_cashback_balance=Decimal("33.00"),
        restaurant_code="REST-001",
        processed_at=datetime(2026, 5, 29, 14, 30, 0, tzinfo=timezone.utc),
    )
