"""
End-to-end tests for the restaurant_service FastAPI application.

The KafkaMealEventPublisher is replaced with a MagicMock so that no real
Kafka broker is needed during test execution.
"""
import pytest
from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid4

from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI

from restaurant_service.application.use_cases import RegisterMealUseCase
from restaurant_service.domain.ports import IEventPublisher
from restaurant_service.infrastructure.in_memory_repository import InMemoryTransactionRepository
from restaurant_service.infrastructure.http_router import router


def build_test_app() -> FastAPI:
    """Build a minimal FastAPI app with mocked dependencies (no real Kafka)."""
    app = FastAPI()
    app.include_router(router)

    mock_publisher = MagicMock(spec=IEventPublisher)
    repository = InMemoryTransactionRepository()
    use_case = RegisterMealUseCase(publisher=mock_publisher, repository=repository)

    app.state.kafka_publisher = mock_publisher
    app.state.transaction_repository = repository
    app.state.register_meal_use_case = use_case
    return app


@pytest.fixture
def test_app() -> FastAPI:
    """Fresh test app per test with mock publisher."""
    return build_test_app()


@pytest.mark.asyncio
async def test_post_meal_returns_201(test_app):
    """A valid POST /api/v1/meals payload must return HTTP 201 with transaction_id."""
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://testserver") as client:
        response = await client.post("/api/v1/meals", json={
            "card_number": "4532-TEST-1234",
            "restaurant_code": "REST-001",
            "amount": "150.00",
            "customer_email": "customer@example.com",
        })

    assert response.status_code == 201
    data = response.json()
    assert "transaction_id" in data
    assert data["card_number"] == "4532-TEST-1234"
    assert data["restaurant_code"] == "REST-001"
    assert data["currency"] == "PEN"


@pytest.mark.asyncio
async def test_post_meal_missing_card_number_returns_422(test_app):
    """A POST /api/v1/meals without card_number must return HTTP 422."""
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://testserver") as client:
        response = await client.post("/api/v1/meals", json={
            "restaurant_code": "REST-001",
            "amount": "50.00",
        })

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_post_meal_negative_amount_returns_422(test_app):
    """A POST /api/v1/meals with negative amount must return HTTP 422."""
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://testserver") as client:
        response = await client.post("/api/v1/meals", json={
            "card_number": "4532-TEST-1234",
            "restaurant_code": "REST-001",
            "amount": "-10.00",
        })

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_post_meal_zero_amount_returns_422(test_app):
    """A POST /api/v1/meals with amount == 0 must return HTTP 422."""
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://testserver") as client:
        response = await client.post("/api/v1/meals", json={
            "card_number": "4532-TEST-1234",
            "restaurant_code": "REST-001",
            "amount": "0",
        })

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_post_meal_missing_restaurant_code_returns_422(test_app):
    """A POST /api/v1/meals without restaurant_code must return HTTP 422."""
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://testserver") as client:
        response = await client.post("/api/v1/meals", json={
            "card_number": "4532-TEST-1234",
            "amount": "50.00",
        })

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_post_meal_empty_card_number_returns_422(test_app):
    """An empty card_number passes Pydantic but fails domain validation → 422.

    This exercises the domain-exception handler in the router (InvalidCardNumberError),
    distinct from Pydantic's automatic field validation.
    """
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://testserver") as client:
        response = await client.post("/api/v1/meals", json={
            "card_number": "   ",
            "restaurant_code": "REST-001",
            "amount": "50.00",
        })

    assert response.status_code == 422
    assert "card number" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_transaction_invalid_uuid_returns_422(test_app):
    """A non-UUID transaction id in the path returns 422."""
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://testserver") as client:
        response = await client.get("/api/v1/meals/not-a-valid-uuid")

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_health_endpoint_returns_ok(test_app):
    """GET /health must return HTTP 200 with status='ok'."""
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://testserver") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "restaurant_service"


@pytest.mark.asyncio
async def test_get_transaction_not_found_returns_404(test_app):
    """GET /api/v1/meals/{transaction_id} for unknown UUID must return HTTP 404."""
    unknown_id = str(uuid4())
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://testserver") as client:
        response = await client.get(f"/api/v1/meals/{unknown_id}")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
