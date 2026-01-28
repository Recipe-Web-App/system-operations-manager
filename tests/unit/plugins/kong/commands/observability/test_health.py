"""Unit tests for health commands."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kong.exceptions import KongAPIError
from system_operations_manager.integrations.kong.models.observability import (
    UpstreamHealthSummary,
)
from system_operations_manager.plugins.kong.commands.observability.health import (
    register_health_commands,
)


class TestHealthCommands:
    """Tests for health CLI commands."""

    @pytest.fixture
    def app(
        self,
        mock_upstream_manager: MagicMock,
        mock_observability_manager: MagicMock,
    ) -> typer.Typer:
        """Create a test app with health commands."""
        app = typer.Typer()
        register_health_commands(
            app,
            lambda: mock_upstream_manager,
            lambda: mock_observability_manager,
        )
        return app


class TestHealthShow(TestHealthCommands):
    """Tests for health show command."""

    @pytest.mark.unit
    def test_show_displays_upstream_health(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_observability_manager: MagicMock,
    ) -> None:
        """health show should display upstream health status."""
        result = cli_runner.invoke(app, ["health", "show", "test-upstream"])

        assert result.exit_code == 0
        mock_observability_manager.get_upstream_health.assert_called_once_with("test-upstream")
        assert "healthy" in result.stdout.lower()

    @pytest.mark.unit
    def test_show_displays_targets(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_observability_manager: MagicMock,
    ) -> None:
        """health show should display target details."""
        result = cli_runner.invoke(app, ["health", "show", "test-upstream"])

        assert result.exit_code == 0
        # Should show target addresses
        assert "api1:8080" in result.stdout or "8080" in result.stdout

    @pytest.mark.unit
    def test_show_json_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_observability_manager: MagicMock,
    ) -> None:
        """health show should support JSON output."""
        result = cli_runner.invoke(app, ["health", "show", "test-upstream", "--output", "json"])

        assert result.exit_code == 0
        mock_observability_manager.get_upstream_health.assert_called_once()

    @pytest.mark.unit
    def test_show_error_handling(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_observability_manager: MagicMock,
    ) -> None:
        """health show should handle KongAPIError gracefully."""
        mock_observability_manager.get_upstream_health.side_effect = KongAPIError(
            "Upstream not found",
            status_code=404,
        )

        result = cli_runner.invoke(app, ["health", "show", "nonexistent"])

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()


class TestHealthList(TestHealthCommands):
    """Tests for health list command."""

    @pytest.mark.unit
    def test_list_displays_all_upstreams(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_observability_manager: MagicMock,
    ) -> None:
        """health list should display all upstreams."""
        result = cli_runner.invoke(app, ["health", "list"])

        assert result.exit_code == 0
        mock_observability_manager.list_upstreams_health.assert_called_once()
        assert "upstream-1" in result.stdout

    @pytest.mark.unit
    def test_list_unhealthy_only(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_observability_manager: MagicMock,
    ) -> None:
        """health list should filter to unhealthy only."""
        result = cli_runner.invoke(app, ["health", "list", "--unhealthy-only"])

        assert result.exit_code == 0
        # Should only show upstream-2 which is unhealthy
        assert "upstream-2" in result.stdout

    @pytest.mark.unit
    def test_list_no_upstreams(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_observability_manager: MagicMock,
    ) -> None:
        """health list should show message when no upstreams."""
        mock_observability_manager.list_upstreams_health.return_value = []

        result = cli_runner.invoke(app, ["health", "list"])

        assert result.exit_code == 0
        assert "no upstreams" in result.stdout.lower()

    @pytest.mark.unit
    def test_list_all_healthy(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_observability_manager: MagicMock,
    ) -> None:
        """health list --unhealthy-only should show message when all healthy."""
        mock_observability_manager.list_upstreams_health.return_value = [
            UpstreamHealthSummary(
                upstream_name="upstream-1",
                overall_health="HEALTHY",
                total_targets=2,
                healthy_targets=2,
                unhealthy_targets=0,
                targets=[],
            ),
        ]

        result = cli_runner.invoke(app, ["health", "list", "--unhealthy-only"])

        assert result.exit_code == 0
        assert "all upstreams are healthy" in result.stdout.lower()

    @pytest.mark.unit
    def test_list_json_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_observability_manager: MagicMock,
    ) -> None:
        """health list should support JSON output."""
        result = cli_runner.invoke(app, ["health", "list", "--output", "json"])

        assert result.exit_code == 0
        mock_observability_manager.list_upstreams_health.assert_called_once()


class TestHealthSet(TestHealthCommands):
    """Tests for health set command."""

    @pytest.mark.unit
    def test_set_requires_options(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """health set should fail without any options."""
        result = cli_runner.invoke(app, ["health", "set", "test-upstream"])

        assert result.exit_code == 1
        assert "no health check options" in result.stdout.lower()

    @pytest.mark.unit
    def test_set_active_type(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_upstream_manager: MagicMock,
    ) -> None:
        """health set should update active health check type."""
        from system_operations_manager.integrations.kong.models.upstream import Upstream

        mock_upstream = MagicMock()
        mock_upstream.model_dump.return_value = {
            "name": "test-upstream",
            "healthchecks": {},
        }
        mock_upstream_manager.get.return_value = mock_upstream
        mock_upstream_manager.update.return_value = Upstream(name="test-upstream")

        result = cli_runner.invoke(app, ["health", "set", "test-upstream", "--active-type", "http"])

        assert result.exit_code == 0
        mock_upstream_manager.update.assert_called_once()

    @pytest.mark.unit
    def test_set_active_http_path(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_upstream_manager: MagicMock,
    ) -> None:
        """health set should update active HTTP path."""
        from system_operations_manager.integrations.kong.models.upstream import Upstream

        mock_upstream = MagicMock()
        mock_upstream.model_dump.return_value = {
            "name": "test-upstream",
            "healthchecks": {},
        }
        mock_upstream_manager.get.return_value = mock_upstream
        mock_upstream_manager.update.return_value = Upstream(name="test-upstream")

        result = cli_runner.invoke(
            app, ["health", "set", "test-upstream", "--active-http-path", "/health"]
        )

        assert result.exit_code == 0
        mock_upstream_manager.update.assert_called_once()

    @pytest.mark.unit
    def test_set_passive_options(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_upstream_manager: MagicMock,
    ) -> None:
        """health set should update passive health check options."""
        from system_operations_manager.integrations.kong.models.upstream import Upstream

        mock_upstream = MagicMock()
        mock_upstream.model_dump.return_value = {
            "name": "test-upstream",
            "healthchecks": {},
        }
        mock_upstream_manager.get.return_value = mock_upstream
        mock_upstream_manager.update.return_value = Upstream(name="test-upstream")

        result = cli_runner.invoke(
            app,
            [
                "health",
                "set",
                "test-upstream",
                "--passive-unhealthy-failures",
                "5",
            ],
        )

        assert result.exit_code == 0
        mock_upstream_manager.update.assert_called_once()

    @pytest.mark.unit
    def test_set_error_handling(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_upstream_manager: MagicMock,
    ) -> None:
        """health set should handle KongAPIError gracefully."""
        mock_upstream_manager.get.side_effect = KongAPIError(
            "Upstream not found",
            status_code=404,
        )

        result = cli_runner.invoke(app, ["health", "set", "nonexistent", "--active-type", "http"])

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()


class TestHealthFailures(TestHealthCommands):
    """Tests for health failures command."""

    @pytest.mark.unit
    def test_failures_displays_list(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_observability_manager: MagicMock,
    ) -> None:
        """health failures should display failure list."""
        result = cli_runner.invoke(app, ["health", "failures", "test-upstream"])

        assert result.exit_code == 0
        mock_observability_manager.get_health_failures.assert_called_once_with("test-upstream")
        assert "api1:8080" in result.stdout or "health_check_failed" in result.stdout

    @pytest.mark.unit
    def test_failures_shows_details(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_observability_manager: MagicMock,
    ) -> None:
        """health failures should show failure details."""
        result = cli_runner.invoke(app, ["health", "failures", "test-upstream"])

        assert result.exit_code == 0
        # Should show failure types
        assert (
            "health_check_failed" in result.stdout.lower() or "dns_error" in result.stdout.lower()
        )

    @pytest.mark.unit
    def test_failures_no_failures(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_observability_manager: MagicMock,
    ) -> None:
        """health failures should show message when no failures."""
        mock_observability_manager.get_health_failures.return_value = []

        result = cli_runner.invoke(app, ["health", "failures", "test-upstream"])

        assert result.exit_code == 0
        assert (
            "no health check failures" in result.stdout.lower()
            or "no failures" in result.stdout.lower()
        )

    @pytest.mark.unit
    def test_failures_json_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_observability_manager: MagicMock,
    ) -> None:
        """health failures should support JSON output."""
        result = cli_runner.invoke(app, ["health", "failures", "test-upstream", "--output", "json"])

        assert result.exit_code == 0
        mock_observability_manager.get_health_failures.assert_called_once()

    @pytest.mark.unit
    def test_failures_error_handling(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_observability_manager: MagicMock,
    ) -> None:
        """health failures should handle KongAPIError gracefully."""
        mock_observability_manager.get_health_failures.side_effect = KongAPIError(
            "Upstream not found",
            status_code=404,
        )

        result = cli_runner.invoke(app, ["health", "failures", "nonexistent"])

        assert result.exit_code == 1
        assert "error" in result.stdout.lower()
