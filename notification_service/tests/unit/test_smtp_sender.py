"""Unit tests for SMTPEmailSender — covers the successful send path with mocked smtplib."""
import smtplib
import pytest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

from notification_service.domain.entities import NotificationRequest
from notification_service.infrastructure.smtp_sender import SMTPEmailSender


@pytest.fixture
def smtp_config():
    config = MagicMock()
    config.user = "rewards@restaurant.com"
    config.password = "app-password"
    config.host = "smtp.gmail.com"
    config.port = 587
    config.from_address = "rewards@restaurant.com"
    return config


@pytest.fixture
def notification_request():
    return NotificationRequest(
        recipient_email="cliente@ejemplo.com",
        card_number="4532-TEST-1234",
        points_earned=100,
        cashback_amount=Decimal("3.00"),
        total_points_balance=500,
        total_cashback_balance=Decimal("15.00"),
        restaurant_code="REST-001",
        transaction_id="abc-123",
        processed_at=datetime(2026, 5, 30, 12, 0, 0, tzinfo=timezone.utc),
    )


def test_send_success_path(smtp_config, notification_request):
    """With valid credentials, send() opens an SMTP session and sends the email."""
    mock_server = MagicMock()
    mock_smtp_ctx = MagicMock()
    mock_smtp_ctx.__enter__.return_value = mock_server

    with patch("smtplib.SMTP", return_value=mock_smtp_ctx) as MockSMTP:
        sender = SMTPEmailSender(config=smtp_config)
        sender.send(notification_request)

        MockSMTP.assert_called_once_with("smtp.gmail.com", 587, timeout=10)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("rewards@restaurant.com", "app-password")
        mock_server.sendmail.assert_called_once()
