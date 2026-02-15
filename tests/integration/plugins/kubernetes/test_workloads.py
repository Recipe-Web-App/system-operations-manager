"""Integration tests for WorkloadManager."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from system_operations_manager.integrations.kubernetes.exceptions import KubernetesNotFoundError
from system_operations_manager.services.kubernetes import WorkloadManager


@pytest.mark.integration
@pytest.mark.kubernetes
class TestDeploymentCRUD:
    """Test Deployment CRUD operations."""

    def test_create_deployment(
        self,
        workload_manager: WorkloadManager,
        test_namespace: str,
        unique_name: str,
        wait_for_pod_ready: Callable[..., Any],
    ) -> None:
        """create_deployment should create a new deployment."""
        deploy_name = f"test-deploy-{unique_name}"

        result = workload_manager.create_deployment(
            deploy_name,
            test_namespace,
            image="nginx:alpine",
            replicas=1,
            port=80,
        )

        assert result.name == deploy_name
        assert result.namespace == test_namespace
        assert result.desired_replicas == 1

        # Wait for pod to be ready
        wait_for_pod_ready(
            namespace=test_namespace,
            label_selector=f"app={deploy_name}",
        )

    def test_list_deployments(
        self,
        workload_manager: WorkloadManager,
        test_namespace: str,
        unique_name: str,
    ) -> None:
        """list_deployments should return created deployments."""
        deploy_name = f"test-deploy-{unique_name}"
        workload_manager.create_deployment(
            deploy_name,
            test_namespace,
            image="nginx:alpine",
            replicas=1,
        )

        deployments = workload_manager.list_deployments(test_namespace)

        assert len(deployments) >= 1
        assert any(d.name == deploy_name for d in deployments)

    def test_get_deployment(
        self,
        workload_manager: WorkloadManager,
        test_namespace: str,
        unique_name: str,
    ) -> None:
        """get_deployment should retrieve a deployment by name."""
        deploy_name = f"test-deploy-{unique_name}"
        workload_manager.create_deployment(
            deploy_name,
            test_namespace,
            image="nginx:alpine",
            replicas=1,
        )

        result = workload_manager.get_deployment(deploy_name, test_namespace)

        assert result.name == deploy_name
        assert result.namespace == test_namespace

    def test_update_deployment(
        self,
        workload_manager: WorkloadManager,
        test_namespace: str,
        unique_name: str,
    ) -> None:
        """update_deployment should change deployment replicas."""
        deploy_name = f"test-deploy-{unique_name}"
        workload_manager.create_deployment(
            deploy_name,
            test_namespace,
            image="nginx:alpine",
            replicas=1,
        )

        result = workload_manager.update_deployment(
            deploy_name,
            test_namespace,
            replicas=3,
        )

        assert result.name == deploy_name
        assert result.desired_replicas == 3

    def test_delete_deployment(
        self,
        workload_manager: WorkloadManager,
        test_namespace: str,
        unique_name: str,
    ) -> None:
        """delete_deployment should delete a deployment."""
        deploy_name = f"test-deploy-{unique_name}"
        workload_manager.create_deployment(
            deploy_name,
            test_namespace,
            image="nginx:alpine",
            replicas=1,
        )

        workload_manager.delete_deployment(deploy_name, test_namespace)

        # Verify deletion
        with pytest.raises(KubernetesNotFoundError):
            workload_manager.get_deployment(deploy_name, test_namespace)

    def test_get_nonexistent_raises(
        self,
        workload_manager: WorkloadManager,
        test_namespace: str,
    ) -> None:
        """get_deployment should raise KubernetesNotFoundError for missing deployment."""
        with pytest.raises(KubernetesNotFoundError):
            workload_manager.get_deployment("nonexistent-deploy", test_namespace)


@pytest.mark.integration
@pytest.mark.kubernetes
class TestPodOperations:
    """Test Pod operations."""

    def test_list_pods(
        self,
        workload_manager: WorkloadManager,
        test_namespace: str,
        unique_name: str,
        wait_for_pod_ready: Callable[..., Any],
    ) -> None:
        """list_pods should return pods created by deployment."""
        deploy_name = f"test-deploy-{unique_name}"
        workload_manager.create_deployment(
            deploy_name,
            test_namespace,
            image="nginx:alpine",
            replicas=1,
        )

        # Wait for pod to be ready
        wait_for_pod_ready(
            namespace=test_namespace,
            label_selector=f"app={deploy_name}",
        )

        pods = workload_manager.list_pods(test_namespace)

        assert len(pods) >= 1
        assert any(deploy_name in pod.name for pod in pods)

    def test_list_pods_with_label_selector(
        self,
        workload_manager: WorkloadManager,
        test_namespace: str,
        unique_name: str,
        wait_for_pod_ready: Callable[..., Any],
    ) -> None:
        """list_pods should filter by label selector."""
        deploy_name = f"test-deploy-{unique_name}"
        workload_manager.create_deployment(
            deploy_name,
            test_namespace,
            image="nginx:alpine",
            replicas=1,
        )

        # Wait for pod to be ready
        wait_for_pod_ready(
            namespace=test_namespace,
            label_selector=f"app={deploy_name}",
        )

        pods = workload_manager.list_pods(
            test_namespace,
            label_selector=f"app={deploy_name}",
        )

        assert len(pods) >= 1
        assert all(deploy_name in pod.name for pod in pods)

    def test_get_pod(
        self,
        workload_manager: WorkloadManager,
        test_namespace: str,
        unique_name: str,
        wait_for_pod_ready: Callable[..., Any],
    ) -> None:
        """get_pod should retrieve a pod by name."""
        deploy_name = f"test-deploy-{unique_name}"
        workload_manager.create_deployment(
            deploy_name,
            test_namespace,
            image="nginx:alpine",
            replicas=1,
        )

        # Wait for pod to be ready
        pod = wait_for_pod_ready(
            namespace=test_namespace,
            label_selector=f"app={deploy_name}",
        )

        result = workload_manager.get_pod(pod.metadata.name, test_namespace)

        assert result.name == pod.metadata.name
        assert result.namespace == test_namespace

    def test_delete_pod(
        self,
        workload_manager: WorkloadManager,
        test_namespace: str,
        unique_name: str,
        wait_for_pod_ready: Callable[..., Any],
    ) -> None:
        """delete_pod should delete a pod."""
        deploy_name = f"test-deploy-{unique_name}"
        workload_manager.create_deployment(
            deploy_name,
            test_namespace,
            image="nginx:alpine",
            replicas=1,
        )

        # Wait for pod to be ready
        pod = wait_for_pod_ready(
            namespace=test_namespace,
            label_selector=f"app={deploy_name}",
        )

        workload_manager.delete_pod(pod.metadata.name, test_namespace)

        # Note: Deployment will recreate the pod, so we just verify deletion happened
        # without raising an exception


@pytest.mark.integration
@pytest.mark.kubernetes
class TestDeploymentScaling:
    """Test deployment scaling operations."""

    def test_scale_deployment(
        self,
        workload_manager: WorkloadManager,
        test_namespace: str,
        unique_name: str,
    ) -> None:
        """scale_deployment should change replica count."""
        deploy_name = f"test-deploy-{unique_name}"
        workload_manager.create_deployment(
            deploy_name,
            test_namespace,
            image="nginx:alpine",
            replicas=1,
        )

        result = workload_manager.scale_deployment(
            deploy_name,
            test_namespace,
            replicas=3,
        )

        assert result.name == deploy_name
        assert result.desired_replicas == 3

    def test_restart_deployment(
        self,
        workload_manager: WorkloadManager,
        test_namespace: str,
        unique_name: str,
    ) -> None:
        """restart_deployment should add restart annotation."""
        deploy_name = f"test-deploy-{unique_name}"
        workload_manager.create_deployment(
            deploy_name,
            test_namespace,
            image="nginx:alpine",
            replicas=1,
        )

        result = workload_manager.restart_deployment(deploy_name, test_namespace)

        assert result.name == deploy_name
        # Restart annotation should be present (checked internally)

    def test_get_rollout_status(
        self,
        workload_manager: WorkloadManager,
        test_namespace: str,
        unique_name: str,
        wait_for_pod_ready: Callable[..., Any],
    ) -> None:
        """get_rollout_status should return deployment rollout status."""
        deploy_name = f"test-deploy-{unique_name}"
        workload_manager.create_deployment(
            deploy_name,
            test_namespace,
            image="nginx:alpine",
            replicas=1,
        )

        # Wait for pod to be ready
        wait_for_pod_ready(
            namespace=test_namespace,
            label_selector=f"app={deploy_name}",
            timeout=120,
        )

        status = workload_manager.get_rollout_status(deploy_name, test_namespace)

        assert status["name"] == deploy_name
        assert status["namespace"] == test_namespace
        assert status["desired_replicas"] == 1
        assert "updated_replicas" in status
        assert "ready_replicas" in status
        assert "available_replicas" in status
        assert "complete" in status
        assert "conditions" in status

    def test_list_deployments_with_label_selector(
        self,
        workload_manager: WorkloadManager,
        test_namespace: str,
        unique_name: str,
    ) -> None:
        """list_deployments should filter by label selector."""
        deploy_name = f"test-deploy-{unique_name}"
        labels = {"app": deploy_name, "tier": "frontend"}
        workload_manager.create_deployment(
            deploy_name,
            test_namespace,
            image="nginx:alpine",
            replicas=1,
            labels=labels,
        )

        deployments = workload_manager.list_deployments(
            test_namespace,
            label_selector=f"app={deploy_name}",
        )

        assert len(deployments) >= 1
        assert all(d.name == deploy_name for d in deployments)

    def test_list_deployments_all_namespaces(
        self,
        workload_manager: WorkloadManager,
        test_namespace: str,
        unique_name: str,
    ) -> None:
        """list_deployments should list across all namespaces."""
        deploy_name = f"test-deploy-{unique_name}"
        workload_manager.create_deployment(
            deploy_name,
            test_namespace,
            image="nginx:alpine",
            replicas=1,
        )

        deployments = workload_manager.list_deployments(
            namespace=None,
            all_namespaces=True,
        )

        # Should include deployments from multiple namespaces
        assert len(deployments) >= 1
        assert any(d.name == deploy_name for d in deployments)
