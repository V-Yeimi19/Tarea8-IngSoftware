import logging
from shared.events.schemas import RewardProcessedEvent
from notification_service.domain.entities import NotificationRequest
from notification_service.domain.ports import IEmailSender

logger = logging.getLogger(__name__)


class SendRewardNotificationUseCase:
    def __init__(self, sender: IEmailSender):
        self._sender = sender

    def execute(self, event: RewardProcessedEvent) -> None:
        request = NotificationRequest(
            recipient_email=event.customer_email,
            card_number=event.card_number,
            points_earned=event.points_earned,
            cashback_amount=event.cashback_amount,
            total_points_balance=event.total_points_balance,
            total_cashback_balance=event.total_cashback_balance,
            restaurant_code=event.restaurant_code,
            transaction_id=str(event.transaction_id),
            processed_at=event.processed_at,
        )
        try:
            self._sender.send(request)
            logger.info(f"Notification sent to {event.customer_email} for transaction {event.transaction_id}")
        except Exception as exc:
            logger.error(f"Failed to send notification for {event.transaction_id}: {exc}")
            raise
