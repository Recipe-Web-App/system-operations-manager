"""Unit tests for Kong CLI commands."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kong.exceptions import (
    KongNotFoundError,
)
from system_operations_manager.integrations.kong.models.consumer import Consumer
from system_operations_manager.integrations.kong.models.plugin import KongPluginEntity
from system_operations_manager.integrations.kong.models.route import Route
from system_operations_manager.integrations.kong.models.service import Service
from system_operations_manager.integrations.kong.models.upstream import Target, Upstream


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def mock_service_manager() -> MagicMock:
    """Create a mock ServiceManager."""
    manager = MagicMock()
    manager.list.return_value = (
        [
            Service(id="svc-1", name="api-1", host="api1.local", port=80),
            Service(id="svc-2", name="api-2", host="api2.local", port=8080),
        ],
        None,
    )
    manager.get.return_value = Service(id="svc-1", name="api-1", host="api1.local", port=80)
    manager.create.return_value = Service(id="new-svc", name="new-api", host="new.local", port=80)
    manager.update.return_value = Service(id="svc-1", name="api-1", host="updated.local", port=80)
    manager.get_routes.return_value = [Route(id="route-1", name="route-1", paths=["/api"])]
    return manager


@pytest.fixture
def mock_route_manager() -> MagicMock:
    """Create a mock RouteManager."""
    manager = MagicMock()
    manager.list.return_value = (
        [Route(id="route-1", name="my-route", paths=["/api"])],
        None,
    )
    manager.get.return_value = Route(id="route-1", name="my-route", paths=["/api"])
    manager.create.return_value = Route(id="new-route", name="new-route", paths=["/new"])
    return manager


@pytest.fixture
def mock_consumer_manager() -> MagicMock:
    """Create a mock ConsumerManager."""
    manager = MagicMock()
    manager.list.return_value = (
        [Consumer(id="consumer-1", username="user1")],
        None,
    )
    manager.get.return_value = Consumer(id="consumer-1", username="user1")
    manager.create.return_value = Consumer(id="new-consumer", username="new-user")
    return manager


@pytest.fixture
def mock_upstream_manager() -> MagicMock:
    """Create a mock UpstreamManager."""
    manager = MagicMock()
    manager.list.return_value = (
        [Upstream(id="upstream-1", name="my-upstream")],
        None,
    )
    manager.get.return_value = Upstream(id="upstream-1", name="my-upstream")
    manager.list_targets.return_value = (
        [Target(id="target-1", target="192.168.1.1:8080", weight=100)],
        None,
    )
    return manager


@pytest.fixture
def mock_plugin_manager() -> MagicMock:
    """Create a mock KongPluginManager."""
    manager = MagicMock()
    manager.list.return_value = (
        [KongPluginEntity(id="plugin-1", name="rate-limiting", enabled=True)],
        None,
    )
    manager.get.return_value = KongPluginEntity(id="plugin-1", name="rate-limiting", enabled=True)
    manager.list_available.return_value = {
        "rate-limiting": MagicMock(name="rate-limiting", version="3.0.0", priority=901),
        "key-auth": MagicMock(name="key-auth", version="3.0.0", priority=1003),
    }
    return manager


class TestServiceCommands:
    """Tests for service CLI commands."""

    @pytest.fixture
    def app(self, mock_service_manager: MagicMock) -> typer.Typer:
        """Create a test app with service commands."""
        from system_operations_manager.plugins.kong.commands.services import (
            register_service_commands,
        )

        app = typer.Typer()
        register_service_commands(app, lambda: mock_service_manager)
        return app

    @pytest.mark.unit
    def test_list_services(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_service_manager: MagicMock,
    ) -> None:
        """services list should display services."""
        result = cli_runner.invoke(app, ["services", "list"])

        assert result.exit_code == 0
        assert "api-1" in result.stdout or mock_service_manager.list.called

    @pytest.mark.unit
    def test_list_services_json(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """services list --output json should output JSON."""
        result = cli_runner.invoke(app, ["services", "list", "--output", "json"])

        assert result.exit_code == 0

    @pytest.mark.unit
    def test_get_service(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_service_manager: MagicMock,
    ) -> None:
        """services get should display service details."""
        result = cli_runner.invoke(app, ["services", "get", "api-1"])

        assert result.exit_code == 0
        mock_service_manager.get.assert_called_once_with("api-1")

    @pytest.mark.unit
    def test_create_service(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_service_manager: MagicMock,
    ) -> None:
        """services create should create a service."""
        result = cli_runner.invoke(app, ["services", "create", "--host", "api.example.com"])

        assert result.exit_code == 0
        mock_service_manager.create.assert_called_once()

    @pytest.mark.unit
    def test_delete_service_with_force(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_service_manager: MagicMock,
    ) -> None:
        """services delete --force should delete without confirmation."""
        result = cli_runner.invoke(app, ["services", "delete", "api-1", "--force"])

        assert result.exit_code == 0
        mock_service_manager.delete.assert_called_once_with("api-1")

    @pytest.mark.unit
    def test_service_routes(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_service_manager: MagicMock,
    ) -> None:
        """services routes should list routes for service."""
        result = cli_runner.invoke(app, ["services", "routes", "api-1"])

        assert result.exit_code == 0
        mock_service_manager.get_routes.assert_called_once_with("api-1")


class TestRouteCommands:
    """Tests for route CLI commands."""

    @pytest.fixture
    def app(self, mock_route_manager: MagicMock) -> typer.Typer:
        """Create a test app with route commands."""
        from system_operations_manager.plugins.kong.commands.routes import (
            register_route_commands,
        )

        app = typer.Typer()
        register_route_commands(app, lambda: mock_route_manager)
        return app

    @pytest.mark.unit
    def test_list_routes(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_route_manager: MagicMock,
    ) -> None:
        """routes list should display routes."""
        result = cli_runner.invoke(app, ["routes", "list"])

        assert result.exit_code == 0
        mock_route_manager.list.assert_called_once()

    @pytest.mark.unit
    def test_get_route(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_route_manager: MagicMock,
    ) -> None:
        """routes get should display route details."""
        result = cli_runner.invoke(app, ["routes", "get", "my-route"])

        assert result.exit_code == 0
        mock_route_manager.get.assert_called_once_with("my-route")

    @pytest.mark.unit
    def test_create_route(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_route_manager: MagicMock,
    ) -> None:
        """routes create should create a route."""
        result = cli_runner.invoke(
            app, ["routes", "create", "--service", "my-service", "--path", "/api"]
        )

        assert result.exit_code == 0
        mock_route_manager.create.assert_called_once()


class TestConsumerCommands:
    """Tests for consumer CLI commands."""

    @pytest.fixture
    def app(self, mock_consumer_manager: MagicMock) -> typer.Typer:
        """Create a test app with consumer commands."""
        from system_operations_manager.plugins.kong.commands.consumers import (
            register_consumer_commands,
        )

        app = typer.Typer()
        register_consumer_commands(app, lambda: mock_consumer_manager)
        return app

    @pytest.mark.unit
    def test_list_consumers(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        """consumers list should display consumers."""
        result = cli_runner.invoke(app, ["consumers", "list"])

        assert result.exit_code == 0
        mock_consumer_manager.list.assert_called_once()

    @pytest.mark.unit
    def test_get_consumer(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        """consumers get should display consumer details."""
        result = cli_runner.invoke(app, ["consumers", "get", "user1"])

        assert result.exit_code == 0
        mock_consumer_manager.get.assert_called_once_with("user1")

    @pytest.mark.unit
    def test_create_consumer(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_consumer_manager: MagicMock,
    ) -> None:
        """consumers create should create a consumer."""
        result = cli_runner.invoke(app, ["consumers", "create", "--username", "new-user"])

        assert result.exit_code == 0
        mock_consumer_manager.create.assert_called_once()


class TestUpstreamCommands:
    """Tests for upstream CLI commands."""

    @pytest.fixture
    def app(self, mock_upstream_manager: MagicMock) -> typer.Typer:
        """Create a test app with upstream commands."""
        from system_operations_manager.plugins.kong.commands.upstreams import (
            register_upstream_commands,
        )

        app = typer.Typer()
        register_upstream_commands(app, lambda: mock_upstream_manager)
        return app

    @pytest.mark.unit
    def test_list_upstreams(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_upstream_manager: MagicMock,
    ) -> None:
        """upstreams list should display upstreams."""
        result = cli_runner.invoke(app, ["upstreams", "list"])

        assert result.exit_code == 0
        mock_upstream_manager.list.assert_called_once()

    @pytest.mark.unit
    def test_get_upstream(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_upstream_manager: MagicMock,
    ) -> None:
        """upstreams get should display upstream details."""
        result = cli_runner.invoke(app, ["upstreams", "get", "my-upstream"])

        assert result.exit_code == 0
        mock_upstream_manager.get.assert_called_once_with("my-upstream")

    @pytest.mark.unit
    def test_list_targets(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_upstream_manager: MagicMock,
    ) -> None:
        """upstreams targets list should list targets."""
        result = cli_runner.invoke(app, ["upstreams", "targets", "list", "my-upstream"])

        assert result.exit_code == 0
        mock_upstream_manager.list_targets.assert_called_once()


class TestPluginCommands:
    """Tests for plugin CLI commands."""

    @pytest.fixture
    def app(self, mock_plugin_manager: MagicMock) -> typer.Typer:
        """Create a test app with plugin commands."""
        from system_operations_manager.plugins.kong.commands.plugins import (
            register_plugin_commands,
        )

        app = typer.Typer()
        register_plugin_commands(app, lambda: mock_plugin_manager)
        return app

    @pytest.mark.unit
    def test_list_plugins(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """plugins list should display enabled plugins."""
        result = cli_runner.invoke(app, ["plugins", "list"])

        assert result.exit_code == 0
        mock_plugin_manager.list.assert_called_once()

    @pytest.mark.unit
    def test_list_available_plugins(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """plugins available should list available plugins."""
        result = cli_runner.invoke(app, ["plugins", "available"])

        assert result.exit_code == 0
        mock_plugin_manager.list_available.assert_called_once()

    @pytest.mark.unit
    def test_get_plugin(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """plugins get should display plugin details."""
        result = cli_runner.invoke(app, ["plugins", "get", "plugin-1"])

        assert result.exit_code == 0
        mock_plugin_manager.get.assert_called_once_with("plugin-1")

    @pytest.mark.unit
    def test_enable_plugin(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """plugins enable should enable a plugin."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="new-plugin", name="rate-limiting", enabled=True
        )

        result = cli_runner.invoke(app, ["plugins", "enable", "rate-limiting"])

        assert result.exit_code == 0
        mock_plugin_manager.enable.assert_called_once()

    @pytest.mark.unit
    def test_enable_plugin_with_config(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """plugins enable --config should pass configuration."""
        mock_plugin_manager.enable.return_value = KongPluginEntity(
            id="new-plugin", name="rate-limiting", enabled=True, config={"minute": 100}
        )

        result = cli_runner.invoke(
            app, ["plugins", "enable", "rate-limiting", "--config", "minute=100"]
        )

        assert result.exit_code == 0

    @pytest.mark.unit
    def test_disable_plugin(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_plugin_manager: MagicMock,
    ) -> None:
        """plugins disable --force should disable plugin."""
        result = cli_runner.invoke(app, ["plugins", "disable", "plugin-1", "--force"])

        assert result.exit_code == 0
        mock_plugin_manager.disable.assert_called_once_with("plugin-1")


class TestCommandErrorHandling:
    """Tests for CLI command error handling."""

    @pytest.fixture
    def app(self) -> typer.Typer:
        """Create a test app with error-raising manager."""
        from system_operations_manager.plugins.kong.commands.services import (
            register_service_commands,
        )

        error_manager = MagicMock()
        error_manager.get.side_effect = KongNotFoundError("Not found", "services/none")

        app = typer.Typer()
        register_service_commands(app, lambda: error_manager)
        return app

    @pytest.mark.unit
    def test_not_found_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """Commands should handle KongNotFoundError gracefully."""
        result = cli_runner.invoke(app, ["services", "get", "nonexistent"])

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower() or "error" in result.stdout.lower()
