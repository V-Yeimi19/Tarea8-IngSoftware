import smtplib
import logging
import pytest
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, call

from shared.config import SMTPConfig
from notification_service.domain.entities import NotificationRequest
from notification_service.infrastructure.smtp_sender import SMTPEmailSender
from notification_service.application.use_cases import SendRewardNotificationUseCase


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_smtp_config(**overrides) -> SMTPConfig:
    """Build an SMTPConfig bypassing env-file loading via model_construct (no env lookup)."""
    # model_construct skips validation and env resolution; use field names (not aliases).
    defaults = dict(
        host="smtp.example.com",
        port=587,
        user="user@example.com",
        password="secret",
        from_address="rewards@example.com",
    )
    defaults.update(overrides)
    return SMTPConfig.model_construct(**defaults)


def _make_notification(**overrides) -> NotificationRequest:
    defaults = dict(
        recipient_email="dest@test.com",
        card_number="1111-2222-3333",
        points_earned=50,
        cashback_amount=Decimal("1.50"),
        total_points_balance=550,
        total_cashback_balance=Decimal("16.50"),
        restaurant_code="REST-TEST",
        transaction_id="txn-001",
        processed_at=datetime(2026, 5, 29, 12, 0, 0, tzinfo=timezone.utc),
    )
    defaults.update(overrides)
    return NotificationRequest(**defaults)


# ---------------------------------------------------------------------------
# SMTPEmailSender branch tests
# ---------------------------------------------------------------------------

class TestSMTPEmailSenderBranches:

    def test_smtp_sender_skips_when_no_credentials(self, caplog):
        """When user/password are empty, send() must log a warning and not open any SMTP connection."""
        config = _make_smtp_config(user="", password="")
        sender = SMTPEmailSender(config=config)
        notification = _make_notification()

        with patch("smtplib.SMTP") as mock_smtp_cls:
            with caplog.at_level(logging.WARNING, logger="notification_service.infrastructure.smtp_sender"):
                sender.send(notification)

            # SMTP constructor must NOT be called
            mock_smtp_cls.assert_not_called()

        assert any("skipping" in record.message.lower() or "credentials" in record.message.lower()
                   for record in caplog.records)

    def test_smtp_sender_raises_on_smtp_exception(self):
        """SMTPException during SMTP interaction must propagate out of send()."""
        config = _make_smtp_config()
        sender = SMTPEmailSender(config=config)
        notification = _make_notification()

        mock_server = MagicMock()
        mock_server.__enter__ = MagicMock(return_value=mock_server)
        mock_server.__exit__ = MagicMock(return_value=False)
        mock_server.starttls.side_effect = smtplib.SMTPException("TLS failure")

        with patch("smtplib.SMTP", return_value=mock_server):
            with pytest.raises(smtplib.SMTPException, match="TLS failure"):
                sender.send(notification)

    def test_smtp_sender_raises_on_network_error(self):
        """OSError during SMTP connection must propagate out of send()."""
        config = _make_smtp_config()
        sender = SMTPEmailSender(config=config)
        notification = _make_notification()

        with patch("smtplib.SMTP", side_effect=OSError("Connection refused")):
            with pytest.raises(OSError, match="Connection refused"):
                sender.send(notification)


# ---------------------------------------------------------------------------
# NotificationRequest entity branch tests
# ---------------------------------------------------------------------------

class TestNotificationEntityBranches:

    def test_notification_entity_subject_format(self):
        """Subject string must follow the expected template."""
        req = _make_notification(points_earned=42, restaurant_code="PIZZA-PALACE")
        subject = req.to_email_subject()
        assert "+42 puntos" in subject
        assert "PIZZA-PALACE" in subject

    def test_notification_entity_html_contains_points(self):
        """HTML body must contain the number of points earned."""
        req = _make_notification(points_earned=123)
        assert "123" in req.to_email_body_html()

    def test_notification_entity_html_contains_cashback(self):
        """HTML body must contain the formatted cashback amount."""
        req = _make_notification(cashback_amount=Decimal("9.99"))
        assert "9.99" in req.to_email_body_html()

    def test_notification_entity_html_contains_restaurant_code(self):
        """HTML body must contain the restaurant code."""
        req = _make_notification(restaurant_code="SUSHI-CLUB")
        assert "SUSHI-CLUB" in req.to_email_body_html()


# ---------------------------------------------------------------------------
# Use-case logger branch test
# ---------------------------------------------------------------------------

class TestUseCaseLoggerBranches:

    def test_use_case_logs_error_when_sender_raises(self, sample_reward_event):
        """logger.error must be called when the sender raises an exception."""
        mock_sender = MagicMock()
        mock_sender.send.side_effect = RuntimeError("boom")
        use_case = SendRewardNotificationUseCase(sender=mock_sender)

        target_logger = "notification_service.application.use_cases"
        with patch(f"{target_logger}.logger") as mock_logger:
            with pytest.raises(RuntimeError):
                use_case.execute(sample_reward_event)

            mock_logger.error.assert_called_once()
            error_msg = mock_logger.error.call_args[0][0]
            assert "Failed to send notification" in error_msg
