"""Unit tests for Kubernetes workload resource models."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from system_operations_manager.integrations.kubernetes.models.workloads import (
    ContainerStatus,
    DaemonSetSummary,
    DeploymentSummary,
    PodSummary,
    ReplicaSetSummary,
    StatefulSetSummary,
)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestContainerStatus:
    """Test ContainerStatus model."""

    def test_from_k8s_object_running(self) -> None:
        """Test from_k8s_object with running container."""
        obj = MagicMock()
        obj.name = "nginx"
        obj.image = "nginx:1.21"
        obj.ready = True
        obj.restart_count = 0

        obj.state.running = MagicMock()
        obj.state.waiting = None
        obj.state.terminated = None

        cs = ContainerStatus.from_k8s_object(obj)

        assert cs.name == "nginx"
        assert cs.image == "nginx:1.21"
        assert cs.ready is True
        assert cs.restart_count == 0
        assert cs.state == "running"

    def test_from_k8s_object_waiting(self) -> None:
        """Test from_k8s_object with waiting container."""
        obj = MagicMock()
        obj.name = "app"
        obj.image = "app:latest"
        obj.ready = False
        obj.restart_count = 1

        obj.state.running = None
        obj.state.waiting.reason = "ImagePullBackOff"
        obj.state.terminated = None

        cs = ContainerStatus.from_k8s_object(obj)

        assert cs.ready is False
        assert cs.restart_count == 1
        assert cs.state == "ImagePullBackOff"

    def test_from_k8s_object_terminated(self) -> None:
        """Test from_k8s_object with terminated container."""
        obj = MagicMock()
        obj.name = "job-container"
        obj.image = "busybox"
        obj.ready = False
        obj.restart_count = 0

        obj.state.running = None
        obj.state.waiting = None
        obj.state.terminated.reason = "Completed"

        cs = ContainerStatus.from_k8s_object(obj)

        assert cs.state == "Completed"

    def test_from_k8s_object_terminated_error(self) -> None:
        """Test from_k8s_object with error terminated container."""
        obj = MagicMock()
        obj.name = "failed-container"
        obj.image = "test:1.0"
        obj.ready = False
        obj.restart_count = 3

        obj.state.running = None
        obj.state.waiting = None
        obj.state.terminated.reason = "Error"

        cs = ContainerStatus.from_k8s_object(obj)

        assert cs.state == "Error"
        assert cs.restart_count == 3

    def test_from_k8s_object_no_state(self) -> None:
        """Test from_k8s_object with no state."""
        obj = MagicMock()
        obj.name = "unknown-container"
        obj.image = None
        obj.ready = None
        obj.restart_count = None
        obj.state = None

        cs = ContainerStatus.from_k8s_object(obj)

        assert cs.name == "unknown-container"
        assert cs.ready is False
        assert cs.restart_count == 0
        assert cs.state == "unknown"

    def test_from_k8s_object_waiting_no_reason(self) -> None:
        """Test from_k8s_object with waiting state but no reason."""
        obj = MagicMock()
        obj.name = "container"
        obj.image = "busybox:latest"
        obj.ready = False
        obj.restart_count = 0

        obj.state.running = None
        obj.state.waiting.reason = None
        obj.state.terminated = None

        cs = ContainerStatus.from_k8s_object(obj)

        assert cs.state == "Waiting"

    def test_entity_name(self) -> None:
        """Test entity name class variable."""
        assert ContainerStatus._entity_name == "container"


@pytest.mark.unit
@pytest.mark.kubernetes
class TestPodSummary:
    """Test PodSummary model."""

    def test_from_k8s_object_complete(self) -> None:
        """Test from_k8s_object with complete Pod."""
        obj = MagicMock()
        obj.metadata.name = "nginx-pod"
        obj.metadata.namespace = "default"
        obj.metadata.uid = "uid-pod-123"
        obj.metadata.creation_timestamp = "2024-01-01T00:00:00Z"
        obj.metadata.labels = {"app": "nginx"}
        obj.metadata.annotations = {}

        obj.spec.node_name = "node-1"

        # Containers in spec
        spec_container = MagicMock()
        obj.spec.containers = [spec_container]

        # Container statuses
        cs1 = MagicMock()
        cs1.name = "nginx"
        cs1.image = "nginx:1.21"
        cs1.ready = True
        cs1.restart_count = 0
        cs1.state.running = MagicMock()
        cs1.state.waiting = None
        cs1.state.terminated = None

        obj.status.container_statuses = [cs1]
        obj.status.phase = "Running"
        obj.status.pod_ip = "10.244.1.5"

        pod = PodSummary.from_k8s_object(obj)

        assert pod.name == "nginx-pod"
        assert pod.namespace == "default"
        assert pod.phase == "Running"
        assert pod.node_name == "node-1"
        assert pod.pod_ip == "10.244.1.5"
        assert pod.restarts == 0
        assert pod.ready_count == 1
        assert pod.total_count == 1
        assert len(pod.containers) == 1

    def test_from_k8s_object_multiple_containers(self) -> None:
        """Test from_k8s_object with multiple containers."""
        obj = MagicMock()
        obj.metadata.name = "multi-container-pod"
        obj.metadata.namespace = "default"

        obj.spec.node_name = "node-2"
        obj.spec.containers = [MagicMock(), MagicMock(), MagicMock()]

        # Container statuses
        cs1 = MagicMock()
        cs1.name = "app"
        cs1.image = "app:latest"
        cs1.ready = True
        cs1.restart_count = 2
        cs1.state.running = MagicMock()
        cs1.state.waiting = None
        cs1.state.terminated = None

        cs2 = MagicMock()
        cs2.name = "sidecar"
        cs2.image = "sidecar:latest"
        cs2.ready = True
        cs2.restart_count = 1
        cs2.state.running = MagicMock()
        cs2.state.waiting = None
        cs2.state.terminated = None

        cs3 = MagicMock()
        cs3.name = "init-wait"
        cs3.image = "init:latest"
        cs3.ready = False
        cs3.restart_count = 0
        cs3.state.running = None
        cs3.state.waiting = MagicMock()
        cs3.state.waiting.reason = "Waiting"
        cs3.state.terminated = None

        obj.status.container_statuses = [cs1, cs2, cs3]
        obj.status.phase = "Running"
        obj.status.pod_ip = "10.244.1.6"

        pod = PodSummary.from_k8s_object(obj)

        assert pod.restarts == 3
        assert pod.ready_count == 2
        assert pod.total_count == 3

    def test_from_k8s_object_pending(self) -> None:
        """Test from_k8s_object with pending Pod."""
        obj = MagicMock()
        obj.metadata.name = "pending-pod"
        obj.metadata.namespace = "default"

        obj.spec.node_name = None
        obj.spec.containers = [MagicMock()]

        obj.status.container_statuses = None
        obj.status.phase = "Pending"
        obj.status.pod_ip = None

        pod = PodSummary.from_k8s_object(obj)

        assert pod.phase == "Pending"
        assert pod.node_name is None
        assert pod.pod_ip is None
        assert pod.restarts == 0
        assert pod.ready_count == 0
        assert pod.total_count == 1

    def test_from_k8s_object_failed(self) -> None:
        """Test from_k8s_object with failed Pod."""
        obj = MagicMock()
        obj.metadata.name = "failed-pod"
        obj.metadata.namespace = "default"

        obj.spec.node_name = "node-3"
        obj.spec.containers = [MagicMock()]

        cs = MagicMock()
        cs.name = "failed-container"
        cs.image = "app:latest"
        cs.ready = False
        cs.restart_count = 5
        cs.state.running = None
        cs.state.waiting = None
        cs.state.terminated = MagicMock()
        cs.state.terminated.reason = "Error"

        obj.status.container_statuses = [cs]
        obj.status.phase = "Failed"
        obj.status.pod_ip = None

        pod = PodSummary.from_k8s_object(obj)

        assert pod.phase == "Failed"
        assert pod.restarts == 5

    def test_entity_name(self) -> None:
        """Test entity name class variable."""
        assert PodSummary._entity_name == "pod"


@pytest.mark.unit
@pytest.mark.kubernetes
class TestDeploymentSummary:
    """Test DeploymentSummary model."""

    def test_from_k8s_object_complete(self) -> None:
        """Test from_k8s_object with complete Deployment."""
        obj = MagicMock()
        obj.metadata.name = "nginx-deployment"
        obj.metadata.namespace = "default"
        obj.metadata.uid = "uid-deploy-123"
        obj.metadata.creation_timestamp = "2024-01-01T00:00:00Z"
        obj.metadata.labels = {"app": "nginx"}
        obj.metadata.annotations = {}

        obj.spec.replicas = 3
        obj.spec.strategy.type = "RollingUpdate"

        obj.status.ready_replicas = 3
        obj.status.available_replicas = 3
        obj.status.updated_replicas = 3

        deploy = DeploymentSummary.from_k8s_object(obj)

        assert deploy.name == "nginx-deployment"
        assert deploy.replicas == 3
        assert deploy.ready_replicas == 3
        assert deploy.available_replicas == 3
        assert deploy.updated_replicas == 3
        assert deploy.strategy == "RollingUpdate"

    def test_from_k8s_object_recreate_strategy(self) -> None:
        """Test from_k8s_object with Recreate strategy."""
        obj = MagicMock()
        obj.metadata.name = "app-deployment"
        obj.metadata.namespace = "production"

        obj.spec.replicas = 5
        obj.spec.strategy.type = "Recreate"

        obj.status.ready_replicas = 5
        obj.status.available_replicas = 5
        obj.status.updated_replicas = 5

        deploy = DeploymentSummary.from_k8s_object(obj)

        assert deploy.strategy == "Recreate"

    def test_from_k8s_object_updating(self) -> None:
        """Test from_k8s_object during rolling update."""
        obj = MagicMock()
        obj.metadata.name = "updating-deployment"
        obj.metadata.namespace = "default"

        obj.spec.replicas = 10
        obj.spec.strategy.type = "RollingUpdate"

        obj.status.ready_replicas = 8
        obj.status.available_replicas = 8
        obj.status.updated_replicas = 5

        deploy = DeploymentSummary.from_k8s_object(obj)

        assert deploy.replicas == 10
        assert deploy.ready_replicas == 8
        assert deploy.updated_replicas == 5

    def test_from_k8s_object_minimal(self) -> None:
        """Test from_k8s_object with minimal Deployment."""
        obj = MagicMock()
        obj.metadata.name = "minimal-deployment"

        obj.spec.replicas = None
        obj.spec.strategy.type = None

        obj.status.ready_replicas = None
        obj.status.available_replicas = None
        obj.status.updated_replicas = None

        deploy = DeploymentSummary.from_k8s_object(obj)

        assert deploy.replicas == 0
        assert deploy.ready_replicas == 0
        assert deploy.available_replicas == 0
        assert deploy.updated_replicas == 0

    def test_entity_name(self) -> None:
        """Test entity name class variable."""
        assert DeploymentSummary._entity_name == "deployment"


@pytest.mark.unit
@pytest.mark.kubernetes
class TestStatefulSetSummary:
    """Test StatefulSetSummary model."""

    def test_from_k8s_object_complete(self) -> None:
        """Test from_k8s_object with complete StatefulSet."""
        obj = MagicMock()
        obj.metadata.name = "database-sts"
        obj.metadata.namespace = "production"
        obj.metadata.uid = "uid-sts-123"
        obj.metadata.creation_timestamp = "2024-01-01T00:00:00Z"
        obj.metadata.labels = {"app": "db"}
        obj.metadata.annotations = {}

        obj.spec.replicas = 3
        obj.spec.service_name = "database-headless"

        obj.status.ready_replicas = 3

        sts = StatefulSetSummary.from_k8s_object(obj)

        assert sts.name == "database-sts"
        assert sts.replicas == 3
        assert sts.ready_replicas == 3
        assert sts.service_name == "database-headless"

    def test_from_k8s_object_scaling(self) -> None:
        """Test from_k8s_object during scaling."""
        obj = MagicMock()
        obj.metadata.name = "scaling-sts"
        obj.metadata.namespace = "default"

        obj.spec.replicas = 5
        obj.spec.service_name = "app-svc"

        obj.status.ready_replicas = 3

        sts = StatefulSetSummary.from_k8s_object(obj)

        assert sts.replicas == 5
        assert sts.ready_replicas == 3

    def test_from_k8s_object_minimal(self) -> None:
        """Test from_k8s_object with minimal StatefulSet."""
        obj = MagicMock()
        obj.metadata.name = "minimal-sts"

        obj.spec.replicas = None
        obj.spec.service_name = None

        obj.status.ready_replicas = None

        sts = StatefulSetSummary.from_k8s_object(obj)

        assert sts.replicas == 0
        assert sts.ready_replicas == 0
        assert sts.service_name is None

    def test_entity_name(self) -> None:
        """Test entity name class variable."""
        assert StatefulSetSummary._entity_name == "statefulset"


@pytest.mark.unit
@pytest.mark.kubernetes
class TestDaemonSetSummary:
    """Test DaemonSetSummary model."""

    def test_from_k8s_object_complete(self) -> None:
        """Test from_k8s_object with complete DaemonSet."""
        obj = MagicMock()
        obj.metadata.name = "node-logger"
        obj.metadata.namespace = "kube-system"
        obj.metadata.uid = "uid-ds-123"
        obj.metadata.creation_timestamp = "2024-01-01T00:00:00Z"
        obj.metadata.labels = {"app": "logger"}
        obj.metadata.annotations = {}

        obj.spec.template.spec.node_selector = {"disk": "ssd"}

        obj.status.desired_number_scheduled = 5
        obj.status.current_number_scheduled = 5
        obj.status.number_ready = 5

        ds = DaemonSetSummary.from_k8s_object(obj)

        assert ds.name == "node-logger"
        assert ds.desired_number_scheduled == 5
        assert ds.current_number_scheduled == 5
        assert ds.number_ready == 5
        assert ds.node_selector == {"disk": "ssd"}

    def test_from_k8s_object_partial_rollout(self) -> None:
        """Test from_k8s_object during rollout."""
        obj = MagicMock()
        obj.metadata.name = "rollout-ds"
        obj.metadata.namespace = "default"

        obj.spec.template.spec.node_selector = None

        obj.status.desired_number_scheduled = 10
        obj.status.current_number_scheduled = 7
        obj.status.number_ready = 6

        ds = DaemonSetSummary.from_k8s_object(obj)

        assert ds.desired_number_scheduled == 10
        assert ds.current_number_scheduled == 7
        assert ds.number_ready == 6

    def test_from_k8s_object_no_selector(self) -> None:
        """Test from_k8s_object with no node selector."""
        obj = MagicMock()
        obj.metadata.name = "all-nodes-ds"
        obj.metadata.namespace = "default"

        obj.spec.template.spec.node_selector = None

        obj.status.desired_number_scheduled = 3
        obj.status.current_number_scheduled = 3
        obj.status.number_ready = 3

        ds = DaemonSetSummary.from_k8s_object(obj)

        assert ds.node_selector is None

    def test_from_k8s_object_minimal(self) -> None:
        """Test from_k8s_object with minimal DaemonSet."""
        obj = MagicMock()
        obj.metadata.name = "minimal-ds"

        obj.spec.template.spec.node_selector = None

        obj.status.desired_number_scheduled = None
        obj.status.current_number_scheduled = None
        obj.status.number_ready = None

        ds = DaemonSetSummary.from_k8s_object(obj)

        assert ds.desired_number_scheduled == 0
        assert ds.current_number_scheduled == 0
        assert ds.number_ready == 0

    def test_entity_name(self) -> None:
        """Test entity name class variable."""
        assert DaemonSetSummary._entity_name == "daemonset"


@pytest.mark.unit
@pytest.mark.kubernetes
class TestReplicaSetSummary:
    """Test ReplicaSetSummary model."""

    def test_from_k8s_object_complete(self) -> None:
        """Test from_k8s_object with complete ReplicaSet."""
        obj = MagicMock()
        obj.metadata.name = "nginx-rs-abc123"
        obj.metadata.namespace = "default"
        obj.metadata.uid = "uid-rs-123"
        obj.metadata.creation_timestamp = "2024-01-01T00:00:00Z"
        obj.metadata.labels = {"app": "nginx"}
        obj.metadata.annotations = {}

        # Owner references
        owner = MagicMock()
        owner.api_version = "apps/v1"
        owner.kind = "Deployment"
        owner.name = "nginx-deployment"
        owner.uid = "uid-deploy-456"

        obj.metadata.owner_references = [owner]

        obj.spec.replicas = 3
        obj.status.ready_replicas = 3

        rs = ReplicaSetSummary.from_k8s_object(obj)

        assert rs.name == "nginx-rs-abc123"
        assert rs.replicas == 3
        assert rs.ready_replicas == 3
        assert len(rs.owner_references) == 1
        assert rs.owner_references[0].kind == "Deployment"

    def test_from_k8s_object_no_owners(self) -> None:
        """Test from_k8s_object with no owner references."""
        obj = MagicMock()
        obj.metadata.name = "standalone-rs"
        obj.metadata.namespace = "default"

        obj.metadata.owner_references = None

        obj.spec.replicas = 2
        obj.status.ready_replicas = 2

        rs = ReplicaSetSummary.from_k8s_object(obj)

        assert rs.owner_references == []

    def test_from_k8s_object_scaling(self) -> None:
        """Test from_k8s_object during scaling."""
        obj = MagicMock()
        obj.metadata.name = "scaling-rs"
        obj.metadata.namespace = "production"

        obj.metadata.owner_references = []

        obj.spec.replicas = 10
        obj.status.ready_replicas = 7

        rs = ReplicaSetSummary.from_k8s_object(obj)

        assert rs.replicas == 10
        assert rs.ready_replicas == 7

    def test_from_k8s_object_minimal(self) -> None:
        """Test from_k8s_object with minimal ReplicaSet."""
        obj = MagicMock()
        obj.metadata.name = "minimal-rs"

        obj.metadata.owner_references = None

        obj.spec.replicas = None
        obj.status.ready_replicas = None

        rs = ReplicaSetSummary.from_k8s_object(obj)

        assert rs.replicas == 0
        assert rs.ready_replicas == 0

    def test_entity_name(self) -> None:
        """Test entity name class variable."""
        assert ReplicaSetSummary._entity_name == "replicaset"
