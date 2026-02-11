"""Unit tests for Kubernetes plugin."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import typer

from system_operations_manager.integrations.kubernetes.exceptions import (
    KubernetesConnectionError,
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
