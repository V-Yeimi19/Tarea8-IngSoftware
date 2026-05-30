"""Unit tests for shared/kafka/base_producer.py — confluent_kafka.Producer is fully mocked."""
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from confluent_kafka import KafkaException
from shared.config import KafkaConfig
from shared.events.schemas import MealTransactionEvent


@pytest.fixture
def kafka_config():
    return KafkaConfig(KAFKA_BOOTSTRAP_SERVERS="localhost:9092")


@pytest.fixture
def mock_confluent_producer():
    return MagicMock()


@pytest.fixture
def producer(kafka_config, mock_confluent_producer):
    with patch("shared.kafka.base_producer.Producer", return_value=mock_confluent_producer):
        from shared.kafka.base_producer import BaseKafkaProducer

        class ConcreteProducer(BaseKafkaProducer):
            pass

        instance = ConcreteProducer(kafka_config)
        instance._producer = mock_confluent_producer
        return instance


@pytest.fixture
def sample_event():
    return MealTransactionEvent(
        transaction_id=uuid4(),
        card_number="4532-TEST-0001",
        restaurant_code="REST-001",
        amount=Decimal("100.00"),
        timestamp=datetime.now(timezone.utc),
    )


class TestBaseKafkaProducerInit:
    def test_producer_created_with_correct_brokers(self, kafka_config):
        mock_producer = MagicMock()
        with patch("shared.kafka.base_producer.Producer", return_value=mock_producer) as MockProducer:
            from shared.kafka.base_producer import BaseKafkaProducer

            class CP(BaseKafkaProducer):
                pass

            CP(kafka_config)
            MockProducer.assert_called_once_with({"bootstrap.servers": "localhost:9092"})


class TestBaseKafkaProducerPublish:
    def test_publish_calls_produce_with_json_payload(self, producer, sample_event, mock_confluent_producer):
        producer.publish("meal.transactions", str(sample_event.transaction_id), sample_event)
        mock_confluent_producer.produce.assert_called_once()
        call_kwargs = mock_confluent_producer.produce.call_args[1]
        assert call_kwargs["topic"] == "meal.transactions"
        assert isinstance(call_kwargs["value"], bytes)

    def test_publish_calls_poll_after_produce(self, producer, sample_event, mock_confluent_producer):
        producer.publish("meal.transactions", "key-1", sample_event)
        mock_confluent_producer.poll.assert_called_with(0)

    def test_publish_raises_on_kafka_exception(self, producer, sample_event, mock_confluent_producer):
        mock_confluent_producer.produce.side_effect = KafkaException("broker down")
        with pytest.raises(KafkaException):
            producer.publish("meal.transactions", "key-1", sample_event)

    def test_publish_encodes_key_as_bytes(self, producer, sample_event, mock_confluent_producer):
        key = "test-key-123"
        producer.publish("test-topic", key, sample_event)
        call_kwargs = mock_confluent_producer.produce.call_args[1]
        assert call_kwargs["key"] == key.encode("utf-8")


class TestDeliveryCallback:
    def test_delivery_callback_success(self, producer):
        mock_msg = MagicMock()
        mock_msg.topic.return_value = "meal.transactions"
        mock_msg.partition.return_value = 0
        mock_msg.offset.return_value = 42
        producer._delivery_callback(None, mock_msg)

    def test_delivery_callback_error(self, producer):
        mock_msg = MagicMock()
        mock_msg.topic.return_value = "meal.transactions"
        mock_msg.partition.return_value = 0
        producer._delivery_callback("some kafka error", mock_msg)

    def test_delivery_callback_error_no_message(self, producer):
        producer._delivery_callback("error with no msg", None)


class TestBaseKafkaProducerClose:
    def test_close_calls_flush(self, producer, mock_confluent_producer):
        mock_confluent_producer.flush.return_value = 0
        producer.close()
        mock_confluent_producer.flush.assert_called_once()

    def test_close_warns_when_messages_undelivered(self, producer, mock_confluent_producer):
        mock_confluent_producer.flush.return_value = 5
        producer.close()
        mock_confluent_producer.flush.assert_called_once()


class TestBaseKafkaProducerIsConnected:
    def test_is_connected_returns_true_when_metadata_ok(self, producer, mock_confluent_producer):
        mock_metadata = MagicMock()
        mock_metadata.topics = {"topic1": {}, "topic2": {}}
        mock_confluent_producer.list_topics.return_value = mock_metadata
        assert producer.is_connected() is True

    def test_is_connected_returns_false_on_kafka_exception(self, producer, mock_confluent_producer):
        mock_confluent_producer.list_topics.side_effect = KafkaException("timeout")
        assert producer.is_connected() is False
