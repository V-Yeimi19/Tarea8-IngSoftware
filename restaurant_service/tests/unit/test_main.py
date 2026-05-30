"""Unit tests for restaurant_service/main.py — lifespan and app wiring.

The KafkaMealEventPublisher is patched so no real Kafka broker is contacted.
"""
import pytest
from unittest.mock import MagicMock, patch

from fastapi import FastAPI


class TestApp:
    def test_app_is_fastapi_instance(self):
        """The module-level `app` is a configured FastAPI application."""
        from restaurant_service.main import app
        assert isinstance(app, FastAPI)

    def test_app_exposes_meals_route(self):
        """The meals registration route is included in the app."""
        from restaurant_service.main import app
        paths = {route.path for route in app.routes}
        assert "/api/v1/meals" in paths

    def test_app_exposes_health_route(self):
        """The health route is included in the app."""
        from restaurant_service.main import app
        paths = {route.path for route in app.routes}
        assert "/health" in paths


class TestLifespan:
    @pytest.mark.asyncio
    async def test_lifespan_wires_dependencies_into_state(self):
        """Entering the lifespan attaches publisher, repository and use case to app.state."""
        from restaurant_service.main import lifespan

        mock_publisher = MagicMock()
        with patch(
            "restaurant_service.main.KafkaMealEventPublisher",
            return_value=mock_publisher,
        ):
            app = FastAPI()
            async with lifespan(app):
                assert app.state.kafka_publisher is mock_publisher
                assert app.state.transaction_repository is not None
                assert app.state.register_meal_use_case is not None

    @pytest.mark.asyncio
    async def test_lifespan_closes_publisher_on_shutdown(self):
        """Exiting the lifespan flushes/closes the Kafka publisher."""
        from restaurant_service.main import lifespan

        mock_publisher = MagicMock()
        with patch(
            "restaurant_service.main.KafkaMealEventPublisher",
            return_value=mock_publisher,
        ):
            app = FastAPI()
            async with lifespan(app):
                pass
            mock_publisher.close.assert_called_once()
