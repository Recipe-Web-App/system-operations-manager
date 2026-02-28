"""Unit tests for FluxManager."""

from __future__ import annotations

from typing import Any
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


# =============================================================================
# Error-path and edge-case tests for GitRepository operations
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestGitRepositoryErrorPaths:
    """Tests covering error paths in GitRepository operations (lines 94-95, 199-200, 224-225,
    255-256, 286-287, 325-326)."""

    def test_list_git_repositories_error_propagates(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_git_repositories error handler should call _handle_api_error (lines 94-95)."""
        client: Any = mock_k8s_client
        client.custom_objects.list_namespaced_custom_object.side_effect = Exception("list error")
        client.translate_api_exception.side_effect = RuntimeError("translated list")

        with pytest.raises(RuntimeError, match="translated list"):
            flux_manager.list_git_repositories()

        client.translate_api_exception.assert_called_once()

    def test_create_git_repository_error_propagates(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_git_repository error handler should call _handle_api_error (lines 199-200)."""
        client: Any = mock_k8s_client
        client.custom_objects.create_namespaced_custom_object.side_effect = Exception(
            "create error"
        )
        client.translate_api_exception.side_effect = RuntimeError("translated create")

        with pytest.raises(RuntimeError, match="translated create"):
            flux_manager.create_git_repository(
                "podinfo",
                url="https://github.com/stefanprodan/podinfo",
            )

        client.translate_api_exception.assert_called_once()

    def test_delete_git_repository_error_propagates(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """delete_git_repository error handler should call _handle_api_error (lines 224-225)."""
        client: Any = mock_k8s_client
        client.custom_objects.delete_namespaced_custom_object.side_effect = Exception(
            "delete error"
        )
        client.translate_api_exception.side_effect = RuntimeError("translated delete")

        with pytest.raises(RuntimeError, match="translated delete"):
            flux_manager.delete_git_repository("podinfo")

        client.translate_api_exception.assert_called_once()

    def test_suspend_git_repository_error_propagates(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """suspend_git_repository error handler should call _handle_api_error (lines 255-256)."""
        client: Any = mock_k8s_client
        client.custom_objects.patch_namespaced_custom_object.side_effect = Exception(
            "suspend error"
        )
        client.translate_api_exception.side_effect = RuntimeError("translated suspend")

        with pytest.raises(RuntimeError, match="translated suspend"):
            flux_manager.suspend_git_repository("podinfo")

        client.translate_api_exception.assert_called_once()

    def test_resume_git_repository_error_propagates(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """resume_git_repository error handler should call _handle_api_error (lines 286-287)."""
        client: Any = mock_k8s_client
        client.custom_objects.patch_namespaced_custom_object.side_effect = Exception("resume error")
        client.translate_api_exception.side_effect = RuntimeError("translated resume")

        with pytest.raises(RuntimeError, match="translated resume"):
            flux_manager.resume_git_repository("podinfo")

        client.translate_api_exception.assert_called_once()

    def test_reconcile_git_repository_error_propagates(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """reconcile_git_repository error handler should call _handle_api_error (lines 325-326)."""
        client: Any = mock_k8s_client
        client.custom_objects.patch_namespaced_custom_object.side_effect = Exception(
            "reconcile error"
        )
        client.translate_api_exception.side_effect = RuntimeError("translated reconcile")

        with pytest.raises(RuntimeError, match="translated reconcile"):
            flux_manager.reconcile_git_repository("podinfo")

        client.translate_api_exception.assert_called_once()


# =============================================================================
# Tests for create_git_repository optional ref branches (lines 163, 165, 167, 169, 177)
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestGitRepositoryCreateBranches:
    """Tests covering optional ref and secret_ref branches in create_git_repository."""

    def test_create_git_repository_with_ref_tag(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_git_repository should include tag in ref when ref_tag provided (line 163)."""
        mock_k8s_client.custom_objects.create_namespaced_custom_object.return_value = (
            SAMPLE_GIT_REPO
        )

        flux_manager.create_git_repository(
            "podinfo",
            url="https://github.com/stefanprodan/podinfo",
            ref_tag="v1.0.0",
        )

        call_args = mock_k8s_client.custom_objects.create_namespaced_custom_object.call_args
        body = call_args[0][4]
        assert body["spec"]["ref"]["tag"] == "v1.0.0"
        assert "branch" not in body["spec"]["ref"]

    def test_create_git_repository_with_ref_semver(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_git_repository should include semver in ref when ref_semver provided (line 165)."""
        mock_k8s_client.custom_objects.create_namespaced_custom_object.return_value = (
            SAMPLE_GIT_REPO
        )

        flux_manager.create_git_repository(
            "podinfo",
            url="https://github.com/stefanprodan/podinfo",
            ref_semver=">=1.0.0",
        )

        call_args = mock_k8s_client.custom_objects.create_namespaced_custom_object.call_args
        body = call_args[0][4]
        assert body["spec"]["ref"]["semver"] == ">=1.0.0"
        assert "branch" not in body["spec"]["ref"]

    def test_create_git_repository_with_ref_commit(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_git_repository should include commit in ref when ref_commit provided (line 167)."""
        mock_k8s_client.custom_objects.create_namespaced_custom_object.return_value = (
            SAMPLE_GIT_REPO
        )

        flux_manager.create_git_repository(
            "podinfo",
            url="https://github.com/stefanprodan/podinfo",
            ref_commit="abc123def456",
        )

        call_args = mock_k8s_client.custom_objects.create_namespaced_custom_object.call_args
        body = call_args[0][4]
        assert body["spec"]["ref"]["commit"] == "abc123def456"
        assert "branch" not in body["spec"]["ref"]

    def test_create_git_repository_default_branch_when_no_ref(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_git_repository should default to main branch when no ref provided (line 169)."""
        mock_k8s_client.custom_objects.create_namespaced_custom_object.return_value = (
            SAMPLE_GIT_REPO
        )

        flux_manager.create_git_repository(
            "podinfo",
            url="https://github.com/stefanprodan/podinfo",
        )

        call_args = mock_k8s_client.custom_objects.create_namespaced_custom_object.call_args
        body = call_args[0][4]
        assert body["spec"]["ref"]["branch"] == "main"

    def test_create_git_repository_with_secret_ref(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_git_repository should include secretRef in spec when secret_ref provided (line 177)."""
        mock_k8s_client.custom_objects.create_namespaced_custom_object.return_value = (
            SAMPLE_GIT_REPO
        )

        flux_manager.create_git_repository(
            "podinfo",
            url="https://github.com/stefanprodan/podinfo",
            secret_ref="my-git-secret",
        )

        call_args = mock_k8s_client.custom_objects.create_namespaced_custom_object.call_args
        body = call_args[0][4]
        assert body["spec"]["secretRef"] == {"name": "my-git-secret"}

    def test_create_git_repository_with_all_optional_fields(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_git_repository should include all optional fields when provided."""
        mock_k8s_client.custom_objects.create_namespaced_custom_object.return_value = (
            SAMPLE_GIT_REPO
        )

        flux_manager.create_git_repository(
            "podinfo",
            namespace="production",
            url="https://github.com/stefanprodan/podinfo",
            ref_branch="release",
            interval="5m",
            secret_ref="git-creds",
            labels={"env": "prod"},
        )

        call_args = mock_k8s_client.custom_objects.create_namespaced_custom_object.call_args
        body = call_args[0][4]
        assert body["spec"]["ref"]["branch"] == "release"
        assert body["spec"]["secretRef"] == {"name": "git-creds"}
        assert body["metadata"]["labels"] == {"env": "prod"}
        assert call_args[0][2] == "production"


# =============================================================================
# Tests for get_git_repository_status (lines 342-365)
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestGitRepositoryStatus:
    """Tests covering get_git_repository_status (lines 342-365)."""

    def test_get_git_repository_status_returns_full_status(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_git_repository_status should return structured status dict (lines 342-365)."""
        mock_k8s_client.custom_objects.get_namespaced_custom_object.return_value = {
            "status": {
                "conditions": [{"type": "Ready", "status": "True"}],
                "artifact": {
                    "revision": "main@sha1:abc123",
                    "digest": "sha256:deadbeef",
                },
                "lastHandledReconcileAt": "2026-01-01T00:00:00Z",
                "observedGeneration": 3,
            }
        }

        result = flux_manager.get_git_repository_status("podinfo")

        assert result["name"] == "podinfo"
        assert result["namespace"] == FLUX_NAMESPACE
        assert result["conditions"] == [{"type": "Ready", "status": "True"}]
        assert result["artifact_revision"] == "main@sha1:abc123"
        assert result["artifact_digest"] == "sha256:deadbeef"
        assert result["last_handled_reconcile_at"] == "2026-01-01T00:00:00Z"
        assert result["observed_generation"] == 3

    def test_get_git_repository_status_with_empty_status(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_git_repository_status should handle missing status sub-fields gracefully."""
        mock_k8s_client.custom_objects.get_namespaced_custom_object.return_value = {}

        result = flux_manager.get_git_repository_status("podinfo")

        assert result["conditions"] == []
        assert result["artifact_revision"] is None
        assert result["artifact_digest"] is None
        assert result["last_handled_reconcile_at"] is None
        assert result["observed_generation"] is None

    def test_get_git_repository_status_uses_explicit_namespace(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_git_repository_status should use the provided namespace."""
        mock_k8s_client.custom_objects.get_namespaced_custom_object.return_value = {}

        result = flux_manager.get_git_repository_status("podinfo", namespace="custom-ns")

        assert result["namespace"] == "custom-ns"
        mock_k8s_client.custom_objects.get_namespaced_custom_object.assert_called_once_with(
            SOURCE_GROUP,
            SOURCE_VERSION,
            "custom-ns",
            GIT_REPOSITORY_PLURAL,
            "podinfo",
        )

    def test_get_git_repository_status_error_propagates(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_git_repository_status error handler should re-raise translated error."""
        client: Any = mock_k8s_client
        client.custom_objects.get_namespaced_custom_object.side_effect = Exception("status error")
        client.translate_api_exception.side_effect = RuntimeError("translated status")

        with pytest.raises(RuntimeError, match="translated status"):
            flux_manager.get_git_repository_status("podinfo")


# =============================================================================
# Error-path and edge-case tests for HelmRepository operations
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestHelmRepositoryErrorPaths:
    """Tests covering error paths in HelmRepository operations (lines 404-405, 432-433,
    492-493, 517-518, 548-549, 579-580)."""

    def test_list_helm_repositories_with_label_selector(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_helm_repositories should pass label_selector kwarg (line 391)."""
        mock_k8s_client.custom_objects.list_namespaced_custom_object.return_value = {"items": []}

        flux_manager.list_helm_repositories(label_selector="app=bitnami")

        mock_k8s_client.custom_objects.list_namespaced_custom_object.assert_called_once_with(
            SOURCE_GROUP,
            SOURCE_VERSION,
            FLUX_NAMESPACE,
            HELM_REPOSITORY_PLURAL,
            label_selector="app=bitnami",
        )

    def test_list_helm_repositories_error_propagates(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_helm_repositories error handler should call _handle_api_error (lines 404-405)."""
        client: Any = mock_k8s_client
        client.custom_objects.list_namespaced_custom_object.side_effect = Exception("list error")
        client.translate_api_exception.side_effect = RuntimeError("translated helm list")

        with pytest.raises(RuntimeError, match="translated helm list"):
            flux_manager.list_helm_repositories()

        client.translate_api_exception.assert_called_once()

    def test_get_helm_repository_error_propagates(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_helm_repository error handler should call _handle_api_error (lines 432-433)."""
        client: Any = mock_k8s_client
        client.custom_objects.get_namespaced_custom_object.side_effect = Exception("get error")
        client.translate_api_exception.side_effect = RuntimeError("translated helm get")

        with pytest.raises(RuntimeError, match="translated helm get"):
            flux_manager.get_helm_repository("bitnami")

        client.translate_api_exception.assert_called_once()

    def test_create_helm_repository_error_propagates(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_helm_repository error handler should call _handle_api_error (lines 492-493)."""
        client: Any = mock_k8s_client
        client.custom_objects.create_namespaced_custom_object.side_effect = Exception(
            "create error"
        )
        client.translate_api_exception.side_effect = RuntimeError("translated helm create")

        with pytest.raises(RuntimeError, match="translated helm create"):
            flux_manager.create_helm_repository(
                "bitnami",
                url="https://charts.bitnami.com/bitnami",
            )

        client.translate_api_exception.assert_called_once()

    def test_delete_helm_repository_error_propagates(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """delete_helm_repository error handler should call _handle_api_error (lines 517-518)."""
        client: Any = mock_k8s_client
        client.custom_objects.delete_namespaced_custom_object.side_effect = Exception(
            "delete error"
        )
        client.translate_api_exception.side_effect = RuntimeError("translated helm delete")

        with pytest.raises(RuntimeError, match="translated helm delete"):
            flux_manager.delete_helm_repository("bitnami")

        client.translate_api_exception.assert_called_once()

    def test_suspend_helm_repository_error_propagates(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """suspend_helm_repository error handler should call _handle_api_error (lines 548-549)."""
        client: Any = mock_k8s_client
        client.custom_objects.patch_namespaced_custom_object.side_effect = Exception(
            "suspend error"
        )
        client.translate_api_exception.side_effect = RuntimeError("translated helm suspend")

        with pytest.raises(RuntimeError, match="translated helm suspend"):
            flux_manager.suspend_helm_repository("bitnami")

        client.translate_api_exception.assert_called_once()

    def test_resume_helm_repository_error_propagates(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """resume_helm_repository error handler should call _handle_api_error (lines 579-580)."""
        client: Any = mock_k8s_client
        client.custom_objects.patch_namespaced_custom_object.side_effect = Exception("resume error")
        client.translate_api_exception.side_effect = RuntimeError("translated helm resume")

        with pytest.raises(RuntimeError, match="translated helm resume"):
            flux_manager.resume_helm_repository("bitnami")

        client.translate_api_exception.assert_called_once()


# =============================================================================
# Tests for create_helm_repository optional branches (lines 468, 470)
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestHelmRepositoryCreateBranches:
    """Tests covering optional branches in create_helm_repository (lines 468, 470)."""

    def test_create_helm_repository_with_oci_type(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_helm_repository should add type field when repo_type is not 'default' (line 468)."""
        mock_k8s_client.custom_objects.create_namespaced_custom_object.return_value = (
            SAMPLE_HELM_REPO
        )

        flux_manager.create_helm_repository(
            "my-oci-repo",
            url="oci://registry.example.com/charts",
            repo_type="oci",
        )

        call_args = mock_k8s_client.custom_objects.create_namespaced_custom_object.call_args
        body = call_args[0][4]
        assert body["spec"]["type"] == "oci"

    def test_create_helm_repository_default_type_omits_type_field(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_helm_repository should not include type field when repo_type is 'default'."""
        mock_k8s_client.custom_objects.create_namespaced_custom_object.return_value = (
            SAMPLE_HELM_REPO
        )

        flux_manager.create_helm_repository(
            "bitnami",
            url="https://charts.bitnami.com/bitnami",
        )

        call_args = mock_k8s_client.custom_objects.create_namespaced_custom_object.call_args
        body = call_args[0][4]
        assert "type" not in body["spec"]

    def test_create_helm_repository_with_secret_ref(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_helm_repository should include secretRef when secret_ref provided (line 470)."""
        mock_k8s_client.custom_objects.create_namespaced_custom_object.return_value = (
            SAMPLE_HELM_REPO
        )

        flux_manager.create_helm_repository(
            "private-repo",
            url="https://charts.example.com",
            secret_ref="helm-auth-secret",
        )

        call_args = mock_k8s_client.custom_objects.create_namespaced_custom_object.call_args
        body = call_args[0][4]
        assert body["spec"]["secretRef"] == {"name": "helm-auth-secret"}


# =============================================================================
# Tests for reconcile_helm_repository (lines 596-616)
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestHelmRepositoryReconcile:
    """Tests covering reconcile_helm_repository (lines 596-616)."""

    def test_reconcile_helm_repository_patches_annotation(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """reconcile_helm_repository should patch with reconcile annotation (lines 596-614)."""
        mock_k8s_client.custom_objects.patch_namespaced_custom_object.return_value = {}

        result = flux_manager.reconcile_helm_repository("bitnami")

        assert result["name"] == "bitnami"
        assert result["namespace"] == FLUX_NAMESPACE
        assert "requested_at" in result
        call_args = mock_k8s_client.custom_objects.patch_namespaced_custom_object.call_args
        applied_patch = call_args[0][5]
        assert RECONCILE_ANNOTATION in applied_patch["metadata"]["annotations"]

    def test_reconcile_helm_repository_with_explicit_namespace(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """reconcile_helm_repository should use provided namespace."""
        mock_k8s_client.custom_objects.patch_namespaced_custom_object.return_value = {}

        result = flux_manager.reconcile_helm_repository("bitnami", namespace="custom-ns")

        assert result["namespace"] == "custom-ns"
        mock_k8s_client.custom_objects.patch_namespaced_custom_object.assert_called_once_with(
            SOURCE_GROUP,
            SOURCE_VERSION,
            "custom-ns",
            HELM_REPOSITORY_PLURAL,
            "bitnami",
            {"metadata": {"annotations": {RECONCILE_ANNOTATION: result["requested_at"]}}},
        )

    def test_reconcile_helm_repository_error_propagates(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """reconcile_helm_repository error handler should call _handle_api_error (line 615-616)."""
        client: Any = mock_k8s_client
        client.custom_objects.patch_namespaced_custom_object.side_effect = Exception(
            "reconcile error"
        )
        client.translate_api_exception.side_effect = RuntimeError("translated helm reconcile")

        with pytest.raises(RuntimeError, match="translated helm reconcile"):
            flux_manager.reconcile_helm_repository("bitnami")

        client.translate_api_exception.assert_called_once()


# =============================================================================
# Tests for get_helm_repository_status (lines 632-655)
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestHelmRepositoryStatus:
    """Tests covering get_helm_repository_status (lines 632-655)."""

    def test_get_helm_repository_status_returns_full_status(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_helm_repository_status should return structured status dict (lines 632-654)."""
        mock_k8s_client.custom_objects.get_namespaced_custom_object.return_value = {
            "status": {
                "conditions": [{"type": "Ready", "status": "True"}],
                "artifact": {
                    "revision": "sha256:abc123",
                    "digest": "sha256:deadbeef",
                },
                "lastHandledReconcileAt": "2026-01-01T00:00:00Z",
                "observedGeneration": 2,
            }
        }

        result = flux_manager.get_helm_repository_status("bitnami")

        assert result["name"] == "bitnami"
        assert result["namespace"] == FLUX_NAMESPACE
        assert result["conditions"] == [{"type": "Ready", "status": "True"}]
        assert result["artifact_revision"] == "sha256:abc123"
        assert result["artifact_digest"] == "sha256:deadbeef"
        assert result["last_handled_reconcile_at"] == "2026-01-01T00:00:00Z"
        assert result["observed_generation"] == 2

    def test_get_helm_repository_status_with_empty_status(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_helm_repository_status should handle missing status sub-fields gracefully."""
        mock_k8s_client.custom_objects.get_namespaced_custom_object.return_value = {}

        result = flux_manager.get_helm_repository_status("bitnami")

        assert result["conditions"] == []
        assert result["artifact_revision"] is None
        assert result["artifact_digest"] is None
        assert result["last_handled_reconcile_at"] is None
        assert result["observed_generation"] is None

    def test_get_helm_repository_status_with_explicit_namespace(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_helm_repository_status should use the provided namespace."""
        mock_k8s_client.custom_objects.get_namespaced_custom_object.return_value = {}

        result = flux_manager.get_helm_repository_status("bitnami", namespace="custom-ns")

        assert result["namespace"] == "custom-ns"
        mock_k8s_client.custom_objects.get_namespaced_custom_object.assert_called_once_with(
            SOURCE_GROUP,
            SOURCE_VERSION,
            "custom-ns",
            HELM_REPOSITORY_PLURAL,
            "bitnami",
        )

    def test_get_helm_repository_status_error_propagates(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_helm_repository_status error handler should re-raise translated error (line 655)."""
        client: Any = mock_k8s_client
        client.custom_objects.get_namespaced_custom_object.side_effect = Exception("status error")
        client.translate_api_exception.side_effect = RuntimeError("translated helm status")

        with pytest.raises(RuntimeError, match="translated helm status"):
            flux_manager.get_helm_repository_status("bitnami")


# =============================================================================
# Error-path and edge-case tests for Kustomization operations
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestKustomizationErrorPaths:
    """Tests covering error paths in Kustomization operations (lines 681, 694-695,
    722-723, 795-796, 820-821, 851-852, 882-883, 918-919)."""

    def test_list_kustomizations_with_label_selector(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_kustomizations should pass label_selector kwarg (line 681)."""
        mock_k8s_client.custom_objects.list_namespaced_custom_object.return_value = {"items": []}

        flux_manager.list_kustomizations(label_selector="team=platform")

        mock_k8s_client.custom_objects.list_namespaced_custom_object.assert_called_once_with(
            KUSTOMIZE_GROUP,
            KUSTOMIZE_VERSION,
            FLUX_NAMESPACE,
            KUSTOMIZATION_PLURAL,
            label_selector="team=platform",
        )

    def test_list_kustomizations_error_propagates(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_kustomizations error handler should call _handle_api_error (lines 694-695)."""
        client: Any = mock_k8s_client
        client.custom_objects.list_namespaced_custom_object.side_effect = Exception("list error")
        client.translate_api_exception.side_effect = RuntimeError("translated ks list")

        with pytest.raises(RuntimeError, match="translated ks list"):
            flux_manager.list_kustomizations()

        client.translate_api_exception.assert_called_once()

    def test_get_kustomization_error_propagates(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_kustomization error handler should call _handle_api_error (lines 722-723)."""
        client: Any = mock_k8s_client
        client.custom_objects.get_namespaced_custom_object.side_effect = Exception("get error")
        client.translate_api_exception.side_effect = RuntimeError("translated ks get")

        with pytest.raises(RuntimeError, match="translated ks get"):
            flux_manager.get_kustomization("app-ks")

        client.translate_api_exception.assert_called_once()

    def test_create_kustomization_error_propagates(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_kustomization error handler should call _handle_api_error (lines 795-796)."""
        client: Any = mock_k8s_client
        client.custom_objects.create_namespaced_custom_object.side_effect = Exception(
            "create error"
        )
        client.translate_api_exception.side_effect = RuntimeError("translated ks create")

        with pytest.raises(RuntimeError, match="translated ks create"):
            flux_manager.create_kustomization(
                "app-ks",
                source_kind="GitRepository",
                source_name="podinfo",
            )

        client.translate_api_exception.assert_called_once()

    def test_delete_kustomization_error_propagates(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """delete_kustomization error handler should call _handle_api_error (lines 820-821)."""
        client: Any = mock_k8s_client
        client.custom_objects.delete_namespaced_custom_object.side_effect = Exception(
            "delete error"
        )
        client.translate_api_exception.side_effect = RuntimeError("translated ks delete")

        with pytest.raises(RuntimeError, match="translated ks delete"):
            flux_manager.delete_kustomization("app-ks")

        client.translate_api_exception.assert_called_once()

    def test_suspend_kustomization_error_propagates(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """suspend_kustomization error handler should call _handle_api_error (lines 851-852)."""
        client: Any = mock_k8s_client
        client.custom_objects.patch_namespaced_custom_object.side_effect = Exception(
            "suspend error"
        )
        client.translate_api_exception.side_effect = RuntimeError("translated ks suspend")

        with pytest.raises(RuntimeError, match="translated ks suspend"):
            flux_manager.suspend_kustomization("app-ks")

        client.translate_api_exception.assert_called_once()

    def test_resume_kustomization_error_propagates(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """resume_kustomization error handler should call _handle_api_error (lines 882-883)."""
        client: Any = mock_k8s_client
        client.custom_objects.patch_namespaced_custom_object.side_effect = Exception("resume error")
        client.translate_api_exception.side_effect = RuntimeError("translated ks resume")

        with pytest.raises(RuntimeError, match="translated ks resume"):
            flux_manager.resume_kustomization("app-ks")

        client.translate_api_exception.assert_called_once()

    def test_reconcile_kustomization_error_propagates(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """reconcile_kustomization error handler should call _handle_api_error (lines 918-919)."""
        client: Any = mock_k8s_client
        client.custom_objects.patch_namespaced_custom_object.side_effect = Exception(
            "reconcile error"
        )
        client.translate_api_exception.side_effect = RuntimeError("translated ks reconcile")

        with pytest.raises(RuntimeError, match="translated ks reconcile"):
            flux_manager.reconcile_kustomization("app-ks")

        client.translate_api_exception.assert_called_once()


# =============================================================================
# Tests for create_kustomization optional branches (lines 764, 773)
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestKustomizationCreateBranches:
    """Tests covering optional branches in create_kustomization (lines 764, 773)."""

    def test_create_kustomization_with_source_namespace(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_kustomization should include namespace in sourceRef when provided (line 764)."""
        mock_k8s_client.custom_objects.create_namespaced_custom_object.return_value = (
            SAMPLE_KUSTOMIZATION
        )

        flux_manager.create_kustomization(
            "app-ks",
            source_kind="GitRepository",
            source_name="podinfo",
            source_namespace="flux-system",
        )

        call_args = mock_k8s_client.custom_objects.create_namespaced_custom_object.call_args
        body = call_args[0][4]
        assert body["spec"]["sourceRef"]["namespace"] == "flux-system"

    def test_create_kustomization_without_source_namespace(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_kustomization should omit namespace from sourceRef when not provided."""
        mock_k8s_client.custom_objects.create_namespaced_custom_object.return_value = (
            SAMPLE_KUSTOMIZATION
        )

        flux_manager.create_kustomization(
            "app-ks",
            source_kind="GitRepository",
            source_name="podinfo",
        )

        call_args = mock_k8s_client.custom_objects.create_namespaced_custom_object.call_args
        body = call_args[0][4]
        assert "namespace" not in body["spec"]["sourceRef"]

    def test_create_kustomization_with_target_namespace(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_kustomization should include targetNamespace in spec when provided (line 773)."""
        mock_k8s_client.custom_objects.create_namespaced_custom_object.return_value = (
            SAMPLE_KUSTOMIZATION
        )

        flux_manager.create_kustomization(
            "app-ks",
            source_kind="GitRepository",
            source_name="podinfo",
            target_namespace="production",
        )

        call_args = mock_k8s_client.custom_objects.create_namespaced_custom_object.call_args
        body = call_args[0][4]
        assert body["spec"]["targetNamespace"] == "production"

    def test_create_kustomization_without_target_namespace(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_kustomization should omit targetNamespace from spec when not provided."""
        mock_k8s_client.custom_objects.create_namespaced_custom_object.return_value = (
            SAMPLE_KUSTOMIZATION
        )

        flux_manager.create_kustomization(
            "app-ks",
            source_kind="GitRepository",
            source_name="podinfo",
        )

        call_args = mock_k8s_client.custom_objects.create_namespaced_custom_object.call_args
        body = call_args[0][4]
        assert "targetNamespace" not in body["spec"]


# =============================================================================
# Tests for get_kustomization_status (lines 935-957)
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestKustomizationStatus:
    """Tests covering get_kustomization_status (lines 935-957)."""

    def test_get_kustomization_status_returns_full_status(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_kustomization_status should return structured status dict (lines 935-956)."""
        mock_k8s_client.custom_objects.get_namespaced_custom_object.return_value = {
            "status": {
                "conditions": [{"type": "Ready", "status": "True"}],
                "lastAppliedRevision": "main@sha1:abc123",
                "lastAttemptedRevision": "main@sha1:abc123",
                "lastHandledReconcileAt": "2026-01-01T00:00:00Z",
                "observedGeneration": 5,
            }
        }

        result = flux_manager.get_kustomization_status("app-ks")

        assert result["name"] == "app-ks"
        assert result["namespace"] == FLUX_NAMESPACE
        assert result["conditions"] == [{"type": "Ready", "status": "True"}]
        assert result["last_applied_revision"] == "main@sha1:abc123"
        assert result["last_attempted_revision"] == "main@sha1:abc123"
        assert result["last_handled_reconcile_at"] == "2026-01-01T00:00:00Z"
        assert result["observed_generation"] == 5

    def test_get_kustomization_status_with_empty_status(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_kustomization_status should handle missing status fields gracefully."""
        mock_k8s_client.custom_objects.get_namespaced_custom_object.return_value = {}

        result = flux_manager.get_kustomization_status("app-ks")

        assert result["conditions"] == []
        assert result["last_applied_revision"] is None
        assert result["last_attempted_revision"] is None
        assert result["last_handled_reconcile_at"] is None
        assert result["observed_generation"] is None

    def test_get_kustomization_status_with_explicit_namespace(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_kustomization_status should use the provided namespace."""
        mock_k8s_client.custom_objects.get_namespaced_custom_object.return_value = {}

        result = flux_manager.get_kustomization_status("app-ks", namespace="staging")

        assert result["namespace"] == "staging"
        mock_k8s_client.custom_objects.get_namespaced_custom_object.assert_called_once_with(
            KUSTOMIZE_GROUP,
            KUSTOMIZE_VERSION,
            "staging",
            KUSTOMIZATION_PLURAL,
            "app-ks",
        )

    def test_get_kustomization_status_error_propagates(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_kustomization_status error handler should re-raise translated error (line 957)."""
        client: Any = mock_k8s_client
        client.custom_objects.get_namespaced_custom_object.side_effect = Exception("status error")
        client.translate_api_exception.side_effect = RuntimeError("translated ks status")

        with pytest.raises(RuntimeError, match="translated ks status"):
            flux_manager.get_kustomization_status("app-ks")


# =============================================================================
# Error-path and edge-case tests for HelmRelease operations
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestHelmReleaseErrorPaths:
    """Tests covering error paths in HelmRelease operations (lines 983, 996-997, 1024-1025,
    1102-1103, 1127-1128, 1158-1159, 1189-1190, 1225-1226)."""

    def test_list_helm_releases_with_label_selector(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_helm_releases should pass label_selector kwarg (line 983)."""
        mock_k8s_client.custom_objects.list_namespaced_custom_object.return_value = {"items": []}

        flux_manager.list_helm_releases(label_selector="app=nginx")

        mock_k8s_client.custom_objects.list_namespaced_custom_object.assert_called_once_with(
            HELM_GROUP,
            HELM_VERSION,
            FLUX_NAMESPACE,
            HELM_RELEASE_PLURAL,
            label_selector="app=nginx",
        )

    def test_list_helm_releases_error_propagates(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_helm_releases error handler should call _handle_api_error (lines 996-997)."""
        client: Any = mock_k8s_client
        client.custom_objects.list_namespaced_custom_object.side_effect = Exception("list error")
        client.translate_api_exception.side_effect = RuntimeError("translated hr list")

        with pytest.raises(RuntimeError, match="translated hr list"):
            flux_manager.list_helm_releases()

        client.translate_api_exception.assert_called_once()

    def test_get_helm_release_error_propagates(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_helm_release error handler should call _handle_api_error (lines 1024-1025)."""
        client: Any = mock_k8s_client
        client.custom_objects.get_namespaced_custom_object.side_effect = Exception("get error")
        client.translate_api_exception.side_effect = RuntimeError("translated hr get")

        with pytest.raises(RuntimeError, match="translated hr get"):
            flux_manager.get_helm_release("nginx")

        client.translate_api_exception.assert_called_once()

    def test_create_helm_release_error_propagates(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_helm_release error handler should call _handle_api_error (lines 1102-1103)."""
        client: Any = mock_k8s_client
        client.custom_objects.create_namespaced_custom_object.side_effect = Exception(
            "create error"
        )
        client.translate_api_exception.side_effect = RuntimeError("translated hr create")

        with pytest.raises(RuntimeError, match="translated hr create"):
            flux_manager.create_helm_release(
                "nginx",
                chart_name="nginx",
                chart_source_kind="HelmRepository",
                chart_source_name="bitnami",
            )

        client.translate_api_exception.assert_called_once()

    def test_delete_helm_release_error_propagates(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """delete_helm_release error handler should call _handle_api_error (lines 1127-1128)."""
        client: Any = mock_k8s_client
        client.custom_objects.delete_namespaced_custom_object.side_effect = Exception(
            "delete error"
        )
        client.translate_api_exception.side_effect = RuntimeError("translated hr delete")

        with pytest.raises(RuntimeError, match="translated hr delete"):
            flux_manager.delete_helm_release("nginx")

        client.translate_api_exception.assert_called_once()

    def test_suspend_helm_release_error_propagates(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """suspend_helm_release error handler should call _handle_api_error (lines 1158-1159)."""
        client: Any = mock_k8s_client
        client.custom_objects.patch_namespaced_custom_object.side_effect = Exception(
            "suspend error"
        )
        client.translate_api_exception.side_effect = RuntimeError("translated hr suspend")

        with pytest.raises(RuntimeError, match="translated hr suspend"):
            flux_manager.suspend_helm_release("nginx")

        client.translate_api_exception.assert_called_once()

    def test_resume_helm_release_error_propagates(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """resume_helm_release error handler should call _handle_api_error (lines 1189-1190)."""
        client: Any = mock_k8s_client
        client.custom_objects.patch_namespaced_custom_object.side_effect = Exception("resume error")
        client.translate_api_exception.side_effect = RuntimeError("translated hr resume")

        with pytest.raises(RuntimeError, match="translated hr resume"):
            flux_manager.resume_helm_release("nginx")

        client.translate_api_exception.assert_called_once()

    def test_reconcile_helm_release_error_propagates(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """reconcile_helm_release error handler should call _handle_api_error (lines 1225-1226)."""
        client: Any = mock_k8s_client
        client.custom_objects.patch_namespaced_custom_object.side_effect = Exception(
            "reconcile error"
        )
        client.translate_api_exception.side_effect = RuntimeError("translated hr reconcile")

        with pytest.raises(RuntimeError, match="translated hr reconcile"):
            flux_manager.reconcile_helm_release("nginx")

        client.translate_api_exception.assert_called_once()


# =============================================================================
# Tests for create_helm_release optional branches (lines 1066, 1078, 1080)
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestHelmReleaseCreateBranches:
    """Tests covering optional branches in create_helm_release (lines 1066, 1078, 1080)."""

    def test_create_helm_release_with_chart_source_namespace(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_helm_release should include namespace in sourceRef when provided (line 1066)."""
        mock_k8s_client.custom_objects.create_namespaced_custom_object.return_value = (
            SAMPLE_HELM_RELEASE
        )

        flux_manager.create_helm_release(
            "nginx",
            chart_name="nginx",
            chart_source_kind="HelmRepository",
            chart_source_name="bitnami",
            chart_source_namespace="flux-system",
        )

        call_args = mock_k8s_client.custom_objects.create_namespaced_custom_object.call_args
        body = call_args[0][4]
        assert body["spec"]["chart"]["spec"]["sourceRef"]["namespace"] == "flux-system"

    def test_create_helm_release_without_chart_source_namespace(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_helm_release should omit namespace from sourceRef when not provided."""
        mock_k8s_client.custom_objects.create_namespaced_custom_object.return_value = (
            SAMPLE_HELM_RELEASE
        )

        flux_manager.create_helm_release(
            "nginx",
            chart_name="nginx",
            chart_source_kind="HelmRepository",
            chart_source_name="bitnami",
        )

        call_args = mock_k8s_client.custom_objects.create_namespaced_custom_object.call_args
        body = call_args[0][4]
        assert "namespace" not in body["spec"]["chart"]["spec"]["sourceRef"]

    def test_create_helm_release_with_target_namespace(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_helm_release should include targetNamespace in spec when provided (line 1078)."""
        mock_k8s_client.custom_objects.create_namespaced_custom_object.return_value = (
            SAMPLE_HELM_RELEASE
        )

        flux_manager.create_helm_release(
            "nginx",
            chart_name="nginx",
            chart_source_kind="HelmRepository",
            chart_source_name="bitnami",
            target_namespace="production",
        )

        call_args = mock_k8s_client.custom_objects.create_namespaced_custom_object.call_args
        body = call_args[0][4]
        assert body["spec"]["targetNamespace"] == "production"

    def test_create_helm_release_without_target_namespace(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_helm_release should omit targetNamespace when not provided."""
        mock_k8s_client.custom_objects.create_namespaced_custom_object.return_value = (
            SAMPLE_HELM_RELEASE
        )

        flux_manager.create_helm_release(
            "nginx",
            chart_name="nginx",
            chart_source_kind="HelmRepository",
            chart_source_name="bitnami",
        )

        call_args = mock_k8s_client.custom_objects.create_namespaced_custom_object.call_args
        body = call_args[0][4]
        assert "targetNamespace" not in body["spec"]

    def test_create_helm_release_with_values(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_helm_release should include values in spec when provided (line 1080)."""
        mock_k8s_client.custom_objects.create_namespaced_custom_object.return_value = (
            SAMPLE_HELM_RELEASE
        )

        flux_manager.create_helm_release(
            "nginx",
            chart_name="nginx",
            chart_source_kind="HelmRepository",
            chart_source_name="bitnami",
            values={"replicaCount": 2, "service": {"type": "LoadBalancer"}},
        )

        call_args = mock_k8s_client.custom_objects.create_namespaced_custom_object.call_args
        body = call_args[0][4]
        assert body["spec"]["values"] == {"replicaCount": 2, "service": {"type": "LoadBalancer"}}

    def test_create_helm_release_without_values(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_helm_release should omit values from spec when not provided."""
        mock_k8s_client.custom_objects.create_namespaced_custom_object.return_value = (
            SAMPLE_HELM_RELEASE
        )

        flux_manager.create_helm_release(
            "nginx",
            chart_name="nginx",
            chart_source_kind="HelmRepository",
            chart_source_name="bitnami",
        )

        call_args = mock_k8s_client.custom_objects.create_namespaced_custom_object.call_args
        body = call_args[0][4]
        assert "values" not in body["spec"]

    def test_create_helm_release_with_all_optional_fields(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_helm_release should include all optional fields when provided."""
        mock_k8s_client.custom_objects.create_namespaced_custom_object.return_value = (
            SAMPLE_HELM_RELEASE
        )

        flux_manager.create_helm_release(
            "nginx",
            namespace="apps",
            chart_name="nginx",
            chart_source_kind="HelmRepository",
            chart_source_name="bitnami",
            chart_source_namespace="flux-system",
            target_namespace="production",
            values={"replicaCount": 3},
            labels={"env": "prod"},
        )

        call_args = mock_k8s_client.custom_objects.create_namespaced_custom_object.call_args
        body = call_args[0][4]
        assert body["spec"]["chart"]["spec"]["sourceRef"]["namespace"] == "flux-system"
        assert body["spec"]["targetNamespace"] == "production"
        assert body["spec"]["values"] == {"replicaCount": 3}
        assert body["metadata"]["labels"] == {"env": "prod"}
        assert call_args[0][2] == "apps"


# =============================================================================
# Tests for get_helm_release_status (lines 1242-1265)
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestHelmReleaseStatus:
    """Tests covering get_helm_release_status (lines 1242-1265)."""

    def test_get_helm_release_status_returns_full_status(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_helm_release_status should return structured status dict (lines 1242-1264)."""
        mock_k8s_client.custom_objects.get_namespaced_custom_object.return_value = {
            "status": {
                "conditions": [{"type": "Ready", "status": "True"}],
                "lastAppliedRevision": "1.0.0",
                "lastAttemptedRevision": "1.0.0",
                "lastHandledReconcileAt": "2026-01-01T00:00:00Z",
                "observedGeneration": 4,
                "history": [{"chartVersion": "1.0.0", "status": "deployed"}],
            }
        }

        result = flux_manager.get_helm_release_status("nginx")

        assert result["name"] == "nginx"
        assert result["namespace"] == FLUX_NAMESPACE
        assert result["conditions"] == [{"type": "Ready", "status": "True"}]
        assert result["last_applied_revision"] == "1.0.0"
        assert result["last_attempted_revision"] == "1.0.0"
        assert result["last_handled_reconcile_at"] == "2026-01-01T00:00:00Z"
        assert result["observed_generation"] == 4
        assert result["history"] == [{"chartVersion": "1.0.0", "status": "deployed"}]

    def test_get_helm_release_status_with_empty_status(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_helm_release_status should handle missing status fields gracefully."""
        mock_k8s_client.custom_objects.get_namespaced_custom_object.return_value = {}

        result = flux_manager.get_helm_release_status("nginx")

        assert result["conditions"] == []
        assert result["last_applied_revision"] is None
        assert result["last_attempted_revision"] is None
        assert result["last_handled_reconcile_at"] is None
        assert result["observed_generation"] is None
        assert result["history"] == []

    def test_get_helm_release_status_with_explicit_namespace(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_helm_release_status should use the provided namespace."""
        mock_k8s_client.custom_objects.get_namespaced_custom_object.return_value = {}

        result = flux_manager.get_helm_release_status("nginx", namespace="apps")

        assert result["namespace"] == "apps"
        mock_k8s_client.custom_objects.get_namespaced_custom_object.assert_called_once_with(
            HELM_GROUP,
            HELM_VERSION,
            "apps",
            HELM_RELEASE_PLURAL,
            "nginx",
        )

    def test_get_helm_release_status_error_propagates(
        self,
        flux_manager: FluxManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_helm_release_status error handler should re-raise translated error (line 1265)."""
        client: Any = mock_k8s_client
        client.custom_objects.get_namespaced_custom_object.side_effect = Exception("status error")
        client.translate_api_exception.side_effect = RuntimeError("translated hr status")

        with pytest.raises(RuntimeError, match="translated hr status"):
            flux_manager.get_helm_release_status("nginx")
