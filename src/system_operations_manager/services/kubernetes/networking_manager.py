"""Kubernetes networking resource manager.

Manages Services, Ingresses, and NetworkPolicies through the Kubernetes API.
"""

from __future__ import annotations

from typing import Any

from system_operations_manager.integrations.kubernetes.models.networking import (
    IngressSummary,
    NetworkPolicySummary,
    ServiceSummary,
)
from system_operations_manager.services.kubernetes.base import K8sBaseManager


class NetworkingManager(K8sBaseManager):
    """Manager for Kubernetes networking resources.

    Provides CRUD operations for Services, Ingresses, and NetworkPolicies.
    """

    _entity_name = "networking"

    # =========================================================================
    # Service Operations
    # =========================================================================

    def list_services(
        self,
        namespace: str | None = None,
        *,
        all_namespaces: bool = False,
        label_selector: str | None = None,
    ) -> list[ServiceSummary]:
        """List services.

        Args:
            namespace: Target namespace.
            all_namespaces: List across all namespaces.
            label_selector: Filter by label selector.

        Returns:
            List of service summaries.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("listing_services", namespace=ns, all_namespaces=all_namespaces)
        try:
            kwargs: dict[str, Any] = {}
            if label_selector:
                kwargs["label_selector"] = label_selector

            if all_namespaces:
                result = self._client.core_v1.list_service_for_all_namespaces(**kwargs)
            else:
                result = self._client.core_v1.list_namespaced_service(namespace=ns, **kwargs)

            services = [ServiceSummary.from_k8s_object(svc) for svc in result.items]
            self._log.debug("listed_services", count=len(services))
            return services
        except Exception as e:
            self._handle_api_error(e, "Service", None, ns)

    def get_service(self, name: str, namespace: str | None = None) -> ServiceSummary:
        """Get a single service by name.

        Args:
            name: Service name.
            namespace: Target namespace.

        Returns:
            Service summary.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("getting_service", name=name, namespace=ns)
        try:
            result = self._client.core_v1.read_namespaced_service(name=name, namespace=ns)
            return ServiceSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "Service", name, ns)

    def create_service(
        self,
        name: str,
        namespace: str | None = None,
        *,
        type: str = "ClusterIP",
        selector: dict[str, str] | None = None,
        ports: list[dict[str, Any]] | None = None,
        labels: dict[str, str] | None = None,
    ) -> ServiceSummary:
        """Create a service.

        Args:
            name: Service name.
            namespace: Target namespace.
            type: Service type (ClusterIP, NodePort, LoadBalancer, ExternalName).
            selector: Pod selector labels.
            ports: List of port definitions (each with 'port', 'target_port', 'protocol').
            labels: Service labels.

        Returns:
            Created service summary.
        """
        from kubernetes.client import (
            V1ObjectMeta,
            V1Service,
            V1ServicePort,
            V1ServiceSpec,
        )

        ns = self._resolve_namespace(namespace)

        svc_ports = []
        for p in ports or []:
            svc_ports.append(
                V1ServicePort(
                    port=p["port"],
                    target_port=p.get("target_port"),
                    protocol=p.get("protocol", "TCP"),
                    name=p.get("name"),
                )
            )

        body = V1Service(
            metadata=V1ObjectMeta(name=name, namespace=ns, labels=labels),
            spec=V1ServiceSpec(
                type=type,
                selector=selector,
                ports=svc_ports or None,
            ),
        )

        self._log.info("creating_service", name=name, namespace=ns, type=type)
        try:
            result = self._client.core_v1.create_namespaced_service(namespace=ns, body=body)
            self._log.info("created_service", name=name, namespace=ns)
            return ServiceSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "Service", name, ns)

    def update_service(
        self,
        name: str,
        namespace: str | None = None,
        *,
        type: str | None = None,
        selector: dict[str, str] | None = None,
        ports: list[dict[str, Any]] | None = None,
    ) -> ServiceSummary:
        """Update a service (patch).

        Args:
            name: Service name.
            namespace: Target namespace.
            type: New service type.
            selector: New pod selector.
            ports: New port definitions.

        Returns:
            Updated service summary.
        """
        ns = self._resolve_namespace(namespace)
        self._log.info("updating_service", name=name, namespace=ns)
        try:
            patch: dict[str, Any] = {"spec": {}}
            if type is not None:
                patch["spec"]["type"] = type
            if selector is not None:
                patch["spec"]["selector"] = selector
            if ports is not None:
                patch["spec"]["ports"] = [
                    {
                        "port": p["port"],
                        "targetPort": p.get("target_port"),
                        "protocol": p.get("protocol", "TCP"),
                        "name": p.get("name"),
                    }
                    for p in ports
                ]

            result = self._client.core_v1.patch_namespaced_service(
                name=name, namespace=ns, body=patch
            )
            self._log.info("updated_service", name=name, namespace=ns)
            return ServiceSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "Service", name, ns)

    def delete_service(self, name: str, namespace: str | None = None) -> None:
        """Delete a service.

        Args:
            name: Service name.
            namespace: Target namespace.
        """
        ns = self._resolve_namespace(namespace)
        self._log.info("deleting_service", name=name, namespace=ns)
        try:
            self._client.core_v1.delete_namespaced_service(name=name, namespace=ns)
            self._log.info("deleted_service", name=name, namespace=ns)
        except Exception as e:
            self._handle_api_error(e, "Service", name, ns)

    # =========================================================================
    # Ingress Operations
    # =========================================================================

    def list_ingresses(
        self,
        namespace: str | None = None,
        *,
        all_namespaces: bool = False,
        label_selector: str | None = None,
    ) -> list[IngressSummary]:
        """List ingresses.

        Args:
            namespace: Target namespace.
            all_namespaces: List across all namespaces.
            label_selector: Filter by label selector.

        Returns:
            List of ingress summaries.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("listing_ingresses", namespace=ns, all_namespaces=all_namespaces)
        try:
            kwargs: dict[str, Any] = {}
            if label_selector:
                kwargs["label_selector"] = label_selector

            if all_namespaces:
                result = self._client.networking_v1.list_ingress_for_all_namespaces(**kwargs)
            else:
                result = self._client.networking_v1.list_namespaced_ingress(namespace=ns, **kwargs)

            items = [IngressSummary.from_k8s_object(ing) for ing in result.items]
            self._log.debug("listed_ingresses", count=len(items))
            return items
        except Exception as e:
            self._handle_api_error(e, "Ingress", None, ns)

    def get_ingress(self, name: str, namespace: str | None = None) -> IngressSummary:
        """Get a single ingress by name.

        Args:
            name: Ingress name.
            namespace: Target namespace.

        Returns:
            Ingress summary.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("getting_ingress", name=name, namespace=ns)
        try:
            result = self._client.networking_v1.read_namespaced_ingress(name=name, namespace=ns)
            return IngressSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "Ingress", name, ns)

    def create_ingress(
        self,
        name: str,
        namespace: str | None = None,
        *,
        class_name: str | None = None,
        rules: list[dict[str, Any]] | None = None,
        tls: list[dict[str, Any]] | None = None,
        labels: dict[str, str] | None = None,
    ) -> IngressSummary:
        """Create an ingress.

        Args:
            name: Ingress name.
            namespace: Target namespace.
            class_name: Ingress class name (e.g., 'nginx').
            rules: List of ingress rules, each with 'host' and 'paths'.
                Each path has 'path', 'path_type', 'service_name', 'service_port'.
            tls: List of TLS configs, each with 'hosts' and 'secret_name'.
            labels: Ingress labels.

        Returns:
            Created ingress summary.
        """
        from kubernetes.client import (
            V1HTTPIngressPath,
            V1HTTPIngressRuleValue,
            V1Ingress,
            V1IngressBackend,
            V1IngressRule,
            V1IngressServiceBackend,
            V1IngressSpec,
            V1IngressTLS,
            V1ObjectMeta,
            V1ServiceBackendPort,
        )

        ns = self._resolve_namespace(namespace)

        ingress_rules = []
        for rule in rules or []:
            paths = []
            for p in rule.get("paths", []):
                paths.append(
                    V1HTTPIngressPath(
                        path=p.get("path", "/"),
                        path_type=p.get("path_type", "Prefix"),
                        backend=V1IngressBackend(
                            service=V1IngressServiceBackend(
                                name=p["service_name"],
                                port=V1ServiceBackendPort(
                                    number=p.get("service_port"),
                                ),
                            )
                        ),
                    )
                )
            ingress_rules.append(
                V1IngressRule(
                    host=rule.get("host"),
                    http=V1HTTPIngressRuleValue(paths=paths) if paths else None,
                )
            )

        ingress_tls = None
        if tls:
            ingress_tls = [
                V1IngressTLS(
                    hosts=t.get("hosts", []),
                    secret_name=t.get("secret_name"),
                )
                for t in tls
            ]

        body = V1Ingress(
            metadata=V1ObjectMeta(name=name, namespace=ns, labels=labels),
            spec=V1IngressSpec(
                ingress_class_name=class_name,
                rules=ingress_rules or None,
                tls=ingress_tls,
            ),
        )

        self._log.info("creating_ingress", name=name, namespace=ns)
        try:
            result = self._client.networking_v1.create_namespaced_ingress(namespace=ns, body=body)
            self._log.info("created_ingress", name=name, namespace=ns)
            return IngressSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "Ingress", name, ns)

    def update_ingress(
        self,
        name: str,
        namespace: str | None = None,
        *,
        class_name: str | None = None,
        rules: list[dict[str, Any]] | None = None,
        tls: list[dict[str, Any]] | None = None,
    ) -> IngressSummary:
        """Update an ingress (patch).

        Args:
            name: Ingress name.
            namespace: Target namespace.
            class_name: New ingress class name.
            rules: New ingress rules.
            tls: New TLS configuration.

        Returns:
            Updated ingress summary.
        """
        ns = self._resolve_namespace(namespace)
        self._log.info("updating_ingress", name=name, namespace=ns)
        try:
            patch: dict[str, Any] = {"spec": {}}
            if class_name is not None:
                patch["spec"]["ingressClassName"] = class_name
            if rules is not None:
                patch["spec"]["rules"] = [
                    {
                        "host": r.get("host"),
                        "http": {
                            "paths": [
                                {
                                    "path": p.get("path", "/"),
                                    "pathType": p.get("path_type", "Prefix"),
                                    "backend": {
                                        "service": {
                                            "name": p["service_name"],
                                            "port": {"number": p.get("service_port")},
                                        }
                                    },
                                }
                                for p in r.get("paths", [])
                            ]
                        },
                    }
                    for r in rules
                ]
            if tls is not None:
                patch["spec"]["tls"] = [
                    {"hosts": t.get("hosts", []), "secretName": t.get("secret_name")} for t in tls
                ]

            result = self._client.networking_v1.patch_namespaced_ingress(
                name=name, namespace=ns, body=patch
            )
            self._log.info("updated_ingress", name=name, namespace=ns)
            return IngressSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "Ingress", name, ns)

    def delete_ingress(self, name: str, namespace: str | None = None) -> None:
        """Delete an ingress.

        Args:
            name: Ingress name.
            namespace: Target namespace.
        """
        ns = self._resolve_namespace(namespace)
        self._log.info("deleting_ingress", name=name, namespace=ns)
        try:
            self._client.networking_v1.delete_namespaced_ingress(name=name, namespace=ns)
            self._log.info("deleted_ingress", name=name, namespace=ns)
        except Exception as e:
            self._handle_api_error(e, "Ingress", name, ns)

    # =========================================================================
    # NetworkPolicy Operations
    # =========================================================================

    def list_network_policies(
        self,
        namespace: str | None = None,
        *,
        all_namespaces: bool = False,
        label_selector: str | None = None,
    ) -> list[NetworkPolicySummary]:
        """List network policies.

        Args:
            namespace: Target namespace.
            all_namespaces: List across all namespaces.
            label_selector: Filter by label selector.

        Returns:
            List of network policy summaries.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("listing_network_policies", namespace=ns)
        try:
            kwargs: dict[str, Any] = {}
            if label_selector:
                kwargs["label_selector"] = label_selector

            if all_namespaces:
                result = self._client.networking_v1.list_network_policy_for_all_namespaces(**kwargs)
            else:
                result = self._client.networking_v1.list_namespaced_network_policy(
                    namespace=ns, **kwargs
                )

            items = [NetworkPolicySummary.from_k8s_object(np) for np in result.items]
            self._log.debug("listed_network_policies", count=len(items))
            return items
        except Exception as e:
            self._handle_api_error(e, "NetworkPolicy", None, ns)

    def get_network_policy(self, name: str, namespace: str | None = None) -> NetworkPolicySummary:
        """Get a single network policy by name.

        Args:
            name: NetworkPolicy name.
            namespace: Target namespace.

        Returns:
            NetworkPolicy summary.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("getting_network_policy", name=name, namespace=ns)
        try:
            result = self._client.networking_v1.read_namespaced_network_policy(
                name=name, namespace=ns
            )
            return NetworkPolicySummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "NetworkPolicy", name, ns)

    def create_network_policy(
        self,
        name: str,
        namespace: str | None = None,
        *,
        pod_selector: dict[str, str] | None = None,
        policy_types: list[str] | None = None,
        ingress_rules: list[dict[str, Any]] | None = None,
        egress_rules: list[dict[str, Any]] | None = None,
        labels: dict[str, str] | None = None,
    ) -> NetworkPolicySummary:
        """Create a network policy.

        Args:
            name: NetworkPolicy name.
            namespace: Target namespace.
            pod_selector: Pod selector match labels.
            policy_types: Policy types (Ingress, Egress).
            ingress_rules: Ingress rule definitions.
            egress_rules: Egress rule definitions.
            labels: NetworkPolicy labels.

        Returns:
            Created network policy summary.
        """
        from kubernetes.client import (
            V1LabelSelector,
            V1NetworkPolicy,
            V1NetworkPolicySpec,
            V1ObjectMeta,
        )

        ns = self._resolve_namespace(namespace)

        body = V1NetworkPolicy(
            metadata=V1ObjectMeta(name=name, namespace=ns, labels=labels),
            spec=V1NetworkPolicySpec(
                pod_selector=V1LabelSelector(match_labels=pod_selector or {}),
                policy_types=policy_types,
                ingress=ingress_rules,
                egress=egress_rules,
            ),
        )

        self._log.info("creating_network_policy", name=name, namespace=ns)
        try:
            result = self._client.networking_v1.create_namespaced_network_policy(
                namespace=ns, body=body
            )
            self._log.info("created_network_policy", name=name, namespace=ns)
            return NetworkPolicySummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "NetworkPolicy", name, ns)

    def delete_network_policy(self, name: str, namespace: str | None = None) -> None:
        """Delete a network policy.

        Args:
            name: NetworkPolicy name.
            namespace: Target namespace.
        """
        ns = self._resolve_namespace(namespace)
        self._log.info("deleting_network_policy", name=name, namespace=ns)
        try:
            self._client.networking_v1.delete_namespaced_network_policy(name=name, namespace=ns)
            self._log.info("deleted_network_policy", name=name, namespace=ns)
        except Exception as e:
            self._handle_api_error(e, "NetworkPolicy", name, ns)

    def update_network_policy(
        self,
        name: str,
        namespace: str | None = None,
        *,
        pod_selector: dict[str, str] | None = None,
        policy_types: list[str] | None = None,
        ingress_rules: list[dict[str, Any]] | None = None,
        egress_rules: list[dict[str, Any]] | None = None,
    ) -> NetworkPolicySummary:
        """Update a network policy (patch).

        Args:
            name: NetworkPolicy name.
            namespace: Target namespace.
            pod_selector: Pod selector match labels.
            policy_types: Policy types (Ingress, Egress).
            ingress_rules: Ingress rule definitions.
            egress_rules: Egress rule definitions.

        Returns:
            Updated network policy summary.
        """
        ns = self._resolve_namespace(namespace)
        self._log.info("updating_network_policy", name=name, namespace=ns)
        try:
            patch: dict[str, Any] = {"spec": {}}
            if pod_selector is not None:
                patch["spec"]["podSelector"] = {"matchLabels": pod_selector}
            if policy_types is not None:
                patch["spec"]["policyTypes"] = policy_types
            if ingress_rules is not None:
                patch["spec"]["ingress"] = ingress_rules
            if egress_rules is not None:
                patch["spec"]["egress"] = egress_rules

            result = self._client.networking_v1.patch_namespaced_network_policy(
                name=name, namespace=ns, body=patch
            )
            self._log.info("updated_network_policy", name=name, namespace=ns)
            return NetworkPolicySummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "NetworkPolicy", name, ns)
