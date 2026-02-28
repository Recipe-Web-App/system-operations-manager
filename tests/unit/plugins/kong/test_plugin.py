"""Unit tests for KongPlugin class."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kong.exceptions import KongAPIError
from system_operations_manager.plugins.kong.plugin import KongPlugin

# Module path prefix for patching imports inside _register_entity_commands
_CMD = "system_operations_manager.plugins.kong.commands"
_SVC = "system_operations_manager.services"


@pytest.fixture
def cli_runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def mock_client() -> MagicMock:
    client = MagicMock()
    client.get_status.return_value = {
        "database": {"reachable": True},
        "memory": {
            "lua_shared_dicts": {
                "kong": {"allocated_slabs": "1.23 MiB"},
            }
        },
    }
    client.get_info.return_value = {
        "hostname": "kong-node-1",
        "version": "3.4.0",
        "lua_version": "LuaJIT 2.1.0",
        "tagline": "Welcome to Kong",
        "plugins": {
            "available_on_server": {
                "rate-limiting": True,
                "key-auth": True,
                "openid-connect": True,
            },
            "enabled_in_cluster": ["rate-limiting", "key-auth"],
        },
    }
    return client


@pytest.fixture
def kong_plugin(mock_client: MagicMock) -> KongPlugin:
    """Create a KongPlugin with a mocked client."""
    plugin = KongPlugin()
    plugin._client = mock_client
    plugin._plugin_config = MagicMock()
    plugin._plugin_config.connection.base_url = "http://localhost:8001"
    plugin._plugin_config.observability = None
    return plugin


# ===========================================================================
# KongPlugin.__init__ / properties
# ===========================================================================


@pytest.mark.unit
class TestKongPluginProperties:
    """Tests for KongPlugin properties."""

    def test_client_property_returns_client(self, kong_plugin: KongPlugin) -> None:
        assert kong_plugin.client is not None

    def test_client_property_none_when_not_initialized(self) -> None:
        plugin = KongPlugin()
        assert plugin.client is None

    def test_plugin_config_property(self, kong_plugin: KongPlugin) -> None:
        assert kong_plugin.plugin_config is not None

    def test_plugin_config_none_when_not_initialized(self) -> None:
        plugin = KongPlugin()
        assert plugin.plugin_config is None

    def test_name_version_description(self) -> None:
        plugin = KongPlugin()
        assert plugin.name == "kong"
        assert plugin.version == "0.1.0"
        assert "kong" in plugin.description.lower()


# ===========================================================================
# KongPlugin.on_initialize
# ===========================================================================


@pytest.mark.unit
class TestKongPluginOnInitialize:
    """Tests for KongPlugin.on_initialize."""

    @patch("system_operations_manager.plugins.kong.plugin.KongPluginConfig")
    @patch("system_operations_manager.plugins.kong.plugin.KongAdminClient")
    def test_on_initialize_success(
        self,
        mock_admin_client_cls: MagicMock,
        mock_config_cls: MagicMock,
    ) -> None:
        mock_config = MagicMock()
        mock_config_cls.from_env.return_value = mock_config
        mock_admin_client_cls.return_value = MagicMock()

        plugin = KongPlugin()
        plugin._config = {"connection": {"base_url": "http://localhost:8001"}}
        plugin.on_initialize()

        mock_config_cls.from_env.assert_called_once()
        assert plugin._client is not None
        assert plugin._plugin_config is mock_config

    @patch("system_operations_manager.plugins.kong.plugin.KongPluginConfig")
    def test_on_initialize_error_propagates(
        self,
        mock_config_cls: MagicMock,
    ) -> None:
        mock_config_cls.from_env.side_effect = ValueError("bad config")

        plugin = KongPlugin()
        plugin._config = {}

        with pytest.raises(ValueError, match="bad config"):
            plugin.on_initialize()


# ===========================================================================
# KongPlugin.cleanup
# ===========================================================================


@pytest.mark.unit
class TestKongPluginCleanup:
    """Tests for KongPlugin.cleanup."""

    def test_cleanup_closes_client(self, kong_plugin: KongPlugin) -> None:
        client: Any = kong_plugin._client
        assert client is not None

        kong_plugin.cleanup()

        client.close.assert_called_once()
        assert kong_plugin._client is None

    def test_cleanup_no_client(self) -> None:
        plugin = KongPlugin()
        # Should not raise
        plugin.cleanup()


# ===========================================================================
# KongPlugin status command
# ===========================================================================


@pytest.mark.unit
class TestKongPluginStatusCommand:
    """Tests for the 'kong status' command."""

    @pytest.fixture
    def app(self, kong_plugin: KongPlugin) -> typer.Typer:
        test_app = typer.Typer()
        kong_plugin._register_status_commands(test_app)
        return test_app

    def test_status_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        result = cli_runner.invoke(app, ["status"])

        assert result.exit_code == 0
        assert "kong-node-1" in result.stdout
        assert "3.4.0" in result.stdout
        assert "Enterprise" in result.stdout

    def test_status_verbose(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        result = cli_runner.invoke(app, ["status", "--verbose"])

        assert result.exit_code == 0
        assert "LuaJIT" in result.stdout
        assert "MiB" in result.stdout

    def test_status_json_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        result = cli_runner.invoke(app, ["status", "--output", "json"])

        assert result.exit_code == 0

    def test_status_db_disconnected(
        self,
        cli_runner: CliRunner,
        kong_plugin: KongPlugin,
    ) -> None:
        client: Any = kong_plugin._client
        assert client is not None
        client.get_status.return_value = {"database": {"reachable": False}}

        test_app = typer.Typer()
        kong_plugin._register_status_commands(test_app)

        result = cli_runner.invoke(test_app, ["status"])

        assert result.exit_code == 0
        assert "disconnected" in result.stdout.lower()

    def test_status_oss_edition(
        self,
        cli_runner: CliRunner,
        kong_plugin: KongPlugin,
    ) -> None:
        """Status should show OSS when openid-connect is not available."""
        client: Any = kong_plugin._client
        assert client is not None
        client.get_info.return_value = {
            "hostname": "kong",
            "version": "3.4.0",
            "plugins": {
                "available_on_server": {"rate-limiting": True},
                "enabled_in_cluster": [],
            },
        }

        test_app = typer.Typer()
        kong_plugin._register_status_commands(test_app)

        result = cli_runner.invoke(test_app, ["status"])

        assert result.exit_code == 0
        assert "OSS" in result.stdout

    def test_status_kong_api_error(
        self,
        cli_runner: CliRunner,
        kong_plugin: KongPlugin,
    ) -> None:
        client: Any = kong_plugin._client
        assert client is not None
        client.get_status.side_effect = KongAPIError("timeout", status_code=503)

        test_app = typer.Typer()
        kong_plugin._register_status_commands(test_app)

        result = cli_runner.invoke(test_app, ["status"])

        assert result.exit_code == 1

    def test_status_no_client(
        self,
        cli_runner: CliRunner,
    ) -> None:
        plugin = KongPlugin()
        test_app = typer.Typer()
        plugin._register_status_commands(test_app)

        result = cli_runner.invoke(test_app, ["status"])

        assert result.exit_code == 1
        assert "not configured" in result.stdout.lower()


# ===========================================================================
# KongPlugin info command
# ===========================================================================


@pytest.mark.unit
class TestKongPluginInfoCommand:
    """Tests for the 'kong info' command."""

    @pytest.fixture
    def app(self, kong_plugin: KongPlugin) -> typer.Typer:
        test_app = typer.Typer()
        kong_plugin._register_status_commands(test_app)
        return test_app

    def test_info_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        result = cli_runner.invoke(app, ["info"])

        assert result.exit_code == 0
        assert "3.4.0" in result.stdout

    def test_info_json_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        result = cli_runner.invoke(app, ["info", "--output", "json"])

        assert result.exit_code == 0

    def test_info_kong_api_error(
        self,
        cli_runner: CliRunner,
        kong_plugin: KongPlugin,
    ) -> None:
        client: Any = kong_plugin._client
        assert client is not None
        client.get_info.side_effect = KongAPIError("timeout", status_code=503)

        test_app = typer.Typer()
        kong_plugin._register_status_commands(test_app)

        result = cli_runner.invoke(test_app, ["info"])

        assert result.exit_code == 1

    def test_info_no_client(
        self,
        cli_runner: CliRunner,
    ) -> None:
        plugin = KongPlugin()
        test_app = typer.Typer()
        plugin._register_status_commands(test_app)

        result = cli_runner.invoke(test_app, ["info"])

        assert result.exit_code == 1
        assert "not configured" in result.stdout.lower()


# ===========================================================================
# KongPlugin.register_commands
# ===========================================================================


@pytest.mark.unit
class TestKongPluginRegisterCommands:
    """Tests for the register_commands hookimpl."""

    @patch.object(KongPlugin, "_register_entity_commands")
    @patch.object(KongPlugin, "_register_status_commands")
    def test_register_commands_creates_kong_subapp(
        self,
        mock_status: MagicMock,
        mock_entity: MagicMock,
        kong_plugin: KongPlugin,
    ) -> None:
        main_app = typer.Typer()
        kong_plugin.register_commands(main_app)

        # Both registration methods should be called
        mock_status.assert_called_once()
        mock_entity.assert_called_once()


# ===========================================================================
# KongPlugin._register_entity_commands
# ===========================================================================


def _patch_all_register_commands() -> Any:
    """Return a combined patch context for all register_*_commands functions."""
    targets = [
        f"{_CMD}.services.register_service_commands",
        f"{_CMD}.routes.register_route_commands",
        f"{_CMD}.consumers.register_consumer_commands",
        f"{_CMD}.upstreams.register_upstream_commands",
        f"{_CMD}.plugins.register_plugin_commands",
        f"{_CMD}.security.register_security_commands",
        f"{_CMD}.traffic.register_traffic_commands",
        f"{_CMD}.observability.register_observability_commands",
        f"{_CMD}.config.register_config_commands",
        f"{_CMD}.openapi.register_openapi_commands",
        f"{_CMD}.deployment.register_deployment_commands",
        f"{_CMD}.registry.register_registry_commands",
        f"{_CMD}.konnect.register_konnect_commands",
        f"{_CMD}.sync.register_sync_commands",
    ]
    return {t.rsplit(".", 1)[-1]: t for t in targets}


@pytest.fixture
def _patched_register_fns() -> Generator[dict[str, MagicMock]]:
    """Patch all register_*_commands to capture the factory functions passed to them."""
    targets = _patch_all_register_commands()
    patches: dict[str, Any] = {}
    mocks: dict[str, MagicMock] = {}
    for name, target in targets.items():
        p = patch(target)
        mocks[name] = p.start()
        patches[name] = p
    yield mocks
    for p in patches.values():
        p.stop()


@pytest.mark.unit
class TestRegisterEntityCommands:
    """Tests for _register_entity_commands factory functions."""

    @pytest.fixture
    def factories(
        self,
        kong_plugin: KongPlugin,
        _patched_register_fns: dict[str, MagicMock],
    ) -> dict[str, MagicMock]:
        """Call _register_entity_commands and return captured mocks."""
        app = typer.Typer()
        kong_plugin._register_entity_commands(app)
        return _patched_register_fns

    def test_all_register_functions_called(
        self,
        factories: dict[str, MagicMock],
    ) -> None:
        for name, mock_fn in factories.items():
            assert mock_fn.called, f"{name} was not called"

    def test_get_service_manager_returns_manager(
        self,
        factories: dict[str, MagicMock],
    ) -> None:
        args = factories["register_service_commands"].call_args
        get_service_manager = args[0][1]
        result = get_service_manager()
        assert result is not None

    def test_get_route_manager_returns_manager(
        self,
        factories: dict[str, MagicMock],
    ) -> None:
        args = factories["register_route_commands"].call_args
        get_route_manager = args[0][1]
        result = get_route_manager()
        assert result is not None

    def test_get_consumer_manager_returns_manager(
        self,
        factories: dict[str, MagicMock],
    ) -> None:
        args = factories["register_consumer_commands"].call_args
        get_consumer_manager = args[0][1]
        result = get_consumer_manager()
        assert result is not None

    def test_get_upstream_manager_returns_manager(
        self,
        factories: dict[str, MagicMock],
    ) -> None:
        args = factories["register_upstream_commands"].call_args
        get_upstream_manager = args[0][1]
        result = get_upstream_manager()
        assert result is not None

    def test_get_plugin_manager_returns_manager(
        self,
        factories: dict[str, MagicMock],
    ) -> None:
        args = factories["register_plugin_commands"].call_args
        get_plugin_manager = args[0][1]
        result = get_plugin_manager()
        assert result is not None

    def test_factory_raises_when_no_client(
        self,
        kong_plugin: KongPlugin,
        factories: dict[str, MagicMock],
    ) -> None:
        args = factories["register_service_commands"].call_args
        get_service_manager = args[0][1]

        kong_plugin._client = None
        with pytest.raises(RuntimeError, match="not initialized"):
            get_service_manager()

    def test_get_registry_manager_returns_manager(
        self,
        factories: dict[str, MagicMock],
    ) -> None:
        args = factories["register_registry_commands"].call_args
        get_registry_manager = args[0][1]
        result = get_registry_manager()
        assert result is not None

    def test_get_deployment_manager_returns_manager(
        self,
        factories: dict[str, MagicMock],
    ) -> None:
        args = factories["register_deployment_commands"].call_args
        get_deployment_manager = args[0][1]
        result = get_deployment_manager()
        assert result is not None

    def test_get_observability_manager_returns_manager(
        self,
        factories: dict[str, MagicMock],
    ) -> None:
        args = factories["register_observability_commands"].call_args
        get_observability_manager = args[0][3]
        result = get_observability_manager()
        assert result is not None

    def test_get_config_manager_returns_manager(
        self,
        factories: dict[str, MagicMock],
    ) -> None:
        args = factories["register_config_commands"].call_args
        get_config_manager = args[0][1]
        result = get_config_manager()
        assert result is not None

    def test_get_openapi_sync_manager_returns_manager(
        self,
        factories: dict[str, MagicMock],
    ) -> None:
        args = factories["register_openapi_commands"].call_args
        get_openapi_sync_manager = args[0][1]
        result = get_openapi_sync_manager()
        assert result is not None

    def test_factory_raises_for_each_manager_type(
        self,
        kong_plugin: KongPlugin,
        factories: dict[str, MagicMock],
    ) -> None:
        """All manager factories raise RuntimeError when client is None."""
        kong_plugin._client = None

        # route manager
        get_route = factories["register_route_commands"].call_args[0][1]
        with pytest.raises(RuntimeError, match="not initialized"):
            get_route()

        # consumer manager
        get_consumer = factories["register_consumer_commands"].call_args[0][1]
        with pytest.raises(RuntimeError, match="not initialized"):
            get_consumer()

        # upstream manager
        get_upstream = factories["register_upstream_commands"].call_args[0][1]
        with pytest.raises(RuntimeError, match="not initialized"):
            get_upstream()

        # plugin manager
        get_plugin = factories["register_plugin_commands"].call_args[0][1]
        with pytest.raises(RuntimeError, match="not initialized"):
            get_plugin()

        # observability manager
        get_obs = factories["register_observability_commands"].call_args[0][3]
        with pytest.raises(RuntimeError, match="not initialized"):
            get_obs()

        # config manager
        get_config = factories["register_config_commands"].call_args[0][1]
        with pytest.raises(RuntimeError, match="not initialized"):
            get_config()

        # openapi sync manager (depends on route/service which will also fail)
        get_openapi = factories["register_openapi_commands"].call_args[0][1]
        with pytest.raises(RuntimeError, match="not initialized"):
            get_openapi()

    def test_get_konnect_route_manager(
        self,
        factories: dict[str, MagicMock],
    ) -> None:
        get_konnect_route = factories["register_sync_commands"].call_args[1][
            "get_konnect_route_manager"
        ]
        with patch("system_operations_manager.integrations.konnect.KonnectConfig") as mock_config:
            mock_config.exists.return_value = False
            assert get_konnect_route() is None

    def test_get_konnect_consumer_manager(
        self,
        factories: dict[str, MagicMock],
    ) -> None:
        get_konnect_consumer = factories["register_sync_commands"].call_args[1][
            "get_konnect_consumer_manager"
        ]
        with patch("system_operations_manager.integrations.konnect.KonnectConfig") as mock_config:
            mock_config.exists.return_value = False
            assert get_konnect_consumer() is None

    def test_get_konnect_plugin_manager(
        self,
        factories: dict[str, MagicMock],
    ) -> None:
        get_konnect_plugin = factories["register_sync_commands"].call_args[1][
            "get_konnect_plugin_manager"
        ]
        with patch("system_operations_manager.integrations.konnect.KonnectConfig") as mock_config:
            mock_config.exists.return_value = False
            assert get_konnect_plugin() is None

    def test_get_konnect_upstream_manager(
        self,
        factories: dict[str, MagicMock],
    ) -> None:
        get_konnect_upstream = factories["register_sync_commands"].call_args[1][
            "get_konnect_upstream_manager"
        ]
        with patch("system_operations_manager.integrations.konnect.KonnectConfig") as mock_config:
            mock_config.exists.return_value = False
            assert get_konnect_upstream() is None

    def test_get_unified_query_service_returns_none_without_konnect(
        self,
        kong_plugin: KongPlugin,
        factories: dict[str, MagicMock],
    ) -> None:
        """Unified query service should return None when Konnect is not configured."""
        args = factories["register_service_commands"].call_args
        get_unified_query_service = args[0][2]

        with patch("system_operations_manager.integrations.konnect.KonnectConfig") as mock_config:
            mock_config.exists.return_value = False
            result = get_unified_query_service()
            assert result is None

    def test_get_unified_query_service_returns_none_without_client(
        self,
        kong_plugin: KongPlugin,
        factories: dict[str, MagicMock],
    ) -> None:
        args = factories["register_service_commands"].call_args
        get_unified_query_service = args[0][2]

        kong_plugin._client = None
        result = get_unified_query_service()
        assert result is None

    def test_get_konnect_manager_returns_none_when_not_configured(
        self,
        factories: dict[str, MagicMock],
    ) -> None:
        """Konnect manager factories return None when Konnect is not configured."""
        args = factories["register_sync_commands"].call_args
        get_konnect_service_manager = args[1]["get_konnect_service_manager"]

        with patch("system_operations_manager.integrations.konnect.KonnectConfig") as mock_config:
            mock_config.exists.return_value = False
            result = get_konnect_service_manager()
            assert result is None

    def test_get_konnect_manager_returns_none_on_config_error(
        self,
        factories: dict[str, MagicMock],
    ) -> None:
        args = factories["register_sync_commands"].call_args
        get_konnect_service_manager = args[1]["get_konnect_service_manager"]

        with (
            patch("system_operations_manager.integrations.konnect.KonnectConfig") as mock_config,
            patch(
                "system_operations_manager.integrations.konnect.exceptions.KonnectConfigError",
                new=ValueError,
            ),
        ):
            mock_config.exists.return_value = True
            mock_config.load.side_effect = ValueError("bad config")
            result = get_konnect_service_manager()
            assert result is None

    def test_get_konnect_manager_returns_none_no_default_cp(
        self,
        factories: dict[str, MagicMock],
    ) -> None:
        args = factories["register_sync_commands"].call_args
        get_konnect_service_manager = args[1]["get_konnect_service_manager"]

        with patch("system_operations_manager.integrations.konnect.KonnectConfig") as mock_config:
            config_obj = MagicMock()
            config_obj.default_control_plane = None
            mock_config.exists.return_value = True
            mock_config.load.return_value = config_obj
            result = get_konnect_service_manager()
            assert result is None

    def test_get_konnect_manager_success(
        self,
        factories: dict[str, MagicMock],
    ) -> None:
        args = factories["register_sync_commands"].call_args
        get_konnect_service_manager = args[1]["get_konnect_service_manager"]

        # The factory imports KonnectConfig and KonnectClient inside the closure,
        # so we patch them where they're looked up (integrations.konnect module).
        with (
            patch("system_operations_manager.integrations.konnect.KonnectConfig") as mock_config,
            patch(
                "system_operations_manager.integrations.konnect.KonnectClient"
            ) as mock_client_cls,
        ):
            config_obj = MagicMock()
            config_obj.default_control_plane = "my-cp"
            mock_config.exists.return_value = True
            mock_config.load.return_value = config_obj

            mock_client = MagicMock()
            mock_cp = MagicMock()
            mock_cp.id = "cp-123"
            mock_client.find_control_plane.return_value = mock_cp
            mock_client_cls.return_value = mock_client

            result = get_konnect_service_manager()
            assert result is not None

    def test_get_konnect_manager_returns_none_on_find_error(
        self,
        factories: dict[str, MagicMock],
    ) -> None:
        args = factories["register_sync_commands"].call_args
        get_konnect_service_manager = args[1]["get_konnect_service_manager"]

        with (
            patch("system_operations_manager.integrations.konnect.KonnectConfig") as mock_config,
            patch(
                "system_operations_manager.integrations.konnect.KonnectClient"
            ) as mock_client_cls,
        ):
            config_obj = MagicMock()
            config_obj.default_control_plane = "my-cp"
            mock_config.exists.return_value = True
            mock_config.load.return_value = config_obj
            mock_client_cls.return_value.find_control_plane.side_effect = RuntimeError("oops")

            result = get_konnect_service_manager()
            assert result is None


@pytest.mark.unit
class TestRegisterEntityCommandsObservability:
    """Tests for observability config branch in _register_entity_commands."""

    @pytest.fixture
    def _all_patched(self) -> Generator[dict[str, MagicMock]]:
        targets = _patch_all_register_commands()
        patches: dict[str, Any] = {}
        mocks: dict[str, MagicMock] = {}
        for name, target in targets.items():
            p = patch(target)
            mocks[name] = p.start()
            patches[name] = p
        yield mocks
        for p in patches.values():
            p.stop()

    def test_observability_prometheus_factory(
        self,
        mock_client: MagicMock,
        _all_patched: dict[str, MagicMock],
    ) -> None:
        """When prometheus config is set, get_metrics_manager factory should be passed."""
        plugin = KongPlugin()
        plugin._client = mock_client
        plugin._plugin_config = MagicMock()
        plugin._plugin_config.observability.prometheus = MagicMock()
        plugin._plugin_config.observability.elasticsearch = None
        plugin._plugin_config.observability.loki = None
        plugin._plugin_config.observability.jaeger = None
        plugin._plugin_config.observability.zipkin = None

        app = typer.Typer()
        plugin._register_entity_commands(app)

        obs_call = _all_patched["register_observability_commands"].call_args
        assert obs_call[1]["get_metrics_manager"] is not None
        assert obs_call[1]["get_logs_manager"] is None
        assert obs_call[1]["get_tracing_manager"] is None

        # Call the factory to verify it returns a MetricsManager
        result = obs_call[1]["get_metrics_manager"]()
        assert result is not None

    def test_observability_logs_factory(
        self,
        mock_client: MagicMock,
        _all_patched: dict[str, MagicMock],
    ) -> None:
        plugin = KongPlugin()
        plugin._client = mock_client
        plugin._plugin_config = MagicMock()
        plugin._plugin_config.observability.prometheus = None
        plugin._plugin_config.observability.elasticsearch = MagicMock()
        plugin._plugin_config.observability.loki = None
        plugin._plugin_config.observability.jaeger = None
        plugin._plugin_config.observability.zipkin = None

        app = typer.Typer()
        plugin._register_entity_commands(app)

        obs_call = _all_patched["register_observability_commands"].call_args
        assert obs_call[1]["get_logs_manager"] is not None

        result = obs_call[1]["get_logs_manager"]()
        assert result is not None

    def test_observability_tracing_factory(
        self,
        mock_client: MagicMock,
        _all_patched: dict[str, MagicMock],
    ) -> None:
        plugin = KongPlugin()
        plugin._client = mock_client
        plugin._plugin_config = MagicMock()
        plugin._plugin_config.observability.prometheus = None
        plugin._plugin_config.observability.elasticsearch = None
        plugin._plugin_config.observability.loki = None
        plugin._plugin_config.observability.jaeger = MagicMock()
        plugin._plugin_config.observability.zipkin = None

        app = typer.Typer()
        plugin._register_entity_commands(app)

        obs_call = _all_patched["register_observability_commands"].call_args
        assert obs_call[1]["get_tracing_manager"] is not None

        result = obs_call[1]["get_tracing_manager"]()
        assert result is not None

    def test_no_observability_config(
        self,
        kong_plugin: KongPlugin,
        _all_patched: dict[str, MagicMock],
    ) -> None:
        """When observability is None, all factories should be None."""
        config: Any = kong_plugin._plugin_config
        config.observability = None

        app = typer.Typer()
        kong_plugin._register_entity_commands(app)

        obs_call = _all_patched["register_observability_commands"].call_args
        assert obs_call[1]["get_metrics_manager"] is None
        assert obs_call[1]["get_logs_manager"] is None
        assert obs_call[1]["get_tracing_manager"] is None
