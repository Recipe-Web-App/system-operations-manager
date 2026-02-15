"""Unit tests for Kubernetes TUI screens.

Tests ResourceListScreen, ResourceDetailScreen, column definitions,
and row conversion.
"""

from __future__ import annotations

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
