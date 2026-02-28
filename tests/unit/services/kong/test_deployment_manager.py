"""Unit tests for Kong Gateway deployment manager."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, call, patch

import pytest

from system_operations_manager.services.kong.deployment_manager import (
    DeploymentError,
    DeploymentInfo,
    DeploymentStatus,
    HelmClient,
    KongDeploymentManager,
    KubernetesClient,
    PodInfo,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_api_exception_class() -> type:
    """Build a lightweight ApiException class for use in tests."""

    class ApiException(Exception):
        def __init__(self, status: int = 500, reason: str = "Error", body: str = "") -> None:
            self.status = status
            self.reason = reason
            self.body = body
            super().__init__(reason)

    return ApiException


def _make_k8s_client() -> tuple[KubernetesClient, type]:
    """Create a KubernetesClient with all internals pre-mocked."""
    ApiException = _make_api_exception_class()

    with patch(
        "system_operations_manager.services.kong.deployment_manager.KubernetesClient.__init__",
        lambda self: None,
    ):
        client = KubernetesClient()
        client._core_v1 = MagicMock()
        client._apps_v1 = MagicMock()

        mock_client_module = MagicMock()
        mock_client_module.rest.ApiException = ApiException
        mock_client_module.V1Namespace = MagicMock(return_value=MagicMock())
        mock_client_module.V1ObjectMeta = MagicMock(return_value=MagicMock())
        mock_client_module.V1Secret = MagicMock(return_value=MagicMock())
        mock_client_module.ApiClient.return_value = MagicMock()
        client._client = mock_client_module

    return client, ApiException


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def k8s_client() -> tuple[KubernetesClient, type]:
    """KubernetesClient with all kubernetes calls mocked out."""
    return _make_k8s_client()


@pytest.fixture
def helm_client() -> HelmClient:
    """HelmClient with helm binary presence mocked."""
    with patch("shutil.which", return_value="/usr/bin/helm"):
        return HelmClient()


@pytest.fixture
def manager(tmp_path: Path) -> Any:
    """KongDeploymentManager with lazy clients pre-set as mocks.

    Returns Any so that tests can access MagicMock attributes on _k8s/_helm
    without union-attr mypy errors (the real types are KubernetesClient | None
    and HelmClient | None).
    """
    mgr = KongDeploymentManager(
        project_root=tmp_path,
        namespace="kong",
        release_name="kong",
    )
    mgr._k8s = MagicMock()
    mgr._helm = MagicMock()
    return mgr


# ===========================================================================
# DeploymentError
# ===========================================================================


class TestDeploymentError:
    """Tests for the DeploymentError exception class."""

    @pytest.mark.unit
    @pytest.mark.kong
    def test_message_only(self) -> None:
        """Constructor stores message and leaves details as None."""
        err = DeploymentError("something went wrong")

        assert err.message == "something went wrong"
        assert err.details is None
        assert str(err) == "something went wrong"

    @pytest.mark.unit
    @pytest.mark.kong
    def test_message_and_details(self) -> None:
        """Constructor stores both message and details."""
        err = DeploymentError("helm failed", details="chart not found")

        assert err.message == "helm failed"
        assert err.details == "chart not found"
        assert isinstance(err, Exception)


# ===========================================================================
# DeploymentStatus
# ===========================================================================


class TestDeploymentStatus:
    """Tests for the DeploymentStatus StrEnum."""

    @pytest.mark.unit
    @pytest.mark.kong
    def test_all_enum_values(self) -> None:
        """All expected string values are present on the enum."""
        assert DeploymentStatus.NOT_INSTALLED.value == "not_installed"
        assert DeploymentStatus.RUNNING.value == "running"
        assert DeploymentStatus.DEGRADED.value == "degraded"
        assert DeploymentStatus.FAILED.value == "failed"
        assert DeploymentStatus.UNKNOWN.value == "unknown"

        # Confirm it behaves as a string
        assert str(DeploymentStatus.RUNNING) == "running"


# ===========================================================================
# PodInfo & DeploymentInfo
# ===========================================================================


class TestPodInfo:
    """Tests for the PodInfo dataclass."""

    @pytest.mark.unit
    @pytest.mark.kong
    def test_defaults(self) -> None:
        """PodInfo.restarts defaults to 0."""
        pod = PodInfo(name="my-pod", phase="Running", ready=True)

        assert pod.name == "my-pod"
        assert pod.phase == "Running"
        assert pod.ready is True
        assert pod.restarts == 0

    @pytest.mark.unit
    @pytest.mark.kong
    def test_explicit_restarts(self) -> None:
        """PodInfo accepts an explicit restart count."""
        pod = PodInfo(name="crashing-pod", phase="Running", ready=False, restarts=5)

        assert pod.restarts == 5


class TestDeploymentInfo:
    """Tests for the DeploymentInfo dataclass."""

    @pytest.mark.unit
    @pytest.mark.kong
    def test_defaults(self) -> None:
        """DeploymentInfo optional fields default to None/False/empty list."""
        info = DeploymentInfo(status=DeploymentStatus.UNKNOWN, namespace="kong")

        assert info.status == DeploymentStatus.UNKNOWN
        assert info.namespace == "kong"
        assert info.chart is None
        assert info.chart_version is None
        assert info.app_version is None
        assert info.postgres_ready is False
        assert info.gateway_ready is False
        assert info.controller_ready is False
        assert info.pods == []

    @pytest.mark.unit
    @pytest.mark.kong
    def test_pods_list_not_shared(self) -> None:
        """Each DeploymentInfo instance gets its own pods list."""
        info_a = DeploymentInfo(status=DeploymentStatus.RUNNING, namespace="a")
        info_b = DeploymentInfo(status=DeploymentStatus.RUNNING, namespace="b")

        info_a.pods.append(PodInfo(name="p", phase="Running", ready=True))

        assert info_b.pods == []


# ===========================================================================
# KubernetesClient.__init__
# ===========================================================================


class TestKubernetesClientInit:
    """Tests for KubernetesClient initialisation paths.

    The kubernetes package is installed in the test environment, so we can
    exercise the real __init__ body by patching kubernetes.config at import time.
    """

    @pytest.mark.unit
    @pytest.mark.kong
    def test_incluster_config_success(self) -> None:
        """Uses in-cluster config when load_incluster_config succeeds."""
        with (
            patch("kubernetes.config.load_incluster_config") as mock_incluster,
            patch("kubernetes.client.CoreV1Api") as mock_core,
            patch("kubernetes.client.AppsV1Api") as mock_apps,
        ):
            mock_incluster.return_value = None  # success
            kube = KubernetesClient()

        assert kube._core_v1 is mock_core.return_value
        assert kube._apps_v1 is mock_apps.return_value
        mock_incluster.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.kong
    def test_fallback_to_kubeconfig(self) -> None:
        """Falls back to load_kube_config when in-cluster raises ConfigException."""
        import kubernetes.config as k8s_config

        with (
            patch(
                "kubernetes.config.load_incluster_config",
                side_effect=k8s_config.ConfigException("not in cluster"),
            ),
            patch("kubernetes.config.load_kube_config") as mock_kubeconfig,
            patch("kubernetes.client.CoreV1Api"),
            patch("kubernetes.client.AppsV1Api"),
        ):
            kube = KubernetesClient()

        mock_kubeconfig.assert_called_once()
        assert kube is not None

    @pytest.mark.unit
    @pytest.mark.kong
    def test_import_error_raises_deployment_error(self) -> None:
        """ImportError from kubernetes package is converted to DeploymentError.

        We simulate the ImportError by making the 'from kubernetes import client, config'
        line inside __init__ raise by temporarily hiding the module from sys.modules.
        """
        import sys

        real_kubernetes = sys.modules.pop("kubernetes", None)
        real_kubernetes_config = sys.modules.pop("kubernetes.config", None)
        real_kubernetes_client = sys.modules.pop("kubernetes.client", None)

        try:

            def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
                if name == "kubernetes":
                    raise ImportError("No module named 'kubernetes'")
                return __import__(name, *args, **kwargs)

            import builtins

            original_builtins_import = builtins.__import__
            builtins.__import__ = fake_import
            try:
                with pytest.raises(DeploymentError) as exc_info:
                    KubernetesClient()
                assert "Kubernetes client not installed" in exc_info.value.message
            finally:
                builtins.__import__ = original_builtins_import
        finally:
            # Restore the real kubernetes modules
            if real_kubernetes is not None:
                sys.modules["kubernetes"] = real_kubernetes
            if real_kubernetes_config is not None:
                sys.modules["kubernetes.config"] = real_kubernetes_config
            if real_kubernetes_client is not None:
                sys.modules["kubernetes.client"] = real_kubernetes_client

    @pytest.mark.unit
    @pytest.mark.kong
    def test_generic_exception_raises_deployment_error(self) -> None:
        """Non-Import exceptions during init are wrapped in DeploymentError."""
        with (
            patch(
                "kubernetes.config.load_incluster_config",
                side_effect=RuntimeError("connection refused"),
            ),
            pytest.raises(DeploymentError) as exc_info,
        ):
            KubernetesClient()

        assert "Failed to initialize Kubernetes client" in exc_info.value.message
        assert "connection refused" in exc_info.value.details


# ===========================================================================
# KubernetesClient properties
# ===========================================================================


class TestKubernetesClientProperties:
    """Tests for the core_v1 and apps_v1 properties."""

    @pytest.mark.unit
    @pytest.mark.kong
    def test_core_v1_property(self, k8s_client: tuple[Any, ...]) -> None:
        """core_v1 returns _core_v1."""
        client, _ = k8s_client
        assert client.core_v1 is client._core_v1

    @pytest.mark.unit
    @pytest.mark.kong
    def test_apps_v1_property(self, k8s_client: tuple[Any, ...]) -> None:
        """apps_v1 returns _apps_v1."""
        client, _ = k8s_client
        assert client.apps_v1 is client._apps_v1


# ===========================================================================
# KubernetesClient.namespace_exists
# ===========================================================================


class TestNamespaceExists:
    """Tests for KubernetesClient.namespace_exists."""

    @pytest.mark.unit
    @pytest.mark.kong
    def test_returns_true_when_namespace_found(self, k8s_client: tuple[Any, ...]) -> None:
        """Returns True when read_namespace succeeds."""
        client, _ = k8s_client
        client._core_v1.read_namespace.return_value = MagicMock()

        assert client.namespace_exists("kong") is True
        client._core_v1.read_namespace.assert_called_once_with("kong")

    @pytest.mark.unit
    @pytest.mark.kong
    def test_returns_false_on_404(self, k8s_client: tuple[Any, ...]) -> None:
        """Returns False when read_namespace raises ApiException with status 404."""
        client, ApiException = k8s_client
        client._core_v1.read_namespace.side_effect = ApiException(status=404)

        assert client.namespace_exists("missing") is False

    @pytest.mark.unit
    @pytest.mark.kong
    def test_reraises_non_404_exception(self, k8s_client: tuple[Any, ...]) -> None:
        """Re-raises ApiException when status is not 404."""
        client, ApiException = k8s_client
        client._core_v1.read_namespace.side_effect = ApiException(status=403, reason="Forbidden")

        with pytest.raises(ApiException) as exc_info:
            client.namespace_exists("locked")

        assert exc_info.value.status == 403


# ===========================================================================
# KubernetesClient.create_namespace
# ===========================================================================


class TestCreateNamespace:
    """Tests for KubernetesClient.create_namespace."""

    @pytest.mark.unit
    @pytest.mark.kong
    def test_creates_when_not_exists(self, k8s_client: tuple[Any, ...]) -> None:
        """Calls create_namespace when namespace does not exist."""
        client, ApiException = k8s_client
        # namespace_exists returns False
        client._core_v1.read_namespace.side_effect = ApiException(status=404)

        client.create_namespace("new-ns")

        client._core_v1.create_namespace.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.kong
    def test_skips_when_already_exists(self, k8s_client: tuple[Any, ...]) -> None:
        """Does NOT call create_namespace when namespace already exists."""
        client, _ = k8s_client
        client._core_v1.read_namespace.return_value = MagicMock()  # namespace_exists = True

        client.create_namespace("existing-ns")

        client._core_v1.create_namespace.assert_not_called()


# ===========================================================================
# KubernetesClient.secret_exists
# ===========================================================================


class TestSecretExists:
    """Tests for KubernetesClient.secret_exists."""

    @pytest.mark.unit
    @pytest.mark.kong
    def test_returns_true_when_found(self, k8s_client: tuple[Any, ...]) -> None:
        """Returns True when read_namespaced_secret succeeds."""
        client, _ = k8s_client
        client._core_v1.read_namespaced_secret.return_value = MagicMock()

        assert client.secret_exists("my-secret", "kong") is True

    @pytest.mark.unit
    @pytest.mark.kong
    def test_returns_false_on_404(self, k8s_client: tuple[Any, ...]) -> None:
        """Returns False when secret is not found (404)."""
        client, ApiException = k8s_client
        client._core_v1.read_namespaced_secret.side_effect = ApiException(status=404)

        assert client.secret_exists("missing-secret", "kong") is False

    @pytest.mark.unit
    @pytest.mark.kong
    def test_reraises_non_404(self, k8s_client: tuple[Any, ...]) -> None:
        """Re-raises ApiException for non-404 status codes."""
        client, ApiException = k8s_client
        client._core_v1.read_namespaced_secret.side_effect = ApiException(status=500)

        with pytest.raises(ApiException):
            client.secret_exists("my-secret", "kong")


# ===========================================================================
# KubernetesClient.create_secret_from_env_file
# ===========================================================================


class TestCreateSecretFromEnvFile:
    """Tests for KubernetesClient.create_secret_from_env_file."""

    @pytest.mark.unit
    @pytest.mark.kong
    def test_creates_secret_from_valid_env_file(
        self, k8s_client: tuple[Any, ...], tmp_path: Path
    ) -> None:
        """Parses env file, skips comments and blanks, creates secret."""
        client, ApiException = k8s_client
        # secret does not exist
        client._core_v1.read_namespaced_secret.side_effect = ApiException(status=404)

        env_file = tmp_path / ".env"
        env_file.write_text("KEY1=value1\nKEY2=value2\n# comment\n\n")

        client.create_secret_from_env_file("test-secret", "kong", env_file)

        client._core_v1.create_namespaced_secret.assert_called_once()
        # V1Secret was constructed with string_data containing both keys
        call_kwargs = client._client.V1Secret.call_args
        string_data = call_kwargs.kwargs.get("string_data") or call_kwargs[1].get("string_data")
        assert string_data == {"KEY1": "value1", "KEY2": "value2"}

    @pytest.mark.unit
    @pytest.mark.kong
    def test_raises_when_env_file_not_found(
        self, k8s_client: tuple[Any, ...], tmp_path: Path
    ) -> None:
        """Raises DeploymentError when env file does not exist."""
        client, _ = k8s_client
        missing = tmp_path / "missing.env"

        with pytest.raises(DeploymentError) as exc_info:
            client.create_secret_from_env_file("s", "ns", missing)

        assert "not found" in exc_info.value.message.lower()

    @pytest.mark.unit
    @pytest.mark.kong
    def test_replaces_existing_secret(self, k8s_client: tuple[Any, ...], tmp_path: Path) -> None:
        """Deletes existing secret before creating when replace=True."""
        client, _ = k8s_client
        # secret already exists
        client._core_v1.read_namespaced_secret.return_value = MagicMock()

        env_file = tmp_path / ".env"
        env_file.write_text("A=1\n")

        client.create_secret_from_env_file("old-secret", "kong", env_file, replace=True)

        client._core_v1.delete_namespaced_secret.assert_called_once_with("old-secret", "kong")
        client._core_v1.create_namespaced_secret.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.kong
    def test_skips_delete_when_replace_false(
        self, k8s_client: tuple[Any, ...], tmp_path: Path
    ) -> None:
        """Does not delete when replace=False even if secret exists."""
        client, _ = k8s_client
        client._core_v1.read_namespaced_secret.return_value = MagicMock()

        env_file = tmp_path / ".env"
        env_file.write_text("A=1\n")

        client.create_secret_from_env_file("existing", "kong", env_file, replace=False)

        client._core_v1.delete_namespaced_secret.assert_not_called()
        client._core_v1.create_namespaced_secret.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.kong
    def test_ignores_malformed_lines_without_equals(
        self, k8s_client: tuple[Any, ...], tmp_path: Path
    ) -> None:
        """Lines without '=' are silently skipped."""
        client, ApiException = k8s_client
        client._core_v1.read_namespaced_secret.side_effect = ApiException(status=404)

        env_file = tmp_path / ".env"
        env_file.write_text("VALID=yes\nno_equals_sign\n# comment\n")

        client.create_secret_from_env_file("s", "ns", env_file)

        call_kwargs = client._client.V1Secret.call_args
        string_data = call_kwargs.kwargs.get("string_data") or call_kwargs[1].get("string_data")
        assert "no_equals_sign" not in string_data
        assert string_data == {"VALID": "yes"}


# ===========================================================================
# KubernetesClient.apply_yaml_file
# ===========================================================================


def _make_fake_utils(
    *,
    fail_to_create_exc: Exception | None = None,
) -> tuple[MagicMock, type]:
    """Build a fake kubernetes.utils module for injection into sys.modules.

    Args:
        fail_to_create_exc: If given, create_from_dict will raise this exception.
                            Otherwise create_from_dict returns None (success).
    """

    class FakeFailToCreate(Exception):
        def __init__(self, excs: list[Any]) -> None:
            self.api_exceptions = excs
            super().__init__()

    fake_utils = MagicMock()
    fake_utils.FailToCreateError = FakeFailToCreate
    if fail_to_create_exc is not None:
        fake_utils.create_from_dict.side_effect = fail_to_create_exc
    else:
        fake_utils.create_from_dict.return_value = None
    return fake_utils, FakeFailToCreate


class TestApplyYamlFile:
    """Tests for KubernetesClient.apply_yaml_file.

    Most tests inject a fake ``kubernetes.utils`` module via ``sys.modules``
    so that the real method body (lines 190-229) is exercised without needing
    the kubernetes package installed.
    """

    @pytest.mark.unit
    @pytest.mark.kong
    def test_raises_when_file_not_found(self, k8s_client: tuple[Any, ...], tmp_path: Path) -> None:
        """Raises DeploymentError when YAML file does not exist."""
        client, _ = k8s_client
        missing = tmp_path / "missing.yaml"

        fake_utils, _ = _make_fake_utils()
        with (
            patch.dict("sys.modules", {"kubernetes": MagicMock(), "kubernetes.utils": fake_utils}),
            pytest.raises(DeploymentError) as exc_info,
        ):
            client.apply_yaml_file(missing)

        assert "not found" in exc_info.value.message.lower()

    @pytest.mark.unit
    @pytest.mark.kong
    def test_applies_manifest_successfully(
        self, k8s_client: tuple[Any, ...], tmp_path: Path
    ) -> None:
        """Returns list of created resource names on success."""
        client, _ = k8s_client
        yaml_file = tmp_path / "deploy.yaml"
        yaml_file.write_text("apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: my-app\n")

        with patch("kubernetes.utils.create_from_dict") as mock_create:
            mock_create.return_value = None
            result = client.apply_yaml_file(yaml_file)

        assert result == ["Deployment/my-app"]
        mock_create.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.kong
    def test_handles_409_conflict_as_exists(
        self, k8s_client: tuple[Any, ...], tmp_path: Path
    ) -> None:
        """409 Conflict from create_from_dict is treated as 'already exists'."""
        import kubernetes.utils as k8s_utils

        client, _ = k8s_client
        yaml_file = tmp_path / "manifest.yaml"
        yaml_file.write_text("apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: cfg\n")

        # Build a real FailToCreateError with a 409 api_exception
        api_exc = MagicMock()
        api_exc.status = 409
        api_exc.reason = "AlreadyExists"
        fail_exc = k8s_utils.FailToCreateError([api_exc])

        with patch("kubernetes.utils.create_from_dict", side_effect=fail_exc):
            result = client.apply_yaml_file(yaml_file)

        assert result == ["ConfigMap/cfg (exists)"]

    @pytest.mark.unit
    @pytest.mark.kong
    def test_non_409_failure_raises_deployment_error(
        self, k8s_client: tuple[Any, ...], tmp_path: Path
    ) -> None:
        """Non-409 FailToCreateError is re-raised as DeploymentError."""
        import kubernetes.utils as k8s_utils

        client, _ = k8s_client
        yaml_file = tmp_path / "manifest.yaml"
        yaml_file.write_text("apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: cfg\n")

        api_exc = MagicMock()
        api_exc.status = 500
        api_exc.reason = "InternalError"
        api_exc.body = "internal server error"
        fail_exc = k8s_utils.FailToCreateError([api_exc])

        with (
            patch("kubernetes.utils.create_from_dict", side_effect=fail_exc),
            pytest.raises(DeploymentError) as exc_info,
        ):
            client.apply_yaml_file(yaml_file)

        assert "Failed to apply manifest" in exc_info.value.message

    @pytest.mark.unit
    @pytest.mark.kong
    def test_skips_none_manifests(self, k8s_client: tuple[Any, ...], tmp_path: Path) -> None:
        """Manifests that load as None (empty YAML docs) are skipped."""
        client, _ = k8s_client
        yaml_file = tmp_path / "empty.yaml"
        yaml_file.write_text("---\n---\n")

        with patch("kubernetes.utils.create_from_dict") as mock_create:
            result = client.apply_yaml_file(yaml_file)

        assert result == []
        mock_create.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.kong
    def test_overrides_namespace_in_manifest(
        self, k8s_client: tuple[Any, ...], tmp_path: Path
    ) -> None:
        """When namespace arg is given, it is injected into manifest metadata."""
        client, _ = k8s_client
        yaml_file = tmp_path / "manifest.yaml"
        yaml_file.write_text(
            "apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: cfg\n  namespace: default\n"
        )

        captured_manifests: list[Any] = []

        def capture_manifest(k8s_client_arg: Any, manifest: Any, **kwargs: Any) -> None:
            captured_manifests.append(manifest)

        with patch("kubernetes.utils.create_from_dict", side_effect=capture_manifest):
            result = client.apply_yaml_file(yaml_file, namespace="custom-ns")

        assert result == ["ConfigMap/cfg"]
        assert captured_manifests[0]["metadata"]["namespace"] == "custom-ns"

    @pytest.mark.unit
    @pytest.mark.kong
    def test_multiple_manifests_in_one_file(
        self, k8s_client: tuple[Any, ...], tmp_path: Path
    ) -> None:
        """All manifests in a multi-document YAML file are processed."""
        client, _ = k8s_client
        yaml_file = tmp_path / "multi.yaml"
        yaml_file.write_text(
            "apiVersion: v1\nkind: Service\nmetadata:\n  name: svc\n"
            "---\n"
            "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: dep\n"
        )

        with patch("kubernetes.utils.create_from_dict") as mock_create:
            mock_create.return_value = None
            result = client.apply_yaml_file(yaml_file)

        assert "Service/svc" in result
        assert "Deployment/dep" in result
        assert mock_create.call_count == 2


# ===========================================================================
# KubernetesClient.delete_yaml_file
# ===========================================================================


class TestDeleteYamlFile:
    """Tests for KubernetesClient.delete_yaml_file."""

    @pytest.mark.unit
    @pytest.mark.kong
    def test_returns_empty_list_when_file_not_found(
        self, k8s_client: tuple[Any, ...], tmp_path: Path
    ) -> None:
        """Returns [] without raising when file does not exist."""
        client, _ = k8s_client
        result = client.delete_yaml_file(tmp_path / "nonexistent.yaml")
        assert result == []

    @pytest.mark.unit
    @pytest.mark.kong
    def test_deletes_statefulset(self, k8s_client: tuple[Any, ...], tmp_path: Path) -> None:
        """Calls delete_namespaced_stateful_set for StatefulSet kind."""
        client, _ = k8s_client
        yaml_file = tmp_path / "ss.yaml"
        yaml_file.write_text(
            "apiVersion: apps/v1\nkind: StatefulSet\nmetadata:\n  name: pg\n  namespace: kong\n"
        )

        deleted = client.delete_yaml_file(yaml_file)

        client._apps_v1.delete_namespaced_stateful_set.assert_called_once_with("pg", "kong")
        assert "statefulset/pg" in deleted

    @pytest.mark.unit
    @pytest.mark.kong
    def test_deletes_deployment(self, k8s_client: tuple[Any, ...], tmp_path: Path) -> None:
        """Calls delete_namespaced_deployment for Deployment kind."""
        client, _ = k8s_client
        yaml_file = tmp_path / "deploy.yaml"
        yaml_file.write_text(
            "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: myapp\n  namespace: ns\n"
        )

        deleted = client.delete_yaml_file(yaml_file)

        client._apps_v1.delete_namespaced_deployment.assert_called_once_with("myapp", "ns")
        assert "deployment/myapp" in deleted

    @pytest.mark.unit
    @pytest.mark.kong
    def test_deletes_service(self, k8s_client: tuple[Any, ...], tmp_path: Path) -> None:
        """Calls delete_namespaced_service for Service kind."""
        client, _ = k8s_client
        yaml_file = tmp_path / "svc.yaml"
        yaml_file.write_text(
            "apiVersion: v1\nkind: Service\nmetadata:\n  name: my-svc\n  namespace: ns\n"
        )

        deleted = client.delete_yaml_file(yaml_file)

        client._core_v1.delete_namespaced_service.assert_called_once_with("my-svc", "ns")
        assert "service/my-svc" in deleted

    @pytest.mark.unit
    @pytest.mark.kong
    def test_deletes_configmap(self, k8s_client: tuple[Any, ...], tmp_path: Path) -> None:
        """Calls delete_namespaced_config_map for ConfigMap kind."""
        client, _ = k8s_client
        yaml_file = tmp_path / "cm.yaml"
        yaml_file.write_text(
            "apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: cfg\n  namespace: ns\n"
        )

        deleted = client.delete_yaml_file(yaml_file)

        client._core_v1.delete_namespaced_config_map.assert_called_once_with("cfg", "ns")
        assert "configmap/cfg" in deleted

    @pytest.mark.unit
    @pytest.mark.kong
    def test_deletes_persistentvolumeclaim(
        self, k8s_client: tuple[Any, ...], tmp_path: Path
    ) -> None:
        """Calls delete_namespaced_persistent_volume_claim for PersistentVolumeClaim kind."""
        client, _ = k8s_client
        yaml_file = tmp_path / "pvc.yaml"
        yaml_file.write_text(
            "apiVersion: v1\nkind: PersistentVolumeClaim\nmetadata:\n  name: data-pvc\n  namespace: ns\n"
        )

        deleted = client.delete_yaml_file(yaml_file)

        client._core_v1.delete_namespaced_persistent_volume_claim.assert_called_once_with(
            "data-pvc", "ns"
        )
        assert "persistentvolumeclaim/data-pvc" in deleted

    @pytest.mark.unit
    @pytest.mark.kong
    def test_deletes_secret(self, k8s_client: tuple[Any, ...], tmp_path: Path) -> None:
        """Calls delete_namespaced_secret for Secret kind."""
        client, _ = k8s_client
        yaml_file = tmp_path / "secret.yaml"
        yaml_file.write_text(
            "apiVersion: v1\nkind: Secret\nmetadata:\n  name: my-sec\n  namespace: ns\n"
        )

        deleted = client.delete_yaml_file(yaml_file)

        client._core_v1.delete_namespaced_secret.assert_called_once_with("my-sec", "ns")
        assert "secret/my-sec" in deleted

    @pytest.mark.unit
    @pytest.mark.kong
    def test_ignores_404_on_delete(self, k8s_client: tuple[Any, ...], tmp_path: Path) -> None:
        """404 ApiException during delete is silently ignored."""
        client, ApiException = k8s_client
        client._core_v1.delete_namespaced_service.side_effect = ApiException(status=404)

        yaml_file = tmp_path / "svc.yaml"
        yaml_file.write_text(
            "apiVersion: v1\nkind: Service\nmetadata:\n  name: gone\n  namespace: ns\n"
        )

        # Should not raise; 404 is ignored, resource is not added to deleted list
        deleted = client.delete_yaml_file(yaml_file)
        # 404 means not found - resource wasn't in list to delete
        assert "service/gone" not in deleted

    @pytest.mark.unit
    @pytest.mark.kong
    def test_warns_on_non_404_error(self, k8s_client: tuple[Any, ...], tmp_path: Path) -> None:
        """Non-404 ApiException during delete logs a warning but does not raise."""
        client, ApiException = k8s_client
        client._core_v1.delete_namespaced_service.side_effect = ApiException(
            status=500, reason="InternalError"
        )

        yaml_file = tmp_path / "svc.yaml"
        yaml_file.write_text(
            "apiVersion: v1\nkind: Service\nmetadata:\n  name: svc\n  namespace: ns\n"
        )

        # Should not raise even on 500; just warns internally
        deleted = client.delete_yaml_file(yaml_file)
        assert "service/svc" not in deleted

    @pytest.mark.unit
    @pytest.mark.kong
    def test_uses_override_namespace(self, k8s_client: tuple[Any, ...], tmp_path: Path) -> None:
        """The namespace parameter overrides the one in the manifest."""
        client, _ = k8s_client
        yaml_file = tmp_path / "svc.yaml"
        yaml_file.write_text(
            "apiVersion: v1\nkind: Service\nmetadata:\n  name: my-svc\n  namespace: original\n"
        )

        client.delete_yaml_file(yaml_file, namespace="override-ns")

        client._core_v1.delete_namespaced_service.assert_called_once_with("my-svc", "override-ns")

    @pytest.mark.unit
    @pytest.mark.kong
    def test_skips_manifest_without_name(self, k8s_client: tuple[Any, ...], tmp_path: Path) -> None:
        """Manifests with no metadata.name are skipped."""
        client, _ = k8s_client
        yaml_file = tmp_path / "noname.yaml"
        yaml_file.write_text("apiVersion: v1\nkind: Service\nmetadata:\n  namespace: ns\n")

        deleted = client.delete_yaml_file(yaml_file)

        assert deleted == []
        client._core_v1.delete_namespaced_service.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.kong
    def test_skips_none_documents_in_yaml(
        self, k8s_client: tuple[Any, ...], tmp_path: Path
    ) -> None:
        """Empty YAML documents (None after parse) are silently skipped."""
        client, _ = k8s_client
        # A file with only separator lines produces None manifests
        yaml_file = tmp_path / "empty_docs.yaml"
        yaml_file.write_text("---\n---\n")

        deleted = client.delete_yaml_file(yaml_file)

        assert deleted == []
        client._core_v1.delete_namespaced_service.assert_not_called()
        client._apps_v1.delete_namespaced_deployment.assert_not_called()


# ===========================================================================
# KubernetesClient.get_pods
# ===========================================================================


class TestGetPods:
    """Tests for KubernetesClient.get_pods."""

    @pytest.mark.unit
    @pytest.mark.kong
    def test_returns_pod_info_list(self, k8s_client: tuple[Any, ...]) -> None:
        """Converts pod API objects to PodInfo list."""
        client, _ = k8s_client

        mock_container_status = MagicMock()
        mock_container_status.ready = True
        mock_container_status.restart_count = 2

        mock_pod = MagicMock()
        mock_pod.metadata.name = "kong-pod-1"
        mock_pod.status.phase = "Running"
        mock_pod.status.container_statuses = [mock_container_status]

        client._core_v1.list_namespaced_pod.return_value = MagicMock(items=[mock_pod])

        pods = client.get_pods("kong", label_selector="app=kong")

        assert len(pods) == 1
        assert pods[0].name == "kong-pod-1"
        assert pods[0].phase == "Running"
        assert pods[0].ready is True
        assert pods[0].restarts == 2

    @pytest.mark.unit
    @pytest.mark.kong
    def test_pod_not_ready_when_no_containers(self, k8s_client: tuple[Any, ...]) -> None:
        """Pod is reported as not ready when container_statuses is empty."""
        client, _ = k8s_client

        mock_pod = MagicMock()
        mock_pod.metadata.name = "empty-pod"
        mock_pod.status.phase = "Pending"
        mock_pod.status.container_statuses = []

        client._core_v1.list_namespaced_pod.return_value = MagicMock(items=[mock_pod])

        pods = client.get_pods("kong")

        assert pods[0].ready is False
        assert pods[0].restarts == 0

    @pytest.mark.unit
    @pytest.mark.kong
    def test_pod_not_ready_when_container_statuses_is_none(
        self, k8s_client: tuple[Any, ...]
    ) -> None:
        """Pod is reported as not ready when container_statuses is None."""
        client, _ = k8s_client

        mock_pod = MagicMock()
        mock_pod.metadata.name = "null-pod"
        mock_pod.status.phase = "Running"
        mock_pod.status.container_statuses = None

        client._core_v1.list_namespaced_pod.return_value = MagicMock(items=[mock_pod])

        pods = client.get_pods("kong")

        assert pods[0].ready is False
        assert pods[0].restarts == 0

    @pytest.mark.unit
    @pytest.mark.kong
    def test_uses_empty_string_when_no_label_selector(self, k8s_client: tuple[Any, ...]) -> None:
        """Passes empty string as label_selector when none is given."""
        client, _ = k8s_client
        client._core_v1.list_namespaced_pod.return_value = MagicMock(items=[])

        client.get_pods("kong")

        client._core_v1.list_namespaced_pod.assert_called_once_with("kong", label_selector="")


# ===========================================================================
# KubernetesClient.wait_for_pod_ready
# ===========================================================================


class TestWaitForPodReady:
    """Tests for KubernetesClient.wait_for_pod_ready."""

    @pytest.mark.unit
    @pytest.mark.kong
    def test_returns_true_when_pods_ready_immediately(self, k8s_client: tuple[Any, ...]) -> None:
        """Returns True immediately when pods are already ready."""
        client, _ = k8s_client

        ready_pod = PodInfo(name="p", phase="Running", ready=True)
        client.get_pods = MagicMock(return_value=[ready_pod])

        with patch("time.time", side_effect=[0.0, 1.0]), patch("time.sleep"):
            result = client.wait_for_pod_ready("kong", "app=kong", timeout=10)

        assert result is True

    @pytest.mark.unit
    @pytest.mark.kong
    def test_returns_false_on_timeout(self, k8s_client: tuple[Any, ...]) -> None:
        """Returns False when pods are never ready before timeout expires."""
        client, _ = k8s_client

        not_ready_pod = PodInfo(name="p", phase="Pending", ready=False)
        client.get_pods = MagicMock(return_value=[not_ready_pod])

        # Simulate time advancing: first call = 0.0 (start), subsequent calls
        # exceed the timeout of 5 seconds
        time_values = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
        with patch("time.time", side_effect=time_values), patch("time.sleep"):
            result = client.wait_for_pod_ready("kong", "app=kong", timeout=5, poll_interval=1)

        assert result is False

    @pytest.mark.unit
    @pytest.mark.kong
    def test_polls_until_ready(self, k8s_client: tuple[Any, ...]) -> None:
        """Returns True after a few poll cycles when pods become ready."""
        client, _ = k8s_client

        not_ready = PodInfo(name="p", phase="Pending", ready=False)
        ready = PodInfo(name="p", phase="Running", ready=True)
        client.get_pods = MagicMock(side_effect=[[not_ready], [not_ready], [ready]])

        # time.time: start=0, loop checks: 1, 2, 3 (all < timeout 120)
        time_values = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0]
        with patch("time.time", side_effect=time_values), patch("time.sleep"):
            result = client.wait_for_pod_ready("kong", "app=kong", timeout=120, poll_interval=1)

        assert result is True

    @pytest.mark.unit
    @pytest.mark.kong
    def test_returns_false_when_no_pods_found(self, k8s_client: tuple[Any, ...]) -> None:
        """Returns False on timeout when no pods are ever found."""
        client, _ = k8s_client
        client.get_pods = MagicMock(return_value=[])

        time_values = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
        with patch("time.time", side_effect=time_values), patch("time.sleep"):
            result = client.wait_for_pod_ready("kong", "app=kong", timeout=5, poll_interval=1)

        assert result is False


# ===========================================================================
# HelmClient.__init__
# ===========================================================================


class TestHelmClientInit:
    """Tests for HelmClient initialisation."""

    @pytest.mark.unit
    @pytest.mark.kong
    def test_raises_when_helm_not_found(self) -> None:
        """Raises DeploymentError when helm binary is absent from PATH."""
        with patch("shutil.which", return_value=None), pytest.raises(DeploymentError) as exc_info:
            HelmClient()

        assert "helm is not installed" in exc_info.value.message

    @pytest.mark.unit
    @pytest.mark.kong
    def test_succeeds_when_helm_found(self) -> None:
        """Does not raise when helm is on the PATH."""
        with patch("shutil.which", return_value="/usr/bin/helm"):
            client = HelmClient()

        assert isinstance(client, HelmClient)


# ===========================================================================
# HelmClient._run
# ===========================================================================


class TestHelmClientRun:
    """Tests for HelmClient._run."""

    @pytest.mark.unit
    @pytest.mark.kong
    def test_run_success(self, helm_client: HelmClient) -> None:
        """Returns CompletedProcess on zero exit code."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "ok"

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result = helm_client._run("version")

        mock_run.assert_called_once_with(
            ["helm", "version"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0

    @pytest.mark.unit
    @pytest.mark.kong
    def test_run_failure_raises_deployment_error(self, helm_client: HelmClient) -> None:
        """Raises DeploymentError when helm exits non-zero and check=True."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "error: chart not found"

        with (
            patch("subprocess.run", return_value=mock_result),
            pytest.raises(DeploymentError) as exc_info,
        ):
            helm_client._run("install", "bad-chart")

        assert "Helm command failed" in exc_info.value.message
        assert "error: chart not found" in exc_info.value.details

    @pytest.mark.unit
    @pytest.mark.kong
    def test_run_check_false_ignores_failure(self, helm_client: HelmClient) -> None:
        """Returns result without raising when check=False and exit code is non-zero."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "not found"

        with patch("subprocess.run", return_value=mock_result):
            result = helm_client._run("repo", "add", "kong", "url", check=False)

        assert result.returncode == 1


# ===========================================================================
# HelmClient.setup_repo
# ===========================================================================


class TestHelmSetupRepo:
    """Tests for HelmClient.setup_repo."""

    @pytest.mark.unit
    @pytest.mark.kong
    def test_adds_and_updates_repo(self, helm_client: HelmClient) -> None:
        """Calls repo add (check=False) then repo update."""
        with patch.object(helm_client, "_run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="")
            helm_client.setup_repo()

        calls = mock_run.call_args_list
        assert calls[0] == call(
            "repo", "add", HelmClient.REPO_NAME, HelmClient.REPO_URL, check=False
        )
        assert calls[1] == call("repo", "update")


# ===========================================================================
# HelmClient.get_release
# ===========================================================================


class TestHelmGetRelease:
    """Tests for HelmClient.get_release."""

    @pytest.mark.unit
    @pytest.mark.kong
    def test_returns_release_when_found(self, helm_client: HelmClient) -> None:
        """Returns matching release dict when name is present in list output."""
        releases = [
            {"name": "other", "chart": "other/chart-1.0.0"},
            {"name": "kong", "chart": "kong/ingress-2.0.0", "app_version": "3.5.0"},
        ]
        mock_result = MagicMock(returncode=0, stdout=json.dumps(releases))

        with patch.object(helm_client, "_run", return_value=mock_result):
            release = helm_client.get_release("kong", "kong")

        assert release is not None
        assert release["chart"] == "kong/ingress-2.0.0"

    @pytest.mark.unit
    @pytest.mark.kong
    def test_returns_none_when_not_found(self, helm_client: HelmClient) -> None:
        """Returns None when the named release is not in the list."""
        mock_result = MagicMock(returncode=0, stdout=json.dumps([]))

        with patch.object(helm_client, "_run", return_value=mock_result):
            release = helm_client.get_release("missing", "kong")

        assert release is None

    @pytest.mark.unit
    @pytest.mark.kong
    def test_returns_none_on_non_zero_returncode(self, helm_client: HelmClient) -> None:
        """Returns None when the helm list command itself fails."""
        mock_result = MagicMock(returncode=1, stdout="")

        with patch.object(helm_client, "_run", return_value=mock_result):
            release = helm_client.get_release("kong", "kong")

        assert release is None

    @pytest.mark.unit
    @pytest.mark.kong
    def test_returns_none_on_invalid_json(self, helm_client: HelmClient) -> None:
        """Returns None when helm list output is not valid JSON."""
        mock_result = MagicMock(returncode=0, stdout="not-json")

        with patch.object(helm_client, "_run", return_value=mock_result):
            release = helm_client.get_release("kong", "kong")

        assert release is None


# ===========================================================================
# HelmClient.install_crds
# ===========================================================================


class TestHelmInstallCrds:
    """Tests for HelmClient.install_crds."""

    @pytest.mark.unit
    @pytest.mark.kong
    def test_applies_crds_via_kubectl(self, helm_client: HelmClient) -> None:
        """Pipes helm show crds output into kubectl apply."""
        helm_result = MagicMock(returncode=0, stdout="apiVersion: v1\nkind: CRD\n")

        kubectl_result = MagicMock(returncode=0)

        with (
            patch.object(helm_client, "_run", return_value=helm_result),
            patch("subprocess.run", return_value=kubectl_result) as mock_subprocess,
        ):
            helm_client.install_crds("kong/ingress")

        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args
        assert call_args[0][0] == ["kubectl", "apply", "-f", "-"]

    @pytest.mark.unit
    @pytest.mark.kong
    def test_raises_when_kubectl_fails(self, helm_client: HelmClient) -> None:
        """Raises DeploymentError when kubectl apply returns non-zero."""
        helm_result = MagicMock(returncode=0, stdout="crd: data\n")
        kubectl_result = MagicMock(returncode=1, stderr="connection refused")

        with (
            patch.object(helm_client, "_run", return_value=helm_result),
            patch("subprocess.run", return_value=kubectl_result),
            pytest.raises(DeploymentError) as exc_info,
        ):
            helm_client.install_crds("kong/ingress")

        assert "Failed to install CRDs" in exc_info.value.message

    @pytest.mark.unit
    @pytest.mark.kong
    def test_skips_kubectl_when_no_crds(self, helm_client: HelmClient) -> None:
        """Does not call kubectl when helm show crds returns empty stdout."""
        helm_result = MagicMock(returncode=0, stdout="   ")

        with (
            patch.object(helm_client, "_run", return_value=helm_result),
            patch("subprocess.run") as mock_subprocess,
        ):
            helm_client.install_crds("kong/ingress")

        mock_subprocess.assert_not_called()


# ===========================================================================
# HelmClient.install
# ===========================================================================


class TestHelmInstall:
    """Tests for HelmClient.install."""

    @pytest.mark.unit
    @pytest.mark.kong
    def test_raises_when_values_file_missing(self, helm_client: HelmClient, tmp_path: Path) -> None:
        """Raises DeploymentError when values file does not exist."""
        with pytest.raises(DeploymentError) as exc_info:
            helm_client.install("kong", "kong/ingress", "kong", tmp_path / "missing.yaml")

        assert "Values file not found" in exc_info.value.message

    @pytest.mark.unit
    @pytest.mark.kong
    def test_basic_install_args(self, helm_client: HelmClient, tmp_path: Path) -> None:
        """Passes minimum required args to helm install."""
        values_file = tmp_path / "values.yaml"
        values_file.write_text("key: value\n")

        with patch.object(helm_client, "_run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            helm_client.install(
                "kong",
                "kong/ingress",
                "kong",
                values_file,
                wait=False,
                create_namespace=False,
                skip_crds=False,
            )

        args_passed = mock_run.call_args[0]
        assert "install" in args_passed
        assert "kong" in args_passed
        assert "kong/ingress" in args_passed
        assert "--wait" not in args_passed
        assert "--create-namespace" not in args_passed
        assert "--skip-crds" not in args_passed

    @pytest.mark.unit
    @pytest.mark.kong
    def test_install_with_all_flags(self, helm_client: HelmClient, tmp_path: Path) -> None:
        """Appends --wait, --create-namespace and --skip-crds when enabled."""
        values_file = tmp_path / "values.yaml"
        values_file.write_text("key: value\n")

        with patch.object(helm_client, "_run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            helm_client.install(
                "kong",
                "kong/ingress",
                "kong",
                values_file,
                wait=True,
                create_namespace=True,
                skip_crds=True,
            )

        args_passed = mock_run.call_args[0]
        assert "--wait" in args_passed
        assert "--create-namespace" in args_passed
        assert "--skip-crds" in args_passed


# ===========================================================================
# HelmClient.upgrade
# ===========================================================================


class TestHelmUpgrade:
    """Tests for HelmClient.upgrade."""

    @pytest.mark.unit
    @pytest.mark.kong
    def test_raises_when_values_file_missing(self, helm_client: HelmClient, tmp_path: Path) -> None:
        """Raises DeploymentError when values file does not exist."""
        with pytest.raises(DeploymentError) as exc_info:
            helm_client.upgrade("kong", "kong/ingress", "kong", tmp_path / "missing.yaml")

        assert "Values file not found" in exc_info.value.message

    @pytest.mark.unit
    @pytest.mark.kong
    def test_upgrade_success(self, helm_client: HelmClient, tmp_path: Path) -> None:
        """Calls helm upgrade with required arguments."""
        values_file = tmp_path / "values.yaml"
        values_file.write_text("key: value\n")

        with patch.object(helm_client, "_run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            helm_client.upgrade("kong", "kong/ingress", "kong", values_file)

        args_passed = mock_run.call_args[0]
        assert "upgrade" in args_passed
        assert "kong" in args_passed
        assert "kong/ingress" in args_passed
        assert "--wait" in args_passed  # wait=True by default

    @pytest.mark.unit
    @pytest.mark.kong
    def test_upgrade_without_wait(self, helm_client: HelmClient, tmp_path: Path) -> None:
        """Does not append --wait when wait=False."""
        values_file = tmp_path / "values.yaml"
        values_file.write_text("key: value\n")

        with patch.object(helm_client, "_run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            helm_client.upgrade("kong", "kong/ingress", "kong", values_file, wait=False)

        args_passed = mock_run.call_args[0]
        assert "--wait" not in args_passed


# ===========================================================================
# HelmClient.uninstall
# ===========================================================================


class TestHelmUninstall:
    """Tests for HelmClient.uninstall."""

    @pytest.mark.unit
    @pytest.mark.kong
    def test_returns_true_on_success(self, helm_client: HelmClient) -> None:
        """Returns True when helm uninstall exits zero."""
        mock_result = MagicMock(returncode=0)

        with patch.object(helm_client, "_run", return_value=mock_result):
            result = helm_client.uninstall("kong", "kong")

        assert result is True

    @pytest.mark.unit
    @pytest.mark.kong
    def test_returns_false_on_failure(self, helm_client: HelmClient) -> None:
        """Returns False when helm uninstall exits non-zero (e.g. not found)."""
        mock_result = MagicMock(returncode=1)

        with patch.object(helm_client, "_run", return_value=mock_result):
            result = helm_client.uninstall("missing-release", "kong")

        assert result is False


# ===========================================================================
# KongDeploymentManager.__init__ and helpers
# ===========================================================================


class TestKongDeploymentManagerInit:
    """Tests for KongDeploymentManager constructor and helper methods."""

    @pytest.mark.unit
    @pytest.mark.kong
    def test_init_with_defaults(self, tmp_path: Path) -> None:
        """Default namespace and release_name are set from class constants."""
        mgr = KongDeploymentManager(project_root=tmp_path)

        assert mgr.namespace == KongDeploymentManager.DEFAULT_NAMESPACE
        assert mgr.release_name == KongDeploymentManager.DEFAULT_RELEASE_NAME
        assert mgr._k8s is None
        assert mgr._helm is None

    @pytest.mark.unit
    @pytest.mark.kong
    def test_init_with_custom_params(self, tmp_path: Path) -> None:
        """Custom namespace, release_name, and callback are stored correctly."""
        callback = MagicMock()
        mgr = KongDeploymentManager(
            project_root=tmp_path,
            namespace="custom-ns",
            release_name="my-kong",
            progress_callback=callback,
        )

        assert mgr.namespace == "custom-ns"
        assert mgr.release_name == "my-kong"

        mgr._progress("test")
        callback.assert_called_once_with("test")

    @pytest.mark.unit
    @pytest.mark.kong
    def test_default_progress_callback_is_noop(self, tmp_path: Path) -> None:
        """Default progress callback does nothing (no AttributeError)."""
        mgr = KongDeploymentManager(project_root=tmp_path)
        # Should not raise
        mgr._progress("any message")

    @pytest.mark.unit
    @pytest.mark.kong
    def test_find_project_root_finds_pyproject_toml(self, tmp_path: Path) -> None:
        """_find_project_root returns the directory containing pyproject.toml."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")
        subdir = tmp_path / "src" / "pkg"
        subdir.mkdir(parents=True)

        mgr = KongDeploymentManager.__new__(KongDeploymentManager)
        with patch("pathlib.Path.cwd", return_value=subdir):
            root = mgr._find_project_root()

        assert root == tmp_path

    @pytest.mark.unit
    @pytest.mark.kong
    def test_find_project_root_falls_back_to_cwd(self, tmp_path: Path) -> None:
        """_find_project_root returns cwd when no pyproject.toml is found."""
        mgr = KongDeploymentManager.__new__(KongDeploymentManager)

        # Use a deep tmp subdir that has no pyproject.toml
        deep_dir = tmp_path / "a" / "b" / "c"
        deep_dir.mkdir(parents=True)

        with patch("pathlib.Path.cwd", return_value=deep_dir):
            root = mgr._find_project_root()

        # Root should be cwd (deep_dir) since no pyproject.toml found
        assert root == deep_dir


# ===========================================================================
# KongDeploymentManager lazy properties
# ===========================================================================


class TestKongDeploymentManagerLazyProperties:
    """Tests for k8s and helm lazy-initialization properties."""

    @pytest.mark.unit
    @pytest.mark.kong
    def test_k8s_lazy_init(self, tmp_path: Path) -> None:
        """k8s property creates KubernetesClient on first access."""
        mgr = KongDeploymentManager(project_root=tmp_path)

        mock_k8s = MagicMock(spec=KubernetesClient)
        with patch(
            "system_operations_manager.services.kong.deployment_manager.KubernetesClient",
            return_value=mock_k8s,
        ) as mock_cls:
            client = mgr.k8s

        mock_cls.assert_called_once()
        assert client is mock_k8s

    @pytest.mark.unit
    @pytest.mark.kong
    def test_k8s_returns_cached_instance(self, tmp_path: Path) -> None:
        """k8s property returns the same instance on repeated access."""
        mgr = KongDeploymentManager(project_root=tmp_path)
        mock_k8s = MagicMock(spec=KubernetesClient)

        with patch(
            "system_operations_manager.services.kong.deployment_manager.KubernetesClient",
            return_value=mock_k8s,
        ):
            first = mgr.k8s
            second = mgr.k8s

        assert first is second

    @pytest.mark.unit
    @pytest.mark.kong
    def test_helm_lazy_init(self, tmp_path: Path) -> None:
        """helm property creates HelmClient on first access."""
        mgr = KongDeploymentManager(project_root=tmp_path)

        mock_helm = MagicMock(spec=HelmClient)
        with patch(
            "system_operations_manager.services.kong.deployment_manager.HelmClient",
            return_value=mock_helm,
        ) as mock_cls:
            client = mgr.helm

        mock_cls.assert_called_once()
        assert client is mock_helm

    @pytest.mark.unit
    @pytest.mark.kong
    def test_helm_returns_cached_instance(self, tmp_path: Path) -> None:
        """helm property returns the same instance on repeated access."""
        mgr = KongDeploymentManager(project_root=tmp_path)
        mock_helm = MagicMock(spec=HelmClient)

        with patch(
            "system_operations_manager.services.kong.deployment_manager.HelmClient",
            return_value=mock_helm,
        ):
            first = mgr.helm
            second = mgr.helm

        assert first is second


# ===========================================================================
# KongDeploymentManager._get_paths
# ===========================================================================


class TestKongDeploymentManagerGetPaths:
    """Tests for KongDeploymentManager._get_paths."""

    @pytest.mark.unit
    @pytest.mark.kong
    def test_returns_expected_paths(self, manager: Any) -> None:
        """_get_paths returns a dict with the five expected keys."""
        paths = manager._get_paths()

        assert set(paths.keys()) == {
            "values",
            "postgres",
            "rbac_patch",
            "secrets",
            "secrets_example",
        }

    @pytest.mark.unit
    @pytest.mark.kong
    def test_paths_rooted_at_project_root(self, tmp_path: Path, manager: Any) -> None:
        """All paths are descendants of project_root."""
        manager.project_root = tmp_path
        paths = manager._get_paths()

        for key, path in paths.items():
            assert str(path).startswith(str(tmp_path)), (
                f"Path for '{key}' is not under project root: {path}"
            )

    @pytest.mark.unit
    @pytest.mark.kong
    def test_values_and_postgres_under_k8s_gateway(self, tmp_path: Path, manager: Any) -> None:
        """values and postgres live under k8s/gateway/."""
        manager.project_root = tmp_path
        paths = manager._get_paths()

        gateway_dir = tmp_path / "k8s" / "gateway"
        assert paths["values"].parent == gateway_dir
        assert paths["postgres"].parent == gateway_dir

    @pytest.mark.unit
    @pytest.mark.kong
    def test_secrets_under_config(self, tmp_path: Path, manager: Any) -> None:
        """secrets and secrets_example live under config/."""
        manager.project_root = tmp_path
        paths = manager._get_paths()

        config_dir = tmp_path / "config"
        assert paths["secrets"].parent == config_dir
        assert paths["secrets_example"].parent == config_dir


# ===========================================================================
# KongDeploymentManager.get_status
# ===========================================================================


class TestKongDeploymentManagerGetStatus:
    """Tests for KongDeploymentManager.get_status."""

    @pytest.mark.unit
    @pytest.mark.kong
    def test_not_installed_when_namespace_missing(self, manager: Any) -> None:
        """Returns NOT_INSTALLED when namespace does not exist."""
        manager._k8s.namespace_exists.return_value = False

        info = manager.get_status()

        assert info.status == DeploymentStatus.NOT_INSTALLED
        assert info.namespace == "kong"

    @pytest.mark.unit
    @pytest.mark.kong
    def test_not_installed_when_no_helm_release(self, manager: Any) -> None:
        """Returns NOT_INSTALLED when namespace exists but no Helm release found."""
        manager._k8s.namespace_exists.return_value = True
        manager._helm.get_release.return_value = None
        manager._k8s.get_pods.return_value = []

        info = manager.get_status()

        assert info.status == DeploymentStatus.NOT_INSTALLED

    @pytest.mark.unit
    @pytest.mark.kong
    def test_running_when_gateway_and_controller_ready(self, manager: Any) -> None:
        """Returns RUNNING when gateway and controller pods are ready."""
        manager._k8s.namespace_exists.return_value = True
        manager._helm.get_release.return_value = {
            "name": "kong",
            "chart": "kong/ingress-2.0.0",
            "app_version": "3.5.0",
        }
        manager._k8s.get_pods.return_value = [
            PodInfo(name="kong-gateway-abc", phase="Running", ready=True),
            PodInfo(name="kong-controller-xyz", phase="Running", ready=True),
        ]

        info = manager.get_status()

        assert info.status == DeploymentStatus.RUNNING
        assert info.gateway_ready is True
        assert info.controller_ready is True

    @pytest.mark.unit
    @pytest.mark.kong
    def test_running_when_gateway_and_postgres_ready(self, manager: Any) -> None:
        """Returns RUNNING when gateway and postgres pods are ready."""
        manager._k8s.namespace_exists.return_value = True
        manager._helm.get_release.return_value = {"name": "kong", "chart": "kong/ingress-2.0.0"}
        manager._k8s.get_pods.return_value = [
            PodInfo(name="kong-gateway-abc", phase="Running", ready=True),
            PodInfo(name="kong-postgres-123", phase="Running", ready=True),
        ]

        info = manager.get_status()

        assert info.status == DeploymentStatus.RUNNING
        assert info.postgres_ready is True
        assert info.gateway_ready is True

    @pytest.mark.unit
    @pytest.mark.kong
    def test_degraded_when_pods_exist_but_not_fully_ready(self, manager: Any) -> None:
        """Returns DEGRADED when some pods exist but gateway is not ready."""
        manager._k8s.namespace_exists.return_value = True
        manager._helm.get_release.return_value = {"name": "kong", "chart": "kong/ingress-2.0.0"}
        manager._k8s.get_pods.return_value = [
            PodInfo(name="kong-gateway-abc", phase="Pending", ready=False),
        ]

        info = manager.get_status()

        assert info.status == DeploymentStatus.DEGRADED

    @pytest.mark.unit
    @pytest.mark.kong
    def test_failed_when_release_exists_but_no_pods(self, manager: Any) -> None:
        """Returns FAILED when release exists but no pods are present."""
        manager._k8s.namespace_exists.return_value = True
        manager._helm.get_release.return_value = {"name": "kong", "chart": "kong/ingress-2.0.0"}
        manager._k8s.get_pods.return_value = []

        info = manager.get_status()

        assert info.status == DeploymentStatus.FAILED

    @pytest.mark.unit
    @pytest.mark.kong
    def test_chart_version_parsed_from_chart_string(self, manager: Any) -> None:
        """chart_version is extracted from the chart string after the last hyphen."""
        manager._k8s.namespace_exists.return_value = True
        manager._helm.get_release.return_value = {
            "name": "kong",
            "chart": "kong/ingress-2.5.1",
            "app_version": "3.7.0",
        }
        manager._k8s.get_pods.return_value = [
            PodInfo(name="kong-gateway-x", phase="Running", ready=True),
            PodInfo(name="kong-controller-y", phase="Running", ready=True),
        ]

        info = manager.get_status()

        assert info.chart_version == "2.5.1"
        assert info.app_version == "3.7.0"


# ===========================================================================
# KongDeploymentManager.install
# ===========================================================================


class TestKongDeploymentManagerInstall:
    """Tests for KongDeploymentManager.install."""

    def _setup_paths(self, tmp_path: Path, manager: Any) -> dict[str, Path]:
        """Create directory structure with all required files present."""
        gateway_dir = tmp_path / "k8s" / "gateway"
        config_dir = tmp_path / "config"
        gateway_dir.mkdir(parents=True)
        config_dir.mkdir(parents=True)

        (gateway_dir / "kong-values.yaml").write_text("key: value\n")
        (gateway_dir / "postgres.yaml").write_text(
            "apiVersion: v1\nkind: Service\nmetadata:\n  name: pg\n"
        )
        (config_dir / ".env.kong.secrets").write_text("PASS=secret\n")
        (config_dir / ".env.kong.secrets.example").write_text("PASS=changeme\n")

        manager.project_root = tmp_path
        result: dict[str, Path] = manager._get_paths()
        return result

    @pytest.mark.unit
    @pytest.mark.kong
    def test_raises_when_secrets_missing(self, manager: Any, tmp_path: Path) -> None:
        """Raises DeploymentError when secrets file is missing."""
        gateway_dir = tmp_path / "k8s" / "gateway"
        config_dir = tmp_path / "config"
        gateway_dir.mkdir(parents=True)
        config_dir.mkdir(parents=True)
        (gateway_dir / "kong-values.yaml").write_text("k: v\n")
        (gateway_dir / "postgres.yaml").write_text("k: v\n")
        (config_dir / ".env.kong.secrets.example").write_text("PASS=x\n")
        # .env.kong.secrets intentionally absent
        manager.project_root = tmp_path

        with pytest.raises(DeploymentError) as exc_info:
            manager.install()

        assert "Secrets file not found" in exc_info.value.message

    @pytest.mark.unit
    @pytest.mark.kong
    def test_raises_when_values_missing(self, manager: Any, tmp_path: Path) -> None:
        """Raises DeploymentError when kong-values.yaml is missing."""
        gateway_dir = tmp_path / "k8s" / "gateway"
        config_dir = tmp_path / "config"
        gateway_dir.mkdir(parents=True)
        config_dir.mkdir(parents=True)
        (config_dir / ".env.kong.secrets").write_text("PASS=x\n")
        # values file intentionally absent
        manager.project_root = tmp_path

        with pytest.raises(DeploymentError) as exc_info:
            manager.install()

        assert "Values file not found" in exc_info.value.message

    @pytest.mark.unit
    @pytest.mark.kong
    def test_raises_when_postgres_manifest_missing(self, manager: Any, tmp_path: Path) -> None:
        """Raises DeploymentError when postgres.yaml is missing."""
        gateway_dir = tmp_path / "k8s" / "gateway"
        config_dir = tmp_path / "config"
        gateway_dir.mkdir(parents=True)
        config_dir.mkdir(parents=True)
        (gateway_dir / "kong-values.yaml").write_text("k: v\n")
        (config_dir / ".env.kong.secrets").write_text("PASS=x\n")
        # postgres.yaml intentionally absent
        manager.project_root = tmp_path

        with pytest.raises(DeploymentError) as exc_info:
            manager.install()

        assert "PostgreSQL manifest not found" in exc_info.value.message

    @pytest.mark.unit
    @pytest.mark.kong
    def test_full_install_happy_path(self, manager: Any, tmp_path: Path) -> None:
        """Runs through the entire install sequence without errors."""
        self._setup_paths(tmp_path, manager)
        manager._k8s.wait_for_pod_ready.return_value = True

        manager.install()

        manager._helm.setup_repo.assert_called_once()
        manager._k8s.create_namespace.assert_called_once_with("kong")
        manager._k8s.create_secret_from_env_file.assert_called_once()
        manager._k8s.apply_yaml_file.assert_called_once()
        manager._k8s.wait_for_pod_ready.assert_called_once_with("kong", "app=kong-postgres")
        manager._helm.install_crds.assert_called_once_with(KongDeploymentManager.DEFAULT_CHART)
        manager._helm.install.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.kong
    def test_raises_when_postgres_not_ready(self, manager: Any, tmp_path: Path) -> None:
        """Raises DeploymentError when postgres pod does not become ready."""
        self._setup_paths(tmp_path, manager)
        manager._k8s.wait_for_pod_ready.return_value = False

        with pytest.raises(DeploymentError) as exc_info:
            manager.install()

        assert "PostgreSQL failed to become ready" in exc_info.value.message

    @pytest.mark.unit
    @pytest.mark.kong
    def test_install_passes_correct_args_to_helm_install(
        self, manager: Any, tmp_path: Path
    ) -> None:
        """Verifies helm.install is called with create_namespace=False, skip_crds=True."""
        self._setup_paths(tmp_path, manager)
        manager._k8s.wait_for_pod_ready.return_value = True

        manager.install()

        call_kwargs = manager._helm.install.call_args
        assert call_kwargs.kwargs.get("create_namespace") is False
        assert call_kwargs.kwargs.get("skip_crds") is True


# ===========================================================================
# KongDeploymentManager._apply_rbac_patch
# ===========================================================================


class TestKongDeploymentManagerApplyRbacPatch:
    """Tests for KongDeploymentManager._apply_rbac_patch."""

    @pytest.mark.unit
    @pytest.mark.kong
    def test_applies_patch_successfully(self, manager: Any, tmp_path: Path) -> None:
        """Runs kubectl apply and returns normally on success."""
        rbac_file = tmp_path / "rbac.yaml"
        rbac_file.write_text("apiVersion: rbac.authorization.k8s.io/v1\n")

        mock_result = MagicMock(returncode=0, stderr="")
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            manager._apply_rbac_patch(rbac_file)

        mock_run.assert_called_once_with(
            ["kubectl", "apply", "-f", str(rbac_file)],
            capture_output=True,
            text=True,
        )

    @pytest.mark.unit
    @pytest.mark.kong
    def test_raises_on_kubectl_failure(self, manager: Any, tmp_path: Path) -> None:
        """Raises DeploymentError when kubectl returns non-zero."""
        rbac_file = tmp_path / "rbac.yaml"
        rbac_file.write_text("kind: ClusterRole\n")

        mock_result = MagicMock(returncode=1, stderr="permission denied")
        with (
            patch("subprocess.run", return_value=mock_result),
            pytest.raises(DeploymentError) as exc_info,
        ):
            manager._apply_rbac_patch(rbac_file)

        assert "Failed to apply RBAC patch" in exc_info.value.message
        assert "permission denied" in exc_info.value.details


# ===========================================================================
# KongDeploymentManager.upgrade
# ===========================================================================


class TestKongDeploymentManagerUpgrade:
    """Tests for KongDeploymentManager.upgrade."""

    @pytest.mark.unit
    @pytest.mark.kong
    def test_raises_when_values_missing(self, manager: Any, tmp_path: Path) -> None:
        """Raises DeploymentError when kong-values.yaml is absent."""
        manager.project_root = tmp_path
        # No files created - values file missing

        with pytest.raises(DeploymentError) as exc_info:
            manager.upgrade()

        assert "Values file not found" in exc_info.value.message

    @pytest.mark.unit
    @pytest.mark.kong
    def test_upgrade_happy_path(self, manager: Any, tmp_path: Path) -> None:
        """Runs setup_repo and helm.upgrade on success."""
        gateway_dir = tmp_path / "k8s" / "gateway"
        gateway_dir.mkdir(parents=True)
        (gateway_dir / "kong-values.yaml").write_text("key: value\n")
        manager.project_root = tmp_path

        manager.upgrade()

        manager._helm.setup_repo.assert_called_once()
        manager._helm.upgrade.assert_called_once_with(
            manager.release_name,
            KongDeploymentManager.DEFAULT_CHART,
            manager.namespace,
            gateway_dir / "kong-values.yaml",
        )


# ===========================================================================
# KongDeploymentManager.uninstall
# ===========================================================================


class TestKongDeploymentManagerUninstall:
    """Tests for KongDeploymentManager.uninstall."""

    @pytest.mark.unit
    @pytest.mark.kong
    def test_full_cleanup_default_flags(self, manager: Any, tmp_path: Path) -> None:
        """Default flags: keep_postgres=False, keep_secrets=True, keep_pvc=True."""
        gateway_dir = tmp_path / "k8s" / "gateway"
        gateway_dir.mkdir(parents=True)
        (gateway_dir / "postgres.yaml").write_text(
            "apiVersion: v1\nkind: Service\nmetadata:\n  name: pg\n"
        )
        manager.project_root = tmp_path

        manager.uninstall()

        manager._helm.uninstall.assert_called_once_with("kong", "kong")
        manager._k8s.delete_yaml_file.assert_called_once()  # postgres deleted
        # Secrets and PVC NOT deleted
        manager._k8s.core_v1.delete_namespaced_secret.assert_not_called()
        manager._k8s.core_v1.delete_namespaced_persistent_volume_claim.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.kong
    def test_keep_postgres_skips_postgres_deletion(self, manager: Any, tmp_path: Path) -> None:
        """keep_postgres=True skips postgres.yaml deletion."""
        manager.project_root = tmp_path

        manager.uninstall(keep_postgres=True)

        manager._k8s.delete_yaml_file.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.kong
    def test_deletes_secrets_when_keep_secrets_false(self, manager: Any, tmp_path: Path) -> None:
        """keep_secrets=False deletes the postgres secret."""
        manager.project_root = tmp_path

        manager.uninstall(keep_postgres=True, keep_secrets=False, keep_pvc=True)

        manager._k8s.core_v1.delete_namespaced_secret.assert_called_once_with(
            "kong-postgres-secret", "kong"
        )

    @pytest.mark.unit
    @pytest.mark.kong
    def test_deletes_pvc_when_keep_pvc_false(self, manager: Any, tmp_path: Path) -> None:
        """keep_pvc=False deletes the PVC."""
        manager.project_root = tmp_path

        manager.uninstall(keep_postgres=True, keep_secrets=True, keep_pvc=False)

        manager._k8s.core_v1.delete_namespaced_persistent_volume_claim.assert_called_once_with(
            "kong-postgres-pvc", "kong"
        )

    @pytest.mark.unit
    @pytest.mark.kong
    def test_keep_all_skips_all_secondary_cleanup(self, manager: Any, tmp_path: Path) -> None:
        """keep_postgres=True, keep_secrets=True, keep_pvc=True skips all cleanup."""
        manager.project_root = tmp_path

        manager.uninstall(keep_postgres=True, keep_secrets=True, keep_pvc=True)

        manager._helm.uninstall.assert_called_once()
        manager._k8s.delete_yaml_file.assert_not_called()
        manager._k8s.core_v1.delete_namespaced_secret.assert_not_called()
        manager._k8s.core_v1.delete_namespaced_persistent_volume_claim.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.kong
    def test_suppresses_exception_during_secret_deletion(
        self, manager: Any, tmp_path: Path
    ) -> None:
        """Exceptions from secret deletion are suppressed (contextlib.suppress)."""
        manager.project_root = tmp_path
        manager._k8s.core_v1.delete_namespaced_secret.side_effect = Exception("k8s error")

        # Should not raise
        manager.uninstall(keep_postgres=True, keep_secrets=False, keep_pvc=True)

    @pytest.mark.unit
    @pytest.mark.kong
    def test_suppresses_exception_during_pvc_deletion(self, manager: Any, tmp_path: Path) -> None:
        """Exceptions from PVC deletion are suppressed (contextlib.suppress)."""
        manager.project_root = tmp_path
        manager._k8s.core_v1.delete_namespaced_persistent_volume_claim.side_effect = Exception(
            "k8s error"
        )

        # Should not raise
        manager.uninstall(keep_postgres=True, keep_secrets=True, keep_pvc=False)

    @pytest.mark.unit
    @pytest.mark.kong
    def test_progress_callback_called_during_uninstall(self, tmp_path: Path) -> None:
        """Progress callback is invoked at each stage of uninstall."""
        messages: list[str] = []
        mgr = KongDeploymentManager(
            project_root=tmp_path,
            progress_callback=messages.append,
        )
        mgr._k8s = MagicMock()
        mgr._helm = MagicMock()

        mgr.uninstall(keep_postgres=True, keep_secrets=True, keep_pvc=True)

        assert any("Uninstalling" in m for m in messages)
        assert any("uninstalled" in m.lower() for m in messages)
