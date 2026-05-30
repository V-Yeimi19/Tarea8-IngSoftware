import json
import logging

from shared.kafka.base_consumer import BaseKafkaConsumer
from shared.config import KafkaConfig
from shared.events.schemas import MealTransactionEvent
from rewards_service.application.use_cases import ProcessMealEventUseCase

TOPIC = "meal.transactions"
GROUP_ID = "rewards-service-group"
logger = logging.getLogger(__name__)


class MealTransactionConsumer(BaseKafkaConsumer):
    def __init__(self, config: KafkaConfig, use_case: ProcessMealEventUseCase, dlq_producer=None):
        super().__init__(config, [TOPIC], GROUP_ID, dlq_producer)
        self._use_case = use_case

    def handle_message(self, payload: dict) -> None:
        event = MealTransactionEvent.model_validate(payload)
        result = self._use_case.execute(event)
        if result is None:
            logger.info(f"Transaction {payload.get('transaction_id')} already processed (idempotent)")
        else:
            logger.info(f"Processed reward for card {event.card_number}: {result.points_earned} pts")
