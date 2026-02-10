"""Kubernetes networking resource display models."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import Field

from system_operations_manager.integrations.kubernetes.models.base import (
    K8sEntityBase,
    _get_annotations,
    _get_labels,
    _get_timestamp,
    _safe_get,
)


class ServicePort(K8sEntityBase):
    """Service port definition."""

    _entity_name: ClassVar[str] = "serviceport"

    port: int = Field(description="Service port number")
    target_port: str | int | None = Field(default=None, description="Target port")
    protocol: str = Field(default="TCP", description="Protocol")
    node_port: int | None = Field(default=None, description="Node port")

    @classmethod
    def from_k8s_object(cls, obj: Any) -> ServicePort:
        """Create from a kubernetes V1ServicePort object."""
        target_port = getattr(obj, "target_port", None)
        if target_port is not None:
            target_port = str(target_port)
        return cls(
            name=getattr(obj, "name", "") or "",
            port=getattr(obj, "port", 0),
            target_port=target_port,
            protocol=getattr(obj, "protocol", "TCP") or "TCP",
            node_port=getattr(obj, "node_port", None),
        )


class ServiceSummary(K8sEntityBase):
    """Service display model."""

    _entity_name: ClassVar[str] = "service"

    type: str = Field(default="ClusterIP", description="Service type")
    cluster_ip: str | None = Field(default=None, description="Cluster IP")
    external_ip: str | None = Field(default=None, description="External IP")
    ports: list[ServicePort] = Field(default_factory=list, description="Service ports")
    selector: dict[str, str] | None = Field(default=None, description="Pod selector")

    @classmethod
    def from_k8s_object(cls, obj: Any) -> ServiceSummary:
        """Create from a kubernetes V1Service object."""
        spec = getattr(obj, "spec", None)
        ports = _safe_get(obj, "spec", "ports") or []

        # External IP from status or spec
        external_ips = _safe_get(obj, "spec", "external_i_ps") or []
        lb_ingress = _safe_get(obj, "status", "load_balancer", "ingress") or []
        external_ip = None
        if external_ips:
            external_ip = external_ips[0]
        elif lb_ingress:
            external_ip = getattr(lb_ingress[0], "ip", None) or getattr(
                lb_ingress[0], "hostname", None
            )

        selector = _safe_get(spec, "selector")

        return cls(
            name=_safe_get(obj, "metadata", "name", default=""),
            namespace=_safe_get(obj, "metadata", "namespace"),
            uid=_safe_get(obj, "metadata", "uid"),
            creation_timestamp=_get_timestamp(_safe_get(obj, "metadata", "creation_timestamp")),
            labels=_get_labels(obj),
            annotations=_get_annotations(obj),
            type=_safe_get(spec, "type", default="ClusterIP"),
            cluster_ip=_safe_get(spec, "cluster_ip"),
            external_ip=external_ip,
            ports=[ServicePort.from_k8s_object(p) for p in ports],
            selector=dict(selector) if selector else None,
        )


class IngressRule(K8sEntityBase):
    """Ingress rule definition."""

    _entity_name: ClassVar[str] = "ingressrule"

    host: str | None = Field(default=None, description="Hostname")
    paths: list[str] = Field(default_factory=list, description="Path patterns")

    @classmethod
    def from_k8s_object(cls, obj: Any) -> IngressRule:
        """Create from a kubernetes V1IngressRule object."""
        host = getattr(obj, "host", None)
        http = getattr(obj, "http", None)
        paths: list[str] = []
        if http and (http_paths := getattr(http, "paths", None)):
            for p in http_paths:
                path = getattr(p, "path", "/")
                paths.append(str(path) if path else "/")

        return cls(
            name=host or "*",
            host=host,
            paths=paths,
        )


class IngressSummary(K8sEntityBase):
    """Ingress display model."""

    _entity_name: ClassVar[str] = "ingress"

    class_name: str | None = Field(default=None, description="Ingress class")
    hosts: list[str] = Field(default_factory=list, description="Hostnames")
    addresses: list[str] = Field(default_factory=list, description="Load balancer addresses")
    rules: list[IngressRule] = Field(default_factory=list, description="Ingress rules")

    @classmethod
    def from_k8s_object(cls, obj: Any) -> IngressSummary:
        """Create from a kubernetes V1Ingress object."""
        rules_raw = _safe_get(obj, "spec", "rules") or []
        rules = [IngressRule.from_k8s_object(r) for r in rules_raw]
        hosts = [r.host for r in rules if r.host]

        # Addresses from status
        lb_ingress = _safe_get(obj, "status", "load_balancer", "ingress") or []
        addresses = []
        for ing in lb_ingress:
            addr = getattr(ing, "ip", None) or getattr(ing, "hostname", None)
            if addr:
                addresses.append(str(addr))

        return cls(
            name=_safe_get(obj, "metadata", "name", default=""),
            namespace=_safe_get(obj, "metadata", "namespace"),
            uid=_safe_get(obj, "metadata", "uid"),
            creation_timestamp=_get_timestamp(_safe_get(obj, "metadata", "creation_timestamp")),
            labels=_get_labels(obj),
            annotations=_get_annotations(obj),
            class_name=_safe_get(obj, "spec", "ingress_class_name"),
            hosts=hosts,
            addresses=addresses,
            rules=rules,
        )


class NetworkPolicySummary(K8sEntityBase):
    """NetworkPolicy display model."""

    _entity_name: ClassVar[str] = "networkpolicy"

    pod_selector: dict[str, str] | None = Field(default=None, description="Pod selector")
    policy_types: list[str] = Field(default_factory=list, description="Policy types")
    ingress_rules_count: int = Field(default=0, description="Number of ingress rules")
    egress_rules_count: int = Field(default=0, description="Number of egress rules")

    @classmethod
    def from_k8s_object(cls, obj: Any) -> NetworkPolicySummary:
        """Create from a kubernetes V1NetworkPolicy object."""
        pod_selector_labels = _safe_get(obj, "spec", "pod_selector", "match_labels")
        policy_types = _safe_get(obj, "spec", "policy_types") or []
        ingress_rules = _safe_get(obj, "spec", "ingress") or []
        egress_rules = _safe_get(obj, "spec", "egress") or []

        return cls(
            name=_safe_get(obj, "metadata", "name", default=""),
            namespace=_safe_get(obj, "metadata", "namespace"),
            uid=_safe_get(obj, "metadata", "uid"),
            creation_timestamp=_get_timestamp(_safe_get(obj, "metadata", "creation_timestamp")),
            labels=_get_labels(obj),
            annotations=_get_annotations(obj),
            pod_selector=dict(pod_selector_labels) if pod_selector_labels else None,
            policy_types=list(policy_types),
            ingress_rules_count=len(ingress_rules),
            egress_rules_count=len(egress_rules),
        )
