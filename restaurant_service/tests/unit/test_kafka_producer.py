"""Unit tests for restaurant_service Kafka producer infrastructure."""
import pytest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4

from shared.config import KafkaConfig
from shared.events.schemas import MealTransactionEvent


@pytest.fixture
def kafka_config():
    return KafkaConfig(KAFKA_BOOTSTRAP_SERVERS="localhost:9092")


@pytest.fixture
def sample_event():
    return MealTransactionEvent(
        transaction_id=uuid4(),
        card_number="4532-TEST-0001",
        restaurant_code="REST-001",
        amount=Decimal("100.00"),
        timestamp=datetime.now(timezone.utc),
    )


class TestKafkaMealEventPublisher:
    def test_publish_meal_transaction_calls_base_publish(self, kafka_config, sample_event):
        mock_producer = MagicMock()
        with patch("shared.kafka.base_producer.Producer", return_value=mock_producer):
            from restaurant_service.infrastructure.kafka_producer import KafkaMealEventPublisher
            publisher = KafkaMealEventPublisher(config=kafka_config)
            publisher._producer = mock_producer
            publisher.publish_meal_transaction(sample_event)
            mock_producer.produce.assert_called_once()

    def test_publish_meal_transaction_uses_correct_topic(self, kafka_config, sample_event):
        mock_producer = MagicMock()
        with patch("shared.kafka.base_producer.Producer", return_value=mock_producer):
            from restaurant_service.infrastructure.kafka_producer import (
                KafkaMealEventPublisher,
                MEAL_TRANSACTIONS_TOPIC,
            )
            publisher = KafkaMealEventPublisher(config=kafka_config)
            publisher._producer = mock_producer
            publisher.publish_meal_transaction(sample_event)
            call_kwargs = mock_producer.produce.call_args[1]
            assert call_kwargs["topic"] == MEAL_TRANSACTIONS_TOPIC

    def test_publish_meal_transaction_uses_transaction_id_as_key(self, kafka_config, sample_event):
        mock_producer = MagicMock()
        with patch("shared.kafka.base_producer.Producer", return_value=mock_producer):
            from restaurant_service.infrastructure.kafka_producer import KafkaMealEventPublisher
            publisher = KafkaMealEventPublisher(config=kafka_config)
            publisher._producer = mock_producer
            publisher.publish_meal_transaction(sample_event)
            call_kwargs = mock_producer.produce.call_args[1]
            assert call_kwargs["key"] == str(sample_event.transaction_id).encode("utf-8")
