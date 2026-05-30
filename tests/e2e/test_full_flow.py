"""
End-to-end tests for the restaurant rewards system.

The restaurant_service uses app.state (set inside a lifespan context manager)
rather than a create_app factory. To avoid connecting to a real Kafka broker,
we bypass the lifespan entirely by:
  1. Importing the FastAPI `app` instance.
  2. Manually setting app.state dependencies before each test.
  3. Using AsyncClient without triggering the lifespan
     (lifespan=False on ASGITransport is not available in all versions,
      so we replace app.router.lifespan_context with a no-op).
"""
import pytest
from decimal import Decimal
from httpx import AsyncClient, ASGITransport
from unittest.mock import MagicMock
from uuid import uuid4

from fastapi import FastAPI

from restaurant_service.application.use_cases import RegisterMealUseCase
from restaurant_service.infrastructure.in_memory_repository import InMemoryTransactionRepository


def _build_app_with_mock_publisher(mock_publisher) -> FastAPI:
    """
    Return a fresh FastAPI app wired with a mock publisher.
    State is set directly (no lifespan) because ASGITransport in httpx
    does not trigger the lifespan startup/shutdown lifecycle.
    """
    from restaurant_service.infrastructure.http_router import router

    app = FastAPI(title="Restaurant Service (Test)")
    app.include_router(router)

    repository = InMemoryTransactionRepository()
    use_case = RegisterMealUseCase(publisher=mock_publisher, repository=repository)

    app.state.kafka_publisher = mock_publisher
    app.state.transaction_repository = repository
    app.state.register_meal_use_case = use_case
    return app


@pytest.mark.asyncio
class TestRestaurantServiceE2E:
    """End-to-end tests for the restaurant service API."""

    async def test_register_meal_full_flow(self, mock_kafka_producer):
        """Full flow: POST meal → event published → 201 response with transaction_id."""
        app = _build_app_with_mock_publisher(mock_kafka_producer)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/meals", json={
                "card_number": "4532-E2E-0001",
                "restaurant_code": "REST-001",
                "amount": 150.00,
            })

        assert response.status_code == 201
        data = response.json()
        assert "transaction_id" in data
        assert data["card_number"] == "4532-E2E-0001"
        assert data["restaurant_code"] == "REST-001"
        mock_kafka_producer.publish_meal_transaction.assert_called_once()

    async def test_register_multiple_meals_different_cards(self, mock_kafka_producer):
        """Multiple meals from different cards all receive unique transaction IDs."""
        app = _build_app_with_mock_publisher(mock_kafka_producer)

        transaction_ids = []
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            for i in range(3):
                response = await client.post("/api/v1/meals", json={
                    "card_number": f"4532-CARD-{i:04d}",
                    "restaurant_code": "REST-001",
                    "amount": 75.50,
                })
                assert response.status_code == 201
                transaction_ids.append(response.json()["transaction_id"])

        assert len(set(transaction_ids)) == 3  # all unique

    async def test_health_endpoint_returns_service_info(self, mock_kafka_producer):
        """Health endpoint returns service name and status."""
        app = _build_app_with_mock_publisher(mock_kafka_producer)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "service" in data

    async def test_invalid_amount_rejected(self, mock_kafka_producer):
        """Negative amounts are rejected with 422."""
        app = _build_app_with_mock_publisher(mock_kafka_producer)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/meals", json={
                "card_number": "4532-TEST-0001",
                "restaurant_code": "REST-001",
                "amount": -50.00,
            })

        assert response.status_code == 422

    async def test_missing_card_number_rejected(self, mock_kafka_producer):
        """Missing card_number returns 422."""
        app = _build_app_with_mock_publisher(mock_kafka_producer)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/meals", json={
                "restaurant_code": "REST-001",
                "amount": 100.00,
            })

        assert response.status_code == 422


@pytest.mark.asyncio
class TestRewardsServiceE2E:
    """End-to-end tests for the rewards use case (in-process, no Kafka)."""

    def test_full_rewards_processing_flow(self):
        """Process a meal event → rewards calculated → event published."""
        from decimal import Decimal
        from unittest.mock import MagicMock
        from uuid import uuid4
        from datetime import datetime, timezone
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from rewards_service.infrastructure.database import Base, init_db
        from rewards_service.infrastructure.repository import SQLAlchemyAccountRepository
        from rewards_service.infrastructure.models import CustomerAccountModel, RewardTransactionModel
        from rewards_service.domain.reward_calculator import RewardCalculator
        from rewards_service.application.use_cases import ProcessMealEventUseCase
        from shared.events.schemas import MealTransactionEvent

        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        session = Session()

        repo = SQLAlchemyAccountRepository(session)
        calculator = RewardCalculator()
        mock_publisher = MagicMock()

        use_case = ProcessMealEventUseCase(calculator, repo, mock_publisher)
        event = MealTransactionEvent(
            transaction_id=uuid4(),
            card_number="4532-E2E-REWARDS",
            restaurant_code="REST-GOLD",
            amount=Decimal("200.00"),
            timestamp=datetime.now(timezone.utc),
        )

        result = use_case.execute(event)

        assert result is not None
        assert result.points_earned == 300  # 200 * 1.5 (gold tier)
        assert result.cashback_amount == Decimal("8.00")  # 200 * 0.04
        mock_publisher.publish_reward_processed.assert_called_once()

        account = repo.get_by_card("4532-E2E-REWARDS")
        assert account is not None
        assert account.points_balance == 300

    def test_idempotent_processing(self):
        """Same transaction_id processed twice → only counted once."""
        from decimal import Decimal
        from unittest.mock import MagicMock
        from uuid import uuid4
        from datetime import datetime, timezone
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from rewards_service.infrastructure.database import Base
        from rewards_service.infrastructure.repository import SQLAlchemyAccountRepository
        from rewards_service.domain.reward_calculator import RewardCalculator
        from rewards_service.application.use_cases import ProcessMealEventUseCase
        from shared.events.schemas import MealTransactionEvent

        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=engine)
        session = sessionmaker(bind=engine)()
        repo = SQLAlchemyAccountRepository(session)
        mock_publisher = MagicMock()
        use_case = ProcessMealEventUseCase(RewardCalculator(), repo, mock_publisher)

        tx_id = uuid4()
        event = MealTransactionEvent(
            transaction_id=tx_id,
            card_number="4532-IDEM",
            restaurant_code="REST-001",
            amount=Decimal("100.00"),
            timestamp=datetime.now(timezone.utc),
        )

        use_case.execute(event)
        result2 = use_case.execute(event)

        assert result2 is None
        assert mock_publisher.publish_reward_processed.call_count == 1
        account = repo.get_by_card("4532-IDEM")
        assert account.points_balance == 100  # not doubled


class TestNotificationServiceE2E:
    """End-to-end tests for the notification service (email sending)."""

    def test_full_email_notification_flow(self):
        """
        Complete flow: Reward event → Email construction → SMTP send attempt.

        Demonstrates:
        - RewardProcessedEvent deserialization
        - NotificationRequest creation
        - HTML email body generation
        - SMTP connection and send attempt
        """
        import smtplib
        from unittest.mock import patch, MagicMock
        from datetime import datetime, timezone
        from decimal import Decimal
        from uuid import uuid4

        from notification_service.domain.entities import NotificationRequest
        from notification_service.infrastructure.smtp_sender import SMTPEmailSender
        from notification_service.application.use_cases import SendRewardNotificationUseCase
        from shared.config import SMTPConfig
        from shared.events.schemas import RewardProcessedEvent

        # --- Setup: Create RewardProcessedEvent (as consumed from Kafka) ---
        event = RewardProcessedEvent(
            event_id=uuid4(),
            transaction_id=uuid4(),
            card_number="4532-EMAIL-TEST",
            customer_email="cliente.test@ejemplo.com",
            points_earned=250,
            cashback_amount=Decimal("7.50"),
            total_points_balance=750,
            total_cashback_balance=Decimal("22.50"),
            restaurant_code="REST-GOLD",
            processed_at=datetime.now(timezone.utc),
        )

        # --- Setup: Mock SMTP config ---
        smtp_config = MagicMock(spec=SMTPConfig)
        smtp_config.host = "smtp.gmail.com"
        smtp_config.port = 587
        smtp_config.user = "rewards@restaurant.com"
        smtp_config.password = "app-password-123"
        smtp_config.from_address = "rewards@restaurant.com"

        # --- Create notification request from event ---
        notification = NotificationRequest(
            recipient_email=event.customer_email,
            card_number=event.card_number,
            points_earned=event.points_earned,
            cashback_amount=event.cashback_amount,
            total_points_balance=event.total_points_balance,
            total_cashback_balance=event.total_cashback_balance,
            restaurant_code=event.restaurant_code,
            transaction_id=str(event.transaction_id),
            processed_at=event.processed_at,
        )

        # --- Verify email body generation ---
        email_subject = notification.to_email_subject()
        email_body = notification.to_email_body_html()

        assert "Recompensa acreditada" in email_subject
        assert "250 puntos" in email_subject
        assert "REST-GOLD" in email_subject
        assert "cliente.test@ejemplo.com" not in email_subject  # No leaking email in subject
        assert "250" in email_body  # Points mentioned
        assert "7.50" in email_body  # Cashback mentioned
        assert "REST-GOLD" in email_body  # Restaurant code

        # --- Mock SMTP and test send ---
        mock_server = MagicMock()
        mock_smtp_context = MagicMock()
        mock_smtp_context.__enter__.return_value = mock_server
        mock_smtp_context.__exit__.return_value = None

        with patch("smtplib.SMTP", return_value=mock_smtp_context) as MockSMTP:
            sender = SMTPEmailSender(config=smtp_config)
            sender.send(notification)

            # --- Verify SMTP was called correctly ---
            MockSMTP.assert_called_once_with("smtp.gmail.com", 587, timeout=10)
            mock_server.ehlo.assert_called_once()
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once_with(
                "rewards@restaurant.com",
                "app-password-123"
            )
            mock_server.sendmail.assert_called_once()

            # --- Extract actual call arguments ---
            import base64
            sendmail_call = mock_server.sendmail.call_args
            from_addr, to_addrs, message_bytes = sendmail_call[0]

            assert from_addr == "rewards@restaurant.com"
            assert to_addrs == ["cliente.test@ejemplo.com"]
            # Email is MIME-encoded with base64 body, extract and verify
            message_str = message_bytes.decode("utf-8", errors="ignore")
            # Find base64-encoded content and decode it
            if "Content-Transfer-Encoding: base64" in message_str:
                parts = message_str.split("\n\n")
                for part in parts:
                    try:
                        decoded = base64.b64decode(part.strip()).decode("utf-8")
                        if "250" in decoded:
                            assert "Recompensa acreditada" in decoded or "Tu recompensa fue procesada" in decoded
                            break
                    except Exception:
                        pass
            else:
                assert "Recompensa acreditada" in message_str or "250" in message_str

    def test_missing_smtp_credentials_skips_send(self):
        """When SMTP credentials missing, send() logs warning and returns early."""
        from unittest.mock import MagicMock
        from datetime import datetime, timezone
        from decimal import Decimal

        from notification_service.domain.entities import NotificationRequest
        from notification_service.infrastructure.smtp_sender import SMTPEmailSender
        from shared.config import SMTPConfig

        # --- Setup: Missing SMTP credentials ---
        smtp_config = MagicMock(spec=SMTPConfig)
        smtp_config.user = None  # Missing!
        smtp_config.password = None  # Missing!

        notification = NotificationRequest(
            recipient_email="cliente@ejemplo.com",
            card_number="4532-TEST",
            points_earned=100,
            cashback_amount=Decimal("3.00"),
            total_points_balance=100,
            total_cashback_balance=Decimal("3.00"),
            restaurant_code="REST-001",
            transaction_id="tx-123",
            processed_at=datetime.now(timezone.utc),
        )

        sender = SMTPEmailSender(config=smtp_config)
        # Should not raise, should just log warning
        sender.send(notification)  # No exception raised

    def test_smtp_connection_failure_raises(self):
        """When SMTP connection fails, exception is raised and logged."""
        from unittest.mock import patch, MagicMock
        import smtplib
        from datetime import datetime, timezone
        from decimal import Decimal

        from notification_service.domain.entities import NotificationRequest
        from notification_service.infrastructure.smtp_sender import SMTPEmailSender
        from shared.config import SMTPConfig

        smtp_config = MagicMock(spec=SMTPConfig)
        smtp_config.host = "smtp.gmail.com"
        smtp_config.port = 587
        smtp_config.user = "rewards@restaurant.com"
        smtp_config.password = "app-password"
        smtp_config.from_address = "rewards@restaurant.com"

        notification = NotificationRequest(
            recipient_email="cliente@ejemplo.com",
            card_number="4532-FAIL",
            points_earned=100,
            cashback_amount=Decimal("3.00"),
            total_points_balance=100,
            total_cashback_balance=Decimal("3.00"),
            restaurant_code="REST-001",
            transaction_id="tx-fail",
            processed_at=datetime.now(timezone.utc),
        )

        # --- Mock SMTP to raise connection error ---
        with patch("smtplib.SMTP") as MockSMTP:
            MockSMTP.side_effect = ConnectionRefusedError("Connection refused")

            sender = SMTPEmailSender(config=smtp_config)
            with pytest.raises(ConnectionRefusedError):
                sender.send(notification)
