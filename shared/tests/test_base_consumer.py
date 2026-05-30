"""Unit tests for shared/kafka/base_consumer.py — confluent_kafka.Consumer fully mocked."""
import json
import pytest
from unittest.mock import MagicMock, patch, call
from confluent_kafka import KafkaError, KafkaException

from shared.config import KafkaConfig


@pytest.fixture
def kafka_config():
    return KafkaConfig(KAFKA_BOOTSTRAP_SERVERS="localhost:9092")


@pytest.fixture
def mock_confluent_consumer():
    return MagicMock()


@pytest.fixture
def concrete_consumer(kafka_config, mock_confluent_consumer):
    """Concrete subclass with mocked confluent consumer."""
    with patch("shared.kafka.base_consumer.Consumer", return_value=mock_confluent_consumer):
        from shared.kafka.base_consumer import BaseKafkaConsumer

        class TestConsumer(BaseKafkaConsumer):
            def __init__(self, config, dlq_producer=None):
                super().__init__(config, ["test-topic"], "test-group", dlq_producer)
                self.handled = []
                self.should_raise = None

            def handle_message(self, payload: dict) -> None:
                if self.should_raise:
                    raise self.should_raise
                self.handled.append(payload)

        consumer = TestConsumer(kafka_config)
        consumer._consumer = mock_confluent_consumer
        return consumer


def make_mock_msg(value: dict = None, topic: str = "test-topic", error=None):
    """Build a mock confluent_kafka.Message."""
    msg = MagicMock()
    msg.topic.return_value = topic
    msg.partition.return_value = 0
    msg.offset.return_value = 10
    msg.error.return_value = error
    if value is not None:
        msg.value.return_value = json.dumps(value).encode("utf-8")
    else:
        msg.value.return_value = None
    return msg


class TestBaseKafkaConsumerInit:
    def test_consumer_created_with_correct_config(self, kafka_config):
        mock_consumer = MagicMock()
        with patch("shared.kafka.base_consumer.Consumer", return_value=mock_consumer) as MockConsumer:
            from shared.kafka.base_consumer import BaseKafkaConsumer

            class TC(BaseKafkaConsumer):
                def handle_message(self, payload): pass

            TC(kafka_config, ["my-topic"], "my-group")
            MockConsumer.assert_called_once()
            cfg = MockConsumer.call_args[0][0]
            assert cfg["group.id"] == "my-group"
            assert cfg["enable.auto.commit"] is False
            assert cfg["auto.offset.reset"] == "earliest"


class TestProcessWithRetry:
    def test_successful_message_handled_once(self, concrete_consumer):
        payload = {"transaction_id": "abc", "amount": "100"}
        msg = make_mock_msg(payload)
        concrete_consumer._process_with_retry(msg)
        assert len(concrete_consumer.handled) == 1
        assert concrete_consumer.handled[0] == payload

    def test_null_value_message_skipped(self, concrete_consumer):
        msg = make_mock_msg(value=None)
        concrete_consumer._process_with_retry(msg)
        assert len(concrete_consumer.handled) == 0

    def test_retries_on_exception_then_succeeds(self, concrete_consumer):
        call_count = [0]
        original_handle = concrete_consumer.handle_message

        def flaky(payload):
            call_count[0] += 1
            if call_count[0] < 2:
                raise ValueError("transient error")
            concrete_consumer.handled.append(payload)

        concrete_consumer.handle_message = flaky
        payload = {"amount": "50"}
        msg = make_mock_msg(payload)

        with patch("time.sleep"):
            concrete_consumer._process_with_retry(msg)

        assert call_count[0] == 2
        assert len(concrete_consumer.handled) == 1

    def test_sends_to_dlq_after_max_retries(self, concrete_consumer):
        concrete_consumer.should_raise = RuntimeError("always fails")
        mock_dlq = MagicMock()
        concrete_consumer._dlq_producer = mock_dlq
        msg = make_mock_msg({"amount": "50"})

        with patch("time.sleep"):
            concrete_consumer._process_with_retry(msg)

        mock_dlq.publish.assert_called_once()

    def test_sends_to_dlq_no_producer_logs_error(self, concrete_consumer):
        concrete_consumer.should_raise = RuntimeError("always fails")
        concrete_consumer._dlq_producer = None
        msg = make_mock_msg({"amount": "50"})

        with patch("time.sleep"):
            concrete_consumer._process_with_retry(msg)


class TestSendToDLQ:
    def test_dlq_publishes_dlq_event(self, concrete_consumer):
        mock_dlq = MagicMock()
        concrete_consumer._dlq_producer = mock_dlq
        msg = make_mock_msg({"foo": "bar"})
        concrete_consumer._send_to_dlq(msg, error="boom", retry_count=3)
        mock_dlq.publish.assert_called_once()
        call_kwargs = mock_dlq.publish.call_args[1]
        assert "dlq" in call_kwargs["topic"]

    def test_dlq_handles_null_value_gracefully(self, concrete_consumer):
        mock_dlq = MagicMock()
        concrete_consumer._dlq_producer = mock_dlq
        msg = make_mock_msg(value=None)
        concrete_consumer._send_to_dlq(msg, error="null msg", retry_count=1)
        mock_dlq.publish.assert_called_once()

    def test_dlq_publish_exception_is_handled(self, concrete_consumer):
        mock_dlq = MagicMock()
        mock_dlq.publish.side_effect = Exception("dlq broken")
        concrete_consumer._dlq_producer = mock_dlq
        msg = make_mock_msg({"x": 1})
        concrete_consumer._send_to_dlq(msg, error="test", retry_count=1)

    def test_dlq_handles_invalid_json_in_message(self, concrete_consumer):
        mock_dlq = MagicMock()
        concrete_consumer._dlq_producer = mock_dlq
        msg = MagicMock()
        msg.topic.return_value = "test-topic"
        msg.value.return_value = b"not valid json {"
        concrete_consumer._send_to_dlq(msg, error="bad json", retry_count=1)
        mock_dlq.publish.assert_called_once()


class TestRun:
    def test_run_subscribes_to_topics(self, concrete_consumer, mock_confluent_consumer):
        mock_confluent_consumer.poll.side_effect = [None, KeyboardInterrupt]
        concrete_consumer.run()
        mock_confluent_consumer.subscribe.assert_called_once_with(["test-topic"])

    def test_run_processes_valid_message(self, concrete_consumer, mock_confluent_consumer):
        payload = {"transaction_id": "t1", "amount": "100"}
        msg = make_mock_msg(payload)
        msg.error.return_value = None
        mock_confluent_consumer.poll.side_effect = [msg, KeyboardInterrupt]
        mock_confluent_consumer.commit.return_value = None
        concrete_consumer.run()
        assert len(concrete_consumer.handled) == 1

    def test_run_skips_partition_eof_error(self, concrete_consumer, mock_confluent_consumer):
        mock_err = MagicMock()
        mock_err.code.return_value = KafkaError._PARTITION_EOF
        msg = MagicMock()
        msg.error.return_value = mock_err
        msg.topic.return_value = "test-topic"
        msg.partition.return_value = 0
        mock_confluent_consumer.poll.side_effect = [msg, KeyboardInterrupt]
        concrete_consumer.run()
        assert len(concrete_consumer.handled) == 0

    def test_run_logs_non_eof_kafka_error(self, concrete_consumer, mock_confluent_consumer):
        mock_err = MagicMock()
        mock_err.code.return_value = KafkaError.UNKNOWN
        msg = MagicMock()
        msg.error.return_value = mock_err
        msg.topic.return_value = "test-topic"
        mock_confluent_consumer.poll.side_effect = [msg, KeyboardInterrupt]
        concrete_consumer.run()

    def test_run_commits_offset_after_success(self, concrete_consumer, mock_confluent_consumer):
        payload = {"amount": "50"}
        msg = make_mock_msg(payload)
        msg.error.return_value = None
        mock_confluent_consumer.poll.side_effect = [msg, KeyboardInterrupt]
        mock_confluent_consumer.commit.return_value = None
        concrete_consumer.run()
        mock_confluent_consumer.commit.assert_called_once_with(message=msg, asynchronous=False)

    def test_run_closes_consumer_on_exit(self, concrete_consumer, mock_confluent_consumer):
        mock_confluent_consumer.poll.side_effect = [KeyboardInterrupt]
        concrete_consumer.run()
        mock_confluent_consumer.close.assert_called()


class TestStop:
    def test_stop_sets_running_false(self, concrete_consumer, mock_confluent_consumer):
        concrete_consumer._running = True
        concrete_consumer.stop()
        assert concrete_consumer._running is False

    def test_stop_closes_consumer(self, concrete_consumer, mock_confluent_consumer):
        concrete_consumer.stop()
        mock_confluent_consumer.close.assert_called()
