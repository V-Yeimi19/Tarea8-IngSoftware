"""Unit tests for rewards_service/main.py — bootstrap wiring and health endpoints.

All Kafka/network dependencies are patched; a real in-memory SQLite engine is used.
"""
import pytest
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine


class TestHealthEndpoints:
    def test_health_check_returns_ok(self):
        """health_check() reports the service as ok."""
        from rewards_service.main import health_check
        result = health_check()
        assert result["status"] == "ok"
        assert result["service"] == "rewards_service"

    def test_readiness_check_returns_ready(self):
        """readiness_check() reports the service as ready."""
        from rewards_service.main import readiness_check
        result = readiness_check()
        assert result["status"] == "ready"


class TestBuildConsumer:
    def test_build_consumer_returns_meal_transaction_consumer(self):
        """build_consumer wires the dependency graph and returns a consumer."""
        from rewards_service import main as main_module

        app_config = MagicMock()
        app_config.database_url = "sqlite:///:memory:"
        app_config.kafka = MagicMock()

        in_memory_engine = create_engine("sqlite:///:memory:")

        with patch.object(main_module, "get_engine", return_value=in_memory_engine), \
             patch.object(main_module, "init_db") as mock_init_db, \
             patch.object(main_module, "KafkaRewardEventPublisher") as MockPublisher, \
             patch.object(main_module, "MealTransactionConsumer") as MockConsumer:

            MockConsumer.return_value = MagicMock(name="consumer")
            consumer = main_module.build_consumer(app_config)

            mock_init_db.assert_called_once()
            MockPublisher.assert_called_once_with(app_config.kafka)
            MockConsumer.assert_called_once()
            assert consumer is MockConsumer.return_value


class TestStartHealthServer:
    def test_start_health_server_launches_daemon_thread(self):
        """start_health_server spins up a daemon thread running uvicorn."""
        from rewards_service import main as main_module

        with patch.object(main_module, "uvicorn") as mock_uvicorn, \
             patch.object(main_module.threading, "Thread") as MockThread:
            mock_thread = MagicMock()
            MockThread.return_value = mock_thread

            result = main_module.start_health_server()

            MockThread.assert_called_once()
            assert MockThread.call_args.kwargs["daemon"] is True
            mock_thread.start.assert_called_once()
            assert result is mock_thread


class TestMain:
    def test_main_registers_signals_and_runs_consumer(self):
        """main() builds the consumer, registers signal handlers and starts the run loop."""
        from rewards_service import main as main_module

        mock_consumer = MagicMock()

        with patch.object(main_module, "AppConfig") as MockAppConfig, \
             patch.object(main_module, "build_consumer", return_value=mock_consumer), \
             patch.object(main_module, "start_health_server") as mock_health, \
             patch.object(main_module.signal, "signal") as mock_signal:

            main_module.main()

            mock_health.assert_called_once()
            mock_consumer.run.assert_called_once()
            # SIGTERM and SIGINT handlers registered
            assert mock_signal.call_count == 2

    def test_shutdown_handler_stops_consumer(self):
        """The registered signal handler stops the consumer and exits."""
        from rewards_service import main as main_module

        mock_consumer = MagicMock()
        captured = {}

        def capture_signal(sig, handler):
            captured[sig] = handler

        with patch.object(main_module, "AppConfig"), \
             patch.object(main_module, "build_consumer", return_value=mock_consumer), \
             patch.object(main_module, "start_health_server"), \
             patch.object(main_module.signal, "signal", side_effect=capture_signal):

            main_module.main()

        # Invoke a captured handler and assert graceful shutdown
        handler = next(iter(captured.values()))
        with pytest.raises(SystemExit):
            handler(15, None)
        mock_consumer.stop.assert_called_once()
