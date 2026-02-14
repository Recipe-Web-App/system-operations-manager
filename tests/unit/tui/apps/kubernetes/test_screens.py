"""Unit tests for Kubernetes TUI screens.

Tests ResourceListScreen, column definitions, and row conversion.
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
