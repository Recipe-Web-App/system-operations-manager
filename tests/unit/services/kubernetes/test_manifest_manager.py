"""Unit tests for ManifestManager."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from system_operations_manager.services.kubernetes.manifest_manager import (
    ApplyResult,
    ManifestManager,
)


@pytest.fixture
def mock_k8s_client() -> MagicMock:
    """Create a mock Kubernetes client."""
    mock_client = MagicMock()
    mock_client.default_namespace = "default"
    return mock_client


@pytest.fixture
def manifest_manager(mock_k8s_client: MagicMock) -> ManifestManager:
    """Create a ManifestManager with a mocked client."""
    return ManifestManager(mock_k8s_client)


@pytest.fixture
def valid_manifest() -> dict[str, object]:
    """A valid Kubernetes manifest dictionary."""
    return {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {"name": "test-app", "namespace": "default"},
        "spec": {"replicas": 1},
    }


@pytest.fixture
def invalid_manifest_no_kind() -> dict[str, object]:
    """A manifest missing the 'kind' field."""
    return {
        "apiVersion": "v1",
        "metadata": {"name": "test-config"},
    }


@pytest.fixture
def invalid_manifest_no_name() -> dict[str, object]:
    """A manifest missing metadata.name."""
    return {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": {},
    }


# ===========================================================================
# TestLoadManifests
# ===========================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestLoadManifests:
    """Tests for ManifestManager.load_manifests."""

    def test_load_single_file(self, manifest_manager: ManifestManager, tmp_path: Path) -> None:
        """Should load a single YAML file."""
        manifest_file = tmp_path / "deployment.yaml"
        manifest_file.write_text("apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: test\n")

        result = manifest_manager.load_manifests(manifest_file)

        assert len(result) == 1
        assert result[0]["kind"] == "Deployment"
        assert result[0]["metadata"]["name"] == "test"

    def test_load_multi_document_file(
        self, manifest_manager: ManifestManager, tmp_path: Path
    ) -> None:
        """Should handle multi-document YAML (--- separator)."""
        manifest_file = tmp_path / "multi.yaml"
        manifest_file.write_text(
            "apiVersion: v1\nkind: Service\nmetadata:\n  name: svc\n"
            "---\n"
            "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: deploy\n"
        )

        result = manifest_manager.load_manifests(manifest_file)

        assert len(result) == 2
        assert result[0]["kind"] == "Service"
        assert result[1]["kind"] == "Deployment"

    def test_load_directory_recursive(
        self, manifest_manager: ManifestManager, tmp_path: Path
    ) -> None:
        """Should recursively find YAML files in directories."""
        sub_dir = tmp_path / "sub"
        sub_dir.mkdir()
        (tmp_path / "a.yaml").write_text("apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: a\n")
        (sub_dir / "b.yml").write_text("apiVersion: v1\nkind: Secret\nmetadata:\n  name: b\n")

        result = manifest_manager.load_manifests(tmp_path)

        assert len(result) == 2
        kinds = {r["kind"] for r in result}
        assert kinds == {"ConfigMap", "Secret"}

    def test_load_directory_skips_non_yaml(
        self, manifest_manager: ManifestManager, tmp_path: Path
    ) -> None:
        """Should skip non-YAML files."""
        (tmp_path / "readme.md").write_text("# README")
        (tmp_path / "deploy.yaml").write_text(
            "apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: cfg\n"
        )

        result = manifest_manager.load_manifests(tmp_path)

        assert len(result) == 1

    def test_load_nonexistent_path_raises(
        self, manifest_manager: ManifestManager, tmp_path: Path
    ) -> None:
        """Should raise FileNotFoundError for missing paths."""
        with pytest.raises(FileNotFoundError):
            manifest_manager.load_manifests(tmp_path / "nonexistent.yaml")

    def test_load_empty_file(self, manifest_manager: ManifestManager, tmp_path: Path) -> None:
        """Should return empty list for an empty YAML file."""
        empty = tmp_path / "empty.yaml"
        empty.write_text("")

        result = manifest_manager.load_manifests(empty)

        assert result == []

    def test_load_filters_none_documents(
        self, manifest_manager: ManifestManager, tmp_path: Path
    ) -> None:
        """Should filter out None entries from multi-doc YAML."""
        manifest_file = tmp_path / "with_empty.yaml"
        manifest_file.write_text(
            "---\napiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: cfg\n---\n---\n"
        )

        result = manifest_manager.load_manifests(manifest_file)

        assert len(result) == 1


# ===========================================================================
# TestValidateManifests
# ===========================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestValidateManifests:
    """Tests for ManifestManager.validate_manifests."""

    def test_validate_valid_manifest(
        self, manifest_manager: ManifestManager, valid_manifest: dict[str, object]
    ) -> None:
        """Should return valid=True for a correct manifest."""
        results = manifest_manager.validate_manifests([valid_manifest])

        assert len(results) == 1
        assert results[0].valid is True
        assert results[0].errors == []

    def test_validate_missing_api_version(self, manifest_manager: ManifestManager) -> None:
        """Should report missing apiVersion."""
        manifest: dict[str, object] = {"kind": "ConfigMap", "metadata": {"name": "test"}}

        results = manifest_manager.validate_manifests([manifest])

        assert results[0].valid is False
        assert any("apiVersion" in e for e in results[0].errors)

    def test_validate_missing_kind(
        self,
        manifest_manager: ManifestManager,
        invalid_manifest_no_kind: dict[str, object],
    ) -> None:
        """Should report missing kind."""
        results = manifest_manager.validate_manifests([invalid_manifest_no_kind])

        assert results[0].valid is False
        assert any("kind" in e for e in results[0].errors)

    def test_validate_missing_metadata(self, manifest_manager: ManifestManager) -> None:
        """Should report missing metadata."""
        manifest: dict[str, object] = {"apiVersion": "v1", "kind": "ConfigMap"}

        results = manifest_manager.validate_manifests([manifest])

        assert results[0].valid is False
        assert any("metadata" in e for e in results[0].errors)

    def test_validate_missing_metadata_name(
        self,
        manifest_manager: ManifestManager,
        invalid_manifest_no_name: dict[str, object],
    ) -> None:
        """Should report missing metadata.name."""
        results = manifest_manager.validate_manifests([invalid_manifest_no_name])

        assert results[0].valid is False
        assert any("metadata.name" in e for e in results[0].errors)

    def test_validate_empty_list(self, manifest_manager: ManifestManager) -> None:
        """Should return empty results for empty input."""
        results = manifest_manager.validate_manifests([])

        assert results == []


# ===========================================================================
# TestApplyManifests
# ===========================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestApplyManifests:
    """Tests for ManifestManager.apply_manifests."""

    def test_apply_client_dry_run(
        self,
        manifest_manager: ManifestManager,
        valid_manifest: dict[str, object],
    ) -> None:
        """Client dry run should not call any Kubernetes APIs."""
        results = manifest_manager.apply_manifests([valid_manifest], dry_run=True)

        assert len(results) == 1
        assert results[0].success is True
        assert "dry-run" in results[0].action

    @patch(
        "system_operations_manager.services.kubernetes.manifest_manager.ManifestManager._get_dynamic_client"
    )
    @patch("kubernetes.utils.create_from_dict")
    def test_apply_creates_new_resource(
        self,
        mock_create: MagicMock,
        mock_dynamic: MagicMock,
        manifest_manager: ManifestManager,
        valid_manifest: dict[str, object],
    ) -> None:
        """Should create a resource when it does not exist."""
        mock_create.return_value = None  # Success

        results = manifest_manager.apply_manifests([valid_manifest])

        assert len(results) == 1
        assert results[0].success is True
        assert results[0].action == "created"
        mock_create.assert_called_once()

    @patch(
        "system_operations_manager.services.kubernetes.manifest_manager.ManifestManager._server_side_apply"
    )
    @patch("kubernetes.utils.create_from_dict")
    def test_apply_patches_existing_resource(
        self,
        mock_create: MagicMock,
        mock_ssa: MagicMock,
        manifest_manager: ManifestManager,
        valid_manifest: dict[str, object],
    ) -> None:
        """Should fall back to server-side apply on 409 Conflict."""
        from kubernetes import utils

        mock_api_exc = MagicMock()
        mock_api_exc.status = 409
        mock_create.side_effect = utils.FailToCreateError([mock_api_exc])
        mock_ssa.return_value = ApplyResult(
            resource="Deployment/test-app",
            action="configured",
            namespace="default",
            success=True,
            message="",
        )

        results = manifest_manager.apply_manifests([valid_manifest])

        assert len(results) == 1
        assert results[0].success is True
        assert results[0].action == "configured"

    @patch("kubernetes.utils.create_from_dict")
    def test_apply_handles_api_error(
        self,
        mock_create: MagicMock,
        manifest_manager: ManifestManager,
        valid_manifest: dict[str, object],
    ) -> None:
        """Should capture non-conflict API errors in result."""
        from kubernetes import utils

        mock_api_exc = MagicMock()
        mock_api_exc.status = 403
        mock_api_exc.reason = "Forbidden"
        mock_create.side_effect = utils.FailToCreateError([mock_api_exc])

        results = manifest_manager.apply_manifests([valid_manifest])

        assert len(results) == 1
        assert results[0].success is False
        assert "Forbidden" in results[0].message

    def test_apply_with_namespace_override(
        self,
        manifest_manager: ManifestManager,
        valid_manifest: dict[str, object],
    ) -> None:
        """Client dry run with namespace should set namespace in result."""
        results = manifest_manager.apply_manifests(
            [valid_manifest], namespace="staging", dry_run=True
        )

        assert results[0].namespace == "staging"

    @patch("kubernetes.utils.create_from_dict")
    def test_apply_server_dry_run(
        self,
        mock_create: MagicMock,
        manifest_manager: ManifestManager,
        valid_manifest: dict[str, object],
    ) -> None:
        """Server dry run should call API with dry_run parameter."""
        mock_create.return_value = None

        results = manifest_manager.apply_manifests([valid_manifest], server_dry_run=True)

        assert len(results) == 1
        assert results[0].success is True
        assert "server dry-run" in results[0].action

    @patch("kubernetes.utils.create_from_dict")
    def test_apply_partial_failure(
        self,
        mock_create: MagicMock,
        manifest_manager: ManifestManager,
        valid_manifest: dict[str, object],
    ) -> None:
        """Should handle partial failures (some succeed, some fail)."""
        manifest_2: dict[str, object] = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {"name": "cfg"},
        }

        # First call succeeds, second fails
        mock_create.side_effect = [
            None,
            Exception("Connection reset"),
        ]

        results = manifest_manager.apply_manifests([valid_manifest, manifest_2])

        assert len(results) == 2
        assert results[0].success is True
        assert results[1].success is False


# ===========================================================================
# TestDiffManifests
# ===========================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestDiffManifests:
    """Tests for ManifestManager.diff_manifests."""

    @patch(
        "system_operations_manager.services.kubernetes.manifest_manager.ManifestManager._get_dynamic_client"
    )
    def test_diff_resource_not_on_cluster(
        self,
        mock_dynamic: MagicMock,
        manifest_manager: ManifestManager,
        valid_manifest: dict[str, object],
    ) -> None:
        """Should mark resource as new when not found on cluster."""
        from kubernetes.client import ApiException

        mock_resource_api = MagicMock()
        mock_resource_api.get.side_effect = ApiException(status=404, reason="Not Found")
        mock_dynamic.return_value.resources.get.return_value = mock_resource_api

        results = manifest_manager.diff_manifests([valid_manifest])

        assert len(results) == 1
        assert results[0].exists_on_cluster is False
        assert results[0].identical is False

    @patch(
        "system_operations_manager.services.kubernetes.manifest_manager.ManifestManager._get_dynamic_client"
    )
    def test_diff_resource_identical(
        self,
        mock_dynamic: MagicMock,
        manifest_manager: ManifestManager,
        valid_manifest: dict[str, object],
    ) -> None:
        """Should detect identical resources."""
        # Return the same manifest as the live resource
        mock_live = MagicMock()
        mock_live.to_dict.return_value = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {"name": "test-app", "namespace": "default"},
            "spec": {"replicas": 1},
        }
        mock_resource_api = MagicMock()
        mock_resource_api.get.return_value = mock_live
        mock_dynamic.return_value.resources.get.return_value = mock_resource_api

        results = manifest_manager.diff_manifests([valid_manifest])

        assert len(results) == 1
        assert results[0].exists_on_cluster is True
        assert results[0].identical is True

    @patch(
        "system_operations_manager.services.kubernetes.manifest_manager.ManifestManager._get_dynamic_client"
    )
    def test_diff_resource_changed(
        self,
        mock_dynamic: MagicMock,
        manifest_manager: ManifestManager,
        valid_manifest: dict[str, object],
    ) -> None:
        """Should show diff when resources differ."""
        mock_live = MagicMock()
        mock_live.to_dict.return_value = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {"name": "test-app", "namespace": "default"},
            "spec": {"replicas": 3},  # Different from local (1)
        }
        mock_resource_api = MagicMock()
        mock_resource_api.get.return_value = mock_live
        mock_dynamic.return_value.resources.get.return_value = mock_resource_api

        results = manifest_manager.diff_manifests([valid_manifest])

        assert len(results) == 1
        assert results[0].exists_on_cluster is True
        assert results[0].identical is False
        assert results[0].diff != ""

    @patch(
        "system_operations_manager.services.kubernetes.manifest_manager.ManifestManager._get_dynamic_client"
    )
    def test_diff_strips_server_fields(
        self,
        mock_dynamic: MagicMock,
        manifest_manager: ManifestManager,
        valid_manifest: dict[str, object],
    ) -> None:
        """Should strip server-managed fields before diffing."""
        mock_live = MagicMock()
        mock_live.to_dict.return_value = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": "test-app",
                "namespace": "default",
                "uid": "abc-123",
                "resourceVersion": "12345",
                "creationTimestamp": "2024-01-01T00:00:00Z",
                "managedFields": [{"manager": "kubectl"}],
                "generation": 1,
            },
            "spec": {"replicas": 1},
            "status": {"readyReplicas": 1},
        }
        mock_resource_api = MagicMock()
        mock_resource_api.get.return_value = mock_live
        mock_dynamic.return_value.resources.get.return_value = mock_resource_api

        results = manifest_manager.diff_manifests([valid_manifest])

        assert len(results) == 1
        # After stripping server fields, should be identical
        assert results[0].identical is True

    @patch(
        "system_operations_manager.services.kubernetes.manifest_manager.ManifestManager._get_dynamic_client"
    )
    def test_diff_with_namespace_override(
        self,
        mock_dynamic: MagicMock,
        manifest_manager: ManifestManager,
        valid_manifest: dict[str, object],
    ) -> None:
        """Should use overridden namespace for cluster lookup."""
        mock_live = MagicMock()
        mock_live.to_dict.return_value = dict(valid_manifest)
        mock_resource_api = MagicMock()
        mock_resource_api.get.return_value = mock_live
        mock_dynamic.return_value.resources.get.return_value = mock_resource_api

        results = manifest_manager.diff_manifests([valid_manifest], namespace="staging")

        assert results[0].namespace == "staging"
        mock_resource_api.get.assert_called_once_with(name="test-app", namespace="staging")
