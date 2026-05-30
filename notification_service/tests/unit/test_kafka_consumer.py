"""Unit tests for notification_service Kafka consumer infrastructure."""
import pytest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4

from shared.config import KafkaConfig


@pytest.fixture
def kafka_config():
    return KafkaConfig(KAFKA_BOOTSTRAP_SERVERS="localhost:9092")


class TestRewardProcessedConsumer:
    def test_handle_message_calls_use_case(self, kafka_config):
        mock_consumer = MagicMock()
        with patch("shared.kafka.base_consumer.Consumer", return_value=mock_consumer):
            from notification_service.infrastructure.kafka_consumer import RewardProcessedConsumer
            mock_use_case = MagicMock()
            consumer = RewardProcessedConsumer(config=kafka_config, use_case=mock_use_case)

            payload = {
                "event_id": str(uuid4()),
                "transaction_id": str(uuid4()),
                "card_number": "4532-TEST",
                "customer_email": "test@example.com",
                "points_earned": 100,
                "cashback_amount": "3.00",
                "total_points_balance": 200,
                "total_cashback_balance": "6.00",
                "restaurant_code": "REST-001",
                "processed_at": datetime.now(timezone.utc).isoformat(),
            }
            consumer.handle_message(payload)
            mock_use_case.execute.assert_called_once()

    def test_consumer_subscribes_to_reward_processed_topic(self, kafka_config):
        mock_consumer = MagicMock()
        with patch("shared.kafka.base_consumer.Consumer", return_value=mock_consumer):
            from notification_service.infrastructure.kafka_consumer import RewardProcessedConsumer, TOPIC
            mock_use_case = MagicMock()
            consumer = RewardProcessedConsumer(config=kafka_config, use_case=mock_use_case)
            assert TOPIC in consumer._topics

    def test_consumer_uses_correct_group_id(self, kafka_config):
        mock_consumer = MagicMock()
        with patch("shared.kafka.base_consumer.Consumer", return_value=mock_consumer):
            from notification_service.infrastructure.kafka_consumer import RewardProcessedConsumer, GROUP_ID
            mock_use_case = MagicMock()
            consumer = RewardProcessedConsumer(config=kafka_config, use_case=mock_use_case)
            assert consumer._group_id == GROUP_ID

    def test_handle_message_with_invalid_payload_raises(self, kafka_config):
        mock_consumer = MagicMock()
        with patch("shared.kafka.base_consumer.Consumer", return_value=mock_consumer):
            from notification_service.infrastructure.kafka_consumer import RewardProcessedConsumer
            mock_use_case = MagicMock()
            consumer = RewardProcessedConsumer(config=kafka_config, use_case=mock_use_case)
            with pytest.raises(Exception):
                consumer.handle_message({"invalid": "payload"})
