import logging
import signal
import sys
import threading

import uvicorn
from fastapi import FastAPI

from shared.config import KafkaConfig, SMTPConfig
from notification_service.infrastructure.smtp_sender import SMTPEmailSender
from notification_service.infrastructure.kafka_consumer import RewardProcessedConsumer
from notification_service.application.use_cases import SendRewardNotificationUseCase

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Health check FastAPI app (runs on port 8002 in a background thread)
# ---------------------------------------------------------------------------
health_app = FastAPI(title="Notification Service Health")


@health_app.get("/health")
def health_check() -> dict:
    return {"status": "ok", "service": "notification_service"}


@health_app.get("/")
def root() -> dict:
    return {"service": "notification_service", "version": "1.0.0"}


def _run_health_server() -> None:
    """Start uvicorn on port 8002 — runs in a daemon thread."""
    uvicorn.run(health_app, host="127.0.0.1", port=8002, log_level="warning")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main() -> None:
    logger.info("Starting notification_service…")

    # --- Build dependencies ---
    kafka_config = KafkaConfig()
    smtp_config = SMTPConfig()

    email_sender = SMTPEmailSender(config=smtp_config)
    use_case = SendRewardNotificationUseCase(sender=email_sender)
    consumer = RewardProcessedConsumer(config=kafka_config, use_case=use_case)

    # --- Start health endpoint in background daemon thread ---
    health_thread = threading.Thread(target=_run_health_server, name="health-server", daemon=True)
    health_thread.start()
    logger.info("Health server started on port 8002")

    # --- Graceful shutdown on SIGTERM / SIGINT ---
    def _handle_signal(signum: int, frame) -> None:
        sig_name = signal.Signals(signum).name
        logger.info("Received %s — initiating graceful shutdown…", sig_name)
        consumer.stop()

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    # --- Start consuming (blocks until stop() is called) ---
    logger.info("notification_service ready — consuming from 'reward.processed'")
    try:
        consumer.run()
    except Exception as exc:
        logger.exception("Consumer exited with an unexpected error: %s", exc)
        sys.exit(1)

    logger.info("notification_service shutdown complete")


if __name__ == "__main__":
    main()
