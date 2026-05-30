import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from shared.config import KafkaConfig
from restaurant_service.application.use_cases import RegisterMealUseCase
from restaurant_service.infrastructure.in_memory_repository import InMemoryTransactionRepository
from restaurant_service.infrastructure.kafka_producer import KafkaMealEventPublisher
from restaurant_service.infrastructure.http_router import router

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
# Lifespan — initialise and teardown shared resources
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("Starting up restaurant_service…")

    kafka_config = KafkaConfig()
    publisher = KafkaMealEventPublisher(config=kafka_config)
    repository = InMemoryTransactionRepository()
    use_case = RegisterMealUseCase(publisher=publisher, repository=repository)

    # Attach to app.state so routes can access them via request.app.state
    app.state.kafka_publisher = publisher
    app.state.transaction_repository = repository
    app.state.register_meal_use_case = use_case

    logger.info("Dependencies initialised — publisher, repository, use_case ready")
    yield

    logger.info("Shutting down restaurant_service — flushing Kafka producer…")
    publisher.close()
    logger.info("Shutdown complete")


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Restaurant Service",
    description="Registers meal transactions and publishes events to Kafka for reward processing.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(router)

logger.info("restaurant_service FastAPI app created")
