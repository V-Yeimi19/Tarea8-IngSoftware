import logging

from shared.kafka.base_producer import BaseKafkaProducer
from shared.config import KafkaConfig
from shared.events.schemas import MealTransactionEvent
from restaurant_service.domain.ports import IEventPublisher

MEAL_TRANSACTIONS_TOPIC = "meal.transactions"
logger = logging.getLogger(__name__)


class KafkaMealEventPublisher(BaseKafkaProducer, IEventPublisher):
    def __init__(self, config: KafkaConfig):
        super().__init__(config)

    def publish_meal_transaction(self, event: MealTransactionEvent) -> None:
        self.publish(
            topic=MEAL_TRANSACTIONS_TOPIC,
            key=str(event.transaction_id),
            value=event,
        )
        logger.info(f"Published meal transaction {event.transaction_id} to {MEAL_TRANSACTIONS_TOPIC}")
