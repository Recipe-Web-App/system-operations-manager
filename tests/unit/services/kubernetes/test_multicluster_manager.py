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
