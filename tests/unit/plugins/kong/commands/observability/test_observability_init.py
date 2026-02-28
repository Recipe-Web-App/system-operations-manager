"""Unit tests for observability __init__.py registration function."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock, patch

import pytest
import typer

from system_operations_manager.plugins.kong.commands.observability import (
    register_observability_commands,
)


def _make_factory(mock: MagicMock) -> Callable[[], MagicMock]:
    return lambda: mock


class TestRegisterObservabilityCommandsBase:
    """Base class that provides common fixtures for observability init tests."""

    @pytest.fixture
    def mock_plugin_manager(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def mock_upstream_manager(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def mock_observability_manager(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def app(self) -> typer.Typer:
        return typer.Typer()


class TestRegisterObservabilityCommandsNoOptional(TestRegisterObservabilityCommandsBase):
    """Tests for register_observability_commands without optional managers."""

    @pytest.mark.unit
    def test_registers_observability_subapp_without_optional_managers(
        self,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
        mock_upstream_manager: MagicMock,
        mock_observability_manager: MagicMock,
    ) -> None:
        """register_observability_commands should register the observability sub-app."""
        register_observability_commands(
            app,
            _make_factory(mock_plugin_manager),
            _make_factory(mock_upstream_manager),
            _make_factory(mock_observability_manager),
        )

        # The app should now have a registered group named "observability"
        registered_names = [g.name for g in app.registered_groups]
        assert "observability" in registered_names

    @pytest.mark.unit
    def test_no_external_registration_when_no_optional_managers(
        self,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
        mock_upstream_manager: MagicMock,
        mock_observability_manager: MagicMock,
    ) -> None:
        """Optional external commands should not be registered when managers are None."""
        ext_module = "system_operations_manager.plugins.kong.commands.observability.external"

        with (
            patch(f"{ext_module}.register_external_metrics_commands") as m_metrics,
            patch(f"{ext_module}.register_external_logs_commands") as m_logs,
            patch(f"{ext_module}.register_external_tracing_commands") as m_tracing,
        ):
            register_observability_commands(
                app,
                _make_factory(mock_plugin_manager),
                _make_factory(mock_upstream_manager),
                _make_factory(mock_observability_manager),
                get_metrics_manager=None,
                get_logs_manager=None,
                get_tracing_manager=None,
            )

        m_metrics.assert_not_called()
        m_logs.assert_not_called()
        m_tracing.assert_not_called()


class TestRegisterObservabilityCommandsWithMetricsManager(TestRegisterObservabilityCommandsBase):
    """Tests for register_observability_commands with an optional metrics manager."""

    @pytest.mark.unit
    def test_registers_external_metrics_commands_when_manager_provided(
        self,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
        mock_upstream_manager: MagicMock,
        mock_observability_manager: MagicMock,
    ) -> None:
        """External metrics commands should be registered when get_metrics_manager is given."""
        mock_metrics_manager: MagicMock = MagicMock()
        ext_module = "system_operations_manager.plugins.kong.commands.observability.external"

        with patch(f"{ext_module}.register_external_metrics_commands") as m_metrics:
            register_observability_commands(
                app,
                _make_factory(mock_plugin_manager),
                _make_factory(mock_upstream_manager),
                _make_factory(mock_observability_manager),
                get_metrics_manager=_make_factory(mock_metrics_manager),
            )

        m_metrics.assert_called_once()

    @pytest.mark.unit
    def test_external_logs_and_tracing_not_called_when_only_metrics_provided(
        self,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
        mock_upstream_manager: MagicMock,
        mock_observability_manager: MagicMock,
    ) -> None:
        """External logs and tracing commands should not be registered without their managers."""
        mock_metrics_manager: MagicMock = MagicMock()
        ext_module = "system_operations_manager.plugins.kong.commands.observability.external"

        with (
            patch(f"{ext_module}.register_external_metrics_commands"),
            patch(f"{ext_module}.register_external_logs_commands") as m_logs,
            patch(f"{ext_module}.register_external_tracing_commands") as m_tracing,
        ):
            register_observability_commands(
                app,
                _make_factory(mock_plugin_manager),
                _make_factory(mock_upstream_manager),
                _make_factory(mock_observability_manager),
                get_metrics_manager=_make_factory(mock_metrics_manager),
            )

        m_logs.assert_not_called()
        m_tracing.assert_not_called()


class TestRegisterObservabilityCommandsWithLogsManager(TestRegisterObservabilityCommandsBase):
    """Tests for register_observability_commands with an optional logs manager."""

    @pytest.mark.unit
    def test_registers_external_logs_commands_when_manager_provided(
        self,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
        mock_upstream_manager: MagicMock,
        mock_observability_manager: MagicMock,
    ) -> None:
        """External logs commands should be registered when get_logs_manager is given."""
        mock_logs_manager: MagicMock = MagicMock()
        ext_module = "system_operations_manager.plugins.kong.commands.observability.external"

        with patch(f"{ext_module}.register_external_logs_commands") as m_logs:
            register_observability_commands(
                app,
                _make_factory(mock_plugin_manager),
                _make_factory(mock_upstream_manager),
                _make_factory(mock_observability_manager),
                get_logs_manager=_make_factory(mock_logs_manager),
            )

        m_logs.assert_called_once()

    @pytest.mark.unit
    def test_external_metrics_and_tracing_not_called_when_only_logs_provided(
        self,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
        mock_upstream_manager: MagicMock,
        mock_observability_manager: MagicMock,
    ) -> None:
        """External metrics and tracing commands should not be registered without their managers."""
        mock_logs_manager: MagicMock = MagicMock()
        ext_module = "system_operations_manager.plugins.kong.commands.observability.external"

        with (
            patch(f"{ext_module}.register_external_metrics_commands") as m_metrics,
            patch(f"{ext_module}.register_external_logs_commands"),
            patch(f"{ext_module}.register_external_tracing_commands") as m_tracing,
        ):
            register_observability_commands(
                app,
                _make_factory(mock_plugin_manager),
                _make_factory(mock_upstream_manager),
                _make_factory(mock_observability_manager),
                get_logs_manager=_make_factory(mock_logs_manager),
            )

        m_metrics.assert_not_called()
        m_tracing.assert_not_called()


class TestRegisterObservabilityCommandsWithTracingManager(TestRegisterObservabilityCommandsBase):
    """Tests for register_observability_commands with an optional tracing manager."""

    @pytest.mark.unit
    def test_registers_external_tracing_commands_when_manager_provided(
        self,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
        mock_upstream_manager: MagicMock,
        mock_observability_manager: MagicMock,
    ) -> None:
        """External tracing commands should be registered when get_tracing_manager is given."""
        mock_tracing_manager: MagicMock = MagicMock()
        ext_module = "system_operations_manager.plugins.kong.commands.observability.external"

        with patch(f"{ext_module}.register_external_tracing_commands") as m_tracing:
            register_observability_commands(
                app,
                _make_factory(mock_plugin_manager),
                _make_factory(mock_upstream_manager),
                _make_factory(mock_observability_manager),
                get_tracing_manager=_make_factory(mock_tracing_manager),
            )

        m_tracing.assert_called_once()

    @pytest.mark.unit
    def test_external_metrics_and_logs_not_called_when_only_tracing_provided(
        self,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
        mock_upstream_manager: MagicMock,
        mock_observability_manager: MagicMock,
    ) -> None:
        """External metrics and logs commands should not be registered without their managers."""
        mock_tracing_manager: MagicMock = MagicMock()
        ext_module = "system_operations_manager.plugins.kong.commands.observability.external"

        with (
            patch(f"{ext_module}.register_external_metrics_commands") as m_metrics,
            patch(f"{ext_module}.register_external_logs_commands") as m_logs,
            patch(f"{ext_module}.register_external_tracing_commands"),
        ):
            register_observability_commands(
                app,
                _make_factory(mock_plugin_manager),
                _make_factory(mock_upstream_manager),
                _make_factory(mock_observability_manager),
                get_tracing_manager=_make_factory(mock_tracing_manager),
            )

        m_metrics.assert_not_called()
        m_logs.assert_not_called()


class TestRegisterObservabilityCommandsWithAllManagers(TestRegisterObservabilityCommandsBase):
    """Tests for register_observability_commands with all optional managers."""

    @pytest.mark.unit
    def test_registers_all_external_commands_when_all_managers_provided(
        self,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
        mock_upstream_manager: MagicMock,
        mock_observability_manager: MagicMock,
    ) -> None:
        """All three external command groups should be registered when all managers given."""
        mock_metrics_manager: MagicMock = MagicMock()
        mock_logs_manager: MagicMock = MagicMock()
        mock_tracing_manager: MagicMock = MagicMock()
        ext_module = "system_operations_manager.plugins.kong.commands.observability.external"

        with (
            patch(f"{ext_module}.register_external_metrics_commands") as m_metrics,
            patch(f"{ext_module}.register_external_logs_commands") as m_logs,
            patch(f"{ext_module}.register_external_tracing_commands") as m_tracing,
        ):
            register_observability_commands(
                app,
                _make_factory(mock_plugin_manager),
                _make_factory(mock_upstream_manager),
                _make_factory(mock_observability_manager),
                get_metrics_manager=_make_factory(mock_metrics_manager),
                get_logs_manager=_make_factory(mock_logs_manager),
                get_tracing_manager=_make_factory(mock_tracing_manager),
            )

        m_metrics.assert_called_once()
        m_logs.assert_called_once()
        m_tracing.assert_called_once()
