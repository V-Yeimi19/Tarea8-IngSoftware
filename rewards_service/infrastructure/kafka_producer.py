import logging

from shared.kafka.base_producer import BaseKafkaProducer
from shared.config import KafkaConfig
from shared.events.schemas import RewardProcessedEvent
from rewards_service.domain.ports import IRewardEventPublisher

REWARD_PROCESSED_TOPIC = "reward.processed"
logger = logging.getLogger(__name__)


class KafkaRewardEventPublisher(BaseKafkaProducer, IRewardEventPublisher):
    """Kafka producer that publishes RewardProcessedEvent to the reward.processed topic."""

    def __init__(self, config: KafkaConfig) -> None:
        super().__init__(config)

    def publish_reward_processed(self, event: RewardProcessedEvent) -> None:
        self.publish(
            topic=REWARD_PROCESSED_TOPIC,
            key=event.card_number,
            value=event,
        )
        logger.info(
            "Published RewardProcessedEvent — card: %s, transaction: %s, points: %d",
            event.card_number,
            event.transaction_id,
            event.points_earned,
        )
