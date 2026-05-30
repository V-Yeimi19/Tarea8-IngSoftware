import logging
import os
import signal
import sys
import threading

import uvicorn
from fastapi import FastAPI

from shared.config import AppConfig, KafkaConfig, SMTPConfig
from rewards_service.application.use_cases import ProcessMealEventUseCase
from rewards_service.domain.reward_calculator import RewardCalculator
from rewards_service.infrastructure.database import get_engine, get_session_factory, init_db
from rewards_service.infrastructure.kafka_consumer import MealTransactionConsumer
from rewards_service.infrastructure.kafka_producer import KafkaRewardEventPublisher
from rewards_service.infrastructure.repository import SQLAlchemyAccountRepository

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FastAPI health-check app
# ---------------------------------------------------------------------------
health_app = FastAPI(title="rewards-service", version="1.0.0")


@health_app.get("/health")
def health_check():
    return {"status": "ok", "service": "rewards_service"}


@health_app.get("/ready")
def readiness_check():
    return {"status": "ready"}


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

def build_consumer(app_config: AppConfig) -> MealTransactionConsumer:
    engine = get_engine(app_config.database_url)
    init_db(engine)
    session_factory = get_session_factory(engine)
    session = session_factory()

    kafka_config = app_config.kafka
    smtp_config = SMTPConfig()
    calculator = RewardCalculator()
    repo = SQLAlchemyAccountRepository(session)
    publisher = KafkaRewardEventPublisher(kafka_config)
    use_case = ProcessMealEventUseCase(
        calculator=calculator,
        account_repo=repo,
        publisher=publisher,
        default_email=smtp_config.from_address,
    )
    consumer = MealTransactionConsumer(
        config=kafka_config,
        use_case=use_case,
        dlq_producer=publisher,
    )
    return consumer


def start_health_server() -> threading.Thread:
    """Run FastAPI/uvicorn in a daemon background thread on port 8001."""
    def _run():  # pragma: no cover - blocking uvicorn server entrypoint
        uvicorn.run(
            health_app,
            host="127.0.0.1",
            port=8001,
            log_level="warning",
        )

    thread = threading.Thread(target=_run, name="health-server", daemon=True)
    thread.start()
    logger.info("Health-check server started on port 8001")
    return thread


def main() -> None:
    app_config = AppConfig()
    consumer = build_consumer(app_config)

    # Graceful shutdown handler
    def _shutdown(signum, frame):
        logger.info("Received signal %s — initiating graceful shutdown", signum)
        consumer.stop()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    start_health_server()

    logger.info("Starting MealTransactionConsumer …")
    consumer.run()


if __name__ == "__main__":
    main()
