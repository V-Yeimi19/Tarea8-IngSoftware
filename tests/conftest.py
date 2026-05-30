import sys
import os
import pytest
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock
from uuid import uuid4

# Make shared/ importable from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture
def sample_meal_payload():
    return {
        "card_number": "4532-E2E-TEST",
        "restaurant_code": "REST-E2E",
        "amount": 100.00,
        "customer_email": "e2e@test.com",
    }


@pytest.fixture
def mock_kafka_producer():
    mock = MagicMock()
    mock.publish_meal_transaction = MagicMock(return_value=None)
    mock.is_connected = MagicMock(return_value=True)
    return mock


@pytest.fixture
def mock_email_sender():
    mock = MagicMock()
    mock.send = MagicMock(return_value=None)
    return mock
