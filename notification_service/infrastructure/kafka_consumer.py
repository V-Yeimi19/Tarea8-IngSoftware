import logging
from shared.kafka.base_consumer import BaseKafkaConsumer
from shared.config import KafkaConfig
from shared.events.schemas import RewardProcessedEvent
from notification_service.application.use_cases import SendRewardNotificationUseCase

TOPIC = "reward.processed"
GROUP_ID = "notification-service-group"
logger = logging.getLogger(__name__)


class RewardProcessedConsumer(BaseKafkaConsumer):
    def __init__(self, config: KafkaConfig, use_case: SendRewardNotificationUseCase, dlq_producer=None):
        super().__init__(config, [TOPIC], GROUP_ID, dlq_producer)
        self._use_case = use_case

    def handle_message(self, payload: dict) -> None:
        event = RewardProcessedEvent.model_validate(payload)
        self._use_case.execute(event)
        logger.info(f"Notification processed for transaction {event.transaction_id}")
