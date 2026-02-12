"""Unit tests for WorkloadManager."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from system_operations_manager.services.kubernetes.workload_manager import (
    WorkloadManager,
)


@pytest.fixture
def mock_k8s_client() -> MagicMock:
    """Create a mock Kubernetes client."""
    mock_client = MagicMock()
    mock_client.default_namespace = "default"
    return mock_client


@pytest.fixture
def workload_manager(mock_k8s_client: MagicMock) -> WorkloadManager:
    """Create a WorkloadManager instance with mocked client."""
    return WorkloadManager(mock_k8s_client)


class TestWorkloadManagerPods:
    """Tests for Pod operations."""

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_pods_success(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should list pods successfully."""
        mock_pod = MagicMock()
        mock_pod.metadata.name = "test-pod"
        mock_pod.metadata.namespace = "default"
        mock_pod.metadata.uid = "uid-123"
        mock_response = MagicMock()
        mock_response.items = [mock_pod]
        mock_k8s_client.core_v1.list_namespaced_pod.return_value = mock_response

        with patch(
            "system_operations_manager.services.kubernetes.workload_manager.PodSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = workload_manager.list_pods()

            assert len(result) == 1
            assert result[0] == mock_summary
            mock_k8s_client.core_v1.list_namespaced_pod.assert_called_once_with(namespace="default")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_pods_empty(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should return empty list when no pods exist."""
        mock_response = MagicMock()
        mock_response.items = []
        mock_k8s_client.core_v1.list_namespaced_pod.return_value = mock_response

        result = workload_manager.list_pods()

        assert result == []

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_pods_all_namespaces(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should list pods across all namespaces."""
        mock_response = MagicMock()
        mock_response.items = []
        mock_k8s_client.core_v1.list_pod_for_all_namespaces.return_value = mock_response

        result = workload_manager.list_pods(all_namespaces=True)

        assert result == []
        mock_k8s_client.core_v1.list_pod_for_all_namespaces.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_pods_with_selectors(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should list pods with label and field selectors."""
        mock_response = MagicMock()
        mock_response.items = []
        mock_k8s_client.core_v1.list_namespaced_pod.return_value = mock_response

        workload_manager.list_pods(label_selector="app=test", field_selector="status.phase=Running")

        mock_k8s_client.core_v1.list_namespaced_pod.assert_called_once_with(
            namespace="default", label_selector="app=test", field_selector="status.phase=Running"
        )

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_pods_error(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when listing pods."""
        mock_k8s_client.core_v1.list_namespaced_pod.side_effect = Exception("API error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            workload_manager.list_pods()

        mock_k8s_client.translate_api_exception.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_get_pod_success(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should get pod successfully."""
        mock_pod = MagicMock()
        mock_k8s_client.core_v1.read_namespaced_pod.return_value = mock_pod

        with patch(
            "system_operations_manager.services.kubernetes.workload_manager.PodSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = workload_manager.get_pod("test-pod")

            assert result == mock_summary
            mock_k8s_client.core_v1.read_namespaced_pod.assert_called_once_with(
                name="test-pod", namespace="default"
            )

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_get_pod_error(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when getting pod."""
        mock_k8s_client.core_v1.read_namespaced_pod.side_effect = Exception("Not found")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            workload_manager.get_pod("test-pod")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_delete_pod_success(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should delete pod successfully."""
        workload_manager.delete_pod("test-pod", "test-ns")

        mock_k8s_client.core_v1.delete_namespaced_pod.assert_called_once_with(
            name="test-pod", namespace="test-ns"
        )

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_delete_pod_error(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when deleting pod."""
        mock_k8s_client.core_v1.delete_namespaced_pod.side_effect = Exception("Delete error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            workload_manager.delete_pod("test-pod")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_get_pod_logs_success(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should get pod logs successfully."""
        mock_k8s_client.core_v1.read_namespaced_pod_log.return_value = "log output"

        result = workload_manager.get_pod_logs("test-pod", container="app", tail_lines=100)

        assert result == "log output"
        mock_k8s_client.core_v1.read_namespaced_pod_log.assert_called_once_with(
            name="test-pod", namespace="default", container="app", tail_lines=100
        )

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_get_pod_logs_error(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when getting pod logs."""
        mock_k8s_client.core_v1.read_namespaced_pod_log.side_effect = Exception("Log error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            workload_manager.get_pod_logs("test-pod")


class TestWorkloadManagerDeployments:
    """Tests for Deployment operations."""

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_deployments_success(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should list deployments successfully."""
        mock_response = MagicMock()
        mock_response.items = []
        mock_k8s_client.apps_v1.list_namespaced_deployment.return_value = mock_response

        result = workload_manager.list_deployments()

        assert result == []
        mock_k8s_client.apps_v1.list_namespaced_deployment.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_deployments_all_namespaces(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should list deployments across all namespaces."""
        mock_response = MagicMock()
        mock_response.items = []
        mock_k8s_client.apps_v1.list_deployment_for_all_namespaces.return_value = mock_response

        result = workload_manager.list_deployments(all_namespaces=True)

        assert result == []
        mock_k8s_client.apps_v1.list_deployment_for_all_namespaces.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_deployments_error(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when listing deployments."""
        mock_k8s_client.apps_v1.list_namespaced_deployment.side_effect = Exception("API error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            workload_manager.list_deployments()

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_get_deployment_success(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should get deployment successfully."""
        mock_deployment = MagicMock()
        mock_k8s_client.apps_v1.read_namespaced_deployment.return_value = mock_deployment

        with patch(
            "system_operations_manager.services.kubernetes.workload_manager.DeploymentSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = workload_manager.get_deployment("test-deploy")

            assert result == mock_summary

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_get_deployment_error(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when getting deployment."""
        mock_k8s_client.apps_v1.read_namespaced_deployment.side_effect = Exception("Not found")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            workload_manager.get_deployment("test-deploy")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_create_deployment_success(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should create deployment successfully."""
        mock_deployment = MagicMock()
        mock_k8s_client.apps_v1.create_namespaced_deployment.return_value = mock_deployment

        with patch(
            "system_operations_manager.services.kubernetes.workload_manager.DeploymentSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = workload_manager.create_deployment(
                "test-deploy", image="nginx:latest", replicas=3
            )

            assert result == mock_summary
            mock_k8s_client.apps_v1.create_namespaced_deployment.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_create_deployment_error(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when creating deployment."""
        mock_k8s_client.apps_v1.create_namespaced_deployment.side_effect = Exception("Create error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            workload_manager.create_deployment("test-deploy", image="nginx:latest")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_update_deployment_success(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should update deployment successfully."""
        mock_deployment = MagicMock()
        mock_k8s_client.apps_v1.patch_namespaced_deployment.return_value = mock_deployment

        with patch(
            "system_operations_manager.services.kubernetes.workload_manager.DeploymentSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = workload_manager.update_deployment(
                "test-deploy", image="nginx:1.19", replicas=5
            )

            assert result == mock_summary

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_update_deployment_error(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when updating deployment."""
        mock_k8s_client.apps_v1.patch_namespaced_deployment.side_effect = Exception("Update error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            workload_manager.update_deployment("test-deploy", image="nginx:latest")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_delete_deployment_success(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should delete deployment successfully."""
        workload_manager.delete_deployment("test-deploy")

        mock_k8s_client.apps_v1.delete_namespaced_deployment.assert_called_once_with(
            name="test-deploy", namespace="default"
        )

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_delete_deployment_error(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when deleting deployment."""
        mock_k8s_client.apps_v1.delete_namespaced_deployment.side_effect = Exception("Delete error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            workload_manager.delete_deployment("test-deploy")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_scale_deployment_success(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should scale deployment successfully."""
        mock_deployment = MagicMock()
        mock_k8s_client.apps_v1.patch_namespaced_deployment.return_value = mock_deployment

        with patch(
            "system_operations_manager.services.kubernetes.workload_manager.DeploymentSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = workload_manager.scale_deployment("test-deploy", replicas=10)

            assert result == mock_summary

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_scale_deployment_error(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when scaling deployment."""
        mock_k8s_client.apps_v1.patch_namespaced_deployment.side_effect = Exception("Scale error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            workload_manager.scale_deployment("test-deploy", replicas=5)

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_restart_deployment_success(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should restart deployment successfully."""
        mock_deployment = MagicMock()
        mock_k8s_client.apps_v1.patch_namespaced_deployment.return_value = mock_deployment

        with patch(
            "system_operations_manager.services.kubernetes.workload_manager.DeploymentSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = workload_manager.restart_deployment("test-deploy")

            assert result == mock_summary

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_restart_deployment_error(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when restarting deployment."""
        mock_k8s_client.apps_v1.patch_namespaced_deployment.side_effect = Exception("Restart error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            workload_manager.restart_deployment("test-deploy")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_get_rollout_status_success(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should get rollout status successfully."""
        mock_deployment = MagicMock()
        mock_deployment.spec.replicas = 3
        mock_deployment.status.updated_replicas = 3
        mock_deployment.status.ready_replicas = 3
        mock_deployment.status.available_replicas = 3
        mock_deployment.status.conditions = []
        mock_k8s_client.apps_v1.read_namespaced_deployment.return_value = mock_deployment

        result = workload_manager.get_rollout_status("test-deploy")

        assert result["desired_replicas"] == 3
        assert result["complete"] is True

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_get_rollout_status_error(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when getting rollout status."""
        mock_k8s_client.apps_v1.read_namespaced_deployment.side_effect = Exception("Status error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            workload_manager.get_rollout_status("test-deploy")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_rollback_deployment_success(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should rollback deployment successfully."""
        mock_deployment = MagicMock()
        mock_deployment.spec.selector.match_labels = {"app": "test"}

        mock_rs1 = MagicMock()
        mock_rs1.metadata.annotations = {"deployment.kubernetes.io/revision": "2"}
        owner1 = MagicMock()
        owner1.kind = "Deployment"
        owner1.name = "test-deploy"
        mock_rs1.metadata.owner_references = [owner1]
        mock_rs1.spec.template = MagicMock()

        mock_rs2 = MagicMock()
        mock_rs2.metadata.annotations = {"deployment.kubernetes.io/revision": "1"}
        owner2 = MagicMock()
        owner2.kind = "Deployment"
        owner2.name = "test-deploy"
        mock_rs2.metadata.owner_references = [owner2]
        mock_rs2.spec.template = MagicMock()

        mock_rs_list = MagicMock()
        mock_rs_list.items = [mock_rs1, mock_rs2]

        mock_k8s_client.apps_v1.read_namespaced_deployment.return_value = mock_deployment
        mock_k8s_client.apps_v1.list_namespaced_replica_set.return_value = mock_rs_list
        mock_k8s_client.apps_v1.patch_namespaced_deployment.return_value = mock_deployment

        workload_manager.rollback_deployment("test-deploy")

        # Verify patch was called to apply the rollback
        mock_k8s_client.apps_v1.patch_namespaced_deployment.assert_called_once_with(
            name="test-deploy",
            namespace="default",
            body={"spec": {"template": mock_rs2.spec.template}},
        )

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_rollback_deployment_error(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when rolling back deployment."""
        mock_k8s_client.apps_v1.read_namespaced_deployment.side_effect = Exception("Rollback error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            workload_manager.rollback_deployment("test-deploy")


class TestWorkloadManagerStatefulSets:
    """Tests for StatefulSet operations."""

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_stateful_sets_success(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should list statefulsets successfully."""
        mock_response = MagicMock()
        mock_response.items = []
        mock_k8s_client.apps_v1.list_namespaced_stateful_set.return_value = mock_response

        result = workload_manager.list_stateful_sets()

        assert result == []

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_stateful_sets_error(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when listing statefulsets."""
        mock_k8s_client.apps_v1.list_namespaced_stateful_set.side_effect = Exception("API error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            workload_manager.list_stateful_sets()

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_get_stateful_set_success(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should get statefulset successfully."""
        mock_statefulset = MagicMock()
        mock_k8s_client.apps_v1.read_namespaced_stateful_set.return_value = mock_statefulset

        with patch(
            "system_operations_manager.services.kubernetes.workload_manager.StatefulSetSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = workload_manager.get_stateful_set("test-ss")

            assert result == mock_summary

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_get_stateful_set_error(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when getting statefulset."""
        mock_k8s_client.apps_v1.read_namespaced_stateful_set.side_effect = Exception("Not found")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            workload_manager.get_stateful_set("test-ss")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_create_stateful_set_success(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should create statefulset successfully."""
        mock_statefulset = MagicMock()
        mock_k8s_client.apps_v1.create_namespaced_stateful_set.return_value = mock_statefulset

        with patch(
            "system_operations_manager.services.kubernetes.workload_manager.StatefulSetSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = workload_manager.create_stateful_set(
                "test-ss", image="postgres:14", service_name="test-svc"
            )

            assert result == mock_summary

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_create_stateful_set_error(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when creating statefulset."""
        mock_k8s_client.apps_v1.create_namespaced_stateful_set.side_effect = Exception(
            "Create error"
        )
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            workload_manager.create_stateful_set("test-ss", image="postgres:14", service_name="svc")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_update_stateful_set_success(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should update statefulset successfully."""
        mock_statefulset = MagicMock()
        mock_k8s_client.apps_v1.patch_namespaced_stateful_set.return_value = mock_statefulset

        with patch(
            "system_operations_manager.services.kubernetes.workload_manager.StatefulSetSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = workload_manager.update_stateful_set("test-ss", replicas=5)

            assert result == mock_summary

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_update_stateful_set_error(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when updating statefulset."""
        mock_k8s_client.apps_v1.patch_namespaced_stateful_set.side_effect = Exception(
            "Update error"
        )
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            workload_manager.update_stateful_set("test-ss", replicas=3)

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_delete_stateful_set_success(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should delete statefulset successfully."""
        workload_manager.delete_stateful_set("test-ss")

        mock_k8s_client.apps_v1.delete_namespaced_stateful_set.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_delete_stateful_set_error(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when deleting statefulset."""
        mock_k8s_client.apps_v1.delete_namespaced_stateful_set.side_effect = Exception(
            "Delete error"
        )
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            workload_manager.delete_stateful_set("test-ss")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_scale_stateful_set_success(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should scale statefulset successfully."""
        mock_statefulset = MagicMock()
        mock_k8s_client.apps_v1.patch_namespaced_stateful_set.return_value = mock_statefulset

        with patch(
            "system_operations_manager.services.kubernetes.workload_manager.StatefulSetSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = workload_manager.scale_stateful_set("test-ss", replicas=7)

            assert result == mock_summary

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_scale_stateful_set_error(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when scaling statefulset."""
        mock_k8s_client.apps_v1.patch_namespaced_stateful_set.side_effect = Exception("Scale error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            workload_manager.scale_stateful_set("test-ss", replicas=3)

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_restart_stateful_set_success(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should restart statefulset successfully."""
        mock_statefulset = MagicMock()
        mock_k8s_client.apps_v1.patch_namespaced_stateful_set.return_value = mock_statefulset

        with patch(
            "system_operations_manager.services.kubernetes.workload_manager.StatefulSetSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = workload_manager.restart_stateful_set("test-ss")

            assert result == mock_summary

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_restart_stateful_set_error(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when restarting statefulset."""
        mock_k8s_client.apps_v1.patch_namespaced_stateful_set.side_effect = Exception(
            "Restart error"
        )
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            workload_manager.restart_stateful_set("test-ss")


class TestWorkloadManagerDaemonSets:
    """Tests for DaemonSet operations."""

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_daemon_sets_success(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should list daemonsets successfully."""
        mock_response = MagicMock()
        mock_response.items = []
        mock_k8s_client.apps_v1.list_namespaced_daemon_set.return_value = mock_response

        result = workload_manager.list_daemon_sets()

        assert result == []

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_daemon_sets_error(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when listing daemonsets."""
        mock_k8s_client.apps_v1.list_namespaced_daemon_set.side_effect = Exception("API error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            workload_manager.list_daemon_sets()

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_get_daemon_set_success(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should get daemonset successfully."""
        mock_daemonset = MagicMock()
        mock_k8s_client.apps_v1.read_namespaced_daemon_set.return_value = mock_daemonset

        with patch(
            "system_operations_manager.services.kubernetes.workload_manager.DaemonSetSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = workload_manager.get_daemon_set("test-ds")

            assert result == mock_summary

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_get_daemon_set_error(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when getting daemonset."""
        mock_k8s_client.apps_v1.read_namespaced_daemon_set.side_effect = Exception("Not found")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            workload_manager.get_daemon_set("test-ds")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_create_daemon_set_success(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should create daemonset successfully."""
        mock_daemonset = MagicMock()
        mock_k8s_client.apps_v1.create_namespaced_daemon_set.return_value = mock_daemonset

        with patch(
            "system_operations_manager.services.kubernetes.workload_manager.DaemonSetSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = workload_manager.create_daemon_set("test-ds", image="fluentd:latest")

            assert result == mock_summary

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_create_daemon_set_error(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when creating daemonset."""
        mock_k8s_client.apps_v1.create_namespaced_daemon_set.side_effect = Exception("Create error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            workload_manager.create_daemon_set("test-ds", image="fluentd:latest")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_update_daemon_set_success(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should update daemonset successfully."""
        mock_daemonset = MagicMock()
        mock_k8s_client.apps_v1.patch_namespaced_daemon_set.return_value = mock_daemonset

        with patch(
            "system_operations_manager.services.kubernetes.workload_manager.DaemonSetSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = workload_manager.update_daemon_set("test-ds", image="fluentd:v2")

            assert result == mock_summary

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_update_daemon_set_error(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when updating daemonset."""
        mock_k8s_client.apps_v1.patch_namespaced_daemon_set.side_effect = Exception("Update error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            workload_manager.update_daemon_set("test-ds", image="fluentd:v2")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_delete_daemon_set_success(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should delete daemonset successfully."""
        workload_manager.delete_daemon_set("test-ds")

        mock_k8s_client.apps_v1.delete_namespaced_daemon_set.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_delete_daemon_set_error(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when deleting daemonset."""
        mock_k8s_client.apps_v1.delete_namespaced_daemon_set.side_effect = Exception("Delete error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            workload_manager.delete_daemon_set("test-ds")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_restart_daemon_set_success(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should restart daemonset successfully."""
        mock_daemonset = MagicMock()
        mock_k8s_client.apps_v1.patch_namespaced_daemon_set.return_value = mock_daemonset

        with patch(
            "system_operations_manager.services.kubernetes.workload_manager.DaemonSetSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = workload_manager.restart_daemon_set("test-ds")

            assert result == mock_summary

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_restart_daemon_set_error(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when restarting daemonset."""
        mock_k8s_client.apps_v1.patch_namespaced_daemon_set.side_effect = Exception("Restart error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            workload_manager.restart_daemon_set("test-ds")


class TestWorkloadManagerReplicaSets:
    """Tests for ReplicaSet operations."""

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_replica_sets_success(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should list replicasets successfully."""
        mock_response = MagicMock()
        mock_response.items = []
        mock_k8s_client.apps_v1.list_namespaced_replica_set.return_value = mock_response

        result = workload_manager.list_replica_sets()

        assert result == []

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_list_replica_sets_error(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when listing replicasets."""
        mock_k8s_client.apps_v1.list_namespaced_replica_set.side_effect = Exception("API error")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            workload_manager.list_replica_sets()

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_get_replica_set_success(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should get replicaset successfully."""
        mock_replicaset = MagicMock()
        mock_k8s_client.apps_v1.read_namespaced_replica_set.return_value = mock_replicaset

        with patch(
            "system_operations_manager.services.kubernetes.workload_manager.ReplicaSetSummary.from_k8s_object"
        ) as mock_from_k8s:
            mock_summary = MagicMock()
            mock_from_k8s.return_value = mock_summary

            result = workload_manager.get_replica_set("test-rs")

            assert result == mock_summary

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_get_replica_set_error(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when getting replicaset."""
        mock_k8s_client.apps_v1.read_namespaced_replica_set.side_effect = Exception("Not found")
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            workload_manager.get_replica_set("test-rs")

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_delete_replica_set_success(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should delete replicaset successfully."""
        workload_manager.delete_replica_set("test-rs")

        mock_k8s_client.apps_v1.delete_namespaced_replica_set.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.kubernetes
    def test_delete_replica_set_error(
        self, workload_manager: WorkloadManager, mock_k8s_client: MagicMock
    ) -> None:
        """Should handle API error when deleting replicaset."""
        mock_k8s_client.apps_v1.delete_namespaced_replica_set.side_effect = Exception(
            "Delete error"
        )
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("Translated error")

        with pytest.raises(RuntimeError, match="Translated error"):
            workload_manager.delete_replica_set("test-rs")
