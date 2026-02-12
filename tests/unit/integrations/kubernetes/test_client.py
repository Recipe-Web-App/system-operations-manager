"""Unit tests for Kubernetes client."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from system_operations_manager.integrations.kubernetes.client import KubernetesClient
from system_operations_manager.integrations.kubernetes.config import (
    ClusterConfig,
    KubernetesPluginConfig,
)
from system_operations_manager.integrations.kubernetes.exceptions import (
    KubernetesAuthError,
    KubernetesConflictError,
    KubernetesConnectionError,
    KubernetesError,
    KubernetesNotFoundError,
    KubernetesValidationError,
)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestKubernetesClientInitialization:
    """Test KubernetesClient initialization."""

    @patch("kubernetes.config")
    def test_init_with_default_config(self, mock_config: MagicMock) -> None:
        """Test client initialization with default config."""
        plugin_config = KubernetesPluginConfig()
        client = KubernetesClient(plugin_config)

        assert client._config == plugin_config
        assert client._retries == 3
        mock_config.load_kube_config.assert_called_once()

    @patch("kubernetes.config")
    def test_init_with_cluster_config(self, mock_config: MagicMock) -> None:
        """Test client initialization with cluster configuration."""
        cluster_cfg = ClusterConfig(
            context="test-context",
            kubeconfig="/path/to/config",
        )
        plugin_config = KubernetesPluginConfig(
            clusters={"test": cluster_cfg},
            active_cluster="test",
        )
        client = KubernetesClient(plugin_config)

        mock_config.load_kube_config.assert_called_once_with(
            config_file="/path/to/config",
            context="test-context",
        )
        assert client._current_context == "test-context"

    @patch("kubernetes.config")
    def test_init_fallback_to_incluster(self, mock_config: MagicMock) -> None:
        """Test client falls back to in-cluster config."""
        from kubernetes.config import ConfigException

        mock_config.load_kube_config.side_effect = ConfigException("Not found")
        mock_config.load_incluster_config.return_value = None

        plugin_config = KubernetesPluginConfig()
        client = KubernetesClient(plugin_config)

        mock_config.load_incluster_config.assert_called_once()
        assert client._current_context == "in-cluster"

    @patch("kubernetes.config")
    def test_init_connection_error(self, mock_config: MagicMock) -> None:
        """Test client raises KubernetesConnectionError when config loading fails."""
        from kubernetes.config import ConfigException

        mock_config.load_kube_config.side_effect = ConfigException("No config")
        mock_config.load_incluster_config.side_effect = ConfigException("Not in cluster")

        plugin_config = KubernetesPluginConfig()
        with pytest.raises(KubernetesConnectionError) as exc_info:
            KubernetesClient(plugin_config)

        assert "Cannot load Kubernetes configuration" in str(exc_info.value)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestKubernetesClientAPIProperties:
    """Test KubernetesClient lazy API properties."""

    @patch("kubernetes.config")
    def test_core_v1_lazy_loading(self, mock_config: MagicMock) -> None:
        """Test CoreV1Api is lazily loaded."""
        plugin_config = KubernetesPluginConfig()
        client = KubernetesClient(plugin_config)

        assert client._core_v1 is None

        with patch("kubernetes.client.CoreV1Api") as mock_api:
            _ = client.core_v1
            mock_api.assert_called_once()
            assert client._core_v1 is not None

    @patch("kubernetes.config")
    def test_apps_v1_lazy_loading(self, mock_config: MagicMock) -> None:
        """Test AppsV1Api is lazily loaded."""
        plugin_config = KubernetesPluginConfig()
        client = KubernetesClient(plugin_config)

        with patch("kubernetes.client.AppsV1Api") as mock_api:
            _ = client.apps_v1
            mock_api.assert_called_once()

    @patch("kubernetes.config")
    def test_batch_v1_lazy_loading(self, mock_config: MagicMock) -> None:
        """Test BatchV1Api is lazily loaded."""
        plugin_config = KubernetesPluginConfig()
        client = KubernetesClient(plugin_config)

        with patch("kubernetes.client.BatchV1Api") as mock_api:
            _ = client.batch_v1
            mock_api.assert_called_once()

    @patch("kubernetes.config")
    def test_networking_v1_lazy_loading(self, mock_config: MagicMock) -> None:
        """Test NetworkingV1Api is lazily loaded."""
        plugin_config = KubernetesPluginConfig()
        client = KubernetesClient(plugin_config)

        with patch("kubernetes.client.NetworkingV1Api") as mock_api:
            _ = client.networking_v1
            mock_api.assert_called_once()

    @patch("kubernetes.config")
    def test_rbac_v1_lazy_loading(self, mock_config: MagicMock) -> None:
        """Test RbacAuthorizationV1Api is lazily loaded."""
        plugin_config = KubernetesPluginConfig()
        client = KubernetesClient(plugin_config)

        with patch("kubernetes.client.RbacAuthorizationV1Api") as mock_api:
            _ = client.rbac_v1
            mock_api.assert_called_once()

    @patch("kubernetes.config")
    def test_storage_v1_lazy_loading(self, mock_config: MagicMock) -> None:
        """Test StorageV1Api is lazily loaded."""
        plugin_config = KubernetesPluginConfig()
        client = KubernetesClient(plugin_config)

        with patch("kubernetes.client.StorageV1Api") as mock_api:
            _ = client.storage_v1
            mock_api.assert_called_once()

    @patch("kubernetes.config")
    def test_version_api_lazy_loading(self, mock_config: MagicMock) -> None:
        """Test VersionApi is lazily loaded."""
        plugin_config = KubernetesPluginConfig()
        client = KubernetesClient(plugin_config)

        with patch("kubernetes.client.VersionApi") as mock_api:
            _ = client.version_api
            mock_api.assert_called_once()

    @patch("kubernetes.config")
    def test_api_caching(self, mock_config: MagicMock) -> None:
        """Test that API instances are cached."""
        plugin_config = KubernetesPluginConfig()
        client = KubernetesClient(plugin_config)

        with patch("kubernetes.client.CoreV1Api") as mock_api:
            api1 = client.core_v1
            api2 = client.core_v1
            mock_api.assert_called_once()
            assert api1 is api2


@pytest.mark.unit
@pytest.mark.kubernetes
class TestKubernetesClientContextManagement:
    """Test KubernetesClient context switching."""

    @patch("kubernetes.config")
    def test_switch_context_by_name(self, mock_config: MagicMock) -> None:
        """Test switching to a different context."""
        plugin_config = KubernetesPluginConfig()
        client = KubernetesClient(plugin_config)

        client.switch_context("new-context")

        assert mock_config.load_kube_config.call_count == 2
        mock_config.load_kube_config.assert_called_with(
            config_file=None,
            context="new-context",
        )
        assert client._current_context == "new-context"

    @patch("kubernetes.config")
    def test_switch_context_named_cluster(self, mock_config: MagicMock) -> None:
        """Test switching to a named cluster from config."""
        cluster_cfg = ClusterConfig(
            context="prod-ctx",
            kubeconfig="/prod/config",
        )
        plugin_config = KubernetesPluginConfig(clusters={"production": cluster_cfg})
        client = KubernetesClient(plugin_config)

        client.switch_context("production")

        mock_config.load_kube_config.assert_called_with(
            config_file="/prod/config",
            context="prod-ctx",
        )

    @patch("kubernetes.config")
    def test_switch_context_invalidates_cache(self, mock_config: MagicMock) -> None:
        """Test that switching context invalidates API cache."""
        plugin_config = KubernetesPluginConfig()
        client = KubernetesClient(plugin_config)

        with patch("kubernetes.client.CoreV1Api"):
            _ = client.core_v1
            assert client._core_v1 is not None

        client.switch_context("new-context")
        assert client._core_v1 is None

    @patch("kubernetes.config")
    def test_switch_context_error(self, mock_config: MagicMock) -> None:
        """Test error handling when switching to invalid context."""
        from kubernetes.config import ConfigException

        plugin_config = KubernetesPluginConfig()
        client = KubernetesClient(plugin_config)

        mock_config.load_kube_config.side_effect = ConfigException("Invalid")

        with pytest.raises(KubernetesConnectionError) as exc_info:
            client.switch_context("invalid-context")

        assert "Failed to switch to context 'invalid-context'" in str(exc_info.value)

    @patch("kubernetes.config")
    def test_get_current_context(self, mock_config: MagicMock) -> None:
        """Test getting current context name."""
        plugin_config = KubernetesPluginConfig()
        client = KubernetesClient(plugin_config)
        client._current_context = "test-ctx"

        assert client.get_current_context() == "test-ctx"

    @patch("kubernetes.config")
    def test_get_current_context_unknown(self, mock_config: MagicMock) -> None:
        """Test getting current context when not set."""
        plugin_config = KubernetesPluginConfig()
        client = KubernetesClient(plugin_config)
        client._current_context = None

        assert client.get_current_context() == "unknown"

    @patch("kubernetes.config")
    def test_list_contexts(self, mock_config: MagicMock) -> None:
        """Test listing available contexts."""
        mock_contexts = [
            {
                "name": "context1",
                "context": {"cluster": "cluster1", "namespace": "default"},
            },
            {
                "name": "context2",
                "context": {"cluster": "cluster2", "namespace": "prod"},
            },
        ]
        mock_active = {"name": "context1"}
        mock_config.list_kube_config_contexts.return_value = (mock_contexts, mock_active)

        plugin_config = KubernetesPluginConfig()
        client = KubernetesClient(plugin_config)

        contexts = client.list_contexts()

        assert len(contexts) == 2
        assert contexts[0]["name"] == "context1"
        assert contexts[0]["active"] is True
        assert contexts[1]["name"] == "context2"
        assert contexts[1]["active"] is False

    @patch("kubernetes.config")
    def test_list_contexts_error(self, mock_config: MagicMock) -> None:
        """Test list_contexts returns empty list on error."""
        mock_config.list_kube_config_contexts.side_effect = Exception("Error")

        plugin_config = KubernetesPluginConfig()
        client = KubernetesClient(plugin_config)

        contexts = client.list_contexts()
        assert contexts == []


@pytest.mark.unit
@pytest.mark.kubernetes
class TestKubernetesClientErrorTranslation:
    """Test KubernetesClient error translation."""

    def test_translate_401_to_auth_error(self) -> None:
        """Test 401 status code translates to KubernetesAuthError."""
        from kubernetes.client import ApiException

        api_exc = ApiException(status=401, reason="Unauthorized")
        result = KubernetesClient.translate_api_exception(api_exc)

        assert isinstance(result, KubernetesAuthError)
        assert result.status_code == 401

    def test_translate_403_to_auth_error(self) -> None:
        """Test 403 status code translates to KubernetesAuthError."""
        from kubernetes.client import ApiException

        api_exc = ApiException(status=403, reason="Forbidden")
        result = KubernetesClient.translate_api_exception(api_exc)

        assert isinstance(result, KubernetesAuthError)
        assert result.status_code == 403

    def test_translate_404_to_not_found_error(self) -> None:
        """Test 404 status code translates to KubernetesNotFoundError."""
        from kubernetes.client import ApiException

        api_exc = ApiException(status=404)
        result = KubernetesClient.translate_api_exception(
            api_exc,
            resource_type="Pod",
            resource_name="test-pod",
        )

        assert isinstance(result, KubernetesNotFoundError)
        assert result.resource_type == "Pod"
        assert result.resource_name == "test-pod"

    def test_translate_409_to_conflict_error(self) -> None:
        """Test 409 status code translates to KubernetesConflictError."""
        from kubernetes.client import ApiException

        api_exc = ApiException(status=409)
        result = KubernetesClient.translate_api_exception(
            api_exc,
            resource_type="Service",
            resource_name="api",
        )

        assert isinstance(result, KubernetesConflictError)
        assert result.resource_type == "Service"

    def test_translate_400_to_validation_error(self) -> None:
        """Test 400 status code translates to KubernetesValidationError."""
        from kubernetes.client import ApiException

        api_exc = ApiException(status=400, reason="Bad Request")
        result = KubernetesClient.translate_api_exception(api_exc)

        assert isinstance(result, KubernetesValidationError)
        assert result.status_code == 400

    def test_translate_422_to_validation_error(self) -> None:
        """Test 422 status code translates to KubernetesValidationError."""
        from kubernetes.client import ApiException

        api_exc = ApiException(status=422, reason="Unprocessable Entity")
        result = KubernetesClient.translate_api_exception(api_exc)

        assert isinstance(result, KubernetesValidationError)
        assert result.status_code == 422

    def test_translate_generic_api_exception(self) -> None:
        """Test generic API exception translates to KubernetesError."""
        from kubernetes.client import ApiException

        api_exc = ApiException(status=500, reason="Internal Server Error")
        result = KubernetesClient.translate_api_exception(api_exc)

        assert isinstance(result, KubernetesError)
        assert result.status_code == 500

    def test_translate_non_api_exception(self) -> None:
        """Test non-ApiException translates to generic KubernetesError."""
        exc = ValueError("Something went wrong")
        result = KubernetesClient.translate_api_exception(exc)

        assert isinstance(result, KubernetesError)
        assert "Something went wrong" in result.message


@pytest.mark.unit
@pytest.mark.kubernetes
class TestKubernetesClientRetryDecorator:
    """Test KubernetesClient retry decorator."""

    @patch("kubernetes.config")
    def test_make_retry_decorator(self, mock_config: MagicMock) -> None:
        """Test creation of retry decorator."""
        plugin_config = KubernetesPluginConfig()
        client = KubernetesClient(plugin_config)

        decorator = client.make_retry_decorator()
        assert decorator is not None


@pytest.mark.unit
@pytest.mark.kubernetes
class TestKubernetesClientConnectionCheck:
    """Test KubernetesClient connection checking."""

    @patch("kubernetes.config")
    @patch("kubernetes.client.VersionApi")
    def test_check_connection_success(
        self, mock_version_api: MagicMock, mock_config: MagicMock
    ) -> None:
        """Test successful connection check."""
        mock_api_instance = MagicMock()
        mock_version_api.return_value = mock_api_instance

        plugin_config = KubernetesPluginConfig()
        client = KubernetesClient(plugin_config)

        result = client.check_connection()
        assert result is True
        mock_api_instance.get_code.assert_called_once()

    @patch("kubernetes.config")
    @patch("kubernetes.client.VersionApi")
    def test_check_connection_failure(
        self, mock_version_api: MagicMock, mock_config: MagicMock
    ) -> None:
        """Test failed connection check."""
        mock_api_instance = MagicMock()
        mock_api_instance.get_code.side_effect = Exception("Connection failed")
        mock_version_api.return_value = mock_api_instance

        plugin_config = KubernetesPluginConfig()
        client = KubernetesClient(plugin_config)

        result = client.check_connection()
        assert result is False

    @patch("kubernetes.config")
    @patch("kubernetes.client.VersionApi")
    def test_get_cluster_version(self, mock_version_api: MagicMock, mock_config: MagicMock) -> None:
        """Test getting cluster version."""
        mock_version_info = MagicMock()
        mock_version_info.major = "1"
        mock_version_info.minor = "28"

        mock_api_instance = MagicMock()
        mock_api_instance.get_code.return_value = mock_version_info
        mock_version_api.return_value = mock_api_instance

        plugin_config = KubernetesPluginConfig()
        client = KubernetesClient(plugin_config)

        version = client.get_cluster_version()
        assert version == "v1.28"

    @patch("kubernetes.config")
    @patch("kubernetes.client.VersionApi")
    def test_get_cluster_version_error(
        self, mock_version_api: MagicMock, mock_config: MagicMock
    ) -> None:
        """Test error handling when getting cluster version."""
        mock_api_instance = MagicMock()
        mock_api_instance.get_code.side_effect = Exception("Connection failed")
        mock_version_api.return_value = mock_api_instance

        plugin_config = KubernetesPluginConfig()
        client = KubernetesClient(plugin_config)

        with pytest.raises(KubernetesConnectionError) as exc_info:
            client.get_cluster_version()

        assert "Failed to get cluster version" in str(exc_info.value)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestKubernetesClientProperties:
    """Test KubernetesClient properties."""

    @patch("kubernetes.config")
    def test_default_namespace_property(self, mock_config: MagicMock) -> None:
        """Test default_namespace property."""
        cluster_cfg = ClusterConfig(namespace="production")
        plugin_config = KubernetesPluginConfig(
            clusters={"prod": cluster_cfg},
            active_cluster="prod",
        )
        client = KubernetesClient(plugin_config)

        assert client.default_namespace == "production"

    @patch("kubernetes.config")
    def test_timeout_property(self, mock_config: MagicMock) -> None:
        """Test timeout property."""
        cluster_cfg = ClusterConfig(timeout=600)
        plugin_config = KubernetesPluginConfig(
            clusters={"test": cluster_cfg},
            active_cluster="test",
        )
        client = KubernetesClient(plugin_config)

        assert client.timeout == 600


@pytest.mark.unit
@pytest.mark.kubernetes
class TestKubernetesClientLifecycle:
    """Test KubernetesClient lifecycle methods."""

    @patch("kubernetes.config")
    def test_close(self, mock_config: MagicMock) -> None:
        """Test close method invalidates API cache."""
        plugin_config = KubernetesPluginConfig()
        client = KubernetesClient(plugin_config)

        with patch("kubernetes.client.CoreV1Api"):
            _ = client.core_v1
            assert client._core_v1 is not None

        client.close()
        assert client._core_v1 is None

    @patch("kubernetes.config")
    def test_context_manager(self, mock_config: MagicMock) -> None:
        """Test context manager protocol."""
        plugin_config = KubernetesPluginConfig()

        with KubernetesClient(plugin_config) as client:
            assert isinstance(client, KubernetesClient)
            with patch("kubernetes.client.CoreV1Api"):
                _ = client.core_v1
                assert client._core_v1 is not None

        assert client._core_v1 is None

    @patch("kubernetes.config")
    def test_invalidate_api_cache(self, mock_config: MagicMock) -> None:
        """Test _invalidate_api_cache method."""
        plugin_config = KubernetesPluginConfig()
        client = KubernetesClient(plugin_config)

        with patch("kubernetes.client.CoreV1Api"):
            _ = client.core_v1
        with patch("kubernetes.client.AppsV1Api"):
            _ = client.apps_v1

        client._invalidate_api_cache()

        assert client._core_v1 is None
        assert client._apps_v1 is None
        assert client._batch_v1 is None
        assert client._networking_v1 is None
        assert client._rbac_v1 is None
        assert client._storage_v1 is None
        assert client._version_api is None
