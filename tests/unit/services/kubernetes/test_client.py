"""Unit tests for KubernetesService client."""

from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock, call, patch

import pytest

from system_operations_manager.services.kubernetes.client import KubernetesService

# ---------------------------------------------------------------------------
# MockApiException replicates the kubernetes.client.ApiException interface
# without requiring a live Kubernetes cluster.  It is used by every test that
# exercises the 404 / non-404 / re-raise branches.
# ---------------------------------------------------------------------------


class MockApiException(Exception):
    """Minimal stand-in for kubernetes.client.ApiException."""

    def __init__(self, status: int = 500, reason: str = "Error") -> None:
        self.status = status
        self.reason = reason
        super().__init__(reason)


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def k8s_service() -> KubernetesService:
    """Return a KubernetesService whose __init__ has been bypassed.

    All kubernetes-package interaction happens through pre-installed MagicMock
    objects on the instance so that no real cluster or kubeconfig is needed.
    """
    with patch(
        "system_operations_manager.services.kubernetes.client.KubernetesService.__init__",
        lambda self: None,
    ):
        svc = KubernetesService()
        svc._core_v1 = MagicMock()
        svc._apps_v1 = MagicMock()
        svc._log = MagicMock()
        return svc


# ===========================================================================
# Constructor Tests
# ===========================================================================


class TestKubernetesServiceInit:
    """Tests for KubernetesService.__init__."""

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_init_loads_kubeconfig_successfully(self) -> None:
        """Constructor should bind the logger and call load_kube_config."""
        mock_k8s = ModuleType("kubernetes")
        mock_client_mod = ModuleType("kubernetes.client")
        mock_config_mod = ModuleType("kubernetes.config")

        mock_k8s.client = mock_client_mod  # type: ignore[attr-defined]
        mock_k8s.config = mock_config_mod  # type: ignore[attr-defined]

        mock_client_mod.CoreV1Api = MagicMock(return_value=MagicMock())  # type: ignore[attr-defined]
        mock_client_mod.AppsV1Api = MagicMock(return_value=MagicMock())  # type: ignore[attr-defined]
        mock_config_mod.load_kube_config = MagicMock()  # type: ignore[attr-defined]
        mock_config_mod.load_incluster_config = MagicMock()  # type: ignore[attr-defined]
        mock_config_mod.ConfigException = Exception  # type: ignore[attr-defined]

        with patch.dict(
            sys.modules,
            {
                "kubernetes": mock_k8s,
                "kubernetes.client": mock_client_mod,
                "kubernetes.config": mock_config_mod,
            },
        ):
            svc = KubernetesService()

        mock_config_mod.load_kube_config.assert_called_once()
        mock_config_mod.load_incluster_config.assert_not_called()
        assert svc._core_v1 is mock_client_mod.CoreV1Api.return_value
        assert svc._apps_v1 is mock_client_mod.AppsV1Api.return_value

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_init_falls_back_to_incluster_config_on_config_exception(self) -> None:
        """Constructor should fall back to load_incluster_config when kubeconfig fails."""
        mock_k8s = ModuleType("kubernetes")
        mock_client_mod = ModuleType("kubernetes.client")
        mock_config_mod = ModuleType("kubernetes.config")

        mock_k8s.client = mock_client_mod  # type: ignore[attr-defined]
        mock_k8s.config = mock_config_mod  # type: ignore[attr-defined]

        class _ConfigException(Exception):
            pass

        mock_config_mod.ConfigException = _ConfigException  # type: ignore[attr-defined]
        mock_config_mod.load_kube_config = MagicMock(  # type: ignore[attr-defined]
            side_effect=_ConfigException("no kubeconfig")
        )
        mock_config_mod.load_incluster_config = MagicMock()  # type: ignore[attr-defined]
        mock_client_mod.CoreV1Api = MagicMock(return_value=MagicMock())  # type: ignore[attr-defined]
        mock_client_mod.AppsV1Api = MagicMock(return_value=MagicMock())  # type: ignore[attr-defined]

        with patch.dict(
            sys.modules,
            {
                "kubernetes": mock_k8s,
                "kubernetes.client": mock_client_mod,
                "kubernetes.config": mock_config_mod,
            },
        ):
            svc = KubernetesService()

        mock_config_mod.load_kube_config.assert_called_once()
        mock_config_mod.load_incluster_config.assert_called_once()
        assert svc._core_v1 is mock_client_mod.CoreV1Api.return_value
        assert svc._apps_v1 is mock_client_mod.AppsV1Api.return_value

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_init_creates_core_v1_and_apps_v1_apis(self) -> None:
        """Constructor should attach CoreV1Api and AppsV1Api instances."""
        mock_k8s = ModuleType("kubernetes")
        mock_client_mod = ModuleType("kubernetes.client")
        mock_config_mod = ModuleType("kubernetes.config")

        mock_k8s.client = mock_client_mod  # type: ignore[attr-defined]
        mock_k8s.config = mock_config_mod  # type: ignore[attr-defined]

        core_v1_instance = MagicMock(name="CoreV1Api")
        apps_v1_instance = MagicMock(name="AppsV1Api")
        mock_client_mod.CoreV1Api = MagicMock(return_value=core_v1_instance)  # type: ignore[attr-defined]
        mock_client_mod.AppsV1Api = MagicMock(return_value=apps_v1_instance)  # type: ignore[attr-defined]
        mock_config_mod.load_kube_config = MagicMock()  # type: ignore[attr-defined]
        mock_config_mod.load_incluster_config = MagicMock()  # type: ignore[attr-defined]
        mock_config_mod.ConfigException = Exception  # type: ignore[attr-defined]

        with patch.dict(
            sys.modules,
            {
                "kubernetes": mock_k8s,
                "kubernetes.client": mock_client_mod,
                "kubernetes.config": mock_config_mod,
            },
        ):
            svc = KubernetesService()

        assert svc._core_v1 is core_v1_instance
        assert svc._apps_v1 is apps_v1_instance


# ===========================================================================
# Namespace Operations
# ===========================================================================


class TestNamespaceExists:
    """Tests for KubernetesService.namespace_exists."""

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_namespace_exists_returns_true_when_found(self, k8s_service: KubernetesService) -> None:
        """Should return True when read_namespace succeeds."""
        k8s_service._core_v1.read_namespace.return_value = MagicMock()

        with patch("kubernetes.client.ApiException", MockApiException):
            result = k8s_service.namespace_exists("my-namespace")

        assert result is True
        k8s_service._core_v1.read_namespace.assert_called_once_with("my-namespace")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_namespace_exists_returns_false_on_404(self, k8s_service: KubernetesService) -> None:
        """Should return False when the API raises a 404 ApiException."""
        k8s_service._core_v1.read_namespace.side_effect = MockApiException(
            status=404, reason="Not Found"
        )

        with patch("kubernetes.client.ApiException", MockApiException):
            result = k8s_service.namespace_exists("missing-namespace")

        assert result is False

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_namespace_exists_reraises_non_404_exception(
        self, k8s_service: KubernetesService
    ) -> None:
        """Should re-raise ApiException when status is not 404."""
        k8s_service._core_v1.read_namespace.side_effect = MockApiException(
            status=500, reason="Internal Server Error"
        )

        with (
            patch("kubernetes.client.ApiException", MockApiException),
            pytest.raises(MockApiException) as exc_info,
        ):
            k8s_service.namespace_exists("any-namespace")

        assert exc_info.value.status == 500


class TestCreateNamespace:
    """Tests for KubernetesService.create_namespace."""

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_create_namespace_calls_api_and_returns_result(
        self, k8s_service: KubernetesService
    ) -> None:
        """Should call create_namespace on core_v1 and return the result."""
        expected = MagicMock(name="V1Namespace")
        k8s_service._core_v1.create_namespace.return_value = expected

        mock_namespace = MagicMock(name="MockNamespaceObj")
        with (
            patch("kubernetes.client.V1Namespace", return_value=mock_namespace) as mock_v1ns,
            patch("kubernetes.client.V1ObjectMeta", return_value=MagicMock()) as mock_meta,
        ):
            result = k8s_service.create_namespace("new-namespace")

        assert result is expected
        k8s_service._core_v1.create_namespace.assert_called_once_with(mock_namespace)
        mock_meta.assert_called_once_with(name="new-namespace")
        mock_v1ns.assert_called_once_with(metadata=mock_meta.return_value)
        k8s_service._log.info.assert_called_once_with(
            "namespace_created", namespace="new-namespace"
        )


class TestEnsureNamespace:
    """Tests for KubernetesService.ensure_namespace."""

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_ensure_namespace_returns_existing_namespace(
        self, k8s_service: KubernetesService
    ) -> None:
        """Should return the existing namespace when read_namespace succeeds."""
        existing = MagicMock(name="ExistingNamespace")
        k8s_service._core_v1.read_namespace.return_value = existing

        with patch("kubernetes.client.ApiException", MockApiException):
            result = k8s_service.ensure_namespace("existing-namespace")

        assert result is existing
        k8s_service._core_v1.read_namespace.assert_called_once_with("existing-namespace")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_ensure_namespace_creates_when_not_found(self, k8s_service: KubernetesService) -> None:
        """Should call create_namespace when a 404 is raised."""
        k8s_service._core_v1.read_namespace.side_effect = MockApiException(
            status=404, reason="Not Found"
        )
        created = MagicMock(name="CreatedNamespace")
        k8s_service.create_namespace = MagicMock(return_value=created)  # type: ignore[method-assign]

        with patch("kubernetes.client.ApiException", MockApiException):
            result = k8s_service.ensure_namespace("new-namespace")

        assert result is created
        k8s_service.create_namespace.assert_called_once_with("new-namespace")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_ensure_namespace_reraises_non_404_exception(
        self, k8s_service: KubernetesService
    ) -> None:
        """Should re-raise ApiException when status is not 404."""
        k8s_service._core_v1.read_namespace.side_effect = MockApiException(
            status=403, reason="Forbidden"
        )

        with (
            patch("kubernetes.client.ApiException", MockApiException),
            pytest.raises(MockApiException) as exc_info,
        ):
            k8s_service.ensure_namespace("any-namespace")

        assert exc_info.value.status == 403


class TestDeleteNamespace:
    """Tests for KubernetesService.delete_namespace."""

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_delete_namespace_calls_api(self, k8s_service: KubernetesService) -> None:
        """Should call delete_namespace on core_v1 and log the event."""
        k8s_service.delete_namespace("old-namespace")

        k8s_service._core_v1.delete_namespace.assert_called_once_with("old-namespace")
        k8s_service._log.info.assert_called_once_with(
            "namespace_deleted", namespace="old-namespace"
        )


# ===========================================================================
# Secret Operations
# ===========================================================================


class TestSecretExists:
    """Tests for KubernetesService.secret_exists."""

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_secret_exists_returns_true_when_found(self, k8s_service: KubernetesService) -> None:
        """Should return True when read_namespaced_secret succeeds."""
        k8s_service._core_v1.read_namespaced_secret.return_value = MagicMock()

        with patch("kubernetes.client.ApiException", MockApiException):
            result = k8s_service.secret_exists("my-ns", "my-secret")

        assert result is True
        k8s_service._core_v1.read_namespaced_secret.assert_called_once_with("my-secret", "my-ns")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_secret_exists_returns_false_on_404(self, k8s_service: KubernetesService) -> None:
        """Should return False when the API raises a 404 ApiException."""
        k8s_service._core_v1.read_namespaced_secret.side_effect = MockApiException(
            status=404, reason="Not Found"
        )

        with patch("kubernetes.client.ApiException", MockApiException):
            result = k8s_service.secret_exists("my-ns", "missing-secret")

        assert result is False

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_secret_exists_reraises_non_404_exception(self, k8s_service: KubernetesService) -> None:
        """Should re-raise ApiException when status is not 404."""
        k8s_service._core_v1.read_namespaced_secret.side_effect = MockApiException(
            status=503, reason="Service Unavailable"
        )

        with (
            patch("kubernetes.client.ApiException", MockApiException),
            pytest.raises(MockApiException) as exc_info,
        ):
            k8s_service.secret_exists("my-ns", "any-secret")

        assert exc_info.value.status == 503


class TestCreateSecret:
    """Tests for KubernetesService.create_secret."""

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_create_secret_with_default_opaque_type(self, k8s_service: KubernetesService) -> None:
        """Should create secret with type=Opaque by default."""
        expected = MagicMock(name="V1Secret")
        k8s_service._core_v1.create_namespaced_secret.return_value = expected

        mock_secret = MagicMock(name="MockSecretObj")
        with (
            patch("kubernetes.client.V1Secret", return_value=mock_secret) as mock_v1secret,
            patch("kubernetes.client.V1ObjectMeta", return_value=MagicMock()) as mock_meta,
        ):
            result = k8s_service.create_secret(
                namespace="my-ns",
                name="my-secret",
                data={"key": "value"},
            )

        assert result is expected
        k8s_service._core_v1.create_namespaced_secret.assert_called_once_with("my-ns", mock_secret)
        mock_meta.assert_called_once_with(name="my-secret", namespace="my-ns")
        mock_v1secret.assert_called_once_with(
            metadata=mock_meta.return_value,
            type="Opaque",
            string_data={"key": "value"},
        )
        k8s_service._log.info.assert_called_once_with(
            "secret_created", namespace="my-ns", name="my-secret"
        )

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_create_secret_with_custom_type(self, k8s_service: KubernetesService) -> None:
        """Should pass the custom secret_type through to V1Secret."""
        expected = MagicMock(name="V1Secret")
        k8s_service._core_v1.create_namespaced_secret.return_value = expected

        mock_secret = MagicMock(name="MockSecretObj")
        with (
            patch("kubernetes.client.V1Secret", return_value=mock_secret) as mock_v1secret,
            patch("kubernetes.client.V1ObjectMeta", return_value=MagicMock()) as mock_meta,
        ):
            result = k8s_service.create_secret(
                namespace="my-ns",
                name="tls-secret",
                data={"tls.crt": "cert", "tls.key": "key"},
                secret_type="kubernetes.io/tls",
            )

        assert result is expected
        mock_v1secret.assert_called_once_with(
            metadata=mock_meta.return_value,
            type="kubernetes.io/tls",
            string_data={"tls.crt": "cert", "tls.key": "key"},
        )


class TestCreateTlsSecret:
    """Tests for KubernetesService.create_tls_secret."""

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_create_tls_secret_when_secret_does_not_exist(
        self, k8s_service: KubernetesService
    ) -> None:
        """Should call create_secret directly when the secret does not already exist."""
        expected = MagicMock(name="TlsSecret")
        k8s_service.secret_exists = MagicMock(return_value=False)  # type: ignore[method-assign]
        k8s_service.create_secret = MagicMock(return_value=expected)  # type: ignore[method-assign]

        result = k8s_service.create_tls_secret("my-ns", "tls-cert", "CERT_PEM", "KEY_PEM")

        assert result is expected
        k8s_service.secret_exists.assert_called_once_with("my-ns", "tls-cert")
        k8s_service.create_secret.assert_called_once_with(
            namespace="my-ns",
            name="tls-cert",
            data={"tls.crt": "CERT_PEM", "tls.key": "KEY_PEM"},
            secret_type="kubernetes.io/tls",
        )

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_create_tls_secret_raises_runtime_error_when_exists_and_no_force(
        self, k8s_service: KubernetesService
    ) -> None:
        """Should raise RuntimeError when secret exists and force=False."""
        k8s_service.secret_exists = MagicMock(return_value=True)  # type: ignore[method-assign]
        k8s_service.delete_secret = MagicMock()  # type: ignore[method-assign]
        k8s_service.create_secret = MagicMock()  # type: ignore[method-assign]

        with pytest.raises(RuntimeError, match="already exists"):
            k8s_service.create_tls_secret("my-ns", "existing-secret", "CERT", "KEY")

        k8s_service.delete_secret.assert_not_called()
        k8s_service.create_secret.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_create_tls_secret_with_force_deletes_then_creates(
        self, k8s_service: KubernetesService
    ) -> None:
        """Should delete the existing secret then create a new one when force=True."""
        expected = MagicMock(name="ReplacedTlsSecret")
        k8s_service.secret_exists = MagicMock(return_value=True)  # type: ignore[method-assign]
        k8s_service.delete_secret = MagicMock()  # type: ignore[method-assign]
        k8s_service.create_secret = MagicMock(return_value=expected)  # type: ignore[method-assign]

        manager = MagicMock()
        manager.attach_mock(k8s_service.delete_secret, "delete_secret")
        manager.attach_mock(k8s_service.create_secret, "create_secret")

        result = k8s_service.create_tls_secret(
            "my-ns", "existing-secret", "CERT", "KEY", force=True
        )

        assert result is expected
        # Verify ordering: delete before create
        assert manager.mock_calls == [
            call.delete_secret("my-ns", "existing-secret"),
            call.create_secret(
                namespace="my-ns",
                name="existing-secret",
                data={"tls.crt": "CERT", "tls.key": "KEY"},
                secret_type="kubernetes.io/tls",
            ),
        ]


class TestDeleteSecret:
    """Tests for KubernetesService.delete_secret."""

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_delete_secret_calls_api_and_logs(self, k8s_service: KubernetesService) -> None:
        """Should call delete_namespaced_secret and log the deletion."""
        k8s_service.delete_secret("my-ns", "old-secret")

        k8s_service._core_v1.delete_namespaced_secret.assert_called_once_with("old-secret", "my-ns")
        k8s_service._log.info.assert_called_once_with(
            "secret_deleted", namespace="my-ns", name="old-secret"
        )


class TestGetSecret:
    """Tests for KubernetesService.get_secret."""

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_get_secret_returns_secret_from_api(self, k8s_service: KubernetesService) -> None:
        """Should return the object returned by read_namespaced_secret."""
        expected = MagicMock(name="V1Secret")
        k8s_service._core_v1.read_namespaced_secret.return_value = expected

        result = k8s_service.get_secret("my-ns", "my-secret")

        assert result is expected
        k8s_service._core_v1.read_namespaced_secret.assert_called_once_with("my-secret", "my-ns")


# ===========================================================================
# ConfigMap Operations
# ===========================================================================


class TestConfigMapExists:
    """Tests for KubernetesService.configmap_exists."""

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_configmap_exists_returns_true_when_found(self, k8s_service: KubernetesService) -> None:
        """Should return True when read_namespaced_config_map succeeds."""
        k8s_service._core_v1.read_namespaced_config_map.return_value = MagicMock()

        with patch("kubernetes.client.ApiException", MockApiException):
            result = k8s_service.configmap_exists("my-ns", "my-cm")

        assert result is True
        k8s_service._core_v1.read_namespaced_config_map.assert_called_once_with("my-cm", "my-ns")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_configmap_exists_returns_false_on_404(self, k8s_service: KubernetesService) -> None:
        """Should return False when the API raises a 404 ApiException."""
        k8s_service._core_v1.read_namespaced_config_map.side_effect = MockApiException(
            status=404, reason="Not Found"
        )

        with patch("kubernetes.client.ApiException", MockApiException):
            result = k8s_service.configmap_exists("my-ns", "missing-cm")

        assert result is False

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_configmap_exists_reraises_non_404_exception(
        self, k8s_service: KubernetesService
    ) -> None:
        """Should re-raise ApiException when status is not 404."""
        k8s_service._core_v1.read_namespaced_config_map.side_effect = MockApiException(
            status=401, reason="Unauthorized"
        )

        with (
            patch("kubernetes.client.ApiException", MockApiException),
            pytest.raises(MockApiException) as exc_info,
        ):
            k8s_service.configmap_exists("my-ns", "any-cm")

        assert exc_info.value.status == 401


class TestCreateConfigMap:
    """Tests for KubernetesService.create_configmap."""

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_create_configmap_calls_api_and_logs(self, k8s_service: KubernetesService) -> None:
        """Should build and submit a V1ConfigMap object then log the creation."""
        mock_cm = MagicMock(name="MockConfigMapObj")
        with (
            patch("kubernetes.client.V1ConfigMap", return_value=mock_cm) as mock_v1cm,
            patch("kubernetes.client.V1ObjectMeta", return_value=MagicMock()) as mock_meta,
        ):
            k8s_service.create_configmap(
                namespace="my-ns",
                name="app-config",
                data={"key": "value"},
            )

        k8s_service._core_v1.create_namespaced_config_map.assert_called_once_with("my-ns", mock_cm)
        mock_meta.assert_called_once_with(name="app-config", namespace="my-ns")
        mock_v1cm.assert_called_once_with(
            metadata=mock_meta.return_value,
            data={"key": "value"},
        )
        k8s_service._log.info.assert_called_once_with(
            "configmap_created", namespace="my-ns", name="app-config"
        )


class TestDeleteConfigMap:
    """Tests for KubernetesService.delete_configmap."""

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_delete_configmap_calls_api_and_logs(self, k8s_service: KubernetesService) -> None:
        """Should call delete_namespaced_config_map and log the deletion."""
        k8s_service.delete_configmap("my-ns", "old-config")

        k8s_service._core_v1.delete_namespaced_config_map.assert_called_once_with(
            "old-config", "my-ns"
        )
        k8s_service._log.info.assert_called_once_with(
            "configmap_deleted", namespace="my-ns", name="old-config"
        )
