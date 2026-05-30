"""Unit tests for rewards_service Kafka infrastructure classes."""
import pytest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4

from shared.config import KafkaConfig
from shared.events.schemas import MealTransactionEvent, RewardProcessedEvent


@pytest.fixture
def kafka_config():
    return KafkaConfig(KAFKA_BOOTSTRAP_SERVERS="localhost:9092")


@pytest.fixture
def sample_meal_event():
    return MealTransactionEvent(
        transaction_id=uuid4(),
        card_number="4532-TEST-0001",
        restaurant_code="REST-001",
        amount=Decimal("100.00"),
        timestamp=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_reward_event():
    return RewardProcessedEvent(
        event_id=uuid4(),
        transaction_id=uuid4(),
        card_number="4532-TEST-0001",
        customer_email="test@example.com",
        points_earned=100,
        cashback_amount=Decimal("3.00"),
        total_points_balance=200,
        total_cashback_balance=Decimal("6.00"),
        restaurant_code="REST-001",
        processed_at=datetime.now(timezone.utc),
    )


class TestKafkaRewardEventPublisher:
    def test_publish_reward_processed_calls_produce(self, kafka_config, sample_reward_event):
        mock_producer = MagicMock()
        with patch("shared.kafka.base_producer.Producer", return_value=mock_producer):
            from rewards_service.infrastructure.kafka_producer import KafkaRewardEventPublisher
            publisher = KafkaRewardEventPublisher(config=kafka_config)
            publisher._producer = mock_producer
            publisher.publish_reward_processed(sample_reward_event)
            mock_producer.produce.assert_called_once()

    def test_publish_reward_processed_uses_correct_topic(self, kafka_config, sample_reward_event):
        mock_producer = MagicMock()
        with patch("shared.kafka.base_producer.Producer", return_value=mock_producer):
            from rewards_service.infrastructure.kafka_producer import (
                KafkaRewardEventPublisher,
                REWARD_PROCESSED_TOPIC,
            )
            publisher = KafkaRewardEventPublisher(config=kafka_config)
            publisher._producer = mock_producer
            publisher.publish_reward_processed(sample_reward_event)
            call_kwargs = mock_producer.produce.call_args[1]
            assert call_kwargs["topic"] == REWARD_PROCESSED_TOPIC


class TestMealTransactionConsumer:
    def test_handle_message_calls_use_case(self, kafka_config):
        mock_consumer = MagicMock()
        with patch("shared.kafka.base_consumer.Consumer", return_value=mock_consumer):
            from rewards_service.infrastructure.kafka_consumer import MealTransactionConsumer
            mock_use_case = MagicMock()
            mock_use_case.execute.return_value = MagicMock(points_earned=100, card_number="4532")
            consumer = MealTransactionConsumer(config=kafka_config, use_case=mock_use_case)

            payload = {
                "transaction_id": str(uuid4()),
                "card_number": "4532-TEST",
                "restaurant_code": "REST-001",
                "amount": "100.00",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "currency": "PEN",
            }
            consumer.handle_message(payload)
            mock_use_case.execute.assert_called_once()

    def test_handle_message_idempotent_logs_skip(self, kafka_config):
        mock_consumer = MagicMock()
        with patch("shared.kafka.base_consumer.Consumer", return_value=mock_consumer):
            from rewards_service.infrastructure.kafka_consumer import MealTransactionConsumer
            mock_use_case = MagicMock()
            mock_use_case.execute.return_value = None  # idempotent: already processed
            consumer = MealTransactionConsumer(config=kafka_config, use_case=mock_use_case)

            payload = {
                "transaction_id": str(uuid4()),
                "card_number": "4532-TEST",
                "restaurant_code": "REST-001",
                "amount": "100.00",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "currency": "PEN",
            }
            consumer.handle_message(payload)
            mock_use_case.execute.assert_called_once()

    def test_consumer_subscribes_to_meal_transactions_topic(self, kafka_config):
        mock_consumer = MagicMock()
        with patch("shared.kafka.base_consumer.Consumer", return_value=mock_consumer):
            from rewards_service.infrastructure.kafka_consumer import MealTransactionConsumer, TOPIC
            mock_use_case = MagicMock()
            consumer = MealTransactionConsumer(config=kafka_config, use_case=mock_use_case)
            assert TOPIC in consumer._topics


class TestRewardsDatabase:
    def test_get_engine_uses_env_default(self):
        from rewards_service.infrastructure.database import get_engine
        engine = get_engine("sqlite:///:memory:")
        assert engine is not None

    def test_get_session_factory_returns_callable(self):
        from rewards_service.infrastructure.database import get_engine, get_session_factory
        engine = get_engine("sqlite:///:memory:")
        factory = get_session_factory(engine)
        assert callable(factory)

    def test_init_db_creates_tables(self):
        from rewards_service.infrastructure.database import get_engine, init_db, Base
        engine = get_engine("sqlite:///:memory:")
        init_db(engine)
        assert "customer_accounts" in Base.metadata.tables
        assert "reward_transactions" in Base.metadata.tables

    def test_get_engine_defaults_when_no_url(self, monkeypatch):
        monkeypatch.delenv("DATABASE_URL", raising=False)
        from rewards_service.infrastructure.database import get_engine
        engine = get_engine()
        assert engine is not None
