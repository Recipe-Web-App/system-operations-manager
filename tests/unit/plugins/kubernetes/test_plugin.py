"""Unit tests for Kubernetes plugin."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kubernetes.exceptions import (
    KubernetesConnectionError,
    KubernetesError,
)
from system_operations_manager.plugins.kubernetes.plugin import KubernetesPlugin


@pytest.mark.unit
@pytest.mark.kubernetes
class TestKubernetesPluginMetadata:
    """Tests for KubernetesPlugin metadata."""

    def test_plugin_name(self) -> None:
        """Plugin should have correct name."""
        plugin = KubernetesPlugin()
        assert plugin.name == "kubernetes"

    def test_plugin_version(self) -> None:
        """Plugin should have version."""
        plugin = KubernetesPlugin()
        assert plugin.version == "0.1.0"

    def test_plugin_description(self) -> None:
        """Plugin should have description."""
        plugin = KubernetesPlugin()
        assert "Kubernetes" in plugin.description
        assert "cluster management" in plugin.description


@pytest.mark.unit
@pytest.mark.kubernetes
class TestKubernetesPluginInit:
    """Tests for KubernetesPlugin initialization."""

    @patch("system_operations_manager.plugins.kubernetes.plugin.structlog")
    @patch("system_operations_manager.plugins.kubernetes.plugin.KubernetesClient")
    @patch("system_operations_manager.plugins.kubernetes.plugin.KubernetesPluginConfig.from_env")
    def test_on_initialize_creates_client(
        self,
        mock_config_from_env: MagicMock,
        mock_client_class: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        """on_initialize should create KubernetesClient from config."""
        mock_config = MagicMock()
        mock_config.get_active_namespace.return_value = "default"
        mock_config_from_env.return_value = mock_config

        mock_client = MagicMock()
        mock_client.get_current_context.return_value = "minikube"
        mock_client_class.return_value = mock_client

        plugin = KubernetesPlugin()
        plugin.on_initialize()

        assert plugin._client is mock_client
        assert plugin._plugin_config is mock_config
        mock_config_from_env.assert_called_once()
        mock_client_class.assert_called_once_with(mock_config)

    @patch("system_operations_manager.plugins.kubernetes.plugin.structlog")
    @patch("system_operations_manager.plugins.kubernetes.plugin.KubernetesClient")
    @patch("system_operations_manager.plugins.kubernetes.plugin.KubernetesPluginConfig.from_env")
    def test_on_initialize_handles_connection_error_gracefully(
        self,
        mock_config_from_env: MagicMock,
        mock_client_class: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        """on_initialize should handle KubernetesConnectionError gracefully."""
        mock_config = MagicMock()
        mock_config_from_env.return_value = mock_config
        mock_client_class.side_effect = KubernetesConnectionError("Connection failed")

        plugin = KubernetesPlugin()
        # Should not raise, just log warning
        plugin.on_initialize()

        # Plugin should still initialize but without client
        assert plugin._plugin_config is mock_config

    @patch("system_operations_manager.plugins.kubernetes.plugin.structlog")
    @patch("system_operations_manager.plugins.kubernetes.plugin.KubernetesClient")
    @patch("system_operations_manager.plugins.kubernetes.plugin.KubernetesPluginConfig.from_env")
    def test_on_initialize_handles_other_errors(
        self,
        mock_config_from_env: MagicMock,
        mock_client_class: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        """on_initialize should re-raise non-connection errors."""
        mock_config_from_env.side_effect = ValueError("Invalid config")

        plugin = KubernetesPlugin()
        with pytest.raises(ValueError, match="Invalid config"):
            plugin.on_initialize()


@pytest.mark.unit
@pytest.mark.kubernetes
class TestKubernetesPluginCommands:
    """Tests for KubernetesPlugin command registration."""

    @patch("system_operations_manager.plugins.kubernetes.plugin.structlog")
    @patch("system_operations_manager.plugins.kubernetes.plugin.KubernetesClient")
    @patch("system_operations_manager.plugins.kubernetes.plugin.KubernetesPluginConfig.from_env")
    def test_register_commands_adds_k8s_typer_group(
        self,
        mock_config_from_env: MagicMock,
        mock_client_class: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        """register_commands should add k8s Typer group to app."""
        mock_config = MagicMock()
        mock_config.get_active_namespace.return_value = "default"
        mock_config_from_env.return_value = mock_config

        mock_client = MagicMock()
        mock_client.get_current_context.return_value = "test-context"
        mock_client_class.return_value = mock_client

        plugin = KubernetesPlugin()
        plugin.on_initialize()

        app = typer.Typer()
        plugin.register_commands(app)

        # Verify k8s command group was added (we can't easily inspect typer internals)
        # but we can check the method executed without errors
        assert plugin._client is not None

    @patch("system_operations_manager.plugins.kubernetes.plugin.structlog")
    def test_register_commands_without_initialization(self, mock_logger: MagicMock) -> None:
        """register_commands should work even without client initialization."""
        plugin = KubernetesPlugin()
        app = typer.Typer()

        # Should not raise even if on_initialize wasn't called
        plugin.register_commands(app)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestKubernetesPluginCleanup:
    """Tests for KubernetesPlugin cleanup."""

    @patch("system_operations_manager.plugins.kubernetes.plugin.structlog")
    @patch("system_operations_manager.plugins.kubernetes.plugin.KubernetesClient")
    @patch("system_operations_manager.plugins.kubernetes.plugin.KubernetesPluginConfig.from_env")
    def test_cleanup_closes_client(
        self,
        mock_config_from_env: MagicMock,
        mock_client_class: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        """cleanup should close client and set to None."""
        mock_config = MagicMock()
        mock_config.get_active_namespace.return_value = "default"
        mock_config_from_env.return_value = mock_config

        mock_client = MagicMock()
        mock_client.get_current_context.return_value = "test"
        mock_client_class.return_value = mock_client

        plugin = KubernetesPlugin()
        plugin.on_initialize()

        assert plugin._client is mock_client

        plugin.cleanup()

        mock_client.close.assert_called_once()
        assert plugin._client is None

    @patch("system_operations_manager.plugins.kubernetes.plugin.structlog")
    def test_cleanup_idempotent_without_client(self, mock_logger: MagicMock) -> None:
        """cleanup should be safe to call when client is None."""
        plugin = KubernetesPlugin()

        # Should not raise
        plugin.cleanup()
        plugin.cleanup()  # Call twice to test idempotency


@pytest.mark.unit
@pytest.mark.kubernetes
class TestKubernetesPluginProperties:
    """Tests for KubernetesPlugin properties."""

    @patch("system_operations_manager.plugins.kubernetes.plugin.structlog")
    @patch("system_operations_manager.plugins.kubernetes.plugin.KubernetesClient")
    @patch("system_operations_manager.plugins.kubernetes.plugin.KubernetesPluginConfig.from_env")
    def test_client_property(
        self,
        mock_config_from_env: MagicMock,
        mock_client_class: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        """client property should return the KubernetesClient instance."""
        mock_config = MagicMock()
        mock_config.get_active_namespace.return_value = "default"
        mock_config_from_env.return_value = mock_config

        mock_client = MagicMock()
        mock_client.get_current_context.return_value = "test"
        mock_client_class.return_value = mock_client

        plugin = KubernetesPlugin()
        plugin.on_initialize()

        assert plugin.client is mock_client

    @patch("system_operations_manager.plugins.kubernetes.plugin.structlog")
    @patch("system_operations_manager.plugins.kubernetes.plugin.KubernetesClient")
    @patch("system_operations_manager.plugins.kubernetes.plugin.KubernetesPluginConfig.from_env")
    def test_plugin_config_property(
        self,
        mock_config_from_env: MagicMock,
        mock_client_class: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        """plugin_config property should return the KubernetesPluginConfig instance."""
        mock_config = MagicMock()
        mock_config.get_active_namespace.return_value = "default"
        mock_config_from_env.return_value = mock_config

        mock_client = MagicMock()
        mock_client.get_current_context.return_value = "test"
        mock_client_class.return_value = mock_client

        plugin = KubernetesPlugin()
        plugin.on_initialize()

        assert plugin.plugin_config is mock_config

    def test_client_property_none_before_init(self) -> None:
        """client property should return None before initialization."""
        plugin = KubernetesPlugin()
        assert plugin.client is None

    def test_plugin_config_property_none_before_init(self) -> None:
        """plugin_config property should return None before initialization."""
        plugin = KubernetesPlugin()
        assert plugin.plugin_config is None


# ---------------------------------------------------------------------------
# Helpers shared by status-command tests
# ---------------------------------------------------------------------------

_ALL_REGISTER_NAMES = [
    "register_workload_commands",
    "register_networking_commands",
    "register_config_commands",
    "register_cluster_commands",
    "register_namespace_commands",
    "register_job_commands",
    "register_storage_commands",
    "register_rbac_commands",
    "register_helm_commands",
    "register_kustomize_commands",
    "register_manifest_commands",
    "register_policy_commands",
    "register_external_secrets_commands",
    "register_flux_commands",
    "register_optimization_commands",
    "register_argocd_commands",
    "register_rollout_commands",
    "register_workflow_commands",
    "register_certs_commands",
    "register_streaming_commands",
    "register_multicluster_commands",
]


def _patch_all_entity_registers(mocker: Any) -> None:
    """Patch every register_*_commands to a no-op so entity setup is skipped."""
    for name in _ALL_REGISTER_NAMES:
        mocker.patch(
            f"system_operations_manager.plugins.kubernetes.commands.{name}",
        )


@pytest.mark.unit
@pytest.mark.kubernetes
class TestStatusCommands:
    """Tests for _register_status_commands closures (status / contexts / use-context)."""

    @pytest.fixture
    def status_app(self, mocker: Any) -> tuple[typer.Typer, MagicMock]:
        """Return (app, mock_client) with status commands registered."""
        mock_client = MagicMock()
        mocker.patch(
            "system_operations_manager.plugins.kubernetes.plugin.KubernetesClient",
            return_value=mock_client,
        )
        mocker.patch(
            "system_operations_manager.plugins.kubernetes.plugin.KubernetesPluginConfig.from_env",
            return_value=MagicMock(get_active_namespace=MagicMock(return_value="default")),
        )
        mocker.patch("system_operations_manager.plugins.kubernetes.plugin.structlog")
        _patch_all_entity_registers(mocker)

        plugin = KubernetesPlugin()
        plugin.on_initialize()

        app = typer.Typer()
        plugin.register_commands(app)
        return app, mock_client

    @pytest.fixture
    def no_client_app(self, mocker: Any) -> typer.Typer:
        """Return app where the plugin was never initialized (client=None)."""
        mocker.patch("system_operations_manager.plugins.kubernetes.plugin.structlog")
        _patch_all_entity_registers(mocker)

        plugin = KubernetesPlugin()
        # Deliberately skip on_initialize so _client stays None
        app = typer.Typer()
        plugin.register_commands(app)
        return app

    # ------------------------------------------------------------------
    # status command
    # ------------------------------------------------------------------

    @pytest.mark.unit
    def test_status_connected(self, status_app: tuple[typer.Typer, MagicMock]) -> None:
        """status command should show cluster info when connected."""
        app, mock_client = status_app
        mock_client.check_connection.return_value = True
        mock_client.get_current_context.return_value = "minikube"
        mock_client.get_cluster_version.return_value = "v1.28.0"
        node = MagicMock()
        mock_client.core_v1.list_node.return_value.items = [node]

        runner = CliRunner()
        result = runner.invoke(app, ["k8s", "status"])

        assert result.exit_code == 0
        assert "minikube" in result.output

    @pytest.mark.unit
    def test_status_not_connected(self, status_app: tuple[typer.Typer, MagicMock]) -> None:
        """status command should show 'no' when cluster is not reachable."""
        app, mock_client = status_app
        mock_client.check_connection.return_value = False
        mock_client.get_current_context.return_value = "offline-ctx"

        runner = CliRunner()
        result = runner.invoke(app, ["k8s", "status"])

        assert result.exit_code == 0
        assert "no" in result.output.lower()

    @pytest.mark.unit
    def test_status_version_error(self, status_app: tuple[typer.Typer, MagicMock]) -> None:
        """status command should show 'unknown' when get_cluster_version raises."""
        app, mock_client = status_app
        mock_client.check_connection.return_value = True
        mock_client.get_current_context.return_value = "minikube"
        mock_client.get_cluster_version.side_effect = KubernetesError("version error")
        mock_client.core_v1.list_node.return_value.items = []

        runner = CliRunner()
        result = runner.invoke(app, ["k8s", "status"])

        assert result.exit_code == 0
        assert "unknown" in result.output.lower()

    @pytest.mark.unit
    def test_status_nodes_error(self, status_app: tuple[typer.Typer, MagicMock]) -> None:
        """status command should show 'unknown' nodes when list_node raises."""
        app, mock_client = status_app
        mock_client.check_connection.return_value = True
        mock_client.get_current_context.return_value = "minikube"
        mock_client.get_cluster_version.return_value = "v1.28.0"
        mock_client.core_v1.list_node.side_effect = Exception("nodes unavailable")

        runner = CliRunner()
        result = runner.invoke(app, ["k8s", "status"])

        assert result.exit_code == 0
        assert "unknown" in result.output.lower()

    @pytest.mark.unit
    def test_status_json_output(self, status_app: tuple[typer.Typer, MagicMock]) -> None:
        """status command should succeed with --output json."""
        app, mock_client = status_app
        mock_client.check_connection.return_value = True
        mock_client.get_current_context.return_value = "minikube"
        mock_client.get_cluster_version.return_value = "v1.28.0"
        mock_client.core_v1.list_node.return_value.items = []

        runner = CliRunner()
        result = runner.invoke(app, ["k8s", "status", "--output", "json"])

        assert result.exit_code == 0

    @pytest.mark.unit
    def test_status_no_client(self, no_client_app: typer.Typer) -> None:
        """status command should exit 1 and print error when client is not configured."""
        runner = CliRunner()
        result = runner.invoke(no_client_app, ["k8s", "status"])

        assert result.exit_code == 1
        assert "not configured" in result.output.lower()

    # ------------------------------------------------------------------
    # contexts command
    # ------------------------------------------------------------------

    @pytest.mark.unit
    def test_contexts_list(self, status_app: tuple[typer.Typer, MagicMock]) -> None:
        """contexts command should list available contexts."""
        app, mock_client = status_app
        mock_client.list_contexts.return_value = [
            {"name": "minikube", "cluster": "k8s", "namespace": "default", "active": True},
            {"name": "production", "cluster": "prod-k8s", "namespace": "prod", "active": False},
        ]

        runner = CliRunner()
        result = runner.invoke(app, ["k8s", "contexts"])

        assert result.exit_code == 0
        assert "minikube" in result.output

    @pytest.mark.unit
    def test_contexts_no_client(self, no_client_app: typer.Typer) -> None:
        """contexts command should exit 1 when client is not configured."""
        runner = CliRunner()
        result = runner.invoke(no_client_app, ["k8s", "contexts"])

        assert result.exit_code == 1
        assert "not configured" in result.output.lower()

    @pytest.mark.unit
    def test_contexts_json_output(self, status_app: tuple[typer.Typer, MagicMock]) -> None:
        """contexts command should succeed with --output json."""
        app, mock_client = status_app
        mock_client.list_contexts.return_value = [
            {"name": "minikube", "cluster": "k8s", "namespace": "default", "active": True},
        ]

        runner = CliRunner()
        result = runner.invoke(app, ["k8s", "contexts", "--output", "json"])

        assert result.exit_code == 0

    @pytest.mark.unit
    def test_contexts_error(self, status_app: tuple[typer.Typer, MagicMock]) -> None:
        """contexts command should handle KubernetesError and exit 1."""
        app, mock_client = status_app
        mock_client.list_contexts.side_effect = KubernetesError("list failed")

        runner = CliRunner()
        result = runner.invoke(app, ["k8s", "contexts"])

        assert result.exit_code == 1

    # ------------------------------------------------------------------
    # use-context command
    # ------------------------------------------------------------------

    @pytest.mark.unit
    def test_use_context_success(self, status_app: tuple[typer.Typer, MagicMock]) -> None:
        """use-context command should call switch_context and print success."""
        app, mock_client = status_app

        runner = CliRunner()
        result = runner.invoke(app, ["k8s", "use-context", "minikube"])

        assert result.exit_code == 0
        mock_client.switch_context.assert_called_once_with("minikube")
        assert "minikube" in result.output

    @pytest.mark.unit
    def test_use_context_error(self, status_app: tuple[typer.Typer, MagicMock]) -> None:
        """use-context command should handle KubernetesError and exit 1."""
        app, mock_client = status_app
        mock_client.switch_context.side_effect = KubernetesError("context not found")

        runner = CliRunner()
        result = runner.invoke(app, ["k8s", "use-context", "bad-context"])

        assert result.exit_code == 1

    @pytest.mark.unit
    def test_use_context_no_client(self, no_client_app: typer.Typer) -> None:
        """use-context command should exit 1 when client is not configured."""
        runner = CliRunner()
        result = runner.invoke(no_client_app, ["k8s", "use-context", "minikube"])

        assert result.exit_code == 1
        assert "not configured" in result.output.lower()

    @pytest.mark.unit
    def test_status_connection_check_raises_kubernetes_error(
        self, status_app: tuple[typer.Typer, MagicMock]
    ) -> None:
        """status command outer except should catch KubernetesError from check_connection."""
        app, mock_client = status_app
        mock_client.check_connection.side_effect = KubernetesError("cluster error")

        runner = CliRunner()
        result = runner.invoke(app, ["k8s", "status"])

        assert result.exit_code == 1


@pytest.mark.unit
@pytest.mark.kubernetes
class TestEntityCommandFactories:
    """Tests for _register_entity_commands manager factory closures."""

    @pytest.mark.unit
    def test_factories_create_managers_with_client(self, mocker: Any) -> None:
        """Every get_*_manager factory should return a manager when client is set."""
        mock_client = MagicMock()
        mocker.patch(
            "system_operations_manager.plugins.kubernetes.plugin.KubernetesClient",
            return_value=mock_client,
        )
        mocker.patch(
            "system_operations_manager.plugins.kubernetes.plugin.KubernetesPluginConfig.from_env",
            return_value=MagicMock(get_active_namespace=MagicMock(return_value="default")),
        )
        mocker.patch("system_operations_manager.plugins.kubernetes.plugin.structlog")

        # Capture the factory (get_manager) argument from each register_*_commands call.
        captured: dict[str, Any] = {}

        def _make_capture(reg_name: str) -> Any:
            def fake_register(app: Any, get_manager: Any, *args: Any, **kwargs: Any) -> None:
                captured[reg_name] = get_manager

            return fake_register

        for name in _ALL_REGISTER_NAMES:
            mocker.patch(
                f"system_operations_manager.plugins.kubernetes.commands.{name}",
                side_effect=_make_capture(name),
            )

        plugin = KubernetesPlugin()
        plugin.on_initialize()
        app = typer.Typer()
        plugin.register_commands(app)

        # Every register function should have been called exactly once.
        assert len(captured) == len(_ALL_REGISTER_NAMES), (
            f"Expected {len(_ALL_REGISTER_NAMES)} factories, got {len(captured)}: "
            f"missing={set(_ALL_REGISTER_NAMES) - set(captured)}"
        )

        # Calling each factory with a live client must return a non-None manager.
        for name, factory in captured.items():
            result = factory()
            assert result is not None, f"Factory from {name} returned None"

    @pytest.mark.unit
    def test_factories_raise_without_client(self, mocker: Any) -> None:
        """Every get_*_manager factory should raise RuntimeError when client is None."""
        mocker.patch("system_operations_manager.plugins.kubernetes.plugin.structlog")

        captured: dict[str, Any] = {}

        def _make_capture(reg_name: str) -> Any:
            def fake_register(app: Any, get_manager: Any, *args: Any, **kwargs: Any) -> None:
                captured[reg_name] = get_manager

            return fake_register

        for name in _ALL_REGISTER_NAMES:
            mocker.patch(
                f"system_operations_manager.plugins.kubernetes.commands.{name}",
                side_effect=_make_capture(name),
            )

        # Do NOT call on_initialize so _client stays None.
        plugin = KubernetesPlugin()
        app = typer.Typer()
        plugin.register_commands(app)

        assert len(captured) == len(_ALL_REGISTER_NAMES), (
            f"Expected {len(_ALL_REGISTER_NAMES)} factories captured, got {len(captured)}"
        )

        for _name, factory in captured.items():
            with pytest.raises(RuntimeError, match="Kubernetes client not initialized"):
                factory()

    @pytest.mark.unit
    def test_all_register_functions_called(self, mocker: Any) -> None:
        """register_commands must invoke every register_*_commands exactly once."""
        mock_client = MagicMock()
        mocker.patch(
            "system_operations_manager.plugins.kubernetes.plugin.KubernetesClient",
            return_value=mock_client,
        )
        mocker.patch(
            "system_operations_manager.plugins.kubernetes.plugin.KubernetesPluginConfig.from_env",
            return_value=MagicMock(get_active_namespace=MagicMock(return_value="default")),
        )
        mocker.patch("system_operations_manager.plugins.kubernetes.plugin.structlog")

        mocks: dict[str, MagicMock] = {}
        for name in _ALL_REGISTER_NAMES:
            mocks[name] = mocker.patch(
                f"system_operations_manager.plugins.kubernetes.commands.{name}",
            )

        plugin = KubernetesPlugin()
        plugin.on_initialize()
        app = typer.Typer()
        plugin.register_commands(app)

        for name, mock_fn in mocks.items():
            assert mock_fn.call_count == 1, f"{name} was not called"
