import sys
import os
import pytest
from decimal import Decimal
from unittest.mock import MagicMock

# Ensure the project root is on sys.path so `shared` and `restaurant_service` are importable
# when pytest is run from any working directory.
_PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from restaurant_service.domain.ports import IEventPublisher, ITransactionRepository
from restaurant_service.application.use_cases import RegisterMealCommand


@pytest.fixture
def mock_publisher():
    mock = MagicMock(spec=IEventPublisher)
    return mock


@pytest.fixture
def mock_repository():
    mock = MagicMock(spec=ITransactionRepository)
    mock.exists.return_value = False
    return mock


@pytest.fixture
def sample_command():
    return RegisterMealCommand(
        card_number="4532-TEST-1234",
        restaurant_code="REST-001",
        amount=Decimal("100.00"),
        customer_email="test@example.com",
    )
