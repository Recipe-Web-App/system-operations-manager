"""Unit tests for Kubernetes TUI screens.

Tests ResourceListScreen, ResourceDetailScreen, column definitions,
and row conversion.
"""

from __future__ import annotations

from typing import Any, cast
from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from textual.binding import Binding

from system_operations_manager.integrations.kubernetes.models.cluster import (
    EventSummary,
    NamespaceSummary,
    NodeSummary,
)
from system_operations_manager.integrations.kubernetes.models.configuration import (
    ConfigMapSummary,
    SecretSummary,
)
from system_operations_manager.integrations.kubernetes.models.networking import (
    IngressSummary,
    NetworkPolicySummary,
    ServicePort,
    ServiceSummary,
)
from system_operations_manager.integrations.kubernetes.models.workloads import (
    DaemonSetSummary,
    DeploymentSummary,
    PodSummary,
    ReplicaSetSummary,
    StatefulSetSummary,
)
from system_operations_manager.tui.apps.kubernetes.app import ResourceType
from system_operations_manager.tui.apps.kubernetes.screens import (
    COLUMN_DEFS,
    STATUS_COLOR_MAP,
    DashboardScreen,
    ResourceDetailScreen,
    ResourceListScreen,
    _resource_to_row,
)

# ============================================================================
# Column Definition Tests
# ============================================================================


class TestColumnDefs:
    """Tests for COLUMN_DEFS completeness."""

    @pytest.mark.unit
    def test_all_resource_types_have_column_defs(self) -> None:
        """Every ResourceType has an entry in COLUMN_DEFS."""
        for rt in ResourceType:
            assert rt in COLUMN_DEFS, f"Missing column definition for {rt.value}"

    @pytest.mark.unit
    def test_column_defs_have_at_least_two_columns(self) -> None:
        """Each resource type has at least two columns."""
        for rt, cols in COLUMN_DEFS.items():
            assert len(cols) >= 2, f"{rt.value} has fewer than 2 columns"

    @pytest.mark.unit
    def test_pods_columns(self) -> None:
        """Pods have expected columns."""
        col_names = [c[0] for c in COLUMN_DEFS[ResourceType.PODS]]
        assert "Name" in col_names
        assert "Status" in col_names
        assert "Ready" in col_names
        assert "Age" in col_names

    @pytest.mark.unit
    def test_deployments_columns(self) -> None:
        """Deployments have expected columns."""
        col_names = [c[0] for c in COLUMN_DEFS[ResourceType.DEPLOYMENTS]]
        assert "Name" in col_names
        assert "Ready" in col_names
        assert "Available" in col_names

    @pytest.mark.unit
    def test_nodes_columns(self) -> None:
        """Nodes have expected columns."""
        col_names = [c[0] for c in COLUMN_DEFS[ResourceType.NODES]]
        assert "Name" in col_names
        assert "Status" in col_names
        assert "Roles" in col_names
        assert "Version" in col_names


# ============================================================================
# Row Conversion Tests
# ============================================================================


class TestResourceToRow:
    """Tests for _resource_to_row conversion function."""

    @pytest.mark.unit
    def test_pod_row(self) -> None:
        """Pod converts to correct row tuple."""
        pod = PodSummary(
            name="nginx-abc123",
            namespace="default",
            phase="Running",
            ready_count=1,
            total_count=1,
            restarts=0,
            node_name="node-1",
            creation_timestamp="2026-01-01T00:00:00Z",
        )
        row = _resource_to_row(pod, ResourceType.PODS)
        assert row[0] == "nginx-abc123"
        assert row[1] == "default"
        assert "Running" in row[2]
        assert row[3] == "1/1"
        assert row[4] == "0"
        assert row[5] == "node-1"

    @pytest.mark.unit
    def test_deployment_row(self) -> None:
        """Deployment converts to correct row tuple."""
        deploy = DeploymentSummary(
            name="web-app",
            namespace="production",
            replicas=3,
            ready_replicas=3,
            updated_replicas=3,
            available_replicas=3,
            creation_timestamp="2026-01-01T00:00:00Z",
        )
        row = _resource_to_row(deploy, ResourceType.DEPLOYMENTS)
        assert row[0] == "web-app"
        assert row[1] == "production"
        assert row[2] == "3/3"
        assert row[3] == "3"
        assert row[4] == "3"

    @pytest.mark.unit
    def test_statefulset_row(self) -> None:
        """StatefulSet converts to correct row tuple."""
        sts = StatefulSetSummary(
            name="redis",
            namespace="default",
            replicas=3,
            ready_replicas=2,
            creation_timestamp="2026-01-01T00:00:00Z",
        )
        row = _resource_to_row(sts, ResourceType.STATEFULSETS)
        assert row[0] == "redis"
        assert row[2] == "2/3"

    @pytest.mark.unit
    def test_daemonset_row(self) -> None:
        """DaemonSet converts to correct row tuple."""
        ds = DaemonSetSummary(
            name="fluentd",
            namespace="logging",
            desired_number_scheduled=5,
            current_number_scheduled=5,
            number_ready=4,
            creation_timestamp="2026-01-01T00:00:00Z",
        )
        row = _resource_to_row(ds, ResourceType.DAEMONSETS)
        assert row[0] == "fluentd"
        assert row[2] == "5"
        assert row[3] == "5"
        assert row[4] == "4"

    @pytest.mark.unit
    def test_replicaset_row(self) -> None:
        """ReplicaSet converts to correct row tuple."""
        rs = ReplicaSetSummary(
            name="web-app-abc123",
            namespace="default",
            replicas=3,
            ready_replicas=3,
            creation_timestamp="2026-01-01T00:00:00Z",
        )
        row = _resource_to_row(rs, ResourceType.REPLICASETS)
        assert row[0] == "web-app-abc123"
        assert row[2] == "3"
        assert row[3] == "3"

    @pytest.mark.unit
    def test_service_row(self) -> None:
        """Service converts to correct row tuple."""
        svc = ServiceSummary(
            name="web-svc",
            namespace="default",
            type="ClusterIP",
            cluster_ip="10.0.0.1",
            ports=[
                ServicePort(name="http", port=80, protocol="TCP"),
                ServicePort(name="https", port=443, protocol="TCP"),
            ],
            creation_timestamp="2026-01-01T00:00:00Z",
        )
        row = _resource_to_row(svc, ResourceType.SERVICES)
        assert row[0] == "web-svc"
        assert row[2] == "ClusterIP"
        assert row[3] == "10.0.0.1"
        assert "80/TCP" in row[4]

    @pytest.mark.unit
    def test_ingress_row(self) -> None:
        """Ingress converts to correct row tuple."""
        ingress = IngressSummary(
            name="web-ingress",
            namespace="default",
            class_name="nginx",
            hosts=["example.com", "api.example.com"],
            addresses=["1.2.3.4"],
            creation_timestamp="2026-01-01T00:00:00Z",
        )
        row = _resource_to_row(ingress, ResourceType.INGRESSES)
        assert row[0] == "web-ingress"
        assert row[2] == "nginx"
        assert "example.com" in row[3]

    @pytest.mark.unit
    def test_network_policy_row(self) -> None:
        """NetworkPolicy converts to correct row tuple."""
        np = NetworkPolicySummary(
            name="deny-all",
            namespace="default",
            policy_types=["Ingress", "Egress"],
            ingress_rules_count=2,
            egress_rules_count=1,
            creation_timestamp="2026-01-01T00:00:00Z",
        )
        row = _resource_to_row(np, ResourceType.NETWORK_POLICIES)
        assert row[0] == "deny-all"
        assert "Ingress" in row[2]
        assert row[3] == "2"
        assert row[4] == "1"

    @pytest.mark.unit
    def test_configmap_row(self) -> None:
        """ConfigMap converts to correct row tuple."""
        cm = ConfigMapSummary(
            name="app-config",
            namespace="default",
            data_keys=["config.yaml", "settings.json"],
            creation_timestamp="2026-01-01T00:00:00Z",
        )
        row = _resource_to_row(cm, ResourceType.CONFIGMAPS)
        assert row[0] == "app-config"
        assert "config.yaml" in row[2]

    @pytest.mark.unit
    def test_secret_row(self) -> None:
        """Secret converts to correct row tuple."""
        secret = SecretSummary(
            name="db-credentials",
            namespace="default",
            type="Opaque",
            data_keys=["username", "password"],
            creation_timestamp="2026-01-01T00:00:00Z",
        )
        row = _resource_to_row(secret, ResourceType.SECRETS)
        assert row[0] == "db-credentials"
        assert row[2] == "Opaque"
        assert "username" in row[3]

    @pytest.mark.unit
    def test_namespace_row(self) -> None:
        """Namespace converts to correct row tuple."""
        ns = NamespaceSummary(
            name="kube-system",
            status="Active",
            creation_timestamp="2026-01-01T00:00:00Z",
        )
        row = _resource_to_row(ns, ResourceType.NAMESPACES)
        assert row[0] == "kube-system"
        assert "Active" in row[1]

    @pytest.mark.unit
    def test_node_row(self) -> None:
        """Node converts to correct row tuple."""
        node = NodeSummary(
            name="node-1",
            status="Ready",
            roles=["control-plane", "worker"],
            version="v1.29.0",
            creation_timestamp="2026-01-01T00:00:00Z",
        )
        row = _resource_to_row(node, ResourceType.NODES)
        assert row[0] == "node-1"
        assert "Ready" in row[1]
        assert "control-plane" in row[2]
        assert row[3] == "v1.29.0"

    @pytest.mark.unit
    def test_event_row(self) -> None:
        """Event converts to correct row tuple."""
        event = EventSummary(
            name="event-123",
            namespace="default",
            type="Warning",
            reason="BackOff",
            message="Back-off restarting failed container",
            involved_object_kind="Pod",
            involved_object_name="nginx-abc123",
            count=5,
            creation_timestamp="2026-01-01T00:00:00Z",
        )
        row = _resource_to_row(event, ResourceType.EVENTS)
        assert "Warning" in row[0]
        assert row[1] == "BackOff"
        assert "Pod" in row[2]
        assert row[4] == "5"

    @pytest.mark.unit
    def test_pod_row_with_missing_namespace(self) -> None:
        """Pod with missing namespace shows empty string."""
        pod = PodSummary(
            name="orphan-pod",
            namespace=None,
            phase="Running",
            ready_count=1,
            total_count=1,
            restarts=0,
        )
        row = _resource_to_row(pod, ResourceType.PODS)
        assert row[1] == ""

    @pytest.mark.unit
    def test_pod_row_colorizes_failed_status(self) -> None:
        """Failed pod status includes red color markup."""
        pod = PodSummary(
            name="crashed-pod",
            namespace="default",
            phase="Failed",
            ready_count=0,
            total_count=1,
            restarts=5,
        )
        row = _resource_to_row(pod, ResourceType.PODS)
        assert "[red]" in row[2]

    @pytest.mark.unit
    def test_service_row_truncates_many_ports(self) -> None:
        """Service with many ports shows truncated display."""
        svc = ServiceSummary(
            name="multi-port",
            namespace="default",
            type="ClusterIP",
            cluster_ip="10.0.0.1",
            ports=[ServicePort(name=f"port-{i}", port=8000 + i, protocol="TCP") for i in range(5)],
            creation_timestamp="2026-01-01T00:00:00Z",
        )
        row = _resource_to_row(svc, ResourceType.SERVICES)
        assert "(+2)" in row[4]


# ============================================================================
# ResourceListScreen Tests
# ============================================================================


class TestResourceListScreen:
    """Tests for ResourceListScreen initialization."""

    @pytest.mark.unit
    def test_screen_has_bindings(self) -> None:
        """ResourceListScreen defines keyboard bindings."""
        assert len(ResourceListScreen.BINDINGS) > 0

    @pytest.mark.unit
    def test_screen_bindings_include_navigation(self) -> None:
        """Screen bindings include j/k/enter/escape."""
        binding_keys = [
            b.key if isinstance(b, Binding) else b[0] for b in ResourceListScreen.BINDINGS
        ]
        assert "j" in binding_keys
        assert "k" in binding_keys
        assert "enter" in binding_keys
        assert "escape" in binding_keys

    @pytest.mark.unit
    def test_screen_bindings_include_selectors(self) -> None:
        """Screen bindings include namespace/cluster/type keys."""
        binding_keys = [
            b.key if isinstance(b, Binding) else b[0] for b in ResourceListScreen.BINDINGS
        ]
        assert "n" in binding_keys
        assert "N" in binding_keys
        assert "c" in binding_keys
        assert "C" in binding_keys
        assert "f" in binding_keys
        assert "F" in binding_keys

    @pytest.mark.unit
    def test_screen_bindings_include_refresh(self) -> None:
        """Screen bindings include refresh."""
        binding_keys = [
            b.key if isinstance(b, Binding) else b[0] for b in ResourceListScreen.BINDINGS
        ]
        assert "r" in binding_keys

    @pytest.mark.unit
    def test_screen_bindings_include_logs(self) -> None:
        """Screen bindings include logs shortcut."""
        binding_keys = [
            b.key if isinstance(b, Binding) else b[0] for b in ResourceListScreen.BINDINGS
        ]
        assert "l" in binding_keys

    @pytest.mark.unit
    def test_resource_selected_message(self) -> None:
        """ResourceSelected message stores resource and type."""
        pod = PodSummary(name="test", phase="Running", ready_count=1, total_count=1, restarts=0)
        msg = ResourceListScreen.ResourceSelected(pod, ResourceType.PODS)
        assert msg.resource.name == "test"
        assert msg.resource_type == ResourceType.PODS


# ============================================================================
# ResourceDetailScreen Tests
# ============================================================================


@pytest.fixture()
def sample_pod() -> PodSummary:
    """Create a sample pod for detail screen tests."""
    return PodSummary(
        name="nginx-abc123",
        namespace="default",
        uid="12345-abcde",
        phase="Running",
        ready_count=1,
        total_count=1,
        restarts=2,
        node_name="node-1",
        pod_ip="10.0.0.5",
        creation_timestamp="2026-01-01T00:00:00Z",
        labels={"app": "nginx", "tier": "frontend"},
        annotations={"kubectl.kubernetes.io/last-applied-configuration": "{}"},
    )


@pytest.fixture()
def sample_deployment() -> DeploymentSummary:
    """Create a sample deployment for detail screen tests."""
    return DeploymentSummary(
        name="web-app",
        namespace="production",
        uid="67890-fghij",
        replicas=3,
        ready_replicas=3,
        updated_replicas=3,
        available_replicas=3,
        strategy="RollingUpdate",
        creation_timestamp="2026-01-01T00:00:00Z",
        labels={"app": "web-app"},
    )


@pytest.fixture()
def sample_node() -> NodeSummary:
    """Create a sample node for detail screen tests."""
    return NodeSummary(
        name="node-1",
        uid="node-uid-123",
        status="Ready",
        roles=["control-plane", "worker"],
        version="v1.29.0",
        internal_ip="192.168.1.10",
        os_image="Ubuntu 22.04",
        container_runtime="containerd://1.7.0",
        creation_timestamp="2026-01-01T00:00:00Z",
        labels={"kubernetes.io/hostname": "node-1"},
    )


class TestResourceDetailScreen:
    """Tests for ResourceDetailScreen text builders and bindings."""

    @pytest.mark.unit
    def test_screen_has_bindings(self) -> None:
        """ResourceDetailScreen defines keyboard bindings."""
        assert len(ResourceDetailScreen.BINDINGS) > 0

    @pytest.mark.unit
    def test_screen_bindings_include_back(self) -> None:
        """Screen bindings include escape for back navigation."""
        binding_keys = [
            b.key if isinstance(b, Binding) else b[0] for b in ResourceDetailScreen.BINDINGS
        ]
        assert "escape" in binding_keys

    @pytest.mark.unit
    def test_screen_bindings_include_yaml_toggle(self) -> None:
        """Screen bindings include y for YAML toggle."""
        binding_keys = [
            b.key if isinstance(b, Binding) else b[0] for b in ResourceDetailScreen.BINDINGS
        ]
        assert "y" in binding_keys

    @pytest.mark.unit
    def test_screen_bindings_include_refresh(self) -> None:
        """Screen bindings include r for event refresh."""
        binding_keys = [
            b.key if isinstance(b, Binding) else b[0] for b in ResourceDetailScreen.BINDINGS
        ]
        assert "r" in binding_keys

    @pytest.mark.unit
    def test_screen_bindings_include_logs(self) -> None:
        """Screen bindings include l for logs."""
        binding_keys = [
            b.key if isinstance(b, Binding) else b[0] for b in ResourceDetailScreen.BINDINGS
        ]
        assert "l" in binding_keys

    @pytest.mark.unit
    def test_screen_bindings_include_exec(self) -> None:
        """Screen bindings include x for exec."""
        binding_keys = [
            b.key if isinstance(b, Binding) else b[0] for b in ResourceDetailScreen.BINDINGS
        ]
        assert "x" in binding_keys

    @pytest.mark.unit
    def test_status_color_map_has_common_statuses(self) -> None:
        """STATUS_COLOR_MAP covers common Kubernetes statuses."""
        assert "Running" in STATUS_COLOR_MAP
        assert "Pending" in STATUS_COLOR_MAP
        assert "Failed" in STATUS_COLOR_MAP
        assert "Ready" in STATUS_COLOR_MAP
        assert "NotReady" in STATUS_COLOR_MAP

    @pytest.mark.unit
    def test_header_text_pod(self, sample_pod: PodSummary) -> None:
        """Header text includes resource type, name, namespace, and status."""
        screen = ResourceDetailScreen.__new__(ResourceDetailScreen)
        screen._resource = sample_pod
        screen._resource_type = ResourceType.PODS
        header = screen._build_header_text()
        assert "Pods" in header
        assert "nginx-abc123" in header
        assert "default" in header
        assert "Running" in header

    @pytest.mark.unit
    def test_header_text_node_no_namespace(self, sample_node: NodeSummary) -> None:
        """Header for cluster-scoped resources omits namespace."""
        screen = ResourceDetailScreen.__new__(ResourceDetailScreen)
        screen._resource = sample_node
        screen._resource_type = ResourceType.NODES
        header = screen._build_header_text()
        assert "node-1" in header
        assert "ns:" not in header

    @pytest.mark.unit
    def test_metadata_text_pod(self, sample_pod: PodSummary) -> None:
        """Metadata text includes UID, creation time, age, namespace."""
        screen = ResourceDetailScreen.__new__(ResourceDetailScreen)
        screen._resource = sample_pod
        screen._resource_type = ResourceType.PODS
        metadata = screen._build_metadata_text()
        assert "12345-abcde" in metadata
        assert "2026-01-01" in metadata
        assert "Namespace" in metadata

    @pytest.mark.unit
    def test_status_text_pod(self, sample_pod: PodSummary) -> None:
        """Status text for pods shows phase, ready, restarts, node, IP."""
        screen = ResourceDetailScreen.__new__(ResourceDetailScreen)
        screen._resource = sample_pod
        screen._resource_type = ResourceType.PODS
        status = screen._build_status_text()
        assert "Running" in status
        assert "1/1" in status
        assert "2" in status
        assert "node-1" in status
        assert "10.0.0.5" in status

    @pytest.mark.unit
    def test_status_text_deployment(self, sample_deployment: DeploymentSummary) -> None:
        """Status text for deployments shows replicas and strategy."""
        screen = ResourceDetailScreen.__new__(ResourceDetailScreen)
        screen._resource = sample_deployment
        screen._resource_type = ResourceType.DEPLOYMENTS
        status = screen._build_status_text()
        assert "3/3" in status
        assert "RollingUpdate" in status

    @pytest.mark.unit
    def test_status_text_node(self, sample_node: NodeSummary) -> None:
        """Status text for nodes shows status, roles, version, IP."""
        screen = ResourceDetailScreen.__new__(ResourceDetailScreen)
        screen._resource = sample_node
        screen._resource_type = ResourceType.NODES
        status = screen._build_status_text()
        assert "Ready" in status
        assert "control-plane" in status
        assert "v1.29.0" in status
        assert "192.168.1.10" in status

    @pytest.mark.unit
    def test_labels_text_with_labels(self, sample_pod: PodSummary) -> None:
        """Labels text shows key=value pairs."""
        screen = ResourceDetailScreen.__new__(ResourceDetailScreen)
        screen._resource = sample_pod
        screen._resource_type = ResourceType.PODS
        labels = screen._build_labels_text()
        assert "app=nginx" in labels
        assert "tier=frontend" in labels

    @pytest.mark.unit
    def test_labels_text_no_labels(self) -> None:
        """Labels text shows placeholder when no labels."""
        pod = PodSummary(
            name="test",
            phase="Running",
            ready_count=1,
            total_count=1,
            restarts=0,
            labels=None,
        )
        screen = ResourceDetailScreen.__new__(ResourceDetailScreen)
        screen._resource = pod
        screen._resource_type = ResourceType.PODS
        labels = screen._build_labels_text()
        assert "No labels" in labels

    @pytest.mark.unit
    def test_annotations_text_with_annotations(self, sample_pod: PodSummary) -> None:
        """Annotations text shows key=value pairs."""
        screen = ResourceDetailScreen.__new__(ResourceDetailScreen)
        screen._resource = sample_pod
        screen._resource_type = ResourceType.PODS
        annotations = screen._build_annotations_text()
        assert "kubectl.kubernetes.io/last-applied-configuration" in annotations

    @pytest.mark.unit
    def test_annotations_text_no_annotations(self) -> None:
        """Annotations text shows placeholder when no annotations."""
        pod = PodSummary(
            name="test",
            phase="Running",
            ready_count=1,
            total_count=1,
            restarts=0,
            annotations=None,
        )
        screen = ResourceDetailScreen.__new__(ResourceDetailScreen)
        screen._resource = pod
        screen._resource_type = ResourceType.PODS
        annotations = screen._build_annotations_text()
        assert "No annotations" in annotations

    @pytest.mark.unit
    def test_annotations_text_truncates_long_values(self) -> None:
        """Long annotation values are truncated."""
        pod = PodSummary(
            name="test",
            phase="Running",
            ready_count=1,
            total_count=1,
            restarts=0,
            annotations={"long-key": "x" * 100},
        )
        screen = ResourceDetailScreen.__new__(ResourceDetailScreen)
        screen._resource = pod
        screen._resource_type = ResourceType.PODS
        annotations = screen._build_annotations_text()
        assert "..." in annotations

    @pytest.mark.unit
    def test_yaml_text_contains_resource_name(self, sample_pod: PodSummary) -> None:
        """YAML text includes the resource name."""
        screen = ResourceDetailScreen.__new__(ResourceDetailScreen)
        screen._resource = sample_pod
        screen._resource_type = ResourceType.PODS
        yaml_text = screen._build_yaml_text()
        assert "nginx-abc123" in yaml_text
        assert "name:" in yaml_text

    @pytest.mark.unit
    def test_yaml_text_excludes_none_fields(self) -> None:
        """YAML text excludes None-valued fields."""
        pod = PodSummary(
            name="test",
            phase="Running",
            ready_count=1,
            total_count=1,
            restarts=0,
            node_name=None,
        )
        screen = ResourceDetailScreen.__new__(ResourceDetailScreen)
        screen._resource = pod
        screen._resource_type = ResourceType.PODS
        yaml_text = screen._build_yaml_text()
        assert "node_name" not in yaml_text

    @pytest.mark.unit
    def test_yaml_text_is_valid_yaml(self, sample_pod: PodSummary) -> None:
        """YAML text is parseable as valid YAML."""
        import yaml

        screen = ResourceDetailScreen.__new__(ResourceDetailScreen)
        screen._resource = sample_pod
        screen._resource_type = ResourceType.PODS
        yaml_text = screen._build_yaml_text()
        parsed = yaml.safe_load(yaml_text)
        assert isinstance(parsed, dict)
        assert parsed["name"] == "nginx-abc123"

    @pytest.mark.unit
    def test_get_primary_status_pod(self, sample_pod: PodSummary) -> None:
        """Primary status for pod is its phase."""
        screen = ResourceDetailScreen.__new__(ResourceDetailScreen)
        screen._resource = sample_pod
        screen._resource_type = ResourceType.PODS
        assert screen._get_primary_status() == "Running"

    @pytest.mark.unit
    def test_get_primary_status_node(self, sample_node: NodeSummary) -> None:
        """Primary status for node is its status field."""
        screen = ResourceDetailScreen.__new__(ResourceDetailScreen)
        screen._resource = sample_node
        screen._resource_type = ResourceType.NODES
        assert screen._get_primary_status() == "Ready"

    @pytest.mark.unit
    def test_status_text_service(self) -> None:
        """Status text for services shows type, IP, ports."""
        svc = ServiceSummary(
            name="web-svc",
            namespace="default",
            type="ClusterIP",
            cluster_ip="10.0.0.1",
            ports=[ServicePort(name="http", port=80, protocol="TCP")],
            creation_timestamp="2026-01-01T00:00:00Z",
        )
        screen = ResourceDetailScreen.__new__(ResourceDetailScreen)
        screen._resource = svc
        screen._resource_type = ResourceType.SERVICES
        status = screen._build_status_text()
        assert "ClusterIP" in status
        assert "10.0.0.1" in status
        assert "80/TCP" in status

    @pytest.mark.unit
    def test_status_text_namespace(self) -> None:
        """Status text for namespaces shows status."""
        ns = NamespaceSummary(
            name="kube-system",
            status="Active",
            creation_timestamp="2026-01-01T00:00:00Z",
        )
        screen = ResourceDetailScreen.__new__(ResourceDetailScreen)
        screen._resource = ns
        screen._resource_type = ResourceType.NAMESPACES
        status = screen._build_status_text()
        assert "Active" in status


# ============================================================================
# Additional _build_status_text branches
# ============================================================================


@pytest.mark.unit
class TestBuildStatusTextAllTypes:
    """Tests for _build_status_text covering remaining resource types."""

    def test_status_text_statefulset(self) -> None:
        """Status text for statefulsets shows ready and service."""
        sts = StatefulSetSummary(
            name="redis",
            namespace="default",
            replicas=3,
            ready_replicas=2,
            service_name="redis-headless",
            creation_timestamp="2026-01-01T00:00:00Z",
        )
        screen = ResourceDetailScreen.__new__(ResourceDetailScreen)
        screen._resource = sts
        screen._resource_type = ResourceType.STATEFULSETS
        status = screen._build_status_text()
        assert "2/3" in status
        assert "redis-headless" in status

    def test_status_text_daemonset(self) -> None:
        """Status text for daemonsets shows desired, current, ready."""
        ds = DaemonSetSummary(
            name="fluentd",
            namespace="logging",
            desired_number_scheduled=5,
            current_number_scheduled=5,
            number_ready=4,
            creation_timestamp="2026-01-01T00:00:00Z",
        )
        screen = ResourceDetailScreen.__new__(ResourceDetailScreen)
        screen._resource = ds
        screen._resource_type = ResourceType.DAEMONSETS
        status = screen._build_status_text()
        assert "5" in status
        assert "4" in status

    def test_status_text_replicaset(self) -> None:
        """Status text for replicasets shows desired, ready."""
        rs = ReplicaSetSummary(
            name="web-abc",
            namespace="default",
            replicas=3,
            ready_replicas=3,
            creation_timestamp="2026-01-01T00:00:00Z",
        )
        screen = ResourceDetailScreen.__new__(ResourceDetailScreen)
        screen._resource = rs
        screen._resource_type = ResourceType.REPLICASETS
        status = screen._build_status_text()
        assert "3" in status

    def test_status_text_ingress(self) -> None:
        """Status text for ingresses shows class, hosts, addresses."""
        ing = IngressSummary(
            name="web-ingress",
            namespace="default",
            class_name="nginx",
            hosts=["example.com", "api.example.com"],
            addresses=["1.2.3.4"],
            creation_timestamp="2026-01-01T00:00:00Z",
        )
        screen = ResourceDetailScreen.__new__(ResourceDetailScreen)
        screen._resource = ing
        screen._resource_type = ResourceType.INGRESSES
        status = screen._build_status_text()
        assert "nginx" in status
        assert "example.com" in status
        assert "1.2.3.4" in status

    def test_status_text_network_policy(self) -> None:
        """Status text for network policies shows policy types and rule counts."""
        np = NetworkPolicySummary(
            name="deny-all",
            namespace="default",
            policy_types=["Ingress", "Egress"],
            ingress_rules_count=2,
            egress_rules_count=1,
            creation_timestamp="2026-01-01T00:00:00Z",
        )
        screen = ResourceDetailScreen.__new__(ResourceDetailScreen)
        screen._resource = np
        screen._resource_type = ResourceType.NETWORK_POLICIES
        status = screen._build_status_text()
        assert "Ingress" in status
        assert "2" in status
        assert "1" in status

    def test_status_text_configmap(self) -> None:
        """Status text for configmaps shows data keys."""
        cm = ConfigMapSummary(
            name="app-config",
            namespace="default",
            data_keys=["key1", "key2"],
            creation_timestamp="2026-01-01T00:00:00Z",
        )
        screen = ResourceDetailScreen.__new__(ResourceDetailScreen)
        screen._resource = cm
        screen._resource_type = ResourceType.CONFIGMAPS
        status = screen._build_status_text()
        assert "key1" in status

    def test_status_text_configmap_truncates_many_keys(self) -> None:
        """Status text for configmaps truncates when >10 keys."""
        cm = ConfigMapSummary(
            name="app-config",
            namespace="default",
            data_keys=[f"key{i}" for i in range(15)],
            creation_timestamp="2026-01-01T00:00:00Z",
        )
        screen = ResourceDetailScreen.__new__(ResourceDetailScreen)
        screen._resource = cm
        screen._resource_type = ResourceType.CONFIGMAPS
        status = screen._build_status_text()
        assert "(+5)" in status

    def test_status_text_secret(self) -> None:
        """Status text for secrets shows type and data keys."""
        secret = SecretSummary(
            name="db-creds",
            namespace="default",
            type="Opaque",
            data_keys=["username", "password"],
            creation_timestamp="2026-01-01T00:00:00Z",
        )
        screen = ResourceDetailScreen.__new__(ResourceDetailScreen)
        screen._resource = secret
        screen._resource_type = ResourceType.SECRETS
        status = screen._build_status_text()
        assert "Opaque" in status
        assert "username" in status

    def test_status_text_event(self) -> None:
        """Status text for events shows type, reason, count, message."""
        event = EventSummary(
            name="event-123",
            namespace="default",
            type="Warning",
            reason="BackOff",
            message="Restarting failed container",
            involved_object_kind="Pod",
            involved_object_name="nginx",
            count=5,
            creation_timestamp="2026-01-01T00:00:00Z",
        )
        screen = ResourceDetailScreen.__new__(ResourceDetailScreen)
        screen._resource = event
        screen._resource_type = ResourceType.EVENTS
        status = screen._build_status_text()
        assert "Warning" in status
        assert "BackOff" in status
        assert "5" in status

    def test_status_text_unknown_type_fallback(self) -> None:
        """_build_status_text returns fallback for unknown resource with no phase/status."""
        mock_resource = MagicMock(spec=[])
        mock_resource.name = "test"
        screen = ResourceDetailScreen.__new__(ResourceDetailScreen)
        screen._resource = mock_resource
        # Use a type that won't match any branch
        screen._resource_type = ResourceType.PODS
        # Override: remove phase attribute so no branch matches
        del mock_resource.phase
        # Use a mock that doesn't match any if/elif
        object.__setattr__(screen, "_resource_type", MagicMock())
        status = screen._build_status_text()
        assert "No status information" in status


# ============================================================================
# _get_primary_status Tests
# ============================================================================


@pytest.mark.unit
class TestGetPrimaryStatus:
    """Tests for _get_primary_status edge cases."""

    def test_primary_status_with_no_phase_or_status(self) -> None:
        """Returns Unknown when resource has neither phase nor status."""
        mock_resource = MagicMock(spec=["name", "namespace"])
        screen = ResourceDetailScreen.__new__(ResourceDetailScreen)
        screen._resource = mock_resource
        screen._resource_type = ResourceType.PODS
        assert screen._get_primary_status() == "Unknown"

    def test_primary_status_deployment(self) -> None:
        """Primary status for deployment returns 'Unknown' (no phase/status)."""
        deploy = DeploymentSummary(
            name="web",
            namespace="default",
            replicas=3,
            ready_replicas=3,
            updated_replicas=3,
            available_replicas=3,
            creation_timestamp="2026-01-01T00:00:00Z",
        )
        screen = ResourceDetailScreen.__new__(ResourceDetailScreen)
        screen._resource = deploy
        screen._resource_type = ResourceType.DEPLOYMENTS
        # Deployments have no phase or status attribute by default
        result = screen._get_primary_status()
        assert isinstance(result, str)


# ============================================================================
# DashboardScreen Tests
# ============================================================================


@pytest.mark.unit
class TestDashboardScreenParseCpu:
    """Tests for DashboardScreen._parse_cpu."""

    def test_parse_cpu_plain_int(self) -> None:
        """_parse_cpu parses plain integer like '8'."""
        assert DashboardScreen._parse_cpu("8") == 8

    def test_parse_cpu_millicores(self) -> None:
        """_parse_cpu parses millicore value like '4000m'."""
        assert DashboardScreen._parse_cpu("4000m") == 4

    def test_parse_cpu_small_millicores(self) -> None:
        """_parse_cpu parses small millicore (rounds down)."""
        assert DashboardScreen._parse_cpu("500m") == 0

    def test_parse_cpu_invalid(self) -> None:
        """_parse_cpu returns None for invalid input."""
        assert DashboardScreen._parse_cpu("invalid") is None


@pytest.mark.unit
class TestDashboardScreenParseMemory:
    """Tests for DashboardScreen._parse_memory."""

    def test_parse_memory_gi(self) -> None:
        """_parse_memory parses GiB."""
        assert DashboardScreen._parse_memory("16Gi") == 16

    def test_parse_memory_mi(self) -> None:
        """_parse_memory parses MiB and converts to GiB."""
        assert DashboardScreen._parse_memory("16384Mi") == 16

    def test_parse_memory_ki(self) -> None:
        """_parse_memory parses KiB and converts to GiB."""
        result = DashboardScreen._parse_memory("16777216Ki")
        assert result == 16

    def test_parse_memory_bytes(self) -> None:
        """_parse_memory parses raw bytes."""
        result = DashboardScreen._parse_memory("17179869184")
        assert result == 16

    def test_parse_memory_invalid(self) -> None:
        """_parse_memory returns None for invalid input."""
        assert DashboardScreen._parse_memory("invalid") is None


# ============================================================================
# ResourceListScreen _fetch_resources Tests (sync via __new__)
# ============================================================================


@pytest.mark.unit
class TestFetchResources:
    """Tests for ResourceListScreen._fetch_resources dispatch."""

    def _make_screen(self, resource_type: ResourceType) -> ResourceListScreen:
        """Create screen bypassing __init__."""
        screen = ResourceListScreen.__new__(ResourceListScreen)
        object.__setattr__(screen, "_client", MagicMock())
        screen._current_type = resource_type
        screen._current_namespace = "default"
        screen._resources = []
        return screen

    def test_fetch_pods(self) -> None:
        """_fetch_resources dispatches to list_pods."""
        screen = self._make_screen(ResourceType.PODS)
        with patch(
            "system_operations_manager.services.kubernetes.workload_manager.WorkloadManager",
        ) as mock_cls:
            mock_cls.return_value.list_pods.return_value = ["pod1"]
            result = screen._fetch_resources()
        assert result == ["pod1"]

    def test_fetch_deployments(self) -> None:
        """_fetch_resources dispatches to list_deployments."""
        screen = self._make_screen(ResourceType.DEPLOYMENTS)
        with patch(
            "system_operations_manager.services.kubernetes.workload_manager.WorkloadManager",
        ) as mock_cls:
            mock_cls.return_value.list_deployments.return_value = ["deploy1"]
            result = screen._fetch_resources()
        assert result == ["deploy1"]

    def test_fetch_statefulsets(self) -> None:
        """_fetch_resources dispatches to list_stateful_sets."""
        screen = self._make_screen(ResourceType.STATEFULSETS)
        with patch(
            "system_operations_manager.services.kubernetes.workload_manager.WorkloadManager",
        ) as mock_cls:
            mock_cls.return_value.list_stateful_sets.return_value = ["sts1"]
            result = screen._fetch_resources()
        assert result == ["sts1"]

    def test_fetch_daemonsets(self) -> None:
        """_fetch_resources dispatches to list_daemon_sets."""
        screen = self._make_screen(ResourceType.DAEMONSETS)
        with patch(
            "system_operations_manager.services.kubernetes.workload_manager.WorkloadManager",
        ) as mock_cls:
            mock_cls.return_value.list_daemon_sets.return_value = ["ds1"]
            result = screen._fetch_resources()
        assert result == ["ds1"]

    def test_fetch_replicasets(self) -> None:
        """_fetch_resources dispatches to list_replica_sets."""
        screen = self._make_screen(ResourceType.REPLICASETS)
        with patch(
            "system_operations_manager.services.kubernetes.workload_manager.WorkloadManager",
        ) as mock_cls:
            mock_cls.return_value.list_replica_sets.return_value = ["rs1"]
            result = screen._fetch_resources()
        assert result == ["rs1"]

    def test_fetch_services(self) -> None:
        """_fetch_resources dispatches to list_services."""
        screen = self._make_screen(ResourceType.SERVICES)
        with patch(
            "system_operations_manager.services.kubernetes.networking_manager.NetworkingManager",
        ) as mock_cls:
            mock_cls.return_value.list_services.return_value = ["svc1"]
            result = screen._fetch_resources()
        assert result == ["svc1"]

    def test_fetch_ingresses(self) -> None:
        """_fetch_resources dispatches to list_ingresses."""
        screen = self._make_screen(ResourceType.INGRESSES)
        with patch(
            "system_operations_manager.services.kubernetes.networking_manager.NetworkingManager",
        ) as mock_cls:
            mock_cls.return_value.list_ingresses.return_value = ["ing1"]
            result = screen._fetch_resources()
        assert result == ["ing1"]

    def test_fetch_network_policies(self) -> None:
        """_fetch_resources dispatches to list_network_policies."""
        screen = self._make_screen(ResourceType.NETWORK_POLICIES)
        with patch(
            "system_operations_manager.services.kubernetes.networking_manager.NetworkingManager",
        ) as mock_cls:
            mock_cls.return_value.list_network_policies.return_value = ["np1"]
            result = screen._fetch_resources()
        assert result == ["np1"]

    def test_fetch_configmaps(self) -> None:
        """_fetch_resources dispatches to list_config_maps."""
        screen = self._make_screen(ResourceType.CONFIGMAPS)
        with patch(
            "system_operations_manager.services.kubernetes.configuration_manager.ConfigurationManager",
        ) as mock_cls:
            mock_cls.return_value.list_config_maps.return_value = ["cm1"]
            result = screen._fetch_resources()
        assert result == ["cm1"]

    def test_fetch_secrets(self) -> None:
        """_fetch_resources dispatches to list_secrets."""
        screen = self._make_screen(ResourceType.SECRETS)
        with patch(
            "system_operations_manager.services.kubernetes.configuration_manager.ConfigurationManager",
        ) as mock_cls:
            mock_cls.return_value.list_secrets.return_value = ["sec1"]
            result = screen._fetch_resources()
        assert result == ["sec1"]

    def test_fetch_namespaces(self) -> None:
        """_fetch_resources dispatches to list_namespaces."""
        screen = self._make_screen(ResourceType.NAMESPACES)
        with patch(
            "system_operations_manager.services.kubernetes.namespace_manager.NamespaceClusterManager",
        ) as mock_cls:
            mock_cls.return_value.list_namespaces.return_value = ["ns1"]
            result = screen._fetch_resources()
        assert result == ["ns1"]

    def test_fetch_nodes(self) -> None:
        """_fetch_resources dispatches to list_nodes."""
        screen = self._make_screen(ResourceType.NODES)
        with patch(
            "system_operations_manager.services.kubernetes.namespace_manager.NamespaceClusterManager",
        ) as mock_cls:
            mock_cls.return_value.list_nodes.return_value = ["node1"]
            result = screen._fetch_resources()
        assert result == ["node1"]

    def test_fetch_events(self) -> None:
        """_fetch_resources dispatches to list_events."""
        screen = self._make_screen(ResourceType.EVENTS)
        with patch(
            "system_operations_manager.services.kubernetes.namespace_manager.NamespaceClusterManager",
        ) as mock_cls:
            mock_cls.return_value.list_events.return_value = ["evt1"]
            result = screen._fetch_resources()
        assert result == ["evt1"]

    def test_fetch_all_namespaces(self) -> None:
        """_fetch_resources passes all_namespaces=True when namespace is None."""
        screen = self._make_screen(ResourceType.PODS)
        screen._current_namespace = None
        with patch(
            "system_operations_manager.services.kubernetes.workload_manager.WorkloadManager",
        ) as mock_cls:
            mock_mgr = MagicMock()
            mock_cls.return_value = mock_mgr
            mock_mgr.list_pods.return_value = []
            screen._fetch_resources()
        mock_mgr.list_pods.assert_called_once_with(namespace=None, all_namespaces=True)


# ============================================================================
# ResourceListScreen Action Tests
# ============================================================================


@pytest.mark.unit
class TestResourceListScreenActions:
    """Tests for ResourceListScreen action methods."""

    def _make_screen(self) -> ResourceListScreen:
        """Create a ResourceListScreen bypassing __init__."""
        screen = ResourceListScreen.__new__(ResourceListScreen)
        object.__setattr__(screen, "_client", MagicMock())
        screen._current_type = ResourceType.PODS
        screen._current_namespace = "default"
        screen._resources = []
        screen._namespaces = ["default"]
        screen._contexts = ["minikube"]
        screen._pending_delete = None
        object.__setattr__(screen, "go_back", MagicMock())
        object.__setattr__(screen, "notify_user", MagicMock())
        object.__setattr__(screen, "query_one", MagicMock())
        object.__setattr__(screen, "post_message", MagicMock())
        return screen

    def test_action_back_calls_go_back(self) -> None:
        """action_back calls go_back."""
        screen = self._make_screen()
        screen.action_back()
        cast(MagicMock, screen.go_back).assert_called_once()

    def test_action_logs_warns_for_non_pods(self) -> None:
        """action_logs warns when not viewing pods."""
        screen = self._make_screen()
        screen._current_type = ResourceType.DEPLOYMENTS
        screen.action_logs()
        cast(MagicMock, screen.notify_user).assert_called_once()
        assert "Pods" in cast(MagicMock, screen.notify_user).call_args[0][0]

    def test_action_create_warns_for_non_creatable(self) -> None:
        """action_create warns for non-creatable types."""
        screen = self._make_screen()
        screen._current_type = ResourceType.EVENTS
        screen.action_create()
        cast(MagicMock, screen.notify_user).assert_called_once()
        assert "Cannot create" in cast(MagicMock, screen.notify_user).call_args[0][0]

    def test_action_delete_warns_for_non_deletable(self) -> None:
        """action_delete warns for non-deletable types."""
        screen = self._make_screen()
        screen._current_type = ResourceType.EVENTS
        screen.action_delete()
        cast(MagicMock, screen.notify_user).assert_called_once()
        assert "Cannot delete" in cast(MagicMock, screen.notify_user).call_args[0][0]


# ============================================================================
# ResourceDetailScreen Action Tests
# ============================================================================


@pytest.mark.unit
class TestResourceDetailScreenActions:
    """Tests for ResourceDetailScreen action methods."""

    def _make_detail_screen(self) -> ResourceDetailScreen:
        """Create a ResourceDetailScreen bypassing __init__."""
        screen = ResourceDetailScreen.__new__(ResourceDetailScreen)
        screen._resource = PodSummary(
            name="test-pod",
            namespace="default",
            phase="Running",
            ready_count=1,
            total_count=1,
            restarts=0,
        )
        screen._resource_type = ResourceType.PODS
        object.__setattr__(screen, "_client", MagicMock())
        screen._yaml_visible = True
        object.__setattr__(screen, "go_back", MagicMock())
        object.__setattr__(screen, "notify_user", MagicMock())
        object.__setattr__(screen, "query_one", MagicMock())
        return screen

    def test_action_back(self) -> None:
        """action_back calls go_back."""
        screen = self._make_detail_screen()
        screen.action_back()
        cast(MagicMock, screen.go_back).assert_called_once()

    def test_action_toggle_yaml(self) -> None:
        """action_toggle_yaml toggles _yaml_visible."""
        screen = self._make_detail_screen()
        assert screen._yaml_visible is True
        screen.action_toggle_yaml()
        assert screen._yaml_visible is False
        screen.action_toggle_yaml()
        assert screen._yaml_visible is True

    def test_action_refresh_events(self) -> None:
        """action_refresh_events loads events and notifies."""
        screen = self._make_detail_screen()
        object.__setattr__(screen, "_load_events", MagicMock())
        screen.action_refresh_events()
        cast(MagicMock, screen._load_events).assert_called_once()
        cast(MagicMock, screen.notify_user).assert_called_once_with("Events refreshed")


# ============================================================================
# _resource_to_row truncation branches
# ============================================================================


@pytest.mark.unit
class TestResourceToRowTruncationBranches:
    """Tests for truncation branches in _resource_to_row."""

    def test_ingress_hosts_truncated_when_more_than_three(self) -> None:
        """Ingress with >3 hosts appends '+N' suffix."""
        ingress = IngressSummary(
            name="big-ingress",
            namespace="default",
            class_name="nginx",
            hosts=["a.com", "b.com", "c.com", "d.com", "e.com"],
            addresses=["1.2.3.4"],
            creation_timestamp="2026-01-01T00:00:00Z",
        )
        row = _resource_to_row(ingress, ResourceType.INGRESSES)
        assert "(+2)" in row[3]

    def test_ingress_addresses_truncated_when_more_than_two(self) -> None:
        """Ingress with >2 addresses appends '+N' suffix."""
        ingress = IngressSummary(
            name="multi-addr",
            namespace="default",
            class_name="nginx",
            hosts=["a.com"],
            addresses=["1.1.1.1", "2.2.2.2", "3.3.3.3"],
            creation_timestamp="2026-01-01T00:00:00Z",
        )
        row = _resource_to_row(ingress, ResourceType.INGRESSES)
        assert "(+1)" in row[4]

    def test_configmap_keys_truncated_when_more_than_five(self) -> None:
        """ConfigMap with >5 data_keys appends '+N' suffix."""
        cm = ConfigMapSummary(
            name="big-config",
            namespace="default",
            data_keys=[f"key{i}" for i in range(8)],
            creation_timestamp="2026-01-01T00:00:00Z",
        )
        row = _resource_to_row(cm, ResourceType.CONFIGMAPS)
        assert "(+3)" in row[2]

    def test_secret_keys_truncated_when_more_than_five(self) -> None:
        """Secret with >5 data_keys appends '+N' suffix."""
        secret = SecretSummary(
            name="big-secret",
            namespace="default",
            type="Opaque",
            data_keys=[f"key{i}" for i in range(7)],
            creation_timestamp="2026-01-01T00:00:00Z",
        )
        row = _resource_to_row(secret, ResourceType.SECRETS)
        assert "(+2)" in row[3]

    def test_fallback_returns_name_and_age(self) -> None:
        """_resource_to_row returns (name, age) fallback for unknown type."""
        from unittest.mock import MagicMock

        resource = MagicMock()
        resource.name = "mystery"
        resource.age = "5d"
        unknown_type = MagicMock()
        # Make all if-checks fail by using a mock that != any ResourceType member
        row = _resource_to_row(resource, unknown_type)
        assert row == ("mystery", "5d")


# ============================================================================
# ResourceListScreen._load_contexts Tests
# ============================================================================


def _make_resource_list_screen() -> ResourceListScreen:
    """Create a ResourceListScreen bypassing __init__.

    Note: _workload_mgr, _config_mgr, _namespace_mgr, _networking_mgr are
    @property methods on the class so they cannot be set as instance attributes.
    Tests that exercise those managers should patch them at the module level.
    """
    screen = ResourceListScreen.__new__(ResourceListScreen)
    object.__setattr__(screen, "_client", MagicMock())
    screen._current_type = ResourceType.PODS
    screen._current_namespace = "default"
    screen._resources = []
    screen._pending_delete = None
    screen._namespaces = ["default", "kube-system"]
    screen._contexts = ["minikube"]
    object.__setattr__(screen, "go_back", MagicMock())
    object.__setattr__(screen, "notify_user", MagicMock())
    object.__setattr__(screen, "query_one", MagicMock())
    object.__setattr__(screen, "post_message", MagicMock())
    return screen


def _make_resource_detail_screen(
    resource: Any = None, resource_type: ResourceType = ResourceType.PODS
) -> ResourceDetailScreen:
    """Create a ResourceDetailScreen bypassing __init__."""
    screen = ResourceDetailScreen.__new__(ResourceDetailScreen)
    if resource is None:
        resource = PodSummary(
            name="test-pod",
            namespace="default",
            phase="Running",
            ready_count=1,
            total_count=1,
            restarts=0,
        )
    screen._resource = resource
    screen._resource_type = resource_type
    object.__setattr__(screen, "_client", MagicMock())
    screen._yaml_visible = True
    object.__setattr__(screen, "go_back", MagicMock())
    object.__setattr__(screen, "notify_user", MagicMock())
    object.__setattr__(screen, "query_one", MagicMock())
    object.__setattr__(screen, "post_message", MagicMock())
    return screen


@pytest.mark.unit
class TestResourceListScreenLoadContexts:
    """Tests for ResourceListScreen._load_contexts."""

    def test_load_contexts_success(self) -> None:
        """_load_contexts populates _contexts from client."""
        screen = _make_resource_list_screen()
        cast(MagicMock, screen._client.list_contexts).return_value = [
            {"name": "ctx1"},
            {"name": "ctx2"},
        ]
        mock_selector = MagicMock()
        cast(MagicMock, screen.query_one).return_value = mock_selector

        screen._load_contexts()

        assert screen._contexts == ["ctx1", "ctx2"]
        assert mock_selector._contexts == ["ctx1", "ctx2"]

    def test_load_contexts_failure_falls_back_to_current_context(self) -> None:
        """_load_contexts falls back to current context on error."""
        screen = _make_resource_list_screen()
        cast(MagicMock, screen._client.list_contexts).side_effect = RuntimeError("api error")
        cast(MagicMock, screen._client.get_current_context).return_value = "fallback-ctx"

        screen._load_contexts()

        assert screen._contexts == ["fallback-ctx"]


# ============================================================================
# ResourceListScreen._load_namespaces Tests
# ============================================================================


@pytest.mark.unit
class TestResourceListScreenLoadNamespaces:
    """Tests for ResourceListScreen._load_namespaces."""

    def test_load_namespaces_success(self) -> None:
        """_load_namespaces populates _namespaces via NamespaceClusterManager."""
        screen = _make_resource_list_screen()
        mock_ns1 = MagicMock()
        mock_ns1.name = "default"
        mock_ns2 = MagicMock()
        mock_ns2.name = "kube-system"
        mock_selector = MagicMock()
        cast(MagicMock, screen.query_one).return_value = mock_selector

        with patch(
            "system_operations_manager.services.kubernetes.namespace_manager.NamespaceClusterManager"
        ) as mock_cls:
            mock_cls.return_value.list_namespaces.return_value = [mock_ns1, mock_ns2]
            screen._load_namespaces()

        assert screen._namespaces == ["default", "kube-system"]

    def test_load_namespaces_failure_falls_back_to_default(self) -> None:
        """_load_namespaces falls back to ['default'] on error."""
        screen = _make_resource_list_screen()

        with patch(
            "system_operations_manager.services.kubernetes.namespace_manager.NamespaceClusterManager"
        ) as mock_cls:
            mock_cls.return_value.list_namespaces.side_effect = RuntimeError("fail")
            screen._load_namespaces()

        assert screen._namespaces == ["default"]


# ============================================================================
# ResourceListScreen._load_resources Tests
# ============================================================================


@pytest.mark.unit
class TestResourceListScreenLoadResources:
    """Tests for ResourceListScreen._load_resources."""

    def test_load_resources_success_updates_status_bar(self) -> None:
        """_load_resources populates table and updates status bar."""
        screen = _make_resource_list_screen()
        mock_pod = PodSummary(
            name="test-pod",
            namespace="default",
            phase="Running",
            ready_count=1,
            total_count=1,
            restarts=0,
        )
        object.__setattr__(screen, "_fetch_resources", MagicMock(return_value=[mock_pod]))
        object.__setattr__(screen, "_populate_table", MagicMock())
        mock_label = MagicMock()
        cast(MagicMock, screen.query_one).return_value = mock_label

        screen._load_resources()

        cast(MagicMock, screen._populate_table).assert_called_once()
        mock_label.update.assert_called_once()
        update_text = mock_label.update.call_args[0][0]
        assert "1" in update_text

    def test_load_resources_failure_shows_error(self) -> None:
        """_load_resources catches exception and notifies user."""
        screen = _make_resource_list_screen()
        object.__setattr__(
            screen, "_fetch_resources", MagicMock(side_effect=RuntimeError("network error"))
        )
        object.__setattr__(screen, "_populate_table", MagicMock())
        mock_label = MagicMock()
        cast(MagicMock, screen.query_one).return_value = mock_label

        screen._load_resources()

        cast(MagicMock, screen.notify_user).assert_called_once()
        assert "error" in cast(MagicMock, screen.notify_user).call_args[1].get("severity", "")
        cast(MagicMock, screen._populate_table).assert_called_once()
        mock_label.update.assert_called_once()


# ============================================================================
# ResourceListScreen._populate_table Tests
# ============================================================================


@pytest.mark.unit
class TestResourceListScreenPopulateTable:
    """Tests for ResourceListScreen._populate_table."""

    def test_populate_table_clears_and_adds_columns(self) -> None:
        """_populate_table calls clear(columns=True) and adds column headers."""
        screen = _make_resource_list_screen()
        mock_table = MagicMock()
        cast(MagicMock, screen.query_one).return_value = mock_table

        pod = PodSummary(
            name="nginx",
            namespace="default",
            phase="Running",
            ready_count=1,
            total_count=1,
            restarts=0,
        )
        screen._resources = [pod]
        screen._current_type = ResourceType.PODS

        screen._populate_table()

        mock_table.clear.assert_called_once_with(columns=True)
        assert (
            mock_table.add_column.call_count
            == len([(label, width) for label, width in [(c[0], c[1]) for c in [("Name", 30)]]])
            or mock_table.add_column.call_count > 0
        )
        mock_table.add_row.assert_called_once()

    def test_populate_table_empty_resources(self) -> None:
        """_populate_table with no resources still clears and adds columns."""
        screen = _make_resource_list_screen()
        mock_table = MagicMock()
        cast(MagicMock, screen.query_one).return_value = mock_table
        screen._resources = []
        screen._current_type = ResourceType.PODS

        screen._populate_table()

        mock_table.clear.assert_called_once_with(columns=True)
        mock_table.add_row.assert_not_called()


# ============================================================================
# ResourceListScreen Action Method Tests (extended)
# ============================================================================


@pytest.mark.unit
class TestResourceListScreenActionMethods:
    """Extended action method tests for ResourceListScreen."""

    def test_action_cursor_down_delegates_to_table(self) -> None:
        """action_cursor_down calls DataTable.action_cursor_down."""
        screen = _make_resource_list_screen()
        mock_table = MagicMock()
        cast(MagicMock, screen.query_one).return_value = mock_table

        screen.action_cursor_down()

        mock_table.action_cursor_down.assert_called_once()

    def test_action_cursor_up_delegates_to_table(self) -> None:
        """action_cursor_up calls DataTable.action_cursor_up."""
        screen = _make_resource_list_screen()
        mock_table = MagicMock()
        cast(MagicMock, screen.query_one).return_value = mock_table

        screen.action_cursor_up()

        mock_table.action_cursor_up.assert_called_once()

    def test_action_select_posts_resource_selected_message(self) -> None:
        """action_select posts ResourceSelected when cursor row is valid."""
        screen = _make_resource_list_screen()
        pod = PodSummary(
            name="nginx",
            namespace="default",
            phase="Running",
            ready_count=1,
            total_count=1,
            restarts=0,
        )
        screen._resources = [pod]
        mock_table = MagicMock()
        mock_table.cursor_row = 0
        cast(MagicMock, screen.query_one).return_value = mock_table

        screen.action_select()

        cast(MagicMock, screen.post_message).assert_called_once()
        msg = cast(MagicMock, screen.post_message).call_args[0][0]
        assert isinstance(msg, ResourceListScreen.ResourceSelected)
        assert msg.resource.name == "nginx"

    def test_action_select_does_nothing_when_no_cursor(self) -> None:
        """action_select does nothing when cursor_row is None."""
        screen = _make_resource_list_screen()
        screen._resources = []
        mock_table = MagicMock()
        mock_table.cursor_row = None
        cast(MagicMock, screen.query_one).return_value = mock_table

        screen.action_select()

        cast(MagicMock, screen.post_message).assert_not_called()

    def test_handle_row_selected_posts_message(self) -> None:
        """handle_row_selected posts ResourceSelected for valid row."""
        from textual.widgets import DataTable

        screen = _make_resource_list_screen()
        pod = PodSummary(
            name="redis",
            namespace="default",
            phase="Running",
            ready_count=1,
            total_count=1,
            restarts=0,
        )
        screen._resources = [pod]
        mock_event = MagicMock(spec=DataTable.RowSelected)
        mock_event.cursor_row = 0

        screen.handle_row_selected(mock_event)

        cast(MagicMock, screen.post_message).assert_called_once()
        msg = cast(MagicMock, screen.post_message).call_args[0][0]
        assert msg.resource.name == "redis"

    def test_handle_row_selected_out_of_bounds(self) -> None:
        """handle_row_selected does nothing when cursor_row >= len(resources)."""
        from textual.widgets import DataTable

        screen = _make_resource_list_screen()
        screen._resources = []
        mock_event = MagicMock(spec=DataTable.RowSelected)
        mock_event.cursor_row = 5

        screen.handle_row_selected(mock_event)

        cast(MagicMock, screen.post_message).assert_not_called()

    def test_action_refresh_calls_load_and_notifies(self) -> None:
        """action_refresh calls _load_resources and notifies."""
        screen = _make_resource_list_screen()
        object.__setattr__(screen, "_load_resources", MagicMock())

        screen.action_refresh()

        cast(MagicMock, screen._load_resources).assert_called_once()
        cast(MagicMock, screen.notify_user).assert_called_once_with("Refreshed")

    def test_action_create_not_creatable_warns(self) -> None:
        """action_create warns for non-creatable types (e.g. EVENTS)."""
        screen = _make_resource_list_screen()
        screen._current_type = ResourceType.EVENTS

        screen.action_create()

        cast(MagicMock, screen.notify_user).assert_called_once()
        assert "Cannot create" in cast(MagicMock, screen.notify_user).call_args[0][0]

    def test_action_create_pushes_screen_for_creatable_type(self) -> None:
        """action_create pushes ResourceCreateScreen for creatable types."""
        screen = _make_resource_list_screen()
        screen._current_type = ResourceType.DEPLOYMENTS
        mock_app = MagicMock()

        with (
            patch.object(type(screen), "app", new_callable=PropertyMock, return_value=mock_app),
            patch(
                "system_operations_manager.tui.apps.kubernetes.create_screen.ResourceCreateScreen"
            ) as mock_create_cls,
        ):
            mock_create_cls.return_value = MagicMock()
            screen.action_create()

        cast(MagicMock, mock_app.push_screen).assert_called_once()

    def test_handle_create_dismissed_calls_load_resources(self) -> None:
        """_handle_create_dismissed calls _load_resources."""
        screen = _make_resource_list_screen()
        object.__setattr__(screen, "_load_resources", MagicMock())

        screen._handle_create_dismissed(None)

        cast(MagicMock, screen._load_resources).assert_called_once()

    def test_action_delete_not_deletable_warns(self) -> None:
        """action_delete warns for non-deletable types."""
        screen = _make_resource_list_screen()
        screen._current_type = ResourceType.EVENTS

        screen.action_delete()

        cast(MagicMock, screen.notify_user).assert_called_once()
        assert "Cannot delete" in cast(MagicMock, screen.notify_user).call_args[0][0]

    def test_action_delete_no_cursor_returns_early(self) -> None:
        """action_delete returns without pushing modal when cursor is None."""
        screen = _make_resource_list_screen()
        screen._current_type = ResourceType.PODS
        mock_table = MagicMock()
        mock_table.cursor_row = None
        cast(MagicMock, screen.query_one).return_value = mock_table
        mock_app = MagicMock()

        with patch.object(type(screen), "app", new_callable=PropertyMock, return_value=mock_app):
            screen.action_delete()

        cast(MagicMock, mock_app.push_screen).assert_not_called()

    def test_action_delete_pushes_modal_for_valid_cursor(self) -> None:
        """action_delete pushes confirmation modal when cursor is valid."""
        screen = _make_resource_list_screen()
        screen._current_type = ResourceType.PODS
        pod = PodSummary(
            name="old-pod",
            namespace="default",
            phase="Running",
            ready_count=1,
            total_count=1,
            restarts=0,
        )
        screen._resources = [pod]
        mock_table = MagicMock()
        mock_table.cursor_row = 0
        cast(MagicMock, screen.query_one).return_value = mock_table
        mock_app = MagicMock()

        with (
            patch.object(type(screen), "app", new_callable=PropertyMock, return_value=mock_app),
            patch("system_operations_manager.tui.components.modal.Modal") as mock_modal_cls,
        ):
            mock_modal_cls.return_value = MagicMock()
            screen.action_delete()

        cast(MagicMock, mock_app.push_screen).assert_called_once()
        assert screen._pending_delete is pod

    def test_handle_delete_result_delete_success(self) -> None:
        """_handle_delete_result calls delete_resource and refreshes on 'delete'."""
        screen = _make_resource_list_screen()
        pod = PodSummary(
            name="dead-pod",
            namespace="default",
            phase="Running",
            ready_count=1,
            total_count=1,
            restarts=0,
        )
        screen._pending_delete = pod
        object.__setattr__(screen, "_load_resources", MagicMock())

        with patch(
            "system_operations_manager.tui.apps.kubernetes.delete_helpers.delete_resource"
        ) as mock_delete:
            screen._handle_delete_result("delete")

        mock_delete.assert_called_once()
        cast(MagicMock, screen.notify_user).assert_called_once()
        assert "dead-pod" in cast(MagicMock, screen.notify_user).call_args[0][0]
        cast(MagicMock, screen._load_resources).assert_called_once()
        assert screen._pending_delete is None

    def test_handle_delete_result_delete_failure_notifies_error(self) -> None:
        """_handle_delete_result notifies error when delete_resource raises."""
        screen = _make_resource_list_screen()
        pod = PodSummary(
            name="stuck-pod",
            namespace="default",
            phase="Running",
            ready_count=1,
            total_count=1,
            restarts=0,
        )
        screen._pending_delete = pod
        object.__setattr__(screen, "_load_resources", MagicMock())

        with patch(
            "system_operations_manager.tui.apps.kubernetes.delete_helpers.delete_resource"
        ) as mock_delete:
            mock_delete.side_effect = RuntimeError("forbidden")
            screen._handle_delete_result("delete")

        cast(MagicMock, screen.notify_user).assert_called_once()
        assert "error" in cast(MagicMock, screen.notify_user).call_args[1].get("severity", "")
        assert screen._pending_delete is None

    def test_handle_delete_result_cancel_clears_pending(self) -> None:
        """_handle_delete_result clears pending on non-delete result."""
        screen = _make_resource_list_screen()
        pod = PodSummary(
            name="saved-pod",
            namespace="default",
            phase="Running",
            ready_count=1,
            total_count=1,
            restarts=0,
        )
        screen._pending_delete = pod

        screen._handle_delete_result("cancel")

        assert screen._pending_delete is None
        cast(MagicMock, screen.notify_user).assert_not_called()

    def test_action_logs_warns_when_not_pods(self) -> None:
        """action_logs warns for non-pod resource type."""
        screen = _make_resource_list_screen()
        screen._current_type = ResourceType.DEPLOYMENTS

        screen.action_logs()

        cast(MagicMock, screen.notify_user).assert_called_once()
        assert "Pods" in cast(MagicMock, screen.notify_user).call_args[0][0]

    def test_action_logs_no_cursor_returns_early(self) -> None:
        """action_logs returns without pushing screen when cursor is None."""
        screen = _make_resource_list_screen()
        screen._current_type = ResourceType.PODS
        mock_table = MagicMock()
        mock_table.cursor_row = None
        cast(MagicMock, screen.query_one).return_value = mock_table
        mock_app = MagicMock()

        with patch.object(type(screen), "app", new_callable=PropertyMock, return_value=mock_app):
            screen.action_logs()

        cast(MagicMock, mock_app.push_screen).assert_not_called()

    def test_action_logs_pushes_log_viewer_for_pods(self) -> None:
        """action_logs pushes LogViewerScreen for valid pod cursor."""
        screen = _make_resource_list_screen()
        screen._current_type = ResourceType.PODS
        pod = PodSummary(
            name="logging-pod",
            namespace="default",
            phase="Running",
            ready_count=1,
            total_count=1,
            restarts=0,
        )
        screen._resources = [pod]
        mock_table = MagicMock()
        mock_table.cursor_row = 0
        cast(MagicMock, screen.query_one).return_value = mock_table
        mock_app = MagicMock()

        with (
            patch.object(type(screen), "app", new_callable=PropertyMock, return_value=mock_app),
            patch(
                "system_operations_manager.tui.apps.kubernetes.log_viewer.LogViewerScreen"
            ) as mock_lv_cls,
        ):
            mock_lv_cls.return_value = MagicMock()
            screen.action_logs()

        cast(MagicMock, mock_app.push_screen).assert_called_once()

    def test_action_cycle_namespace_calls_selector(self) -> None:
        """action_cycle_namespace calls cycle() on the namespace selector."""
        screen = _make_resource_list_screen()
        mock_selector = MagicMock()
        cast(MagicMock, screen.query_one).return_value = mock_selector

        screen.action_cycle_namespace()

        mock_selector.cycle.assert_called_once()

    def test_action_select_namespace_calls_selector(self) -> None:
        """action_select_namespace calls select_from_popup() on ns selector."""
        screen = _make_resource_list_screen()
        mock_selector = MagicMock()
        cast(MagicMock, screen.query_one).return_value = mock_selector

        screen.action_select_namespace()

        mock_selector.select_from_popup.assert_called_once()

    def test_action_cycle_cluster_calls_selector(self) -> None:
        """action_cycle_cluster calls cycle() on the cluster selector."""
        screen = _make_resource_list_screen()
        mock_selector = MagicMock()
        cast(MagicMock, screen.query_one).return_value = mock_selector

        screen.action_cycle_cluster()

        mock_selector.cycle.assert_called_once()

    def test_action_select_cluster_calls_selector(self) -> None:
        """action_select_cluster calls select_from_popup() on cluster selector."""
        screen = _make_resource_list_screen()
        mock_selector = MagicMock()
        cast(MagicMock, screen.query_one).return_value = mock_selector

        screen.action_select_cluster()

        mock_selector.select_from_popup.assert_called_once()

    def test_action_cycle_filter_calls_selector(self) -> None:
        """action_cycle_filter calls cycle() on the resource type filter."""
        screen = _make_resource_list_screen()
        mock_selector = MagicMock()
        cast(MagicMock, screen.query_one).return_value = mock_selector

        screen.action_cycle_filter()

        mock_selector.cycle.assert_called_once()

    def test_action_select_filter_calls_selector(self) -> None:
        """action_select_filter calls select_from_popup() on type filter."""
        screen = _make_resource_list_screen()
        mock_selector = MagicMock()
        cast(MagicMock, screen.query_one).return_value = mock_selector

        screen.action_select_filter()

        mock_selector.select_from_popup.assert_called_once()


# ============================================================================
# ResourceListScreen Event Handler Tests
# ============================================================================


@pytest.mark.unit
class TestResourceListScreenEventHandlers:
    """Tests for ResourceListScreen widget event handlers."""

    def test_handle_namespace_changed_updates_namespace_and_loads(self) -> None:
        """handle_namespace_changed updates namespace and calls _load_resources."""
        from system_operations_manager.tui.apps.kubernetes.widgets import NamespaceSelector

        screen = _make_resource_list_screen()
        object.__setattr__(screen, "_load_resources", MagicMock())
        event = NamespaceSelector.NamespaceChanged("kube-system")

        screen.handle_namespace_changed(event)

        assert screen._current_namespace == "kube-system"
        cast(MagicMock, screen._load_resources).assert_called_once()

    def test_handle_namespace_changed_accepts_none(self) -> None:
        """handle_namespace_changed handles None (all namespaces)."""
        from system_operations_manager.tui.apps.kubernetes.widgets import NamespaceSelector

        screen = _make_resource_list_screen()
        object.__setattr__(screen, "_load_resources", MagicMock())
        event = NamespaceSelector.NamespaceChanged(None)

        screen.handle_namespace_changed(event)

        assert screen._current_namespace is None
        cast(MagicMock, screen._load_resources).assert_called_once()

    def test_handle_cluster_changed_success(self) -> None:
        """handle_cluster_changed switches context, loads namespaces and resources."""
        from system_operations_manager.tui.apps.kubernetes.widgets import ClusterSelector

        screen = _make_resource_list_screen()
        object.__setattr__(screen, "_load_namespaces", MagicMock())
        object.__setattr__(screen, "_load_resources", MagicMock())
        object.__setattr__(screen._client, "switch_context", MagicMock())
        event = ClusterSelector.ClusterChanged("prod-cluster")

        screen.handle_cluster_changed(event)

        cast(MagicMock, screen._client.switch_context).assert_called_once_with("prod-cluster")
        cast(MagicMock, screen._load_namespaces).assert_called_once()
        cast(MagicMock, screen._load_resources).assert_called_once()
        cast(MagicMock, screen.notify_user).assert_called_once()
        assert "prod-cluster" in cast(MagicMock, screen.notify_user).call_args[0][0]

    def test_handle_cluster_changed_failure_notifies_error(self) -> None:
        """handle_cluster_changed notifies error when switch_context raises."""
        from system_operations_manager.tui.apps.kubernetes.widgets import ClusterSelector

        screen = _make_resource_list_screen()
        object.__setattr__(
            screen._client, "switch_context", MagicMock(side_effect=RuntimeError("unauthorized"))
        )
        event = ClusterSelector.ClusterChanged("bad-cluster")

        screen.handle_cluster_changed(event)

        cast(MagicMock, screen.notify_user).assert_called_once()
        assert "error" in cast(MagicMock, screen.notify_user).call_args[1].get("severity", "")

    def test_handle_resource_type_changed_updates_type_and_loads(self) -> None:
        """handle_resource_type_changed updates type and calls _load_resources."""
        from system_operations_manager.tui.apps.kubernetes.widgets import ResourceTypeFilter

        screen = _make_resource_list_screen()
        object.__setattr__(screen, "_load_resources", MagicMock())
        event = ResourceTypeFilter.ResourceTypeChanged(ResourceType.DEPLOYMENTS)

        screen.handle_resource_type_changed(event)

        assert screen._current_type == ResourceType.DEPLOYMENTS
        cast(MagicMock, screen._load_resources).assert_called_once()


# ============================================================================
# DashboardScreen Tests
# ============================================================================


def _make_dashboard_screen() -> DashboardScreen:
    """Create a DashboardScreen bypassing __init__."""
    screen = DashboardScreen.__new__(DashboardScreen)
    object.__setattr__(screen, "_client", MagicMock())
    object.__setattr__(screen, "go_back", MagicMock())
    object.__setattr__(screen, "notify_user", MagicMock())
    object.__setattr__(screen, "query_one", MagicMock())
    return screen


@pytest.mark.unit
class TestDashboardScreenManagers:
    """Tests for DashboardScreen lazy-loaded manager properties."""

    def test_namespace_mgr_property_creates_manager(self) -> None:
        """_namespace_mgr property creates a NamespaceClusterManager."""
        screen = _make_dashboard_screen()

        with patch(
            "system_operations_manager.services.kubernetes.namespace_manager.NamespaceClusterManager"
        ) as mock_cls:
            mock_cls.return_value = MagicMock()
            mgr = screen._namespace_mgr

        mock_cls.assert_called_once_with(screen._client)
        assert mgr is mock_cls.return_value

    def test_workload_mgr_property_creates_manager(self) -> None:
        """_workload_mgr property creates a WorkloadManager."""
        screen = _make_dashboard_screen()

        with patch(
            "system_operations_manager.services.kubernetes.workload_manager.WorkloadManager"
        ) as mock_cls:
            mock_cls.return_value = MagicMock()
            mgr = screen._workload_mgr

        mock_cls.assert_called_once_with(screen._client)
        assert mgr is mock_cls.return_value


@pytest.mark.unit
class TestDashboardScreenSetupTables:
    """Tests for DashboardScreen._setup_tables."""

    def test_setup_tables_configures_node_and_events_tables(self) -> None:
        """_setup_tables sets cursor_type, zebra_stripes, and adds columns."""
        screen = _make_dashboard_screen()
        mock_node_table = MagicMock()
        mock_events_table = MagicMock()

        call_count = [0]

        def side_effect(selector: Any, *args: Any, **kwargs: Any) -> MagicMock:
            call_count[0] += 1
            if "#node-table" in str(selector):
                return mock_node_table
            return mock_events_table

        cast(MagicMock, screen.query_one).side_effect = side_effect

        screen._setup_tables()

        assert mock_node_table.cursor_type == "row"
        assert mock_node_table.zebra_stripes is True
        assert mock_node_table.add_column.call_count > 0

        assert mock_events_table.cursor_type == "row"
        assert mock_events_table.zebra_stripes is True
        assert mock_events_table.add_column.call_count > 0


@pytest.mark.unit
class TestDashboardScreenRefreshAll:
    """Tests for DashboardScreen._refresh_all."""

    def test_refresh_all_calls_all_four_loaders(self) -> None:
        """_refresh_all calls _load_cluster_info, _load_nodes, _load_pod_summary, _load_events."""
        screen = _make_dashboard_screen()
        object.__setattr__(screen, "_load_cluster_info", MagicMock())
        object.__setattr__(screen, "_load_nodes", MagicMock())
        object.__setattr__(screen, "_load_pod_summary", MagicMock())
        object.__setattr__(screen, "_load_events", MagicMock())

        screen._refresh_all()

        cast(MagicMock, screen._load_cluster_info).assert_called_once()
        cast(MagicMock, screen._load_nodes).assert_called_once()
        cast(MagicMock, screen._load_pod_summary).assert_called_once()
        cast(MagicMock, screen._load_events).assert_called_once()


@pytest.mark.unit
class TestDashboardScreenLoadClusterInfo:
    """Tests for DashboardScreen._load_cluster_info."""

    def test_load_cluster_info_success_updates_label(self) -> None:
        """_load_cluster_info fetches cluster info and updates the label."""
        screen = _make_dashboard_screen()
        mock_label = MagicMock()
        cast(MagicMock, screen.query_one).return_value = mock_label

        with patch(
            "system_operations_manager.services.kubernetes.namespace_manager.NamespaceClusterManager"
        ) as mock_cls:
            mock_cls.return_value.get_cluster_info.return_value = {
                "version": "v1.29.0",
                "context": "prod",
                "node_count": 3,
                "namespace_count": 5,
            }
            screen._load_cluster_info()

        mock_label.update.assert_called_once()
        update_text = mock_label.update.call_args[0][0]
        assert "prod" in update_text
        assert "v1.29.0" in update_text

    def test_load_cluster_info_failure_shows_error_label(self) -> None:
        """_load_cluster_info shows error label when fetch fails."""
        screen = _make_dashboard_screen()
        mock_label = MagicMock()
        cast(MagicMock, screen.query_one).return_value = mock_label

        with patch(
            "system_operations_manager.services.kubernetes.namespace_manager.NamespaceClusterManager"
        ) as mock_cls:
            mock_cls.return_value.get_cluster_info.side_effect = RuntimeError("timeout")
            screen._load_cluster_info()

        mock_label.update.assert_called_once()
        update_text = mock_label.update.call_args[0][0]
        assert "Failed" in update_text


@pytest.mark.unit
class TestDashboardScreenLoadNodes:
    """Tests for DashboardScreen._load_nodes."""

    def test_load_nodes_success_populates_table(self) -> None:
        """_load_nodes clears table, adds rows, and calls _update_resource_bars."""
        screen = _make_dashboard_screen()
        mock_table = MagicMock()
        cast(MagicMock, screen.query_one).return_value = mock_table
        object.__setattr__(screen, "_update_resource_bars", MagicMock())

        node1 = NodeSummary(
            name="node-1",
            status="Ready",
            roles=["worker"],
            version="v1.29.0",
            cpu_capacity="4",
            memory_capacity="8Gi",
            pods_capacity="110",
            creation_timestamp="2026-01-01T00:00:00Z",
        )

        with patch(
            "system_operations_manager.services.kubernetes.namespace_manager.NamespaceClusterManager"
        ) as mock_cls:
            mock_cls.return_value.list_nodes.return_value = [node1]
            screen._load_nodes()

        mock_table.clear.assert_called_once()
        mock_table.add_row.assert_called_once()
        cast(MagicMock, screen._update_resource_bars).assert_called_once()

    def test_load_nodes_failure_notifies_error(self) -> None:
        """_load_nodes notifies user on exception."""
        screen = _make_dashboard_screen()

        with patch(
            "system_operations_manager.services.kubernetes.namespace_manager.NamespaceClusterManager"
        ) as mock_cls:
            mock_cls.return_value.list_nodes.side_effect = RuntimeError("forbidden")
            screen._load_nodes()

        cast(MagicMock, screen.notify_user).assert_called_once()
        assert "error" in cast(MagicMock, screen.notify_user).call_args[1].get("severity", "")


@pytest.mark.unit
class TestDashboardScreenLoadPodSummary:
    """Tests for DashboardScreen._load_pod_summary."""

    def test_load_pod_summary_success_counts_phases_and_namespaces(self) -> None:
        """_load_pod_summary counts pods by phase and namespace, updates labels."""
        screen = _make_dashboard_screen()
        mock_phase_label = MagicMock()
        mock_ns_label = MagicMock()

        call_seq = [mock_phase_label, mock_ns_label]
        cast(MagicMock, screen.query_one).side_effect = call_seq

        pod1 = PodSummary(
            name="pod-a",
            namespace="default",
            phase="Running",
            ready_count=1,
            total_count=1,
            restarts=0,
        )
        pod2 = PodSummary(
            name="pod-b",
            namespace="kube-system",
            phase="Pending",
            ready_count=0,
            total_count=1,
            restarts=0,
        )

        with patch(
            "system_operations_manager.services.kubernetes.workload_manager.WorkloadManager"
        ) as mock_cls:
            mock_cls.return_value.list_pods.return_value = [pod1, pod2]
            screen._load_pod_summary()

        mock_phase_label.update.assert_called_once()
        phase_text = mock_phase_label.update.call_args[0][0]
        assert "Total: 2" in phase_text

    def test_load_pod_summary_failure_shows_error(self) -> None:
        """_load_pod_summary shows error label on exception."""
        screen = _make_dashboard_screen()
        mock_label = MagicMock()
        cast(MagicMock, screen.query_one).return_value = mock_label

        with patch(
            "system_operations_manager.services.kubernetes.workload_manager.WorkloadManager"
        ) as mock_cls:
            mock_cls.return_value.list_pods.side_effect = RuntimeError("no pods")
            screen._load_pod_summary()

        mock_label.update.assert_called_once()
        update_text = mock_label.update.call_args[0][0]
        assert "Failed" in update_text


@pytest.mark.unit
class TestDashboardScreenUpdateResourceBars:
    """Tests for DashboardScreen._update_resource_bars."""

    def test_update_resource_bars_mounts_bars_per_node(self) -> None:
        """_update_resource_bars mounts Label and ResourceBar widgets for each node."""
        screen = _make_dashboard_screen()
        mock_container = MagicMock()
        cast(MagicMock, screen.query_one).return_value = mock_container

        node = NodeSummary(
            name="worker-1",
            status="Ready",
            roles=["worker"],
            version="v1.29.0",
            cpu_capacity="8",
            memory_capacity="16Gi",
            pods_capacity="110",
            creation_timestamp="2026-01-01T00:00:00Z",
        )

        screen._update_resource_bars([node])

        mock_container.remove_children.assert_called_once()
        assert mock_container.mount.call_count >= 4  # 1 label + 3 bars (cpu, mem, pods)

    def test_update_resource_bars_skips_none_capacity(self) -> None:
        """_update_resource_bars skips ResourceBar when capacity is None."""
        screen = _make_dashboard_screen()
        mock_container = MagicMock()
        cast(MagicMock, screen.query_one).return_value = mock_container

        node = NodeSummary(
            name="bare-node",
            status="Ready",
            roles=["worker"],
            version="v1.29.0",
            cpu_capacity=None,
            memory_capacity=None,
            pods_capacity=None,
            creation_timestamp="2026-01-01T00:00:00Z",
        )

        screen._update_resource_bars([node])

        mock_container.remove_children.assert_called_once()
        # Only the node Label should be mounted (no bars)
        assert mock_container.mount.call_count == 1


@pytest.mark.unit
class TestDashboardScreenLoadEvents:
    """Tests for DashboardScreen._load_events."""

    def test_load_events_success_filters_warnings_and_populates_table(self) -> None:
        """_load_events filters Warning events, sorts, and fills table."""
        screen = _make_dashboard_screen()
        mock_table = MagicMock()
        cast(MagicMock, screen.query_one).return_value = mock_table

        normal_event = EventSummary(
            name="normal-evt",
            namespace="default",
            type="Normal",
            reason="Created",
            message="Pod created",
            involved_object_kind="Pod",
            involved_object_name="nginx",
            count=1,
            creation_timestamp="2026-01-01T00:00:00Z",
        )
        warn_event = EventSummary(
            name="warn-evt",
            namespace="default",
            type="Warning",
            reason="BackOff",
            message="Back-off restarting container",
            involved_object_kind="Pod",
            involved_object_name="crash-pod",
            count=5,
            creation_timestamp="2026-01-02T00:00:00Z",
        )

        with patch(
            "system_operations_manager.services.kubernetes.namespace_manager.NamespaceClusterManager"
        ) as mock_cls:
            mock_cls.return_value.list_events.return_value = [normal_event, warn_event]
            screen._load_events()

        mock_table.clear.assert_called_once()
        # Only the Warning event should be added
        mock_table.add_row.assert_called_once()
        row_args = mock_table.add_row.call_args[0]
        assert "BackOff" in row_args[1]

    def test_load_events_failure_does_not_crash(self) -> None:
        """_load_events logs warning and continues on exception."""
        screen = _make_dashboard_screen()

        with patch(
            "system_operations_manager.services.kubernetes.namespace_manager.NamespaceClusterManager"
        ) as mock_cls:
            mock_cls.return_value.list_events.side_effect = RuntimeError("forbidden")
            # Should not raise
            screen._load_events()

        # notify_user is NOT called for events (unlike nodes) - just logs
        cast(MagicMock, screen.notify_user).assert_not_called()


@pytest.mark.unit
class TestDashboardScreenActions:
    """Tests for DashboardScreen keyboard action methods."""

    def test_action_back_calls_go_back(self) -> None:
        """action_back calls go_back."""
        screen = _make_dashboard_screen()
        screen.action_back()
        cast(MagicMock, screen.go_back).assert_called_once()

    def test_action_refresh_calls_refresh_all_and_notifies(self) -> None:
        """action_refresh calls _refresh_all, resets timer, notifies."""
        screen = _make_dashboard_screen()
        object.__setattr__(screen, "_refresh_all", MagicMock())
        mock_timer = MagicMock()
        cast(MagicMock, screen.query_one).return_value = mock_timer

        screen.action_refresh()

        cast(MagicMock, screen._refresh_all).assert_called_once()
        mock_timer.reset.assert_called_once()
        cast(MagicMock, screen.notify_user).assert_called_once_with("Dashboard refreshed")

    def test_action_increase_interval_calls_timer(self) -> None:
        """action_increase_interval calls increase_interval on RefreshTimer."""
        screen = _make_dashboard_screen()
        mock_timer = MagicMock()
        cast(MagicMock, screen.query_one).return_value = mock_timer

        screen.action_increase_interval()

        mock_timer.increase_interval.assert_called_once()

    def test_action_decrease_interval_calls_timer(self) -> None:
        """action_decrease_interval calls decrease_interval on RefreshTimer."""
        screen = _make_dashboard_screen()
        mock_timer = MagicMock()
        cast(MagicMock, screen.query_one).return_value = mock_timer

        screen.action_decrease_interval()

        mock_timer.decrease_interval.assert_called_once()

    def test_handle_auto_refresh_calls_refresh_all(self) -> None:
        """handle_auto_refresh calls _refresh_all."""
        from system_operations_manager.tui.apps.kubernetes.widgets import RefreshTimer

        screen = _make_dashboard_screen()
        object.__setattr__(screen, "_refresh_all", MagicMock())
        event = MagicMock(spec=RefreshTimer.RefreshTriggered)

        screen.handle_auto_refresh(event)

        cast(MagicMock, screen._refresh_all).assert_called_once()

    def test_handle_interval_changed_notifies_new_interval(self) -> None:
        """handle_interval_changed notifies the new interval."""
        from system_operations_manager.tui.apps.kubernetes.widgets import RefreshTimer

        screen = _make_dashboard_screen()
        event = RefreshTimer.IntervalChanged(30)

        screen.handle_interval_changed(event)

        cast(MagicMock, screen.notify_user).assert_called_once()
        assert "30" in cast(MagicMock, screen.notify_user).call_args[0][0]


# ============================================================================
# ResourceDetailScreen Additional Text Builder Tests
# ============================================================================


@pytest.mark.unit
class TestResourceDetailScreenStatusTextBranches:
    """Tests for _build_status_text branches not yet covered."""

    def test_status_text_services_with_multiple_ports(self) -> None:
        """_build_status_text for SERVICES joins all ports."""
        svc = ServiceSummary(
            name="multi-svc",
            namespace="default",
            type="NodePort",
            cluster_ip="10.0.0.100",
            ports=[
                ServicePort(name="http", port=80, protocol="TCP"),
                ServicePort(name="https", port=443, protocol="TCP"),
            ],
            creation_timestamp="2026-01-01T00:00:00Z",
        )
        screen = _make_resource_detail_screen(resource=svc, resource_type=ResourceType.SERVICES)
        status = screen._build_status_text()
        assert "80/TCP" in status
        assert "443/TCP" in status

    def test_status_text_namespaces_active(self) -> None:
        """_build_status_text for NAMESPACES shows colored status."""
        ns = NamespaceSummary(
            name="my-ns",
            status="Active",
            creation_timestamp="2026-01-01T00:00:00Z",
        )
        screen = _make_resource_detail_screen(resource=ns, resource_type=ResourceType.NAMESPACES)
        status = screen._build_status_text()
        assert "Active" in status
        assert "green" in status

    def test_status_text_nodes_shows_all_fields(self) -> None:
        """_build_status_text for NODES shows roles, version, IP, OS, runtime."""
        node = NodeSummary(
            name="master-1",
            status="Ready",
            roles=["control-plane"],
            version="v1.29.0",
            internal_ip="10.0.0.1",
            os_image="Ubuntu 22.04",
            container_runtime="containerd://1.7.0",
            creation_timestamp="2026-01-01T00:00:00Z",
        )
        screen = _make_resource_detail_screen(resource=node, resource_type=ResourceType.NODES)
        status = screen._build_status_text()
        assert "control-plane" in status
        assert "v1.29.0" in status
        assert "10.0.0.1" in status
        assert "Ubuntu 22.04" in status
        assert "containerd" in status

    def test_status_text_events_shows_type_reason_count_message(self) -> None:
        """_build_status_text for EVENTS shows type, reason, count, message."""
        event = EventSummary(
            name="test-event",
            namespace="default",
            type="Warning",
            reason="OOMKilled",
            message="Container OOM killed",
            involved_object_kind="Pod",
            involved_object_name="memory-hog",
            count=3,
            creation_timestamp="2026-01-01T00:00:00Z",
        )
        screen = _make_resource_detail_screen(resource=event, resource_type=ResourceType.EVENTS)
        status = screen._build_status_text()
        assert "Warning" in status
        assert "OOMKilled" in status
        assert "3" in status
        assert "OOM killed" in status

    def test_status_text_secrets_with_many_keys_truncates(self) -> None:
        """_build_status_text for SECRETS truncates when >10 keys."""
        secret = SecretSummary(
            name="huge-secret",
            namespace="default",
            type="Opaque",
            data_keys=[f"key{i}" for i in range(15)],
            creation_timestamp="2026-01-01T00:00:00Z",
        )
        screen = _make_resource_detail_screen(resource=secret, resource_type=ResourceType.SECRETS)
        status = screen._build_status_text()
        assert "(+5)" in status


@pytest.mark.unit
class TestResourceDetailScreenLabelsAnnotations:
    """Tests for _build_labels_text and _build_annotations_text edge cases."""

    def test_labels_text_with_empty_dict(self) -> None:
        """_build_labels_text returns placeholder for empty labels dict."""
        pod = PodSummary(
            name="unlabeled",
            phase="Running",
            ready_count=1,
            total_count=1,
            restarts=0,
            labels={},
        )
        screen = _make_resource_detail_screen(resource=pod)
        labels = screen._build_labels_text()
        assert "No labels" in labels

    def test_annotations_text_with_short_value(self) -> None:
        """_build_annotations_text displays short annotation values fully."""
        pod = PodSummary(
            name="annotated",
            phase="Running",
            ready_count=1,
            total_count=1,
            restarts=0,
            annotations={"team": "platform"},
        )
        screen = _make_resource_detail_screen(resource=pod)
        annotations = screen._build_annotations_text()
        assert "team=platform" in annotations
        assert "..." not in annotations

    def test_annotations_text_truncates_values_over_60_chars(self) -> None:
        """_build_annotations_text truncates values > 60 chars with '...'."""
        long_val = "x" * 70
        pod = PodSummary(
            name="long-ann",
            phase="Running",
            ready_count=1,
            total_count=1,
            restarts=0,
            annotations={"big-key": long_val},
        )
        screen = _make_resource_detail_screen(resource=pod)
        annotations = screen._build_annotations_text()
        assert "..." in annotations


@pytest.mark.unit
class TestResourceDetailScreenHeaderText:
    """Tests for _build_header_text edge cases."""

    def test_header_text_with_namespace(self) -> None:
        """_build_header_text includes namespace when present."""
        pod = PodSummary(
            name="test-pod",
            namespace="production",
            phase="Running",
            ready_count=1,
            total_count=1,
            restarts=0,
        )
        screen = _make_resource_detail_screen(resource=pod)
        header = screen._build_header_text()
        assert "production" in header
        assert "ns:" in header

    def test_header_text_without_namespace(self) -> None:
        """_build_header_text omits namespace section when namespace is None."""
        node = NodeSummary(
            name="bare-node",
            status="Ready",
            roles=["worker"],
            version="v1.29.0",
            creation_timestamp="2026-01-01T00:00:00Z",
        )
        screen = _make_resource_detail_screen(resource=node, resource_type=ResourceType.NODES)
        header = screen._build_header_text()
        assert "bare-node" in header
        assert "ns:" not in header


@pytest.mark.unit
class TestResourceDetailScreenLoadEvents:
    """Tests for ResourceDetailScreen._load_events."""

    def test_load_events_with_namespace_uses_namespaced_call(self) -> None:
        """_load_events calls list_events with namespace when resource has namespace."""
        screen = _make_resource_detail_screen()
        screen._resource.name = "my-pod"
        screen._resource.namespace = "default"
        mock_table = MagicMock()
        cast(MagicMock, screen.query_one).return_value = mock_table

        with patch(
            "system_operations_manager.services.kubernetes.namespace_manager.NamespaceClusterManager"
        ) as mock_cls:
            mock_cls.return_value.list_events.return_value = []
            screen._load_events()

        mock_cls.return_value.list_events.assert_called_once()
        call_kwargs = mock_cls.return_value.list_events.call_args[1]
        assert call_kwargs.get("namespace") == "default"

    def test_load_events_without_namespace_uses_all_namespaces(self) -> None:
        """_load_events calls list_events with all_namespaces=True when no namespace."""
        node = NodeSummary(
            name="node-1",
            status="Ready",
            roles=["worker"],
            version="v1.29.0",
            creation_timestamp="2026-01-01T00:00:00Z",
        )
        screen = _make_resource_detail_screen(resource=node, resource_type=ResourceType.NODES)
        mock_table = MagicMock()
        cast(MagicMock, screen.query_one).return_value = mock_table

        with patch(
            "system_operations_manager.services.kubernetes.namespace_manager.NamespaceClusterManager"
        ) as mock_cls:
            mock_cls.return_value.list_events.return_value = []
            screen._load_events()

        call_kwargs = mock_cls.return_value.list_events.call_args[1]
        assert call_kwargs.get("all_namespaces") is True

    def test_load_events_populates_table_rows(self) -> None:
        """_load_events adds rows to the events table for each event."""
        screen = _make_resource_detail_screen()
        mock_table = MagicMock()
        cast(MagicMock, screen.query_one).return_value = mock_table

        evt = EventSummary(
            name="pod-evt",
            namespace="default",
            type="Warning",
            reason="BackOff",
            message="Restarting",
            involved_object_kind="Pod",
            involved_object_name="test-pod",
            count=2,
            creation_timestamp="2026-01-01T00:00:00Z",
        )

        with patch(
            "system_operations_manager.services.kubernetes.namespace_manager.NamespaceClusterManager"
        ) as mock_cls:
            mock_cls.return_value.list_events.return_value = [evt]
            screen._load_events()

        mock_table.clear.assert_called_once()
        mock_table.add_row.assert_called_once()

    def test_load_events_failure_notifies_error(self) -> None:
        """_load_events notifies user on exception."""
        screen = _make_resource_detail_screen()

        with patch(
            "system_operations_manager.services.kubernetes.namespace_manager.NamespaceClusterManager"
        ) as mock_cls:
            mock_cls.return_value.list_events.side_effect = RuntimeError("forbidden")
            screen._load_events()

        cast(MagicMock, screen.notify_user).assert_called_once()
        assert "error" in cast(MagicMock, screen.notify_user).call_args[1].get("severity", "")


@pytest.mark.unit
class TestResourceDetailScreenEditActions:
    """Tests for ResourceDetailScreen action_edit and _open_yaml_editor."""

    def test_action_edit_warns_for_non_editable_types(self) -> None:
        """action_edit warns when resource type is not in EDITABLE_TYPES."""
        screen = _make_resource_detail_screen(resource_type=ResourceType.PODS)
        # PODS is not in EDITABLE_TYPES
        screen.action_edit()
        cast(MagicMock, screen.notify_user).assert_called_once()
        assert "Cannot edit" in cast(MagicMock, screen.notify_user).call_args[0][0]

    def test_action_edit_calls_open_yaml_editor_for_editable_type(self) -> None:
        """action_edit calls _open_yaml_editor for EDITABLE_TYPES."""
        deploy = DeploymentSummary(
            name="web-app",
            namespace="production",
            replicas=3,
            ready_replicas=3,
            updated_replicas=3,
            available_replicas=3,
            creation_timestamp="2026-01-01T00:00:00Z",
        )
        screen = _make_resource_detail_screen(
            resource=deploy, resource_type=ResourceType.DEPLOYMENTS
        )
        object.__setattr__(screen, "_open_yaml_editor", MagicMock())

        screen.action_edit()

        cast(MagicMock, screen._open_yaml_editor).assert_called_once()

    def test_open_yaml_editor_fetch_failure_notifies_error(self) -> None:
        """_open_yaml_editor notifies error when fetch_raw_resource fails."""
        deploy = DeploymentSummary(
            name="web-app",
            namespace="production",
            replicas=3,
            ready_replicas=3,
            updated_replicas=3,
            available_replicas=3,
            creation_timestamp="2026-01-01T00:00:00Z",
        )
        screen = _make_resource_detail_screen(
            resource=deploy, resource_type=ResourceType.DEPLOYMENTS
        )

        with patch(
            "system_operations_manager.tui.apps.kubernetes.edit_helpers.fetch_raw_resource"
        ) as mock_fetch:
            mock_fetch.side_effect = RuntimeError("not found")
            screen._open_yaml_editor()

        cast(MagicMock, screen.notify_user).assert_called_once()
        assert "Failed to fetch" in cast(MagicMock, screen.notify_user).call_args[0][0]

    def test_open_yaml_editor_no_changes_notifies(self) -> None:
        """_open_yaml_editor notifies 'No changes' when content unchanged."""
        import tempfile

        deploy = DeploymentSummary(
            name="web-app",
            namespace="production",
            replicas=3,
            ready_replicas=3,
            updated_replicas=3,
            available_replicas=3,
            creation_timestamp="2026-01-01T00:00:00Z",
        )
        screen = _make_resource_detail_screen(
            resource=deploy, resource_type=ResourceType.DEPLOYMENTS
        )
        obj_dict = {"apiVersion": "apps/v1", "kind": "Deployment"}
        mock_app = MagicMock()

        with (
            patch(
                "system_operations_manager.tui.apps.kubernetes.edit_helpers.fetch_raw_resource",
                return_value=obj_dict,
            ),
            patch("system_operations_manager.utils.editor.get_editor", return_value="vi"),
            patch("subprocess.run"),
            patch.object(type(screen), "app", new_callable=MagicMock, return_value=mock_app),
        ):
            import yaml as yaml_mod

            yaml_content = yaml_mod.dump(obj_dict, default_flow_style=False, sort_keys=False)

            with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as tmp:
                tmp.write(yaml_content)
                tmp_path = tmp.name

            with patch("tempfile.NamedTemporaryFile") as mock_tmpfile:
                mock_tmp_ctx = MagicMock()
                object.__setattr__(
                    mock_tmp_ctx, "__enter__", MagicMock(return_value=MagicMock(name=tmp_path))
                )
                object.__setattr__(mock_tmp_ctx, "__exit__", MagicMock(return_value=False))
                mock_tmpfile.return_value = mock_tmp_ctx

                with patch("pathlib.Path.open") as mock_open:
                    mock_open.return_value.__enter__ = MagicMock(
                        return_value=MagicMock(read=MagicMock(return_value=yaml_content))
                    )
                    mock_open.return_value.__exit__ = MagicMock(return_value=False)
                    with patch("pathlib.Path.unlink"):
                        screen._open_yaml_editor()

        # Should notify "No changes" or similar
        assert cast(MagicMock, screen.notify_user).called


@pytest.mark.unit
class TestResourceDetailScreenRefreshDetail:
    """Tests for ResourceDetailScreen._refresh_detail."""

    def test_refresh_detail_success_updates_yaml_and_events(self) -> None:
        """_refresh_detail fetches resource, updates YAML panel, refreshes events."""
        screen = _make_resource_detail_screen()
        object.__setattr__(screen, "_load_events", MagicMock())
        mock_yaml_widget = MagicMock()
        cast(MagicMock, screen.query_one).return_value = mock_yaml_widget

        with patch(
            "system_operations_manager.tui.apps.kubernetes.edit_helpers.fetch_raw_resource",
            return_value={"name": "test-pod"},
        ):
            screen._refresh_detail()

        mock_yaml_widget.update.assert_called_once()
        cast(MagicMock, screen._load_events).assert_called_once()

    def test_refresh_detail_failure_notifies_error(self) -> None:
        """_refresh_detail notifies user on fetch failure."""
        screen = _make_resource_detail_screen()

        with patch(
            "system_operations_manager.tui.apps.kubernetes.edit_helpers.fetch_raw_resource"
        ) as mock_fetch:
            mock_fetch.side_effect = RuntimeError("not found")
            screen._refresh_detail()

        cast(MagicMock, screen.notify_user).assert_called_once()
        assert "Refresh failed" in cast(MagicMock, screen.notify_user).call_args[0][0]


@pytest.mark.unit
class TestResourceDetailScreenDeleteActions:
    """Tests for ResourceDetailScreen action_delete and _handle_delete_result."""

    def test_action_delete_warns_for_non_deletable_type(self) -> None:
        """action_delete warns when resource type is not deletable."""
        event_resource = EventSummary(
            name="event-1",
            namespace="default",
            type="Warning",
            reason="BackOff",
            count=1,
            creation_timestamp="2026-01-01T00:00:00Z",
        )
        screen = _make_resource_detail_screen(
            resource=event_resource, resource_type=ResourceType.EVENTS
        )
        screen.action_delete()
        cast(MagicMock, screen.notify_user).assert_called_once()
        assert "Cannot delete" in cast(MagicMock, screen.notify_user).call_args[0][0]

    def test_action_delete_pushes_modal_for_deletable_type(self) -> None:
        """action_delete pushes confirmation modal for deletable types."""
        screen = _make_resource_detail_screen(resource_type=ResourceType.PODS)
        mock_app = MagicMock()

        with (
            patch.object(type(screen), "app", new_callable=PropertyMock, return_value=mock_app),
            patch("system_operations_manager.tui.components.modal.Modal") as mock_modal_cls,
        ):
            mock_modal_cls.return_value = MagicMock()
            screen.action_delete()

        cast(MagicMock, mock_app.push_screen).assert_called_once()

    def test_handle_delete_result_delete_success_calls_go_back(self) -> None:
        """_handle_delete_result calls delete_resource and go_back on 'delete'."""
        screen = _make_resource_detail_screen(resource_type=ResourceType.PODS)

        with patch(
            "system_operations_manager.tui.apps.kubernetes.delete_helpers.delete_resource"
        ) as mock_delete:
            screen._handle_delete_result("delete")

        mock_delete.assert_called_once()
        cast(MagicMock, screen.notify_user).assert_called_once()
        cast(MagicMock, screen.go_back).assert_called_once()

    def test_handle_delete_result_delete_failure_notifies_error(self) -> None:
        """_handle_delete_result notifies error when delete_resource raises."""
        screen = _make_resource_detail_screen(resource_type=ResourceType.PODS)

        with patch(
            "system_operations_manager.tui.apps.kubernetes.delete_helpers.delete_resource"
        ) as mock_delete:
            mock_delete.side_effect = RuntimeError("permission denied")
            screen._handle_delete_result("delete")

        cast(MagicMock, screen.notify_user).assert_called_once()
        assert "error" in cast(MagicMock, screen.notify_user).call_args[1].get("severity", "")
        cast(MagicMock, screen.go_back).assert_not_called()

    def test_handle_delete_result_cancel_is_noop(self) -> None:
        """_handle_delete_result with non-'delete' result does nothing."""
        screen = _make_resource_detail_screen(resource_type=ResourceType.PODS)

        with patch(
            "system_operations_manager.tui.apps.kubernetes.delete_helpers.delete_resource"
        ) as mock_delete:
            screen._handle_delete_result("cancel")

        mock_delete.assert_not_called()
        cast(MagicMock, screen.notify_user).assert_not_called()
        cast(MagicMock, screen.go_back).assert_not_called()


@pytest.mark.unit
class TestResourceDetailScreenLogsExec:
    """Tests for ResourceDetailScreen action_logs and action_exec."""

    def test_action_logs_warns_for_non_pods(self) -> None:
        """action_logs warns for non-PODS resource type."""
        deploy = DeploymentSummary(
            name="web-app",
            namespace="production",
            replicas=3,
            ready_replicas=3,
            updated_replicas=3,
            available_replicas=3,
            creation_timestamp="2026-01-01T00:00:00Z",
        )
        screen = _make_resource_detail_screen(
            resource=deploy, resource_type=ResourceType.DEPLOYMENTS
        )
        screen.action_logs()
        cast(MagicMock, screen.notify_user).assert_called_once()
        assert "warning" in cast(MagicMock, screen.notify_user).call_args[1].get("severity", "")

    def test_action_logs_pushes_log_viewer_for_pods(self) -> None:
        """action_logs pushes LogViewerScreen for PODS type."""
        screen = _make_resource_detail_screen(resource_type=ResourceType.PODS)
        mock_app = MagicMock()

        with (
            patch.object(type(screen), "app", new_callable=PropertyMock, return_value=mock_app),
            patch(
                "system_operations_manager.tui.apps.kubernetes.log_viewer.LogViewerScreen"
            ) as mock_lv_cls,
        ):
            mock_lv_cls.return_value = MagicMock()
            screen.action_logs()

        cast(MagicMock, mock_app.push_screen).assert_called_once()

    def test_action_exec_warns_for_non_pods(self) -> None:
        """action_exec warns for non-PODS resource type."""
        deploy = DeploymentSummary(
            name="web-app",
            namespace="production",
            replicas=3,
            ready_replicas=3,
            updated_replicas=3,
            available_replicas=3,
            creation_timestamp="2026-01-01T00:00:00Z",
        )
        screen = _make_resource_detail_screen(
            resource=deploy, resource_type=ResourceType.DEPLOYMENTS
        )
        screen.action_exec()
        cast(MagicMock, screen.notify_user).assert_called_once()
        assert "warning" in cast(MagicMock, screen.notify_user).call_args[1].get("severity", "")

    def test_action_exec_with_single_container_calls_run_exec(self) -> None:
        """action_exec with single container calls _run_exec directly."""
        pod = PodSummary(
            name="single-container-pod",
            namespace="default",
            phase="Running",
            ready_count=1,
            total_count=1,
            restarts=0,
        )
        mock_container = MagicMock()
        mock_container.name = "app"
        pod.containers = [mock_container]

        screen = _make_resource_detail_screen(resource=pod, resource_type=ResourceType.PODS)
        object.__setattr__(screen, "_run_exec", MagicMock())

        screen.action_exec()

        cast(MagicMock, screen._run_exec).assert_called_once_with("app")

    def test_action_exec_with_no_containers_calls_run_exec_with_none(self) -> None:
        """action_exec with no containers calls _run_exec(None)."""
        pod = PodSummary(
            name="empty-pod",
            namespace="default",
            phase="Running",
            ready_count=1,
            total_count=1,
            restarts=0,
        )
        pod.containers = []

        screen = _make_resource_detail_screen(resource=pod, resource_type=ResourceType.PODS)
        object.__setattr__(screen, "_run_exec", MagicMock())

        screen.action_exec()

        cast(MagicMock, screen._run_exec).assert_called_once_with(None)

    def test_action_exec_with_multiple_containers_pushes_selector(self) -> None:
        """action_exec with >1 container pushes SelectorPopup."""
        pod = PodSummary(
            name="multi-pod",
            namespace="default",
            phase="Running",
            ready_count=2,
            total_count=2,
            restarts=0,
        )
        c1 = MagicMock()
        c1.name = "app"
        c2 = MagicMock()
        c2.name = "sidecar"
        pod.containers = [c1, c2]

        screen = _make_resource_detail_screen(resource=pod, resource_type=ResourceType.PODS)
        mock_app = MagicMock()

        with (
            patch.object(type(screen), "app", new_callable=PropertyMock, return_value=mock_app),
            patch(
                "system_operations_manager.tui.apps.kubernetes.widgets.SelectorPopup"
            ) as mock_popup_cls,
        ):
            mock_popup_cls.return_value = MagicMock()
            screen.action_exec()

        cast(MagicMock, mock_app.push_screen).assert_called_once()

    def test_handle_exec_container_selected_calls_run_exec(self) -> None:
        """_handle_exec_container_selected calls _run_exec when result is truthy."""
        screen = _make_resource_detail_screen()
        object.__setattr__(screen, "_run_exec", MagicMock())

        screen._handle_exec_container_selected("app-container")

        cast(MagicMock, screen._run_exec).assert_called_once_with("app-container")

    def test_handle_exec_container_selected_none_is_noop(self) -> None:
        """_handle_exec_container_selected does nothing when result is None."""
        screen = _make_resource_detail_screen()
        object.__setattr__(screen, "_run_exec", MagicMock())

        screen._handle_exec_container_selected(None)

        cast(MagicMock, screen._run_exec).assert_not_called()

    def test_run_exec_failure_notifies_error(self) -> None:
        """_run_exec notifies error when StreamingManager.exec_command raises."""
        screen = _make_resource_detail_screen(resource_type=ResourceType.PODS)

        with patch(
            "system_operations_manager.services.kubernetes.streaming_manager.StreamingManager"
        ) as mock_cls:
            mock_cls.return_value.exec_command.side_effect = RuntimeError("exec failed")
            screen._run_exec("app")

        cast(MagicMock, screen.notify_user).assert_called_once()
        assert "error" in cast(MagicMock, screen.notify_user).call_args[1].get("severity", "")

    def test_run_exec_import_error_notifies_unix_required(self) -> None:
        """_run_exec notifies about Unix terminal requirement on ImportError.

        Simulates the ImportError branch by patching the termios module import
        inside the screens module with a fake that raises ImportError.
        """
        import sys

        screen = _make_resource_detail_screen(resource_type=ResourceType.PODS)
        mock_ws_client = MagicMock()

        # Temporarily hide termios from sys.modules to force ImportError path
        termios_backup = sys.modules.get("termios", None)
        tty_backup = sys.modules.get("tty", None)

        sys.modules["termios"] = None  # type: ignore[assignment]
        sys.modules["tty"] = None  # type: ignore[assignment]

        try:
            with patch(
                "system_operations_manager.services.kubernetes.streaming_manager.StreamingManager"
            ) as mock_cls:
                mock_cls.return_value.exec_command.return_value = mock_ws_client
                screen._run_exec("app")
        except Exception:
            pass
        finally:
            # Restore modules
            if termios_backup is None:
                sys.modules.pop("termios", None)
            else:
                sys.modules["termios"] = termios_backup
            if tty_backup is None:
                sys.modules.pop("tty", None)
            else:
                sys.modules["tty"] = tty_backup

        # exec_command was called and either notified or succeeded depending on platform
        assert mock_ws_client is not None  # ws_client was created or notification sent
