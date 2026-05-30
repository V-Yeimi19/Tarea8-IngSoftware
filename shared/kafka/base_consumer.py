import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional

from confluent_kafka import Consumer, KafkaError, KafkaException, Message

from shared.config import KafkaConfig
from shared.events.schemas import DLQEvent

logger = logging.getLogger(__name__)


class BaseKafkaConsumer(ABC):
    """Abstract base consumer with retry logic and dead-letter queue support."""

    MAX_RETRIES: int = 3
    INITIAL_BACKOFF_SECONDS: float = 0.5

    def __init__(
        self,
        config: KafkaConfig,
        topics: list[str],
        group_id: str,
        dlq_producer=None,
    ) -> None:
        self._config = config
        self._topics = topics
        self._group_id = group_id
        self._dlq_producer = dlq_producer
        self._running: bool = False

        self._consumer = Consumer(
            {
                "bootstrap.servers": config.bootstrap_servers,
                "group.id": group_id,
                "auto.offset.reset": "earliest",
                "enable.auto.commit": False,
            }
        )
        logger.info(
            "KafkaConsumer initialized — group: '%s', topics: %s, brokers: %s",
            group_id,
            topics,
            config.bootstrap_servers,
        )

    @abstractmethod
    def handle_message(self, payload: dict) -> None:
        """Process a deserialized message payload. Must be implemented by subclasses."""
        ...

    def _process_with_retry(self, raw_msg: Message) -> None:
        """
        Deserialize raw_msg and call handle_message with exponential backoff retry.

        Backoff schedule (INITIAL_BACKOFF_SECONDS = 0.5):
          attempt 1 — 0.5 s
          attempt 2 — 1.0 s
          attempt 3 — 2.0 s
        On exhaustion the message is forwarded to the DLQ.
        """
        import json

        last_exception: Optional[Exception] = None

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                raw_value = raw_msg.value()
                if raw_value is None:
                    logger.warning("Received message with null value — skipping")
                    return

                payload: dict = json.loads(raw_value.decode("utf-8"))
                self.handle_message(payload)
                return  # success — exit retry loop

            except Exception as exc:
                last_exception = exc
                backoff = self.INITIAL_BACKOFF_SECONDS * (2 ** (attempt - 1))
                logger.warning(
                    "handle_message failed (attempt %d/%d) — topic: %s, error: %s — retrying in %.1fs",
                    attempt,
                    self.MAX_RETRIES,
                    raw_msg.topic(),
                    exc,
                    backoff,
                )
                if attempt < self.MAX_RETRIES:
                    time.sleep(backoff)

        # All retries exhausted
        logger.error(
            "Max retries (%d) exceeded for message on topic '%s' — sending to DLQ",
            self.MAX_RETRIES,
            raw_msg.topic(),
        )
        self._send_to_dlq(
            raw_msg,
            error=str(last_exception),
            retry_count=self.MAX_RETRIES,
        )

    def _send_to_dlq(self, raw_msg: Message, error: str, retry_count: int) -> None:
        """Forward a failed message to the dead-letter queue topic."""
        import json

        topic = raw_msg.topic() or "unknown"

        try:
            raw_value = raw_msg.value()
            original_message: dict = (
                json.loads(raw_value.decode("utf-8")) if raw_value else {}
            )
        except Exception as parse_exc:
            logger.error("Could not decode original message for DLQ: %s", parse_exc)
            original_message = {}

        dlq_event = DLQEvent(
            original_topic=topic,
            original_message=original_message,
            error=error,
            retry_count=retry_count,
            failed_at=datetime.now(tz=timezone.utc),
        )

        dlq_topic = f"{topic}.dlq"

        if self._dlq_producer is not None:
            try:
                self._dlq_producer.publish(
                    topic=dlq_topic,
                    key=topic,
                    value=dlq_event,
                )
                logger.info("DLQ event published to topic '%s'", dlq_topic)
            except Exception as exc:
                logger.error("Failed to publish DLQ event to topic '%s': %s", dlq_topic, exc)
        else:
            logger.error(
                "No DLQ producer configured — message lost from topic '%s': %s",
                topic,
                dlq_event.model_dump_json(),
            )

    def run(self) -> None:
        """Start the poll loop. Blocks until stop() is called."""
        self._consumer.subscribe(self._topics)
        self._running = True
        logger.info("Consumer started — listening on topics: %s", self._topics)

        try:
            while self._running:
                msg: Optional[Message] = self._consumer.poll(timeout=1.0)

                if msg is None:
                    # No message within the poll timeout — continue polling
                    continue

                if msg.error():
                    kafka_err: KafkaError = msg.error()
                    if kafka_err.code() == KafkaError._PARTITION_EOF:
                        logger.debug(
                            "Reached end of partition — topic: %s, partition: %s",
                            msg.topic(),
                            msg.partition(),
                        )
                    else:
                        logger.error("Kafka consumer error: %s", kafka_err)
                    continue

                try:
                    self._process_with_retry(msg)
                    self._consumer.commit(message=msg, asynchronous=False)
                    logger.debug(
                        "Offset committed — topic: %s, partition: %s, offset: %s",
                        msg.topic(),
                        msg.partition(),
                        msg.offset(),
                    )
                except Exception as exc:
                    # _process_with_retry already handles retries/DLQ; this is a safety net
                    logger.error(
                        "Unexpected error processing message on topic '%s': %s",
                        msg.topic(),
                        exc,
                    )

        except KeyboardInterrupt:
            logger.info("Consumer interrupted by user")
        finally:
            logger.info("Consumer shutting down — closing Kafka consumer")
            self._consumer.close()

    def stop(self) -> None:
        """Signal the poll loop to stop and close the consumer."""
        logger.info("Stop requested for consumer group '%s'", self._group_id)
        self._running = False
        self._consumer.close()
