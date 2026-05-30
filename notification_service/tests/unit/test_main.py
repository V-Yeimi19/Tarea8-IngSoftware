"""Unit tests for notification_service/main.py — bootstrap wiring and health endpoints."""
import pytest
from unittest.mock import MagicMock, patch


class TestHealthEndpoints:
    def test_health_check_returns_ok(self):
        """health_check() reports the service as ok."""
        from notification_service.main import health_check
        result = health_check()
        assert result["status"] == "ok"
        assert result["service"] == "notification_service"

    def test_root_returns_service_info(self):
        """root() returns the service name and version."""
        from notification_service.main import root
        result = root()
        assert result["service"] == "notification_service"
        assert "version" in result


class TestRunHealthServer:
    def test_run_health_server_invokes_uvicorn(self):
        """_run_health_server starts uvicorn on the health app."""
        from notification_service import main as main_module
        with patch.object(main_module, "uvicorn") as mock_uvicorn:
            main_module._run_health_server()
            mock_uvicorn.run.assert_called_once()


class TestMain:
    def test_main_starts_health_thread_and_runs_consumer(self):
        """main() builds dependencies, starts the health thread and runs the consumer."""
        from notification_service import main as main_module

        mock_consumer = MagicMock()

        with patch.object(main_module, "KafkaConfig"), \
             patch.object(main_module, "SMTPConfig"), \
             patch.object(main_module, "SMTPEmailSender"), \
             patch.object(main_module, "SendRewardNotificationUseCase"), \
             patch.object(main_module, "RewardProcessedConsumer", return_value=mock_consumer), \
             patch.object(main_module.threading, "Thread") as MockThread, \
             patch.object(main_module.signal, "signal") as mock_signal:

            MockThread.return_value = MagicMock()
            main_module.main()

            MockThread.return_value.start.assert_called_once()
            mock_consumer.run.assert_called_once()
            assert mock_signal.call_count == 2

    def test_main_exits_on_consumer_exception(self):
        """If the consumer raises, main() logs and exits with code 1."""
        from notification_service import main as main_module

        mock_consumer = MagicMock()
        mock_consumer.run.side_effect = RuntimeError("kafka exploded")

        with patch.object(main_module, "KafkaConfig"), \
             patch.object(main_module, "SMTPConfig"), \
             patch.object(main_module, "SMTPEmailSender"), \
             patch.object(main_module, "SendRewardNotificationUseCase"), \
             patch.object(main_module, "RewardProcessedConsumer", return_value=mock_consumer), \
             patch.object(main_module.threading, "Thread") as MockThread, \
             patch.object(main_module.signal, "signal"):

            MockThread.return_value = MagicMock()
            with pytest.raises(SystemExit) as exc_info:
                main_module.main()
            assert exc_info.value.code == 1

    def test_shutdown_handler_stops_consumer(self):
        """The registered signal handler stops the consumer gracefully."""
        from notification_service import main as main_module

        mock_consumer = MagicMock()
        captured = {}

        def capture_signal(sig, handler):
            captured[sig] = handler

        with patch.object(main_module, "KafkaConfig"), \
             patch.object(main_module, "SMTPConfig"), \
             patch.object(main_module, "SMTPEmailSender"), \
             patch.object(main_module, "SendRewardNotificationUseCase"), \
             patch.object(main_module, "RewardProcessedConsumer", return_value=mock_consumer), \
             patch.object(main_module.threading, "Thread") as MockThread, \
             patch.object(main_module.signal, "signal", side_effect=capture_signal):

            MockThread.return_value = MagicMock()
            main_module.main()

        handler = next(iter(captured.values()))
        handler(2, None)
        mock_consumer.stop.assert_called_once()
