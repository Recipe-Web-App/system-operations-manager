"""Unit tests for Kubernetes cluster resource models."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from system_operations_manager.integrations.kubernetes.models.cluster import (
    EventSummary,
    NamespaceSummary,
    NodeSummary,
)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestNamespaceSummary:
    """Test NamespaceSummary model."""

    def test_from_k8s_object_complete(self) -> None:
        """Test from_k8s_object with complete namespace."""
        obj = MagicMock()
        obj.metadata.name = "production"
        obj.metadata.namespace = None
        obj.metadata.uid = "uid-ns-123"
        obj.metadata.creation_timestamp = "2024-01-01T00:00:00Z"
        obj.metadata.labels = {"env": "prod"}
        obj.metadata.annotations = {"description": "Production namespace"}
        obj.status.phase = "Active"

        ns = NamespaceSummary.from_k8s_object(obj)

        assert ns.name == "production"
        assert ns.uid == "uid-ns-123"
        assert ns.creation_timestamp == "2024-01-01T00:00:00Z"
        assert ns.labels == {"env": "prod"}
        assert ns.annotations == {"description": "Production namespace"}
        assert ns.status == "Active"

    def test_from_k8s_object_minimal(self) -> None:
        """Test from_k8s_object with minimal namespace."""
        obj = MagicMock()
        obj.metadata.name = "default"
        obj.metadata.uid = None
        obj.metadata.creation_timestamp = None
        obj.metadata.labels = None
        obj.metadata.annotations = None
        obj.status.phase = None

        ns = NamespaceSummary.from_k8s_object(obj)

        assert ns.name == "default"
        assert ns.uid is None
        assert ns.labels is None
        assert ns.status == "Active"

    def test_from_k8s_object_terminating(self) -> None:
        """Test from_k8s_object with terminating namespace."""
        obj = MagicMock()
        obj.metadata.name = "old-namespace"
        obj.metadata.namespace = None
        obj.metadata.uid = None
        obj.metadata.creation_timestamp = None
        obj.metadata.labels = None
        obj.metadata.annotations = None
        obj.status.phase = "Terminating"

        ns = NamespaceSummary.from_k8s_object(obj)

        assert ns.name == "old-namespace"
        assert ns.status == "Terminating"

    def test_entity_name(self) -> None:
        """Test entity name class variable."""
        assert NamespaceSummary._entity_name == "namespace"


@pytest.mark.unit
@pytest.mark.kubernetes
class TestNodeSummary:
    """Test NodeSummary model."""

    def test_from_k8s_object_complete(self) -> None:
        """Test from_k8s_object with complete node."""
        obj = MagicMock()
        obj.metadata.name = "node-1"
        obj.metadata.uid = "uid-node-123"
        obj.metadata.creation_timestamp = "2024-01-01T00:00:00Z"
        obj.metadata.labels = {
            "node-role.kubernetes.io/control-plane": "",
            "node-role.kubernetes.io/master": "",
            "kubernetes.io/hostname": "node-1",
        }
        obj.metadata.annotations = {}

        # Status conditions
        ready_condition = MagicMock()
        ready_condition.type = "Ready"
        ready_condition.status = "True"
        obj.status.conditions = [ready_condition]

        # Addresses
        internal_addr = MagicMock()
        internal_addr.type = "InternalIP"
        internal_addr.address = "192.168.1.10"
        obj.status.addresses = [internal_addr]

        # Node info
        obj.status.node_info.kubelet_version = "v1.28.0"
        obj.status.node_info.os_image = "Ubuntu 22.04 LTS"
        obj.status.node_info.kernel_version = "5.15.0-58-generic"
        obj.status.node_info.container_runtime_version = "containerd://1.6.8"

        # Capacity
        obj.status.capacity = {"cpu": "4", "memory": "16Gi", "pods": "110"}

        node = NodeSummary.from_k8s_object(obj)

        assert node.name == "node-1"
        assert node.status == "Ready"
        assert "control-plane" in node.roles
        assert "master" in node.roles
        assert node.version == "v1.28.0"
        assert node.internal_ip == "192.168.1.10"
        assert node.os_image == "Ubuntu 22.04 LTS"
        assert node.kernel_version == "5.15.0-58-generic"
        assert node.container_runtime == "containerd://1.6.8"
        assert node.cpu_capacity == "4"
        assert node.memory_capacity == "16Gi"
        assert node.pods_capacity == "110"

    def test_from_k8s_object_not_ready(self) -> None:
        """Test from_k8s_object with not ready node."""
        obj = MagicMock()
        obj.metadata.name = "node-2"
        obj.metadata.uid = None
        obj.metadata.creation_timestamp = None
        obj.metadata.labels = {}
        obj.metadata.annotations = None

        ready_condition = MagicMock()
        ready_condition.type = "Ready"
        ready_condition.status = "False"
        obj.status.conditions = [ready_condition]

        obj.status.addresses = []
        obj.status.node_info = None
        obj.status.capacity = {}

        node = NodeSummary.from_k8s_object(obj)

        assert node.status == "NotReady"

    def test_from_k8s_object_no_roles(self) -> None:
        """Test from_k8s_object with node without roles."""
        obj = MagicMock()
        obj.metadata.name = "worker-1"
        obj.metadata.uid = None
        obj.metadata.creation_timestamp = None
        obj.metadata.labels = {"kubernetes.io/hostname": "worker-1"}
        obj.metadata.annotations = None

        obj.status.conditions = []
        obj.status.addresses = []
        obj.status.node_info = None
        obj.status.capacity = {}

        node = NodeSummary.from_k8s_object(obj)

        assert node.roles == ["<none>"]

    def test_from_k8s_object_worker_role(self) -> None:
        """Test from_k8s_object with worker role."""
        obj = MagicMock()
        obj.metadata.name = "worker-2"
        obj.metadata.uid = None
        obj.metadata.creation_timestamp = None
        obj.metadata.labels = {"node-role.kubernetes.io/worker": ""}
        obj.metadata.annotations = None

        obj.status.conditions = []
        obj.status.addresses = []
        obj.status.node_info = None
        obj.status.capacity = {}

        node = NodeSummary.from_k8s_object(obj)

        assert "worker" in node.roles

    def test_from_k8s_object_no_conditions(self) -> None:
        """Test from_k8s_object with no conditions."""
        obj = MagicMock()
        obj.metadata.name = "node-3"
        obj.metadata.uid = None
        obj.metadata.creation_timestamp = None
        obj.metadata.labels = {}
        obj.metadata.annotations = None
        obj.status.conditions = None
        obj.status.addresses = []
        obj.status.node_info = None
        obj.status.capacity = {}

        node = NodeSummary.from_k8s_object(obj)

        assert node.status == "Unknown"

    def test_from_k8s_object_external_ip(self) -> None:
        """Test from_k8s_object extracts internal IP correctly."""
        obj = MagicMock()
        obj.metadata.name = "node-4"
        obj.metadata.uid = None
        obj.metadata.creation_timestamp = None
        obj.metadata.labels = {}
        obj.metadata.annotations = None

        external_addr = MagicMock()
        external_addr.type = "ExternalIP"
        external_addr.address = "203.0.113.10"

        internal_addr = MagicMock()
        internal_addr.type = "InternalIP"
        internal_addr.address = "10.0.1.5"

        obj.status.addresses = [external_addr, internal_addr]
        obj.status.conditions = []
        obj.status.node_info = None
        obj.status.capacity = {}

        node = NodeSummary.from_k8s_object(obj)

        assert node.internal_ip == "10.0.1.5"

    def test_entity_name(self) -> None:
        """Test entity name class variable."""
        assert NodeSummary._entity_name == "node"


@pytest.mark.unit
@pytest.mark.kubernetes
class TestEventSummary:
    """Test EventSummary model."""

    def test_from_k8s_object_complete(self) -> None:
        """Test from_k8s_object with complete event."""
        obj = MagicMock()
        obj.metadata.name = "event-123"
        obj.metadata.namespace = "default"
        obj.metadata.uid = "uid-event-456"
        obj.metadata.creation_timestamp = "2024-01-01T12:00:00Z"

        obj.type = "Warning"
        obj.reason = "FailedScheduling"
        obj.message = "0/3 nodes are available: insufficient cpu."

        obj.source.component = "default-scheduler"

        obj.first_timestamp = "2024-01-01T11:55:00Z"
        obj.last_timestamp = "2024-01-01T12:00:00Z"
        obj.count = 5

        obj.involved_object.kind = "Pod"
        obj.involved_object.name = "test-pod"

        event = EventSummary.from_k8s_object(obj)

        assert event.name == "event-123"
        assert event.namespace == "default"
        assert event.type == "Warning"
        assert event.reason == "FailedScheduling"
        assert event.message is not None and "insufficient cpu" in event.message
        assert event.source_component == "default-scheduler"
        assert event.count == 5
        assert event.involved_object_kind == "Pod"
        assert event.involved_object_name == "test-pod"

    def test_from_k8s_object_normal_event(self) -> None:
        """Test from_k8s_object with normal event."""
        obj = MagicMock()
        obj.metadata.name = "event-456"
        obj.metadata.namespace = "kube-system"
        obj.metadata.uid = None
        obj.metadata.creation_timestamp = None

        obj.type = "Normal"
        obj.reason = "Started"
        obj.message = "Started container nginx"
        obj.source = None
        obj.first_timestamp = None
        obj.last_timestamp = None
        obj.count = 1
        obj.involved_object = None

        event = EventSummary.from_k8s_object(obj)

        assert event.type == "Normal"
        assert event.reason == "Started"
        assert event.count == 1

    def test_from_k8s_object_minimal(self) -> None:
        """Test from_k8s_object with minimal event."""
        obj = MagicMock()
        obj.metadata.name = "event-789"
        obj.metadata.namespace = "default"
        obj.metadata.uid = None
        obj.metadata.creation_timestamp = None

        obj.type = None
        obj.reason = None
        obj.message = None
        obj.source = None
        obj.first_timestamp = None
        obj.last_timestamp = None
        obj.count = None
        obj.involved_object = None

        event = EventSummary.from_k8s_object(obj)

        assert event.name == "event-789"
        assert event.type == "Normal"
        assert event.count == 1

    def test_from_k8s_object_no_source(self) -> None:
        """Test from_k8s_object with no source."""
        obj = MagicMock()
        obj.metadata.name = "event-abc"
        obj.metadata.namespace = None
        obj.metadata.uid = None
        obj.metadata.creation_timestamp = None
        obj.source = None
        obj.involved_object = None
        obj.type = "Normal"
        obj.reason = None
        obj.message = None
        obj.first_timestamp = None
        obj.last_timestamp = None
        obj.count = 1

        event = EventSummary.from_k8s_object(obj)

        assert event.source_component is None

    def test_entity_name(self) -> None:
        """Test entity name class variable."""
        assert EventSummary._entity_name == "event"
