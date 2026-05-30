import logging
from typing import Any

from confluent_kafka import Producer, KafkaException
from pydantic import BaseModel

from shared.config import KafkaConfig

logger = logging.getLogger(__name__)


class BaseKafkaProducer:
    """Abstract base producer that wraps confluent_kafka.Producer with JSON serialization."""

    def __init__(self, config: KafkaConfig) -> None:
        self._config = config
        self._producer = Producer(
            {"bootstrap.servers": config.bootstrap_servers}
        )
        logger.info("KafkaProducer initialized with brokers: %s", config.bootstrap_servers)

    def publish(self, topic: str, key: str, value: BaseModel) -> None:
        """Serialize value to JSON bytes and produce to the given topic."""
        try:
            payload: bytes = value.model_dump_json().encode("utf-8")
            self._producer.produce(
                topic=topic,
                key=key.encode("utf-8"),
                value=payload,
                callback=self._delivery_callback,
            )
            # Trigger delivery of queued messages (non-blocking)
            self._producer.poll(0)
            logger.debug("Message enqueued to topic '%s' with key '%s'", topic, key)
        except KafkaException as exc:
            logger.error(
                "Failed to produce message to topic '%s' with key '%s': %s",
                topic,
                key,
                exc,
            )
            raise

    def _delivery_callback(self, err: Any, msg: Any) -> None:
        """Called by confluent_kafka on successful or failed delivery."""
        if err is not None:
            logger.error(
                "Message delivery failed — topic: %s, partition: %s, error: %s",
                msg.topic() if msg else "unknown",
                msg.partition() if msg else "unknown",
                err,
            )
        else:
            logger.debug(
                "Message delivered — topic: %s, partition: %s, offset: %s",
                msg.topic(),
                msg.partition(),
                msg.offset(),
            )

    def close(self) -> None:
        """Flush all outstanding messages and wait for delivery."""
        logger.info("Flushing KafkaProducer before shutdown…")
        remaining = self._producer.flush()
        if remaining > 0:
            logger.warning("%d message(s) were not delivered before shutdown", remaining)
        else:
            logger.info("KafkaProducer flushed successfully")

    def is_connected(self) -> bool:
        """Return True if the broker is reachable (metadata fetch succeeds)."""
        try:
            metadata = self._producer.list_topics(timeout=5)
            logger.debug("Broker metadata retrieved: %d topic(s) known", len(metadata.topics))
            return True
        except KafkaException as exc:
            logger.error("Broker connectivity check failed: %s", exc)
            return False
