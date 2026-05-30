from abc import ABC, abstractmethod
from notification_service.domain.entities import NotificationRequest


class IEmailSender(ABC):
    @abstractmethod
    def send(self, request: NotificationRequest) -> None: ...
