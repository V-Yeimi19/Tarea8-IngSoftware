import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from shared.config import SMTPConfig
from notification_service.domain.entities import NotificationRequest
from notification_service.domain.ports import IEmailSender

logger = logging.getLogger(__name__)


class SMTPEmailSender(IEmailSender):
    def __init__(self, config: SMTPConfig):
        self._config = config

    def send(self, request: NotificationRequest) -> None:
        if not self._config.user or not self._config.password:
            logger.warning("SMTP credentials not configured — skipping email send")
            return

        msg = MIMEMultipart("alternative")
        msg["Subject"] = request.to_email_subject()
        msg["From"] = self._config.from_address
        msg["To"] = request.recipient_email

        html_part = MIMEText(request.to_email_body_html(), "html", "utf-8")
        msg.attach(html_part)

        try:
            with smtplib.SMTP(self._config.host, self._config.port, timeout=10) as server:
                server.ehlo()
                server.starttls()
                server.login(self._config.user, self._config.password)
                server.sendmail(
                    self._config.from_address,
                    [request.recipient_email],
                    msg.as_bytes()
                )
            logger.info(f"Email sent successfully to {request.recipient_email}")
        except smtplib.SMTPException as exc:
            logger.error(f"SMTP error sending to {request.recipient_email}: {exc}")
            raise
        except OSError as exc:
            logger.error(f"Network error sending email: {exc}")
            raise
