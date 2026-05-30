import pytest
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

from notification_service.application.use_cases import SendRewardNotificationUseCase
from notification_service.domain.entities import NotificationRequest
from notification_service.domain.ports import IEmailSender
from shared.events.schemas import RewardProcessedEvent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_event(**overrides) -> RewardProcessedEvent:
    defaults = dict(
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
    defaults.update(overrides)
    return RewardProcessedEvent(**defaults)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSendRewardNotificationUseCase:

    def test_execute_calls_email_sender(self, mock_email_sender, sample_reward_event):
        """sender.send() must be called exactly once."""
        use_case = SendRewardNotificationUseCase(sender=mock_email_sender)
        use_case.execute(sample_reward_event)
        mock_email_sender.send.assert_called_once()

    def test_execute_passes_correct_email(self, mock_email_sender, sample_reward_event):
        """The NotificationRequest passed to sender must carry the event's customer_email."""
        use_case = SendRewardNotificationUseCase(sender=mock_email_sender)
        use_case.execute(sample_reward_event)

        call_args = mock_email_sender.send.call_args
        notification: NotificationRequest = call_args[0][0]
        assert notification.recipient_email == sample_reward_event.customer_email

    def test_execute_raises_when_sender_fails(self, mock_email_sender, sample_reward_event):
        """When sender.send() raises, the use case must re-raise the same exception."""
        mock_email_sender.send.side_effect = RuntimeError("SMTP down")
        use_case = SendRewardNotificationUseCase(sender=mock_email_sender)

        with pytest.raises(RuntimeError, match="SMTP down"):
            use_case.execute(sample_reward_event)

    def test_execute_builds_correct_notification_request(self, mock_email_sender):
        """Every field of NotificationRequest must match the source event."""
        event = _make_event(
            card_number="9999-CARD-0001",
            customer_email="user@example.com",
            points_earned=250,
            cashback_amount=Decimal("7.50"),
            total_points_balance=2500,
            total_cashback_balance=Decimal("75.00"),
            restaurant_code="REST-XYZ",
        )
        use_case = SendRewardNotificationUseCase(sender=mock_email_sender)
        use_case.execute(event)

        call_args = mock_email_sender.send.call_args
        req: NotificationRequest = call_args[0][0]

        assert req.recipient_email == "user@example.com"
        assert req.card_number == "9999-CARD-0001"
        assert req.points_earned == 250
        assert req.cashback_amount == Decimal("7.50")
        assert req.total_points_balance == 2500
        assert req.total_cashback_balance == Decimal("75.00")
        assert req.restaurant_code == "REST-XYZ"
        assert req.transaction_id == str(event.transaction_id)
        assert req.processed_at == event.processed_at
