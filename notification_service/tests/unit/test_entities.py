import pytest
from decimal import Decimal
from datetime import datetime, timezone

from notification_service.domain.entities import NotificationRequest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_request(**overrides) -> NotificationRequest:
    defaults = dict(
        recipient_email="cliente@test.com",
        card_number="4532-TEST-1234",
        points_earned=100,
        cashback_amount=Decimal("3.00"),
        total_points_balance=1100,
        total_cashback_balance=Decimal("33.00"),
        restaurant_code="REST-001",
        transaction_id="txn-abc-123",
        processed_at=datetime(2026, 5, 29, 14, 30, 0, tzinfo=timezone.utc),
    )
    defaults.update(overrides)
    return NotificationRequest(**defaults)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestNotificationRequest:

    def test_to_email_subject_format(self):
        """Subject must contain points and restaurant code."""
        req = _make_request(points_earned=75, restaurant_code="BURGER-HQ")
        subject = req.to_email_subject()
        assert "+75 puntos" in subject
        assert "BURGER-HQ" in subject
        assert subject.startswith("¡Recompensa acreditada!")

    def test_to_email_body_html_contains_all_data(self):
        """HTML body must contain card number, points, cashback, restaurant and transaction id."""
        req = _make_request(
            card_number="1234-TEST-5678",
            points_earned=200,
            cashback_amount=Decimal("6.00"),
            total_points_balance=2200,
            total_cashback_balance=Decimal("66.00"),
            restaurant_code="REST-ABC",
            transaction_id="uuid-xyz",
        )
        html = req.to_email_body_html()
        assert "1234-TEST-5678" in html
        assert "200" in html
        assert "6.00" in html
        assert "REST-ABC" in html
        assert "uuid-xyz" in html

    def test_to_email_body_html_is_valid_html_fragment(self):
        """HTML body must start with a DOCTYPE declaration and contain basic structure tags."""
        req = _make_request()
        html = req.to_email_body_html().strip()
        assert "<!DOCTYPE html>" in html
        assert "<html>" in html
        assert "</html>" in html
        assert "<body" in html
        assert "</body>" in html
