"""Unit tests for MultiClusterManager."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from system_operations_manager.services.kubernetes.manifest_manager import ApplyResult
from system_operations_manager.services.kubernetes.multicluster_manager import (
    MultiClusterManager,
)


@pytest.fixture
def mock_k8s_client() -> MagicMock:
    """Create a mock Kubernetes client with configured clusters."""
    client = MagicMock()
    client.get_current_context.return_value = "original-ctx"
    client._config.clusters = {
        "staging": MagicMock(context="staging-ctx", namespace="default", timeout=300),
        "production": MagicMock(context="prod-ctx", namespace="prod-ns", timeout=300),
    }
    return client


@pytest.fixture
def manager(mock_k8s_client: MagicMock) -> MultiClusterManager:
    """Create a MultiClusterManager with a mocked client."""
    return MultiClusterManager(mock_k8s_client)


# ===========================================================================
# TestGetClusterNames
# ===========================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestGetClusterNames:
    """Tests for MultiClusterManager.get_cluster_names."""

    def test_returns_configured_names(self, manager: MultiClusterManager) -> None:
        """Should return list of all configured cluster names."""
        result = manager.get_cluster_names()

        assert result == ["staging", "production"]

    def test_empty_when_no_clusters(
        self, manager: MultiClusterManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should return empty list when no clusters configured."""
        mock_k8s_client._config.clusters = {}

        result = manager.get_cluster_names()

        assert result == []


# ===========================================================================
# TestResolveClusters
# ===========================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestResolveClusters:
    """Tests for MultiClusterManager._resolve_clusters."""

    def test_returns_all_when_none(self, manager: MultiClusterManager) -> None:
        """Should return all configured clusters when None is passed."""
        result = manager._resolve_clusters(None)

        assert set(result) == {"staging", "production"}

    def test_returns_specified(self, manager: MultiClusterManager) -> None:
        """Should return only the specified clusters."""
        result = manager._resolve_clusters(["staging"])

        assert result == ["staging"]

    def test_raises_for_unknown(self, manager: MultiClusterManager) -> None:
        """Should raise ValueError for unknown cluster names."""
        with pytest.raises(ValueError, match="Unknown clusters: unknown"):
            manager._resolve_clusters(["unknown"])

    def test_raises_when_no_clusters(
        self, manager: MultiClusterManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should raise ValueError when no clusters are configured."""
        mock_k8s_client._config.clusters = {}

        with pytest.raises(ValueError, match="No clusters configured"):
            manager._resolve_clusters(None)


# ===========================================================================
# TestMultiClusterStatus
# ===========================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestMultiClusterStatus:
    """Tests for MultiClusterManager.multi_cluster_status."""

    def test_status_all_connected(
        self, manager: MultiClusterManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should report all clusters as connected when reachable."""
        # Mock successful connections
        mock_k8s_client.check_connection.return_value = True
        mock_k8s_client.get_cluster_version.return_value = "v1.28.0"

        # Mock node list with 3 nodes
        mock_nodes = MagicMock()
        mock_nodes.items = [MagicMock(), MagicMock(), MagicMock()]
        mock_k8s_client.core_v1.list_node.return_value = mock_nodes

        result = manager.multi_cluster_status()

        assert result.total == 2
        assert result.connected == 2
        assert result.disconnected == 0
        assert len(result.clusters) == 2

        # Verify all clusters are marked as connected
        for cluster_status in result.clusters:
            assert cluster_status.connected is True
            assert cluster_status.version == "v1.28.0"
            assert cluster_status.node_count == 3

    def test_status_partial_failure(
        self, manager: MultiClusterManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle partial failures when one cluster is unreachable."""

        # First cluster connects, second cluster fails
        def switch_context_side_effect(cluster_name: str) -> None:
            if cluster_name == "production":
                raise ConnectionError("Connection refused")

        mock_k8s_client.switch_context.side_effect = switch_context_side_effect
        mock_k8s_client.check_connection.return_value = True
        mock_k8s_client.get_cluster_version.return_value = "v1.28.0"

        mock_nodes = MagicMock()
        mock_nodes.items = [MagicMock(), MagicMock()]
        mock_k8s_client.core_v1.list_node.return_value = mock_nodes

        result = manager.multi_cluster_status()

        assert result.total == 2
        assert result.connected == 1
        assert result.disconnected == 1

        # Verify staging succeeded
        staging_status = next(s for s in result.clusters if s.cluster == "staging")
        assert staging_status.connected is True

        # Verify production failed
        prod_status = next(s for s in result.clusters if s.cluster == "production")
        assert prod_status.connected is False
        assert prod_status.error is not None
        assert "Failed to switch context" in prod_status.error

    def test_context_restored(
        self, manager: MultiClusterManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should restore original context after status check."""
        mock_k8s_client.check_connection.return_value = True
        mock_k8s_client.get_cluster_version.return_value = "v1.28.0"
        mock_nodes = MagicMock()
        mock_nodes.items = []
        mock_k8s_client.core_v1.list_node.return_value = mock_nodes

        # Reset switch_context to track calls
        mock_k8s_client.switch_context.reset_mock()

        manager.multi_cluster_status()

        # Verify that switch_context was called to restore original context
        switch_calls = [call[0][0] for call in mock_k8s_client.switch_context.call_args_list]
        assert "original-ctx" in switch_calls


# ===========================================================================
# TestDeployManifestsToClusters
# ===========================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestDeployManifestsToClusters:
    """Tests for MultiClusterManager.deploy_manifests_to_clusters."""

    @patch("system_operations_manager.services.kubernetes.multicluster_manager.ManifestManager")
    def test_deploy_success(
        self,
        MockManifestManager: MagicMock,
        manager: MultiClusterManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """Should successfully deploy manifests to all clusters."""
        # Setup mock ManifestManager
        mock_manifest_mgr = MagicMock()
        MockManifestManager.return_value = mock_manifest_mgr
        mock_manifest_mgr.apply_manifests.return_value = [
            ApplyResult(
                resource="ConfigMap/test-config",
                action="created",
                namespace="default",
                success=True,
                message="",
            ),
            ApplyResult(
                resource="Deployment/test-app",
                action="configured",
                namespace="default",
                success=True,
                message="",
            ),
        ]

        manifests = [
            {"apiVersion": "v1", "kind": "ConfigMap", "metadata": {"name": "test-config"}},
            {"apiVersion": "apps/v1", "kind": "Deployment", "metadata": {"name": "test-app"}},
        ]

        result = manager.deploy_manifests_to_clusters(manifests)

        assert result.total_clusters == 2
        assert result.successful == 2
        assert result.failed == 0

        # Verify each cluster result
        for cluster_result in result.cluster_results:
            assert cluster_result.success is True
            assert cluster_result.resources_applied == 2
            assert cluster_result.resources_failed == 0

    @patch("system_operations_manager.services.kubernetes.multicluster_manager.ManifestManager")
    def test_deploy_context_switch_failure(
        self,
        MockManifestManager: MagicMock,
        manager: MultiClusterManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """Should handle context switch failures gracefully."""

        # First cluster OK, second cluster fails to switch
        def switch_context_side_effect(cluster_name: str) -> None:
            if cluster_name == "production":
                raise RuntimeError("Context switch failed")

        mock_k8s_client.switch_context.side_effect = switch_context_side_effect

        mock_manifest_mgr = MagicMock()
        MockManifestManager.return_value = mock_manifest_mgr
        mock_manifest_mgr.apply_manifests.return_value = [
            ApplyResult(
                resource="ConfigMap/test",
                action="created",
                namespace="default",
                success=True,
                message="",
            )
        ]

        manifests = [{"apiVersion": "v1", "kind": "ConfigMap", "metadata": {"name": "test"}}]

        result = manager.deploy_manifests_to_clusters(manifests)

        assert result.total_clusters == 2
        assert result.successful == 1
        assert result.failed == 1

        # Verify staging succeeded
        staging_result = next(r for r in result.cluster_results if r.cluster == "staging")
        assert staging_result.success is True

        # Verify production failed
        prod_result = next(r for r in result.cluster_results if r.cluster == "production")
        assert prod_result.success is False
        assert prod_result.error is not None
        assert "Failed to switch context" in prod_result.error

    @patch("system_operations_manager.services.kubernetes.multicluster_manager.ManifestManager")
    def test_deploy_dry_run(
        self,
        MockManifestManager: MagicMock,
        manager: MultiClusterManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """Should pass dry_run flag to ManifestManager."""
        mock_manifest_mgr = MagicMock()
        MockManifestManager.return_value = mock_manifest_mgr
        mock_manifest_mgr.apply_manifests.return_value = [
            ApplyResult(
                resource="ConfigMap/test",
                action="dry-run",
                namespace="default",
                success=True,
                message="",
            )
        ]

        manifests = [{"apiVersion": "v1", "kind": "ConfigMap", "metadata": {"name": "test"}}]

        manager.deploy_manifests_to_clusters(manifests, dry_run=True)

        # Verify dry_run was passed to apply_manifests for each cluster
        for call in mock_manifest_mgr.apply_manifests.call_args_list:
            assert call.kwargs["dry_run"] is True


# ===========================================================================
# TestSyncResource
# ===========================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestSyncResource:
    """Tests for MultiClusterManager.sync_resource."""

    @patch("system_operations_manager.services.kubernetes.multicluster_manager.ManifestManager")
    def test_sync_success(
        self,
        MockManifestManager: MagicMock,
        manager: MultiClusterManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """Should successfully sync resource from source to target clusters."""
        # Mock dynamic client and resource reading
        mock_dynamic = MagicMock()
        mock_resource_api = MagicMock()
        mock_dynamic.resources = [mock_resource_api]
        mock_resource_api.kind = "ConfigMap"

        mock_live_obj = MagicMock()
        mock_live_obj.to_dict.return_value = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {
                "name": "test-config",
                "namespace": "default",
                "uid": "abc123",
                "resourceVersion": "12345",
            },
            "data": {"key": "value"},
        }
        mock_resource_api.get.return_value = mock_live_obj

        with patch.object(manager, "_get_dynamic_client", return_value=mock_dynamic):
            # Mock ManifestManager for apply
            mock_manifest_mgr = MagicMock()
            MockManifestManager.return_value = mock_manifest_mgr
            mock_manifest_mgr.apply_manifests.return_value = [
                ApplyResult(
                    resource="ConfigMap/test-config",
                    action="configured",
                    namespace="default",
                    success=True,
                    message="",
                )
            ]

            result = manager.sync_resource(
                source_cluster="staging",
                target_clusters=["production"],
                resource_type="ConfigMap",
                resource_name="test-config",
                namespace="default",
            )

            assert result.source_cluster == "staging"
            assert result.resource_type == "ConfigMap"
            assert result.resource_name == "test-config"
            assert result.total_targets == 1
            assert result.successful == 1
            assert result.failed == 0

    def test_sync_source_read_fails(
        self, manager: MultiClusterManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should mark all targets as failed when source read fails."""

        # Make source cluster switch fail
        def switch_context_side_effect(cluster_name: str) -> None:
            if cluster_name == "staging":
                raise ConnectionError("Source cluster unreachable")

        mock_k8s_client.switch_context.side_effect = switch_context_side_effect

        result = manager.sync_resource(
            source_cluster="staging",
            target_clusters=["production"],
            resource_type="ConfigMap",
            resource_name="test-config",
            namespace="default",
        )

        assert result.total_targets == 1
        assert result.successful == 0
        assert result.failed == 1

        # Verify production was marked as failed
        prod_result = result.cluster_results[0]
        assert prod_result.cluster == "production"
        assert prod_result.success is False
        assert prod_result.error is not None
        assert "Failed to read" in prod_result.error


# ===========================================================================
# TestLoadManifestsFromString
# ===========================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestLoadManifestsFromString:
    """Tests for MultiClusterManager.load_manifests_from_string."""

    def test_parses_single_document(self, manager: MultiClusterManager) -> None:
        """Should parse a single YAML document."""
        yaml_content = """
apiVersion: v1
kind: ConfigMap
metadata:
  name: test-config
data:
  key: value
"""
        result = manager.load_manifests_from_string(yaml_content)

        assert len(result) == 1
        assert result[0]["kind"] == "ConfigMap"
        assert result[0]["metadata"]["name"] == "test-config"
        assert result[0]["_source_file"] == "<stdin>"

    def test_parses_multi_document(self, manager: MultiClusterManager) -> None:
        """Should parse multi-document YAML separated by ---."""
        yaml_content = """
apiVersion: v1
kind: ConfigMap
metadata:
  name: config1
---
apiVersion: v1
kind: Secret
metadata:
  name: secret1
"""
        result = manager.load_manifests_from_string(yaml_content)

        assert len(result) == 2
        assert result[0]["kind"] == "ConfigMap"
        assert result[0]["metadata"]["name"] == "config1"
        assert result[1]["kind"] == "Secret"
        assert result[1]["metadata"]["name"] == "secret1"

    def test_invalid_yaml_raises(self, manager: MultiClusterManager) -> None:
        """Should raise ValueError for invalid YAML."""
        invalid_yaml = """
apiVersion: v1
kind: ConfigMap
metadata:
  name: [invalid yaml structure
"""
        with pytest.raises(ValueError, match="Failed to parse YAML"):
            manager.load_manifests_from_string(invalid_yaml)


# ===========================================================================
# TestLoadManifestsFromStringEdgeCases
# ===========================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestLoadManifestsFromStringEdgeCases:
    """Tests for edge cases in load_manifests_from_string (None and non-dict docs)."""

    def test_skips_null_documents(self, manager: MultiClusterManager) -> None:
        """Should skip null YAML documents (e.g., trailing ---)."""
        yaml_content = """
apiVersion: v1
kind: ConfigMap
metadata:
  name: real-config
---
"""
        result = manager.load_manifests_from_string(yaml_content)

        assert len(result) == 1
        assert result[0]["kind"] == "ConfigMap"

    def test_skips_non_dict_documents(self, manager: MultiClusterManager) -> None:
        """Should skip non-dict YAML documents such as plain lists."""
        yaml_content = """
- item1
- item2
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: valid-config
"""
        result = manager.load_manifests_from_string(yaml_content)

        assert len(result) == 1
        assert result[0]["kind"] == "ConfigMap"

    def test_all_null_documents_returns_empty(self, manager: MultiClusterManager) -> None:
        """Should return empty list when all documents are null."""
        yaml_content = "---\n---\n---"

        result = manager.load_manifests_from_string(yaml_content)

        assert result == []


# ===========================================================================
# TestLoadManifestsFromPath
# ===========================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestLoadManifestsFromPath:
    """Tests for MultiClusterManager.load_manifests_from_path."""

    @patch("system_operations_manager.services.kubernetes.multicluster_manager.ManifestManager")
    def test_delegates_to_manifest_manager(
        self,
        MockManifestManager: MagicMock,
        manager: MultiClusterManager,
    ) -> None:
        """Should delegate path loading to ManifestManager.load_manifests."""
        from pathlib import Path

        mock_manifest_mgr = MagicMock()
        MockManifestManager.return_value = mock_manifest_mgr
        expected = [{"apiVersion": "v1", "kind": "ConfigMap", "metadata": {"name": "cfg"}}]
        mock_manifest_mgr.load_manifests.return_value = expected

        test_path = Path("/some/manifest.yaml")
        result = manager.load_manifests_from_path(test_path)

        MockManifestManager.assert_called_once_with(manager._client)
        mock_manifest_mgr.load_manifests.assert_called_once_with(test_path)
        assert result == expected


# ===========================================================================
# TestSaveAndRestoreContextFailure
# ===========================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestSaveAndRestoreContextFailure:
    """Tests for _save_and_restore_context when restoring the context fails."""

    def test_restore_failure_is_suppressed(
        self, manager: MultiClusterManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should log a warning and not propagate when context restore fails."""
        mock_k8s_client.check_connection.return_value = True
        mock_k8s_client.get_cluster_version.return_value = "v1.28.0"
        mock_nodes = MagicMock()
        mock_nodes.items = []
        mock_k8s_client.core_v1.list_node.return_value = mock_nodes

        # Make switch_context raise only when restoring the original context
        original_ctx = "original-ctx"

        def switch_side_effect(ctx: str) -> None:
            if ctx == original_ctx:
                raise RuntimeError("Cannot restore context")

        mock_k8s_client.switch_context.side_effect = switch_side_effect

        # Should complete without raising even though restore fails
        result = manager.multi_cluster_status()

        assert result.total == 2

    def test_restore_skipped_when_context_unknown(
        self, manager: MultiClusterManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should not attempt to restore context when original context is 'unknown'."""
        mock_k8s_client.get_current_context.return_value = "unknown"
        mock_k8s_client.check_connection.return_value = True
        mock_k8s_client.get_cluster_version.return_value = "v1.29.0"
        mock_nodes = MagicMock()
        mock_nodes.items = []
        mock_k8s_client.core_v1.list_node.return_value = mock_nodes

        manager.multi_cluster_status()

        # switch_context should only have been called for cluster names, not "unknown"
        switch_calls = [call[0][0] for call in mock_k8s_client.switch_context.call_args_list]
        assert "unknown" not in switch_calls

    def test_restore_skipped_when_context_is_none(
        self, manager: MultiClusterManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should not attempt to restore context when original context is None."""
        mock_k8s_client.get_current_context.return_value = None
        mock_k8s_client.check_connection.return_value = True
        mock_k8s_client.get_cluster_version.return_value = "v1.29.0"
        mock_nodes = MagicMock()
        mock_nodes.items = []
        mock_k8s_client.core_v1.list_node.return_value = mock_nodes

        manager.multi_cluster_status()

        switch_calls = [call[0][0] for call in mock_k8s_client.switch_context.call_args_list]
        assert None not in switch_calls


# ===========================================================================
# TestGetSingleClusterStatusEdgeCases
# ===========================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestGetSingleClusterStatusEdgeCases:
    """Tests for edge cases in _get_single_cluster_status."""

    def test_disconnected_when_check_connection_fails(
        self, manager: MultiClusterManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should return disconnected status when check_connection returns False."""
        mock_k8s_client.check_connection.return_value = False

        result = manager._get_single_cluster_status("staging")

        assert result.connected is False
        assert result.cluster == "staging"
        assert result.error == "Cluster unreachable"

    def test_node_list_exception_is_suppressed(
        self, manager: MultiClusterManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should return connected status with None node_count when list_node raises."""
        mock_k8s_client.check_connection.return_value = True
        mock_k8s_client.get_cluster_version.return_value = "v1.28.0"
        mock_k8s_client.core_v1.list_node.side_effect = Exception("API error")

        result = manager._get_single_cluster_status("staging")

        assert result.connected is True
        assert result.node_count is None

    def test_empty_node_list_returns_zero_count(
        self, manager: MultiClusterManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should return node_count=0 when nodes.items is empty/falsy."""
        mock_k8s_client.check_connection.return_value = True
        mock_k8s_client.get_cluster_version.return_value = "v1.28.0"
        mock_nodes = MagicMock()
        mock_nodes.items = []
        mock_k8s_client.core_v1.list_node.return_value = mock_nodes

        result = manager._get_single_cluster_status("staging")

        assert result.connected is True
        assert result.node_count == 0


# ===========================================================================
# TestDeployToSingleClusterException
# ===========================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestDeployToSingleClusterException:
    """Tests for the outer exception handler in _deploy_to_single_cluster."""

    @patch("system_operations_manager.services.kubernetes.multicluster_manager.ManifestManager")
    def test_apply_manifests_exception_returns_failed_result(
        self,
        MockManifestManager: MagicMock,
        manager: MultiClusterManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """Should return failed ClusterDeployResult when apply_manifests raises."""
        mock_manifest_mgr = MagicMock()
        MockManifestManager.return_value = mock_manifest_mgr
        mock_manifest_mgr.apply_manifests.side_effect = RuntimeError("apply boom")

        manifests = [{"apiVersion": "v1", "kind": "ConfigMap", "metadata": {"name": "cfg"}}]

        result = manager.deploy_manifests_to_clusters(manifests, clusters=["staging"])

        assert result.total_clusters == 1
        assert result.failed == 1
        staging = result.cluster_results[0]
        assert staging.success is False
        assert staging.error == "apply boom"


# ===========================================================================
# TestReadResourceFromCluster
# ===========================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestReadResourceFromCluster:
    """Tests for _read_resource_from_cluster error and edge-case branches."""

    def test_returns_none_when_resource_api_not_found(
        self, manager: MultiClusterManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should return None when _find_resource_api returns None."""
        mock_dynamic = MagicMock()

        with (
            patch.object(manager, "_get_dynamic_client", return_value=mock_dynamic),
            patch.object(manager, "_find_resource_api", return_value=None),
        ):
            result = manager._read_resource_from_cluster(
                "staging",
                resource_type="Deployment",
                resource_name="my-app",
                namespace="default",
            )

        assert result is None

    def test_returns_none_when_resource_get_raises(
        self, manager: MultiClusterManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should return None when the resource .get() call raises an exception."""
        mock_dynamic = MagicMock()
        mock_resource_api = MagicMock()
        mock_resource_api.kind = "Deployment"
        mock_resource_api.get.side_effect = Exception("Not found")

        with (
            patch.object(manager, "_get_dynamic_client", return_value=mock_dynamic),
            patch.object(manager, "_find_resource_api", return_value=mock_resource_api),
        ):
            result = manager._read_resource_from_cluster(
                "staging",
                resource_type="Deployment",
                resource_name="my-app",
                namespace="default",
            )

        assert result is None

    def test_returns_dict_from_to_dict(
        self, manager: MultiClusterManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should return dict when live object has to_dict method."""
        mock_dynamic = MagicMock()
        mock_resource_api = MagicMock()
        mock_live_obj = MagicMock()
        expected_dict = {"apiVersion": "v1", "kind": "Deployment"}
        mock_live_obj.to_dict.return_value = expected_dict

        with (
            patch.object(manager, "_get_dynamic_client", return_value=mock_dynamic),
            patch.object(manager, "_find_resource_api", return_value=mock_resource_api),
        ):
            mock_resource_api.get.return_value = mock_live_obj
            result = manager._read_resource_from_cluster(
                "staging",
                resource_type="Deployment",
                resource_name="my-app",
                namespace=None,
            )

        assert result == expected_dict


# ===========================================================================
# TestFindResourceApi
# ===========================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestFindResourceApi:
    """Tests for _find_resource_api discovery and fallback logic."""

    def test_finds_resource_by_kind_iteration(self, manager: MultiClusterManager) -> None:
        """Should return the first api_resource whose kind matches."""
        mock_dynamic = MagicMock()
        match_resource = MagicMock()
        match_resource.kind = "Deployment"
        other_resource = MagicMock()
        other_resource.kind = "Service"
        mock_dynamic.resources = [other_resource, match_resource]

        result = manager._find_resource_api(mock_dynamic, "Deployment")

        assert result is match_resource

    def test_falls_back_to_api_version_get(self, manager: MultiClusterManager) -> None:
        """Should fall back to resources.get() when kind is not in iteration."""
        mock_dynamic = MagicMock()
        # Iteration finds no match
        mock_dynamic.resources.__iter__.return_value = iter([])
        # resources.get raises for all but apps/v1
        sentinel = MagicMock()

        def resources_get_side_effect(api_version: str, kind: str) -> MagicMock:
            if api_version == "apps/v1":
                return sentinel
            raise Exception("not found")

        mock_dynamic.resources.get.side_effect = resources_get_side_effect

        result = manager._find_resource_api(mock_dynamic, "Deployment")

        assert result is sentinel

    def test_returns_none_when_all_fallbacks_fail(self, manager: MultiClusterManager) -> None:
        """Should return None when iteration and all fallback api_versions fail."""
        mock_dynamic = MagicMock()
        mock_dynamic.resources.__iter__.return_value = iter([])
        mock_dynamic.resources.get.side_effect = Exception("not found")

        result = manager._find_resource_api(mock_dynamic, "UnknownKind")

        assert result is None

    def test_iteration_exception_triggers_fallback(self, manager: MultiClusterManager) -> None:
        """Should use fallback when iteration over dynamic.resources raises."""
        mock_dynamic = MagicMock()
        # Make iteration raise
        mock_dynamic.resources.__iter__.side_effect = Exception("iter error")
        sentinel = MagicMock()

        def resources_get_side_effect(api_version: str, kind: str) -> MagicMock:
            if api_version == "v1":
                return sentinel
            raise Exception("not found")

        mock_dynamic.resources.get.side_effect = resources_get_side_effect

        result = manager._find_resource_api(mock_dynamic, "ConfigMap")

        assert result is sentinel


# ===========================================================================
# TestSyncToSingleClusterEdgeCases
# ===========================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestSyncToSingleClusterEdgeCases:
    """Tests for _sync_to_single_cluster error and dry-run branches."""

    def test_context_switch_failure_returns_failed_result(
        self, manager: MultiClusterManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should return failed ClusterSyncResult when switch_context raises."""
        mock_k8s_client.switch_context.side_effect = RuntimeError("ctx switch error")

        result = manager._sync_to_single_cluster(
            "production",
            {"apiVersion": "v1", "kind": "ConfigMap"},
            dry_run=False,
        )

        assert result.success is False
        assert result.cluster == "production"
        assert "Failed to switch context" in (result.error or "")

    def test_dry_run_returns_skipped_result(
        self, manager: MultiClusterManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should return a success result with 'skipped (dry-run)' action when dry_run=True."""
        result = manager._sync_to_single_cluster(
            "staging",
            {"apiVersion": "v1", "kind": "ConfigMap"},
            dry_run=True,
        )

        assert result.success is True
        assert result.action == "skipped (dry-run)"

    @patch("system_operations_manager.services.kubernetes.multicluster_manager.ManifestManager")
    def test_failed_apply_result_returns_error(
        self,
        MockManifestManager: MagicMock,
        manager: MultiClusterManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """Should return failed ClusterSyncResult when apply result reports failure."""
        from system_operations_manager.services.kubernetes.manifest_manager import ApplyResult

        mock_manifest_mgr = MagicMock()
        MockManifestManager.return_value = mock_manifest_mgr
        mock_manifest_mgr.apply_manifests.return_value = [
            ApplyResult(
                resource="ConfigMap/cfg",
                action="",
                namespace="default",
                success=False,
                message="apply failed for cfg",
            )
        ]

        result = manager._sync_to_single_cluster(
            "staging",
            {"apiVersion": "v1", "kind": "ConfigMap"},
            dry_run=False,
        )

        assert result.success is False
        assert result.error == "apply failed for cfg"

    @patch("system_operations_manager.services.kubernetes.multicluster_manager.ManifestManager")
    def test_empty_apply_results_returns_error(
        self,
        MockManifestManager: MagicMock,
        manager: MultiClusterManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """Should return 'No result' error message when apply_manifests returns empty list."""
        mock_manifest_mgr = MagicMock()
        MockManifestManager.return_value = mock_manifest_mgr
        mock_manifest_mgr.apply_manifests.return_value = []

        result = manager._sync_to_single_cluster(
            "staging",
            {"apiVersion": "v1", "kind": "ConfigMap"},
            dry_run=False,
        )

        assert result.success is False
        assert result.error == "No result"

    @patch("system_operations_manager.services.kubernetes.multicluster_manager.ManifestManager")
    def test_apply_exception_returns_failed_result(
        self,
        MockManifestManager: MagicMock,
        manager: MultiClusterManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """Should return failed ClusterSyncResult when apply_manifests raises."""
        mock_manifest_mgr = MagicMock()
        MockManifestManager.return_value = mock_manifest_mgr
        mock_manifest_mgr.apply_manifests.side_effect = Exception("apply exploded")

        result = manager._sync_to_single_cluster(
            "staging",
            {"apiVersion": "v1", "kind": "ConfigMap"},
            dry_run=False,
        )

        assert result.success is False
        assert result.error == "apply exploded"


# ===========================================================================
# TestStripServerFieldsAnnotations
# ===========================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestStripServerFieldsAnnotations:
    """Tests for _strip_server_fields annotation-filtering branch."""

    def test_strips_kubectl_annotations(self) -> None:
        """Should remove annotations prefixed with kubectl.kubernetes.io/."""
        resource = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {
                "name": "my-config",
                "annotations": {
                    "kubectl.kubernetes.io/last-applied-configuration": "{}",
                    "app.kubernetes.io/name": "my-app",
                    "custom.io/owner": "team-a",
                },
            },
        }

        result = MultiClusterManager._strip_server_fields(resource)

        annotations = result["metadata"]["annotations"]
        assert "kubectl.kubernetes.io/last-applied-configuration" not in annotations
        assert annotations["app.kubernetes.io/name"] == "my-app"
        assert annotations["custom.io/owner"] == "team-a"

    def test_sets_annotations_to_none_when_all_stripped(self) -> None:
        """Should set annotations to None when all annotations are kubectl-managed."""
        resource = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {
                "name": "my-config",
                "annotations": {
                    "kubectl.kubernetes.io/last-applied-configuration": "{}",
                },
            },
        }

        result = MultiClusterManager._strip_server_fields(resource)

        assert result["metadata"]["annotations"] is None

    def test_strips_server_managed_metadata_fields(self) -> None:
        """Should remove uid, resourceVersion, and other server-managed metadata."""
        resource = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {
                "name": "my-config",
                "uid": "abc-123",
                "resourceVersion": "99999",
                "generation": 5,
                "managedFields": [{"manager": "kubectl"}],
            },
            "status": {"phase": "Active"},
        }

        result = MultiClusterManager._strip_server_fields(resource)

        assert "uid" not in result["metadata"]
        assert "resourceVersion" not in result["metadata"]
        assert "generation" not in result["metadata"]
        assert "managedFields" not in result["metadata"]
        assert "status" not in result

    def test_no_annotation_key_left_intact(self) -> None:
        """Should leave metadata intact when there are no annotations."""
        resource = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {"name": "no-annot"},
        }

        result = MultiClusterManager._strip_server_fields(resource)

        assert result["metadata"]["name"] == "no-annot"
        assert "annotations" not in result["metadata"]


# ===========================================================================
# TestGetDynamicClient
# ===========================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestGetDynamicClient:
    """Tests for MultiClusterManager._get_dynamic_client."""

    def test_returns_dynamic_client_instance(self, manager: MultiClusterManager) -> None:
        """Should construct and return a DynamicClient wrapping an ApiClient."""
        mock_api_client = MagicMock()
        mock_dynamic_client = MagicMock()

        with (
            patch(
                "kubernetes.dynamic.DynamicClient", return_value=mock_dynamic_client
            ) as MockDynamic,
            patch("kubernetes.client.ApiClient", return_value=mock_api_client) as MockApiClient,
        ):
            result = manager._get_dynamic_client()

        MockApiClient.assert_called_once_with()
        MockDynamic.assert_called_once_with(mock_api_client)
        assert result is mock_dynamic_client
