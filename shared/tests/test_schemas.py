"""Unit tests for shared/events/schemas.py — covers from_json class methods and model fields."""
import json
import pytest
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4, UUID

from shared.events.schemas import MealTransactionEvent, RewardProcessedEvent, DLQEvent


@pytest.fixture
def meal_dict():
    return {
        "transaction_id": str(uuid4()),
        "card_number": "4532-TEST-1234",
        "restaurant_code": "REST-001",
        "amount": "85.50",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "currency": "PEN",
    }


@pytest.fixture
def reward_dict():
    return {
        "event_id": str(uuid4()),
        "transaction_id": str(uuid4()),
        "card_number": "4532-TEST-1234",
        "customer_email": "client@example.com",
        "points_earned": 85,
        "cashback_amount": "2.57",
        "total_points_balance": 500,
        "total_cashback_balance": "15.00",
        "restaurant_code": "REST-001",
        "processed_at": datetime.now(timezone.utc).isoformat(),
    }


class TestMealTransactionEvent:
    def test_from_json_with_dict(self, meal_dict):
        event = MealTransactionEvent.from_json(meal_dict)
        assert event.card_number == "4532-TEST-1234"
        assert event.currency == "PEN"

    def test_from_json_with_json_string(self, meal_dict):
        json_str = json.dumps(meal_dict)
        event = MealTransactionEvent.from_json(json_str)
        assert isinstance(event.transaction_id, UUID)
        assert event.amount == Decimal("85.50")

    def test_from_json_with_bytes(self, meal_dict):
        json_bytes = json.dumps(meal_dict).encode("utf-8")
        event = MealTransactionEvent.from_json(json_bytes)
        assert event.restaurant_code == "REST-001"

    def test_currency_defaults_to_pen(self, meal_dict):
        del meal_dict["currency"]
        event = MealTransactionEvent.from_json(meal_dict)
        assert event.currency == "PEN"

    def test_model_dump_json_serializable(self, meal_dict):
        event = MealTransactionEvent.from_json(meal_dict)
        serialized = event.model_dump_json()
        reparsed = json.loads(serialized)
        assert reparsed["card_number"] == "4532-TEST-1234"


class TestRewardProcessedEvent:
    def test_from_json_with_dict(self, reward_dict):
        event = RewardProcessedEvent.from_json(reward_dict)
        assert event.points_earned == 85
        assert event.cashback_amount == Decimal("2.57")

    def test_from_json_with_json_string(self, reward_dict):
        event = RewardProcessedEvent.from_json(json.dumps(reward_dict))
        assert isinstance(event.event_id, UUID)

    def test_from_json_with_bytes(self, reward_dict):
        event = RewardProcessedEvent.from_json(json.dumps(reward_dict).encode())
        assert event.customer_email == "client@example.com"

    def test_total_balances_are_decimal(self, reward_dict):
        event = RewardProcessedEvent.from_json(reward_dict)
        assert isinstance(event.total_cashback_balance, Decimal)


class TestDLQEvent:
    def test_from_json_with_dict(self):
        data = {
            "original_topic": "meal.transactions",
            "original_message": {"foo": "bar"},
            "error": "ValidationError",
            "retry_count": 3,
            "failed_at": datetime.now(timezone.utc).isoformat(),
        }
        event = DLQEvent.from_json(data)
        assert event.original_topic == "meal.transactions"
        assert event.retry_count == 3

    def test_from_json_with_string(self):
        data = {
            "original_topic": "test",
            "original_message": {},
            "error": "boom",
            "retry_count": 1,
            "failed_at": datetime.now(timezone.utc).isoformat(),
        }
        event = DLQEvent.from_json(json.dumps(data))
        assert event.error == "boom"

    def test_model_dump_json_round_trip(self):
        data = {
            "original_topic": "meal.transactions",
            "original_message": {"amount": "100"},
            "error": "test error",
            "retry_count": 2,
            "failed_at": datetime.now(timezone.utc).isoformat(),
        }
        event = DLQEvent.from_json(data)
        serialized = event.model_dump_json()
        reparsed = json.loads(serialized)
        assert reparsed["retry_count"] == 2
