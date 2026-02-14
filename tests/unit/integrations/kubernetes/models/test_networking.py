"""Unit tests for Kubernetes networking resource models."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from system_operations_manager.integrations.kubernetes.models.networking import (
    IngressRule,
    IngressSummary,
    NetworkPolicySummary,
    ServicePort,
    ServiceSummary,
)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestServicePort:
    """Test ServicePort model."""

    def test_from_k8s_object_complete(self) -> None:
        """Test from_k8s_object with complete ServicePort."""
        obj = MagicMock()
        obj.name = "http"
        obj.port = 80
        obj.target_port = 8080
        obj.protocol = "TCP"
        obj.node_port = 30080

        port = ServicePort.from_k8s_object(obj)

        assert port.name == "http"
        assert port.port == 80
        assert port.target_port == "8080"
        assert port.protocol == "TCP"
        assert port.node_port == 30080

    def test_from_k8s_object_named_target_port(self) -> None:
        """Test from_k8s_object with named target port."""
        obj = MagicMock()
        obj.name = "https"
        obj.port = 443
        obj.target_port = "https"
        obj.protocol = "TCP"
        obj.node_port = None

        port = ServicePort.from_k8s_object(obj)

        assert port.target_port == "https"

    def test_from_k8s_object_minimal(self) -> None:
        """Test from_k8s_object with minimal ServicePort."""
        obj = MagicMock()
        obj.name = ""
        obj.port = 8080
        obj.target_port = None
        obj.protocol = None
        obj.node_port = None

        port = ServicePort.from_k8s_object(obj)

        assert port.name == ""
        assert port.port == 8080
        assert port.target_port is None
        assert port.protocol == "TCP"
        assert port.node_port is None

    def test_from_k8s_object_udp_protocol(self) -> None:
        """Test from_k8s_object with UDP protocol."""
        obj = MagicMock()
        obj.name = "dns"
        obj.port = 53
        obj.target_port = None
        obj.protocol = "UDP"
        obj.node_port = None

        port = ServicePort.from_k8s_object(obj)

        assert port.protocol == "UDP"

    def test_entity_name(self) -> None:
        """Test entity name class variable."""
        assert ServicePort._entity_name == "serviceport"


@pytest.mark.unit
@pytest.mark.kubernetes
class TestServiceSummary:
    """Test ServiceSummary model."""

    def test_from_k8s_object_complete(self) -> None:
        """Test from_k8s_object with complete Service."""
        obj = MagicMock()
        obj.metadata.name = "web-service"
        obj.metadata.namespace = "default"
        obj.metadata.uid = "uid-svc-123"
        obj.metadata.creation_timestamp = "2024-01-01T00:00:00Z"
        obj.metadata.labels = {"app": "web"}
        obj.metadata.annotations = {}

        obj.spec.type = "ClusterIP"
        obj.spec.cluster_ip = "10.96.0.1"
        obj.spec.external_i_ps = []
        obj.spec.selector = {"app": "web", "tier": "frontend"}

        # Ports
        port1 = MagicMock()
        port1.name = "http"
        port1.port = 80
        port1.target_port = 8080
        port1.protocol = "TCP"
        port1.node_port = None

        obj.spec.ports = [port1]
        obj.status.load_balancer.ingress = []

        svc = ServiceSummary.from_k8s_object(obj)

        assert svc.name == "web-service"
        assert svc.type == "ClusterIP"
        assert svc.cluster_ip == "10.96.0.1"
        assert svc.external_ip is None
        assert len(svc.ports) == 1
        assert svc.ports[0].name == "http"
        assert svc.selector == {"app": "web", "tier": "frontend"}

    def test_from_k8s_object_load_balancer(self) -> None:
        """Test from_k8s_object with LoadBalancer Service."""
        obj = MagicMock()
        obj.metadata.name = "lb-service"
        obj.metadata.namespace = "production"
        obj.metadata.uid = None
        obj.metadata.creation_timestamp = None
        obj.metadata.labels = None
        obj.metadata.annotations = None

        obj.spec.type = "LoadBalancer"
        obj.spec.cluster_ip = "10.96.1.1"
        obj.spec.external_i_ps = []
        obj.spec.selector = {"app": "api"}
        obj.spec.ports = []

        # Load balancer ingress
        ingress = MagicMock()
        ingress.ip = "203.0.113.50"
        ingress.hostname = None
        obj.status.load_balancer.ingress = [ingress]

        svc = ServiceSummary.from_k8s_object(obj)

        assert svc.type == "LoadBalancer"
        assert svc.external_ip == "203.0.113.50"

    def test_from_k8s_object_load_balancer_hostname(self) -> None:
        """Test from_k8s_object with LoadBalancer hostname."""
        obj = MagicMock()
        obj.metadata.name = "lb-hostname-service"
        obj.metadata.namespace = "default"
        obj.metadata.uid = None
        obj.metadata.creation_timestamp = None
        obj.metadata.labels = None
        obj.metadata.annotations = None

        obj.spec.type = "LoadBalancer"
        obj.spec.cluster_ip = "10.96.1.2"
        obj.spec.external_i_ps = []
        obj.spec.selector = {}
        obj.spec.ports = []

        ingress = MagicMock()
        ingress.ip = None
        ingress.hostname = "lb.example.com"
        obj.status.load_balancer.ingress = [ingress]

        svc = ServiceSummary.from_k8s_object(obj)

        assert svc.external_ip == "lb.example.com"

    def test_from_k8s_object_node_port(self) -> None:
        """Test from_k8s_object with NodePort Service."""
        obj = MagicMock()
        obj.metadata.name = "nodeport-service"
        obj.metadata.namespace = "default"
        obj.metadata.uid = None
        obj.metadata.creation_timestamp = None
        obj.metadata.labels = None
        obj.metadata.annotations = None

        obj.spec.type = "NodePort"
        obj.spec.cluster_ip = "10.96.2.1"
        obj.spec.external_i_ps = []
        obj.spec.selector = {"app": "backend"}

        port = MagicMock()
        port.name = "api"
        port.port = 8080
        port.target_port = 8080
        port.protocol = "TCP"
        port.node_port = 31000

        obj.spec.ports = [port]
        obj.status.load_balancer.ingress = []

        svc = ServiceSummary.from_k8s_object(obj)

        assert svc.type == "NodePort"
        assert svc.ports[0].node_port == 31000

    def test_from_k8s_object_external_ips(self) -> None:
        """Test from_k8s_object with external IPs."""
        obj = MagicMock()
        obj.metadata.name = "external-service"
        obj.metadata.namespace = "default"
        obj.metadata.uid = None
        obj.metadata.creation_timestamp = None
        obj.metadata.labels = None
        obj.metadata.annotations = None

        obj.spec.type = "ClusterIP"
        obj.spec.cluster_ip = "10.96.3.1"
        obj.spec.external_i_ps = ["203.0.113.100"]
        obj.spec.selector = {}
        obj.spec.ports = []
        obj.status.load_balancer.ingress = []

        svc = ServiceSummary.from_k8s_object(obj)

        assert svc.external_ip == "203.0.113.100"

    def test_from_k8s_object_multiple_ports(self) -> None:
        """Test from_k8s_object with multiple ports."""
        obj = MagicMock()
        obj.metadata.name = "multi-port-service"
        obj.metadata.namespace = "default"
        obj.metadata.uid = None
        obj.metadata.creation_timestamp = None
        obj.metadata.labels = None
        obj.metadata.annotations = None

        obj.spec.type = "ClusterIP"
        obj.spec.cluster_ip = "10.96.4.1"
        obj.spec.external_i_ps = []
        obj.spec.selector = {}

        port1 = MagicMock()
        port1.name = "http"
        port1.port = 80
        port1.target_port = None
        port1.protocol = "TCP"
        port1.node_port = None

        port2 = MagicMock()
        port2.name = "https"
        port2.port = 443
        port2.target_port = None
        port2.protocol = "TCP"
        port2.node_port = None

        obj.spec.ports = [port1, port2]
        obj.status.load_balancer.ingress = []

        svc = ServiceSummary.from_k8s_object(obj)

        assert len(svc.ports) == 2

    def test_from_k8s_object_no_selector(self) -> None:
        """Test from_k8s_object with no selector."""
        obj = MagicMock()
        obj.metadata.name = "headless-service"
        obj.metadata.namespace = "default"
        obj.metadata.uid = None
        obj.metadata.creation_timestamp = None
        obj.metadata.labels = None
        obj.metadata.annotations = None

        obj.spec.type = "ClusterIP"
        obj.spec.cluster_ip = "None"
        obj.spec.external_i_ps = []
        obj.spec.selector = None
        obj.spec.ports = []
        obj.status.load_balancer.ingress = []

        svc = ServiceSummary.from_k8s_object(obj)

        assert svc.selector is None

    def test_entity_name(self) -> None:
        """Test entity name class variable."""
        assert ServiceSummary._entity_name == "service"


@pytest.mark.unit
@pytest.mark.kubernetes
class TestIngressRule:
    """Test IngressRule model."""

    def test_from_k8s_object_complete(self) -> None:
        """Test from_k8s_object with complete IngressRule."""
        obj = MagicMock()
        obj.host = "example.com"

        path1 = MagicMock()
        path1.path = "/api"
        path2 = MagicMock()
        path2.path = "/web"

        obj.http.paths = [path1, path2]

        rule = IngressRule.from_k8s_object(obj)

        assert rule.name == "example.com"
        assert rule.host == "example.com"
        assert rule.paths == ["/api", "/web"]

    def test_from_k8s_object_no_host(self) -> None:
        """Test from_k8s_object with no host (wildcard)."""
        obj = MagicMock()
        obj.host = None

        path = MagicMock()
        path.path = "/"
        obj.http.paths = [path]

        rule = IngressRule.from_k8s_object(obj)

        assert rule.name == "*"
        assert rule.host is None
        assert rule.paths == ["/"]

    def test_from_k8s_object_no_paths(self) -> None:
        """Test from_k8s_object with no paths."""
        obj = MagicMock()
        obj.host = "test.com"
        obj.http = None

        rule = IngressRule.from_k8s_object(obj)

        assert rule.host == "test.com"
        assert rule.paths == []

    def test_from_k8s_object_empty_paths(self) -> None:
        """Test from_k8s_object with empty paths."""
        obj = MagicMock()
        obj.host = "empty.com"
        obj.http.paths = []

        rule = IngressRule.from_k8s_object(obj)

        assert rule.paths == []

    def test_from_k8s_object_none_path_defaults(self) -> None:
        """Test from_k8s_object with None path."""
        obj = MagicMock()
        obj.host = "default.com"

        path = MagicMock()
        path.path = None
        obj.http.paths = [path]

        rule = IngressRule.from_k8s_object(obj)

        assert rule.paths == ["/"]

    def test_entity_name(self) -> None:
        """Test entity name class variable."""
        assert IngressRule._entity_name == "ingressrule"


@pytest.mark.unit
@pytest.mark.kubernetes
class TestIngressSummary:
    """Test IngressSummary model."""

    def test_from_k8s_object_complete(self) -> None:
        """Test from_k8s_object with complete Ingress."""
        obj = MagicMock()
        obj.metadata.name = "web-ingress"
        obj.metadata.namespace = "default"
        obj.metadata.uid = "uid-ing-123"
        obj.metadata.creation_timestamp = "2024-01-01T00:00:00Z"
        obj.metadata.labels = {"app": "web"}
        obj.metadata.annotations = {}

        obj.spec.ingress_class_name = "nginx"

        # Rules
        rule1 = MagicMock()
        rule1.host = "example.com"
        rule1.http.paths = []

        rule2 = MagicMock()
        rule2.host = "www.example.com"
        rule2.http.paths = []

        obj.spec.rules = [rule1, rule2]

        # Load balancer ingress
        lb_ing = MagicMock()
        lb_ing.ip = "203.0.113.10"
        lb_ing.hostname = None
        obj.status.load_balancer.ingress = [lb_ing]

        ingress = IngressSummary.from_k8s_object(obj)

        assert ingress.name == "web-ingress"
        assert ingress.class_name == "nginx"
        assert ingress.hosts == ["example.com", "www.example.com"]
        assert ingress.addresses == ["203.0.113.10"]
        assert len(ingress.rules) == 2

    def test_from_k8s_object_multiple_addresses(self) -> None:
        """Test from_k8s_object with multiple load balancer addresses."""
        obj = MagicMock()
        obj.metadata.name = "multi-lb-ingress"
        obj.metadata.namespace = "default"
        obj.metadata.uid = None
        obj.metadata.creation_timestamp = None
        obj.metadata.labels = None
        obj.metadata.annotations = None

        obj.spec.ingress_class_name = None
        obj.spec.rules = []

        lb_ing1 = MagicMock()
        lb_ing1.ip = "203.0.113.10"
        lb_ing1.hostname = None

        lb_ing2 = MagicMock()
        lb_ing2.ip = None
        lb_ing2.hostname = "lb.example.com"

        obj.status.load_balancer.ingress = [lb_ing1, lb_ing2]

        ingress = IngressSummary.from_k8s_object(obj)

        assert ingress.addresses == ["203.0.113.10", "lb.example.com"]

    def test_from_k8s_object_no_rules(self) -> None:
        """Test from_k8s_object with no rules."""
        obj = MagicMock()
        obj.metadata.name = "empty-ingress"
        obj.metadata.namespace = "default"
        obj.metadata.uid = None
        obj.metadata.creation_timestamp = None
        obj.metadata.labels = None
        obj.metadata.annotations = None

        obj.spec.ingress_class_name = "nginx"
        obj.spec.rules = None
        obj.status.load_balancer.ingress = []

        ingress = IngressSummary.from_k8s_object(obj)

        assert ingress.rules == []
        assert ingress.hosts == []

    def test_from_k8s_object_wildcard_host(self) -> None:
        """Test from_k8s_object with wildcard host."""
        obj = MagicMock()
        obj.metadata.name = "wildcard-ingress"
        obj.metadata.namespace = "default"
        obj.metadata.uid = None
        obj.metadata.creation_timestamp = None
        obj.metadata.labels = None
        obj.metadata.annotations = None

        obj.spec.ingress_class_name = None

        rule = MagicMock()
        rule.host = None
        rule.http.paths = []
        obj.spec.rules = [rule]

        obj.status.load_balancer.ingress = []

        ingress = IngressSummary.from_k8s_object(obj)

        assert len(ingress.rules) == 1
        assert ingress.hosts == []

    def test_entity_name(self) -> None:
        """Test entity name class variable."""
        assert IngressSummary._entity_name == "ingress"


@pytest.mark.unit
@pytest.mark.kubernetes
class TestNetworkPolicySummary:
    """Test NetworkPolicySummary model."""

    def test_from_k8s_object_complete(self) -> None:
        """Test from_k8s_object with complete NetworkPolicy."""
        obj = MagicMock()
        obj.metadata.name = "deny-all"
        obj.metadata.namespace = "production"
        obj.metadata.uid = "uid-np-123"
        obj.metadata.creation_timestamp = "2024-01-01T00:00:00Z"
        obj.metadata.labels = {"security": "strict"}
        obj.metadata.annotations = {}

        obj.spec.pod_selector.match_labels = {"app": "web", "tier": "frontend"}
        obj.spec.policy_types = ["Ingress", "Egress"]

        # Ingress rules
        ingress1 = MagicMock()
        ingress2 = MagicMock()
        obj.spec.ingress = [ingress1, ingress2]

        # Egress rules
        egress1 = MagicMock()
        obj.spec.egress = [egress1]

        np = NetworkPolicySummary.from_k8s_object(obj)

        assert np.name == "deny-all"
        assert np.pod_selector == {"app": "web", "tier": "frontend"}
        assert np.policy_types == ["Ingress", "Egress"]
        assert np.ingress_rules_count == 2
        assert np.egress_rules_count == 1

    def test_from_k8s_object_ingress_only(self) -> None:
        """Test from_k8s_object with ingress only policy."""
        obj = MagicMock()
        obj.metadata.name = "allow-ingress"
        obj.metadata.namespace = "default"
        obj.metadata.uid = None
        obj.metadata.creation_timestamp = None
        obj.metadata.labels = None
        obj.metadata.annotations = None

        obj.spec.pod_selector.match_labels = {"app": "db"}
        obj.spec.policy_types = ["Ingress"]

        ingress = MagicMock()
        obj.spec.ingress = [ingress]
        obj.spec.egress = None

        np = NetworkPolicySummary.from_k8s_object(obj)

        assert np.policy_types == ["Ingress"]
        assert np.ingress_rules_count == 1
        assert np.egress_rules_count == 0

    def test_from_k8s_object_egress_only(self) -> None:
        """Test from_k8s_object with egress only policy."""
        obj = MagicMock()
        obj.metadata.name = "allow-egress"
        obj.metadata.namespace = "default"
        obj.metadata.uid = None
        obj.metadata.creation_timestamp = None
        obj.metadata.labels = None
        obj.metadata.annotations = None

        obj.spec.pod_selector.match_labels = {}
        obj.spec.policy_types = ["Egress"]

        obj.spec.ingress = None
        egress = MagicMock()
        obj.spec.egress = [egress]

        np = NetworkPolicySummary.from_k8s_object(obj)

        assert np.policy_types == ["Egress"]
        assert np.ingress_rules_count == 0
        assert np.egress_rules_count == 1

    def test_from_k8s_object_no_selector(self) -> None:
        """Test from_k8s_object with empty pod selector."""
        obj = MagicMock()
        obj.metadata.name = "all-pods"
        obj.metadata.namespace = "default"
        obj.metadata.uid = None
        obj.metadata.creation_timestamp = None
        obj.metadata.labels = None
        obj.metadata.annotations = None

        obj.spec.pod_selector.match_labels = None
        obj.spec.policy_types = []
        obj.spec.ingress = []
        obj.spec.egress = []

        np = NetworkPolicySummary.from_k8s_object(obj)

        assert np.pod_selector is None

    def test_from_k8s_object_minimal(self) -> None:
        """Test from_k8s_object with minimal NetworkPolicy."""
        obj = MagicMock()
        obj.metadata.name = "minimal-np"
        obj.metadata.namespace = None
        obj.metadata.uid = None
        obj.metadata.creation_timestamp = None
        obj.metadata.labels = None
        obj.metadata.annotations = None

        obj.spec.pod_selector.match_labels = None
        obj.spec.policy_types = None
        obj.spec.ingress = None
        obj.spec.egress = None

        np = NetworkPolicySummary.from_k8s_object(obj)

        assert np.name == "minimal-np"
        assert np.policy_types == []
        assert np.ingress_rules_count == 0
        assert np.egress_rules_count == 0

    def test_entity_name(self) -> None:
        """Test entity name class variable."""
        assert NetworkPolicySummary._entity_name == "networkpolicy"
