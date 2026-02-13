"""Unit tests for FluxManager."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from system_operations_manager.services.kubernetes.flux_manager import (
    FLUX_NAMESPACE,
    GIT_REPOSITORY_PLURAL,
    HELM_GROUP,
    HELM_RELEASE_PLURAL,
    HELM_REPOSITORY_PLURAL,
    HELM_VERSION,
    KUSTOMIZATION_PLURAL,
    KUSTOMIZE_GROUP,
    KUSTOMIZE_VERSION,
    RECONCILE_ANNOTATION,
    SOURCE_GROUP,
    SOURCE_VERSION,
    FluxManager,
)


@pytest.fixture
def mock_k8s_client() -> MagicMock:
    """Create a mock Kubernetes client."""
    mock_client = MagicMock()
    mock_client.default_namespace = "default"
    return mock_client


@pytest.fixture
def flux_manager(mock_k8s_client: MagicMock) -> FluxManager:
    """Create a FluxManager with mocked client."""
    return FluxManager(mock_k8s_client)


# =============================================================================
# Sample CRD objects for testing
# =============================================================================

SAMPLE_GIT_REPO = {
    "metadata": {
        "name": "podinfo",
        "namespace": "flux-system",
        "creationTimestamp": "2026-01-01T00:00:00Z",
    },
    "spec": {
        "url": "https://github.com/stefanprodan/podinfo",
        "ref": {"branch": "main"},
        "interval": "1m",
    },
    "status": {
        "conditions": [
            {
                "type": "Ready",
                "status": "True",
                "reason": "Succeeded",
                "message": "stored artifact",
            },
        ],
        "artifact": {"revision": "main@sha1:abc123"},
    },
}

SAMPLE_HELM_REPO = {
    "metadata": {
        "name": "bitnami",
        "namespace": "flux-system",
        "creationTimestamp": "2026-01-01T00:00:00Z",
    },
    "spec": {
        "url": "https://charts.bitnami.com/bitnami",
        "type": "default",
        "interval": "1m",
    },
    "status": {
        "conditions": [
            {
                "type": "Ready",
                "status": "True",
                "reason": "Succeeded",
                "message": "stored artifact",
            },
        ],
        "artifact": {"revision": "sha256:abc123"},
    },
}

SAMPLE_KUSTOMIZATION = {
    "metadata": {
        "name": "app-ks",
        "namespace": "flux-system",
        "creationTimestamp": "2026-01-01T00:00:00Z",
    },
    "spec": {
        "sourceRef": {"kind": "GitRepository", "name": "podinfo"},
        "path": "./kustomize",
        "interval": "5m",
        "prune": True,
    },
    "status": {
        "conditions": [
            {
                "type": "Ready",
                "status": "True",
                "reason": "ReconciliationSucceeded",
                "message": "Applied",
            },
        ],
        "lastAppliedRevision": "main@sha1:abc123",
        "lastAttemptedRevision": "main@sha1:abc123",
    },
}

SAMPLE_HELM_RELEASE = {
    "metadata": {
        "name": "nginx",
        "namespace": "flux-system",
        "creationTimestamp": "2026-01-01T00:00:00Z",
    },
    "spec": {
        "chart": {
            "spec": {
                "chart": "nginx",
                "sourceRef": {"kind": "HelmRepository", "name": "bitnami"},
            },
        },
        "interval": "5m",
    },
    "status": {
        "conditions": [
            {
                "type": "Ready",
                "status": "True",
                "reason": "ReconciliationSucceeded",
                "message": "Release reconciled",
            },
        ],
    },
}


@pytest.mark.unit
@pytest.mark.kubernetes
class TestFluxManagerGitRepository:
    """Tests for FluxManager GitRepository operations."""

    def test_list_git_repositories(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_git_repositories should call custom_objects API with correct CRD coordinates."""
        mock_k8s_client.custom_objects.list_namespaced_custom_object.return_value = {
            "items": [SAMPLE_GIT_REPO]
        }

        repos = flux_manager.list_git_repositories()

        assert len(repos) == 1
        assert repos[0].name == "podinfo"
        assert repos[0].url == "https://github.com/stefanprodan/podinfo"
        assert repos[0].ready is True
        mock_k8s_client.custom_objects.list_namespaced_custom_object.assert_called_once_with(
            SOURCE_GROUP,
            SOURCE_VERSION,
            FLUX_NAMESPACE,
            GIT_REPOSITORY_PLURAL,
        )

    def test_list_git_repositories_with_namespace(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_git_repositories should use provided namespace."""
        mock_k8s_client.custom_objects.list_namespaced_custom_object.return_value = {"items": []}

        flux_manager.list_git_repositories(namespace="production")

        mock_k8s_client.custom_objects.list_namespaced_custom_object.assert_called_once_with(
            SOURCE_GROUP,
            SOURCE_VERSION,
            "production",
            GIT_REPOSITORY_PLURAL,
        )

    def test_list_git_repositories_with_label_selector(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_git_repositories should pass label_selector."""
        mock_k8s_client.custom_objects.list_namespaced_custom_object.return_value = {"items": []}

        flux_manager.list_git_repositories(label_selector="app=podinfo")

        mock_k8s_client.custom_objects.list_namespaced_custom_object.assert_called_once_with(
            SOURCE_GROUP,
            SOURCE_VERSION,
            FLUX_NAMESPACE,
            GIT_REPOSITORY_PLURAL,
            label_selector="app=podinfo",
        )

    def test_get_git_repository(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_git_repository should return a GitRepositorySummary."""
        mock_k8s_client.custom_objects.get_namespaced_custom_object.return_value = SAMPLE_GIT_REPO

        repo = flux_manager.get_git_repository("podinfo")

        assert repo.name == "podinfo"
        assert repo.ref_branch == "main"
        assert repo.ready is True
        mock_k8s_client.custom_objects.get_namespaced_custom_object.assert_called_once_with(
            SOURCE_GROUP,
            SOURCE_VERSION,
            FLUX_NAMESPACE,
            GIT_REPOSITORY_PLURAL,
            "podinfo",
        )

    def test_create_git_repository(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_git_repository should build correct CRD body."""
        mock_k8s_client.custom_objects.create_namespaced_custom_object.return_value = (
            SAMPLE_GIT_REPO
        )

        repo = flux_manager.create_git_repository(
            "podinfo",
            url="https://github.com/stefanprodan/podinfo",
            ref_branch="main",
        )

        assert repo.name == "podinfo"
        call_args = mock_k8s_client.custom_objects.create_namespaced_custom_object.call_args
        body = call_args[0][4]
        assert body["kind"] == "GitRepository"
        assert body["spec"]["url"] == "https://github.com/stefanprodan/podinfo"
        assert body["spec"]["ref"]["branch"] == "main"

    def test_delete_git_repository(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """delete_git_repository should call delete API."""
        flux_manager.delete_git_repository("podinfo")

        mock_k8s_client.custom_objects.delete_namespaced_custom_object.assert_called_once_with(
            SOURCE_GROUP,
            SOURCE_VERSION,
            FLUX_NAMESPACE,
            GIT_REPOSITORY_PLURAL,
            "podinfo",
        )

    def test_suspend_git_repository(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """suspend_git_repository should patch spec.suspend to True."""
        mock_k8s_client.custom_objects.patch_namespaced_custom_object.return_value = {}

        result = flux_manager.suspend_git_repository("podinfo")

        assert result["suspended"] is True
        call_args = mock_k8s_client.custom_objects.patch_namespaced_custom_object.call_args
        patch = call_args[0][5]
        assert patch == {"spec": {"suspend": True}}

    def test_resume_git_repository(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """resume_git_repository should patch spec.suspend to False."""
        mock_k8s_client.custom_objects.patch_namespaced_custom_object.return_value = {}

        result = flux_manager.resume_git_repository("podinfo")

        assert result["suspended"] is False
        call_args = mock_k8s_client.custom_objects.patch_namespaced_custom_object.call_args
        patch = call_args[0][5]
        assert patch == {"spec": {"suspend": False}}

    def test_reconcile_git_repository(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """reconcile_git_repository should patch with reconcile annotation."""
        mock_k8s_client.custom_objects.patch_namespaced_custom_object.return_value = {}

        result = flux_manager.reconcile_git_repository("podinfo")

        assert "requested_at" in result
        call_args = mock_k8s_client.custom_objects.patch_namespaced_custom_object.call_args
        applied_patch = call_args[0][5]
        assert RECONCILE_ANNOTATION in applied_patch["metadata"]["annotations"]


@pytest.mark.unit
@pytest.mark.kubernetes
class TestFluxManagerHelmRepository:
    """Tests for FluxManager HelmRepository operations."""

    def test_list_helm_repositories(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_helm_repositories should call custom_objects API."""
        mock_k8s_client.custom_objects.list_namespaced_custom_object.return_value = {
            "items": [SAMPLE_HELM_REPO]
        }

        repos = flux_manager.list_helm_repositories()

        assert len(repos) == 1
        assert repos[0].name == "bitnami"
        assert repos[0].url == "https://charts.bitnami.com/bitnami"
        mock_k8s_client.custom_objects.list_namespaced_custom_object.assert_called_once_with(
            SOURCE_GROUP,
            SOURCE_VERSION,
            FLUX_NAMESPACE,
            HELM_REPOSITORY_PLURAL,
        )

    def test_list_helm_repositories_with_namespace(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_helm_repositories should use provided namespace."""
        mock_k8s_client.custom_objects.list_namespaced_custom_object.return_value = {"items": []}

        flux_manager.list_helm_repositories(namespace="custom-ns")

        mock_k8s_client.custom_objects.list_namespaced_custom_object.assert_called_once_with(
            SOURCE_GROUP,
            SOURCE_VERSION,
            "custom-ns",
            HELM_REPOSITORY_PLURAL,
        )

    def test_get_helm_repository(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_helm_repository should return a HelmRepositorySummary."""
        mock_k8s_client.custom_objects.get_namespaced_custom_object.return_value = SAMPLE_HELM_REPO

        repo = flux_manager.get_helm_repository("bitnami")

        assert repo.name == "bitnami"
        assert repo.ready is True
        mock_k8s_client.custom_objects.get_namespaced_custom_object.assert_called_once_with(
            SOURCE_GROUP,
            SOURCE_VERSION,
            FLUX_NAMESPACE,
            HELM_REPOSITORY_PLURAL,
            "bitnami",
        )

    def test_create_helm_repository(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_helm_repository should build correct CRD body."""
        mock_k8s_client.custom_objects.create_namespaced_custom_object.return_value = (
            SAMPLE_HELM_REPO
        )

        repo = flux_manager.create_helm_repository(
            "bitnami",
            url="https://charts.bitnami.com/bitnami",
        )

        assert repo.name == "bitnami"
        call_args = mock_k8s_client.custom_objects.create_namespaced_custom_object.call_args
        body = call_args[0][4]
        assert body["kind"] == "HelmRepository"
        assert body["spec"]["url"] == "https://charts.bitnami.com/bitnami"

    def test_delete_helm_repository(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """delete_helm_repository should call delete API."""
        flux_manager.delete_helm_repository("bitnami")

        mock_k8s_client.custom_objects.delete_namespaced_custom_object.assert_called_once_with(
            SOURCE_GROUP,
            SOURCE_VERSION,
            FLUX_NAMESPACE,
            HELM_REPOSITORY_PLURAL,
            "bitnami",
        )

    def test_suspend_helm_repository(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """suspend_helm_repository should patch spec.suspend to True."""
        mock_k8s_client.custom_objects.patch_namespaced_custom_object.return_value = {}

        result = flux_manager.suspend_helm_repository("bitnami")

        assert result["suspended"] is True
        call_args = mock_k8s_client.custom_objects.patch_namespaced_custom_object.call_args
        patch = call_args[0][5]
        assert patch == {"spec": {"suspend": True}}

    def test_resume_helm_repository(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """resume_helm_repository should patch spec.suspend to False."""
        mock_k8s_client.custom_objects.patch_namespaced_custom_object.return_value = {}

        result = flux_manager.resume_helm_repository("bitnami")

        assert result["suspended"] is False


@pytest.mark.unit
@pytest.mark.kubernetes
class TestFluxManagerKustomization:
    """Tests for FluxManager Kustomization operations."""

    def test_list_kustomizations(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_kustomizations should call custom_objects API."""
        mock_k8s_client.custom_objects.list_namespaced_custom_object.return_value = {
            "items": [SAMPLE_KUSTOMIZATION]
        }

        ks_list = flux_manager.list_kustomizations()

        assert len(ks_list) == 1
        assert ks_list[0].name == "app-ks"
        assert ks_list[0].source_name == "podinfo"
        mock_k8s_client.custom_objects.list_namespaced_custom_object.assert_called_once_with(
            KUSTOMIZE_GROUP,
            KUSTOMIZE_VERSION,
            FLUX_NAMESPACE,
            KUSTOMIZATION_PLURAL,
        )

    def test_list_kustomizations_with_namespace(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_kustomizations should use provided namespace."""
        mock_k8s_client.custom_objects.list_namespaced_custom_object.return_value = {"items": []}

        flux_manager.list_kustomizations(namespace="production")

        mock_k8s_client.custom_objects.list_namespaced_custom_object.assert_called_once_with(
            KUSTOMIZE_GROUP,
            KUSTOMIZE_VERSION,
            "production",
            KUSTOMIZATION_PLURAL,
        )

    def test_get_kustomization(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_kustomization should return a KustomizationSummary."""
        mock_k8s_client.custom_objects.get_namespaced_custom_object.return_value = (
            SAMPLE_KUSTOMIZATION
        )

        ks = flux_manager.get_kustomization("app-ks")

        assert ks.name == "app-ks"
        assert ks.source_kind == "GitRepository"
        assert ks.ready is True
        mock_k8s_client.custom_objects.get_namespaced_custom_object.assert_called_once_with(
            KUSTOMIZE_GROUP,
            KUSTOMIZE_VERSION,
            FLUX_NAMESPACE,
            KUSTOMIZATION_PLURAL,
            "app-ks",
        )

    def test_create_kustomization(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_kustomization should build correct CRD body."""
        mock_k8s_client.custom_objects.create_namespaced_custom_object.return_value = (
            SAMPLE_KUSTOMIZATION
        )

        ks = flux_manager.create_kustomization(
            "app-ks",
            source_kind="GitRepository",
            source_name="podinfo",
            path="./kustomize",
        )

        assert ks.name == "app-ks"
        call_args = mock_k8s_client.custom_objects.create_namespaced_custom_object.call_args
        body = call_args[0][4]
        assert body["kind"] == "Kustomization"
        assert body["spec"]["sourceRef"]["kind"] == "GitRepository"
        assert body["spec"]["sourceRef"]["name"] == "podinfo"
        assert body["spec"]["path"] == "./kustomize"

    def test_delete_kustomization(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """delete_kustomization should call delete API."""
        flux_manager.delete_kustomization("app-ks")

        mock_k8s_client.custom_objects.delete_namespaced_custom_object.assert_called_once_with(
            KUSTOMIZE_GROUP,
            KUSTOMIZE_VERSION,
            FLUX_NAMESPACE,
            KUSTOMIZATION_PLURAL,
            "app-ks",
        )

    def test_suspend_kustomization(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """suspend_kustomization should patch spec.suspend to True."""
        mock_k8s_client.custom_objects.patch_namespaced_custom_object.return_value = {}

        result = flux_manager.suspend_kustomization("app-ks")

        assert result["suspended"] is True
        call_args = mock_k8s_client.custom_objects.patch_namespaced_custom_object.call_args
        patch = call_args[0][5]
        assert patch == {"spec": {"suspend": True}}

    def test_resume_kustomization(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """resume_kustomization should patch spec.suspend to False."""
        mock_k8s_client.custom_objects.patch_namespaced_custom_object.return_value = {}

        result = flux_manager.resume_kustomization("app-ks")

        assert result["suspended"] is False

    def test_reconcile_kustomization(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """reconcile_kustomization should patch with reconcile annotation."""
        mock_k8s_client.custom_objects.patch_namespaced_custom_object.return_value = {}

        result = flux_manager.reconcile_kustomization("app-ks")

        assert "requested_at" in result
        call_args = mock_k8s_client.custom_objects.patch_namespaced_custom_object.call_args
        patch = call_args[0][5]
        assert RECONCILE_ANNOTATION in patch["metadata"]["annotations"]


@pytest.mark.unit
@pytest.mark.kubernetes
class TestFluxManagerHelmRelease:
    """Tests for FluxManager HelmRelease operations."""

    def test_list_helm_releases(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_helm_releases should call custom_objects API."""
        mock_k8s_client.custom_objects.list_namespaced_custom_object.return_value = {
            "items": [SAMPLE_HELM_RELEASE]
        }

        releases = flux_manager.list_helm_releases()

        assert len(releases) == 1
        assert releases[0].name == "nginx"
        assert releases[0].chart_name == "nginx"
        mock_k8s_client.custom_objects.list_namespaced_custom_object.assert_called_once_with(
            HELM_GROUP,
            HELM_VERSION,
            FLUX_NAMESPACE,
            HELM_RELEASE_PLURAL,
        )

    def test_list_helm_releases_with_namespace(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_helm_releases should use provided namespace."""
        mock_k8s_client.custom_objects.list_namespaced_custom_object.return_value = {"items": []}

        flux_manager.list_helm_releases(namespace="apps")

        mock_k8s_client.custom_objects.list_namespaced_custom_object.assert_called_once_with(
            HELM_GROUP,
            HELM_VERSION,
            "apps",
            HELM_RELEASE_PLURAL,
        )

    def test_get_helm_release(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_helm_release should return a HelmReleaseSummary."""
        mock_k8s_client.custom_objects.get_namespaced_custom_object.return_value = (
            SAMPLE_HELM_RELEASE
        )

        release = flux_manager.get_helm_release("nginx")

        assert release.name == "nginx"
        assert release.chart_source_name == "bitnami"
        assert release.ready is True
        mock_k8s_client.custom_objects.get_namespaced_custom_object.assert_called_once_with(
            HELM_GROUP,
            HELM_VERSION,
            FLUX_NAMESPACE,
            HELM_RELEASE_PLURAL,
            "nginx",
        )

    def test_create_helm_release(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_helm_release should build correct CRD body."""
        mock_k8s_client.custom_objects.create_namespaced_custom_object.return_value = (
            SAMPLE_HELM_RELEASE
        )

        release = flux_manager.create_helm_release(
            "nginx",
            chart_name="nginx",
            chart_source_kind="HelmRepository",
            chart_source_name="bitnami",
        )

        assert release.name == "nginx"
        call_args = mock_k8s_client.custom_objects.create_namespaced_custom_object.call_args
        body = call_args[0][4]
        assert body["kind"] == "HelmRelease"
        assert body["spec"]["chart"]["spec"]["chart"] == "nginx"
        assert body["spec"]["chart"]["spec"]["sourceRef"]["name"] == "bitnami"

    def test_delete_helm_release(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """delete_helm_release should call delete API."""
        flux_manager.delete_helm_release("nginx")

        mock_k8s_client.custom_objects.delete_namespaced_custom_object.assert_called_once_with(
            HELM_GROUP,
            HELM_VERSION,
            FLUX_NAMESPACE,
            HELM_RELEASE_PLURAL,
            "nginx",
        )

    def test_suspend_helm_release(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """suspend_helm_release should patch spec.suspend to True."""
        mock_k8s_client.custom_objects.patch_namespaced_custom_object.return_value = {}

        result = flux_manager.suspend_helm_release("nginx")

        assert result["suspended"] is True
        call_args = mock_k8s_client.custom_objects.patch_namespaced_custom_object.call_args
        patch = call_args[0][5]
        assert patch == {"spec": {"suspend": True}}

    def test_resume_helm_release(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """resume_helm_release should patch spec.suspend to False."""
        mock_k8s_client.custom_objects.patch_namespaced_custom_object.return_value = {}

        result = flux_manager.resume_helm_release("nginx")

        assert result["suspended"] is False

    def test_reconcile_helm_release(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """reconcile_helm_release should patch with reconcile annotation."""
        mock_k8s_client.custom_objects.patch_namespaced_custom_object.return_value = {}

        result = flux_manager.reconcile_helm_release("nginx")

        assert "requested_at" in result
        call_args = mock_k8s_client.custom_objects.patch_namespaced_custom_object.call_args
        patch = call_args[0][5]
        assert RECONCILE_ANNOTATION in patch["metadata"]["annotations"]


@pytest.mark.unit
@pytest.mark.kubernetes
class TestFluxManagerErrorHandling:
    """Tests for FluxManager error handling."""

    def test_error_handling_delegates_to_base(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """API errors should be translated via _handle_api_error."""
        api_error = Exception("API Error")
        mock_k8s_client.custom_objects.get_namespaced_custom_object.side_effect = api_error
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("translated")

        with pytest.raises(RuntimeError, match="translated"):
            flux_manager.get_git_repository("podinfo")

        mock_k8s_client.translate_api_exception.assert_called_once()
