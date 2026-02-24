"""Unit tests for ManifestManager."""

from __future__ import annotations

from pathlib import Path
from typing import Any
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


# ===========================================================================
# TestLoadManifestsEdgeCases
# ===========================================================================


@pytest.mark.unit
class TestLoadManifestsEdgeCases:
    """Tests for uncovered branches in load_manifests and _load_file."""

    def test_load_empty_directory_returns_empty_list(
        self, manifest_manager: ManifestManager, tmp_path: Path
    ) -> None:
        """Should log a warning and return [] when a directory has no YAML files.

        Covers lines 126-127 in manifest_manager.py.
        """
        # tmp_path exists and is a directory but has no .yaml/.yml files
        (tmp_path / "notes.txt").write_text("not yaml")

        result = manifest_manager.load_manifests(tmp_path)

        assert result == []

    def test_load_path_not_file_or_directory_raises(
        self, manifest_manager: ManifestManager, tmp_path: Path
    ) -> None:
        """Should raise FileNotFoundError for paths that are neither file nor dir.

        Covers line 132 in manifest_manager.py.
        """
        # Patch Path.is_file and Path.is_dir to both return False while exists() is True
        real_path = tmp_path / "fake_special"

        with (
            patch.object(type(real_path), "exists", return_value=True),
            patch.object(type(real_path), "is_file", return_value=False),
            patch.object(type(real_path), "is_dir", return_value=False),
            pytest.raises(FileNotFoundError, match="neither a file nor a directory"),
        ):
            manifest_manager.load_manifests(real_path)

    def test_load_file_invalid_yaml_raises_value_error(
        self, manifest_manager: ManifestManager, tmp_path: Path
    ) -> None:
        """Should raise ValueError when a YAML file cannot be parsed.

        Covers lines 146-147 in manifest_manager.py.
        """
        bad_yaml = tmp_path / "bad.yaml"
        # Tabs are invalid YAML indentation and trigger a YAMLError
        bad_yaml.write_text("key:\n\t- item\n")

        with pytest.raises(ValueError, match="Failed to parse YAML file"):
            manifest_manager.load_manifests(bad_yaml)

    def test_load_file_skips_non_dict_documents(
        self, manifest_manager: ManifestManager, tmp_path: Path
    ) -> None:
        """Should skip non-dict YAML documents and log a warning.

        Covers lines 154-159 in manifest_manager.py.
        """
        # A bare scalar or list at the top level is valid YAML but not a dict
        manifest_file = tmp_path / "mixed.yaml"
        manifest_file.write_text(
            "- item1\n- item2\n---\napiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: cfg\n"
        )

        result = manifest_manager.load_manifests(manifest_file)

        # The list document should be skipped; only the dict document is kept
        assert len(result) == 1
        assert result[0]["kind"] == "ConfigMap"


# ===========================================================================
# TestValidateManifestsEdgeCases
# ===========================================================================


@pytest.mark.unit
class TestValidateManifestsEdgeCases:
    """Tests for uncovered type-validation branches in _validate_single."""

    def test_validate_api_version_not_string(self, manifest_manager: ManifestManager) -> None:
        """Should report error when apiVersion is not a string.

        Covers line 219 in manifest_manager.py.
        """
        manifest: dict[str, Any] = {
            "apiVersion": 42,
            "kind": "ConfigMap",
            "metadata": {"name": "cfg"},
        }

        results = manifest_manager.validate_manifests([manifest])

        assert results[0].valid is False
        assert any("apiVersion must be a string" in e for e in results[0].errors)

    def test_validate_kind_not_string(self, manifest_manager: ManifestManager) -> None:
        """Should report error when kind is not a string.

        Covers line 223 in manifest_manager.py.
        """
        manifest: dict[str, Any] = {
            "apiVersion": "v1",
            "kind": 99,
            "metadata": {"name": "cfg"},
        }

        results = manifest_manager.validate_manifests([manifest])

        assert results[0].valid is False
        assert any("kind must be a string" in e for e in results[0].errors)

    def test_validate_metadata_name_not_string(self, manifest_manager: ManifestManager) -> None:
        """Should report error when metadata.name is not a string.

        Covers line 230 in manifest_manager.py.
        """
        manifest: dict[str, Any] = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {"name": 123},
        }

        results = manifest_manager.validate_manifests([manifest])

        assert results[0].valid is False
        assert any("metadata.name must be a string" in e for e in results[0].errors)

    def test_validate_metadata_not_dict(self, manifest_manager: ManifestManager) -> None:
        """Should report error when metadata is present but not a dict.

        Covers line 232 in manifest_manager.py.

        Note: _get_resource_identifier calls .get() on the metadata value, so
        a plain string would raise AttributeError before validation runs.
        We use a MagicMock (which supports .get()) to allow the code to reach
        the isinstance check on line 231 and the error-append on line 232.
        """
        fake_metadata: Any = MagicMock(spec=[])  # no spec attributes - not a dict
        # Make manifest.get("metadata", {}) return fake_metadata
        # and fake_metadata.get("name", "unnamed") return "unnamed" so
        # _get_resource_identifier can build the resource id string
        fake_metadata.get = MagicMock(return_value="unnamed")

        manifest: dict[str, Any] = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": fake_metadata,
        }

        results = manifest_manager.validate_manifests([manifest])

        assert results[0].valid is False
        assert any("metadata must be a dict" in e for e in results[0].errors)

    def test_validate_uses_source_file_from_manifest(
        self, manifest_manager: ManifestManager
    ) -> None:
        """Should use _source_file metadata as the file label in the result."""
        manifest: dict[str, Any] = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {"name": "cfg"},
            "_source_file": "/path/to/manifest.yaml",
        }

        results = manifest_manager.validate_manifests([manifest])

        assert results[0].file == "/path/to/manifest.yaml"


# ===========================================================================
# TestApplyManifestsNamespaceOverride
# ===========================================================================


@pytest.mark.unit
class TestApplyManifestsNamespaceOverride:
    """Tests for namespace-override branch in apply_manifests (line 299)."""

    @patch("kubernetes.utils.create_from_dict")
    def test_apply_with_namespace_override_sets_metadata_namespace(
        self,
        mock_create: MagicMock,
        manifest_manager: ManifestManager,
    ) -> None:
        """Should mutate clean metadata.namespace when namespace override is provided.

        Covers line 299 in manifest_manager.py.
        """
        mock_create.return_value = None
        manifest: dict[str, Any] = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {"name": "cfg"},
        }

        results = manifest_manager.apply_manifests([manifest], namespace="production")

        assert len(results) == 1
        assert results[0].success is True
        # Verify that create_from_dict was called (namespace was set in clean copy)
        mock_create.assert_called_once()


# ===========================================================================
# TestApplySingleApiException
# ===========================================================================


@pytest.mark.unit
class TestApplySingleApiException:
    """Tests for ApiException branch in _apply_single (lines 361-362)."""

    @patch("kubernetes.utils.create_from_dict")
    def test_apply_single_handles_api_exception(
        self,
        mock_create: MagicMock,
        manifest_manager: ManifestManager,
        valid_manifest: dict[str, object],
    ) -> None:
        """Should capture ApiException (not FailToCreateError) as a failed result.

        Covers lines 361-362 in manifest_manager.py.
        """
        from kubernetes.client import ApiException

        mock_create.side_effect = ApiException(status=500, reason="Internal Server Error")

        results = manifest_manager.apply_manifests([valid_manifest])

        assert len(results) == 1
        assert results[0].success is False
        assert results[0].action == "failed"
        assert "Internal Server Error" in results[0].message


# ===========================================================================
# TestServerSideApply
# ===========================================================================


@pytest.mark.unit
class TestServerSideApply:
    """Tests for _server_side_apply (lines 388-417)."""

    @patch(
        "system_operations_manager.services.kubernetes.manifest_manager.ManifestManager._get_dynamic_client"
    )
    def test_server_side_apply_success(
        self,
        mock_get_dynamic: MagicMock,
        manifest_manager: ManifestManager,
        valid_manifest: dict[str, object],
    ) -> None:
        """Should return a successful 'configured' result on server-side apply.

        Covers lines 388-414 (success path) in manifest_manager.py.
        """
        mock_resource_api: Any = MagicMock()
        mock_resource_api.server_side_apply.return_value = MagicMock()
        dynamic_client: Any = MagicMock()
        dynamic_client.resources.get.return_value = mock_resource_api
        mock_get_dynamic.return_value = dynamic_client

        manifest: dict[str, Any] = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {"name": "test-app", "namespace": "default"},
            "spec": {"replicas": 1},
        }
        result = manifest_manager._server_side_apply(
            manifest, "default", "Deployment/test-app", dry_run_strategy=None
        )

        assert result.success is True
        assert result.action == "configured"
        mock_resource_api.server_side_apply.assert_called_once()

    @patch(
        "system_operations_manager.services.kubernetes.manifest_manager.ManifestManager._get_dynamic_client"
    )
    def test_server_side_apply_with_dry_run_strategy(
        self,
        mock_get_dynamic: MagicMock,
        manifest_manager: ManifestManager,
    ) -> None:
        """Should include dry_run kwarg and label action accordingly.

        Covers the dry_run_strategy branch inside _server_side_apply.
        """
        mock_resource_api: Any = MagicMock()
        mock_resource_api.server_side_apply.return_value = MagicMock()
        dynamic_client: Any = MagicMock()
        dynamic_client.resources.get.return_value = mock_resource_api
        mock_get_dynamic.return_value = dynamic_client

        manifest: dict[str, Any] = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {"name": "cfg"},
        }
        result = manifest_manager._server_side_apply(
            manifest, "default", "ConfigMap/cfg", dry_run_strategy="All"
        )

        assert result.success is True
        assert "server dry-run" in result.action
        call_kwargs: Any = mock_resource_api.server_side_apply.call_args.kwargs
        assert call_kwargs.get("dry_run") == "All"

    @patch(
        "system_operations_manager.services.kubernetes.manifest_manager.ManifestManager._get_dynamic_client"
    )
    def test_server_side_apply_exception_returns_failed(
        self,
        mock_get_dynamic: MagicMock,
        manifest_manager: ManifestManager,
    ) -> None:
        """Should return a failed ApplyResult when server-side apply raises.

        Covers lines 415-417 (exception path) in manifest_manager.py.
        """
        dynamic_client: Any = MagicMock()
        dynamic_client.resources.get.side_effect = RuntimeError("dynamic client error")
        mock_get_dynamic.return_value = dynamic_client

        manifest: dict[str, Any] = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {"name": "broken"},
        }
        result = manifest_manager._server_side_apply(
            manifest, "default", "Deployment/broken", dry_run_strategy=None
        )

        assert result.success is False
        assert result.action == "failed"
        assert "dynamic client error" in result.message

    @patch(
        "system_operations_manager.services.kubernetes.manifest_manager.ManifestManager._get_dynamic_client"
    )
    @patch("kubernetes.utils.create_from_dict")
    def test_apply_manifests_triggers_server_side_apply_on_conflict(
        self,
        mock_create: MagicMock,
        mock_get_dynamic: MagicMock,
        manifest_manager: ManifestManager,
        valid_manifest: dict[str, object],
    ) -> None:
        """Should invoke _server_side_apply end-to-end on 409 Conflict.

        Covers the full integration of apply_manifests -> _apply_single ->
        _server_side_apply for the success path.
        """
        from kubernetes import utils

        mock_api_exc: Any = MagicMock()
        mock_api_exc.status = 409
        mock_create.side_effect = utils.FailToCreateError([mock_api_exc])

        mock_resource_api: Any = MagicMock()
        mock_resource_api.server_side_apply.return_value = MagicMock()
        dynamic_client: Any = MagicMock()
        dynamic_client.resources.get.return_value = mock_resource_api
        mock_get_dynamic.return_value = dynamic_client

        results = manifest_manager.apply_manifests([valid_manifest])

        assert len(results) == 1
        assert results[0].success is True
        assert results[0].action == "configured"
        mock_resource_api.server_side_apply.assert_called_once()


# ===========================================================================
# TestDiffSingleErrorBranches
# ===========================================================================


@pytest.mark.unit
class TestDiffSingleErrorBranches:
    """Tests for non-404 ApiException and generic Exception in _diff_single."""

    @patch(
        "system_operations_manager.services.kubernetes.manifest_manager.ManifestManager._get_dynamic_client"
    )
    def test_diff_non_404_api_exception_returns_error_result(
        self,
        mock_dynamic: MagicMock,
        manifest_manager: ManifestManager,
        valid_manifest: dict[str, object],
    ) -> None:
        """Should return a DiffResult with error message for non-404 ApiException.

        Covers lines 486-493 in manifest_manager.py.
        """
        from kubernetes.client import ApiException

        mock_resource_api: Any = MagicMock()
        mock_resource_api.get.side_effect = ApiException(status=403, reason="Forbidden")
        dynamic_client: Any = MagicMock()
        dynamic_client.resources.get.return_value = mock_resource_api
        mock_dynamic.return_value = dynamic_client

        results = manifest_manager.diff_manifests([valid_manifest])

        assert len(results) == 1
        result = results[0]
        assert result.exists_on_cluster is False
        assert result.identical is False
        assert "Forbidden" in result.diff

    @patch(
        "system_operations_manager.services.kubernetes.manifest_manager.ManifestManager._get_dynamic_client"
    )
    def test_diff_generic_exception_returns_error_result(
        self,
        mock_dynamic: MagicMock,
        manifest_manager: ManifestManager,
        valid_manifest: dict[str, object],
    ) -> None:
        """Should return a DiffResult with error message for unexpected exceptions.

        Covers lines 494-496 in manifest_manager.py.
        """
        mock_resource_api: Any = MagicMock()
        mock_resource_api.get.side_effect = RuntimeError("unexpected failure")
        dynamic_client: Any = MagicMock()
        dynamic_client.resources.get.return_value = mock_resource_api
        mock_dynamic.return_value = dynamic_client

        results = manifest_manager.diff_manifests([valid_manifest])

        assert len(results) == 1
        result = results[0]
        assert result.exists_on_cluster is False
        assert result.identical is False
        assert "unexpected failure" in result.diff


# ===========================================================================
# TestGetDynamicClient
# ===========================================================================


@pytest.mark.unit
class TestGetDynamicClient:
    """Tests for _get_dynamic_client (lines 556-559)."""

    def test_get_dynamic_client_creates_dynamic_client(
        self,
        manifest_manager: ManifestManager,
    ) -> None:
        """Should construct and return a DynamicClient wrapping a fresh ApiClient.

        Covers lines 556-559 in manifest_manager.py.
        """
        with (
            patch("kubernetes.client.ApiClient") as mock_api_cls,
            patch("kubernetes.dynamic.DynamicClient") as mock_dyn_cls,
        ):
            mock_api_instance: Any = MagicMock()
            mock_api_cls.return_value = mock_api_instance
            mock_dynamic_instance: Any = MagicMock()
            mock_dyn_cls.return_value = mock_dynamic_instance

            result = manifest_manager._get_dynamic_client()

        mock_dyn_cls.assert_called_once_with(mock_api_instance)
        assert result is mock_dynamic_instance
