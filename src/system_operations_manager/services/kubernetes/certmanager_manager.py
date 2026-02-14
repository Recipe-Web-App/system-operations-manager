"""Cert-manager resource manager.

Manages Certificates, Issuers, ClusterIssuers, CertificateRequests,
Orders, and Challenges through the Kubernetes ``CustomObjectsApi``.
"""

from __future__ import annotations

from typing import Any

from system_operations_manager.integrations.kubernetes.models.certmanager import (
    CertificateRequestSummary,
    CertificateSummary,
    ChallengeSummary,
    IssuerSummary,
    OrderSummary,
)
from system_operations_manager.services.kubernetes.base import K8sBaseManager

# cert-manager.io CRD coordinates
CERT_MANAGER_GROUP = "cert-manager.io"
CERT_MANAGER_VERSION = "v1"
CERTIFICATE_PLURAL = "certificates"
ISSUER_PLURAL = "issuers"
CLUSTER_ISSUER_PLURAL = "clusterissuers"
CERTIFICATE_REQUEST_PLURAL = "certificaterequests"

# acme.cert-manager.io CRD coordinates
ACME_GROUP = "acme.cert-manager.io"
ACME_VERSION = "v1"
ORDER_PLURAL = "orders"
CHALLENGE_PLURAL = "challenges"

# Well-known Let's Encrypt servers
LETSENCRYPT_STAGING = "https://acme-staging-v02.api.letsencrypt.org/directory"
LETSENCRYPT_PRODUCTION = "https://acme-v02.api.letsencrypt.org/directory"


class CertManagerManager(K8sBaseManager):
    """Manager for cert-manager resources.

    Provides CRUD operations for Certificates, Issuers, ClusterIssuers,
    and read operations for CertificateRequests, Orders, and Challenges.
    All CRD resources are accessed via ``CustomObjectsApi``.
    """

    _entity_name = "certmanager"

    # =========================================================================
    # Certificate Operations (namespaced)
    # =========================================================================

    def list_certificates(
        self,
        namespace: str | None = None,
        *,
        label_selector: str | None = None,
    ) -> list[CertificateSummary]:
        """List Certificates in a namespace.

        Args:
            namespace: Target namespace.
            label_selector: Filter by label selector.

        Returns:
            List of certificate summaries.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("listing_certificates", namespace=ns)
        try:
            kwargs: dict[str, Any] = {}
            if label_selector:
                kwargs["label_selector"] = label_selector

            result = self._client.custom_objects.list_namespaced_custom_object(
                CERT_MANAGER_GROUP,
                CERT_MANAGER_VERSION,
                ns,
                CERTIFICATE_PLURAL,
                **kwargs,
            )
            items: list[dict[str, Any]] = result.get("items", [])
            certs = [CertificateSummary.from_k8s_object(item) for item in items]
            self._log.debug("listed_certificates", count=len(certs), namespace=ns)
            return certs
        except Exception as e:
            self._handle_api_error(e, "Certificate", None, ns)

    def get_certificate(
        self,
        name: str,
        namespace: str | None = None,
    ) -> CertificateSummary:
        """Get a single Certificate by name.

        Args:
            name: Certificate name.
            namespace: Target namespace.

        Returns:
            Certificate summary.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("getting_certificate", name=name, namespace=ns)
        try:
            result = self._client.custom_objects.get_namespaced_custom_object(
                CERT_MANAGER_GROUP,
                CERT_MANAGER_VERSION,
                ns,
                CERTIFICATE_PLURAL,
                name,
            )
            return CertificateSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "Certificate", name, ns)

    def create_certificate(
        self,
        name: str,
        namespace: str | None = None,
        *,
        secret_name: str,
        issuer_name: str,
        dns_names: list[str],
        issuer_kind: str = "Issuer",
        issuer_group: str = "cert-manager.io",
        common_name: str | None = None,
        duration: str | None = None,
        renew_before: str | None = None,
        labels: dict[str, str] | None = None,
    ) -> CertificateSummary:
        """Create a new Certificate.

        Args:
            name: Certificate name.
            namespace: Target namespace.
            secret_name: Name of the Secret to store the certificate in.
            issuer_name: Name of the Issuer or ClusterIssuer.
            dns_names: List of Subject Alternative Names.
            issuer_kind: Kind of issuer (Issuer or ClusterIssuer).
            issuer_group: API group of the issuer.
            common_name: Certificate Common Name.
            duration: Certificate validity duration (e.g. ``2160h``).
            renew_before: Renewal window before expiry (e.g. ``360h``).
            labels: Optional labels.

        Returns:
            Created certificate summary.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("creating_certificate", name=name, namespace=ns)

        spec: dict[str, Any] = {
            "secretName": secret_name,
            "issuerRef": {
                "name": issuer_name,
                "kind": issuer_kind,
                "group": issuer_group,
            },
            "dnsNames": dns_names,
        }
        if common_name:
            spec["commonName"] = common_name
        if duration:
            spec["duration"] = duration
        if renew_before:
            spec["renewBefore"] = renew_before

        body: dict[str, Any] = {
            "apiVersion": f"{CERT_MANAGER_GROUP}/{CERT_MANAGER_VERSION}",
            "kind": "Certificate",
            "metadata": {
                "name": name,
                "namespace": ns,
                "labels": labels or {},
            },
            "spec": spec,
        }
        try:
            result = self._client.custom_objects.create_namespaced_custom_object(
                CERT_MANAGER_GROUP,
                CERT_MANAGER_VERSION,
                ns,
                CERTIFICATE_PLURAL,
                body,
            )
            self._log.info("created_certificate", name=name, namespace=ns)
            return CertificateSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "Certificate", name, ns)

    def delete_certificate(
        self,
        name: str,
        namespace: str | None = None,
    ) -> None:
        """Delete a Certificate.

        Args:
            name: Certificate name to delete.
            namespace: Target namespace.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("deleting_certificate", name=name, namespace=ns)
        try:
            self._client.custom_objects.delete_namespaced_custom_object(
                CERT_MANAGER_GROUP,
                CERT_MANAGER_VERSION,
                ns,
                CERTIFICATE_PLURAL,
                name,
            )
            self._log.info("deleted_certificate", name=name, namespace=ns)
        except Exception as e:
            self._handle_api_error(e, "Certificate", name, ns)

    def get_certificate_status(
        self,
        name: str,
        namespace: str | None = None,
    ) -> dict[str, Any]:
        """Get detailed status for a Certificate.

        Args:
            name: Certificate name.
            namespace: Target namespace.

        Returns:
            Dict with conditions, expiry, and renewal information.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("getting_certificate_status", name=name, namespace=ns)
        try:
            result = self._client.custom_objects.get_namespaced_custom_object(
                CERT_MANAGER_GROUP,
                CERT_MANAGER_VERSION,
                ns,
                CERTIFICATE_PLURAL,
                name,
            )
            spec: dict[str, Any] = result.get("spec", {})
            status: dict[str, Any] = result.get("status", {})
            issuer_ref: dict[str, Any] = spec.get("issuerRef", {})

            return {
                "name": name,
                "namespace": ns,
                "secret_name": spec.get("secretName", ""),
                "issuer": f"{issuer_ref.get('kind', 'Issuer')}/{issuer_ref.get('name', '')}",
                "dns_names": spec.get("dnsNames", []),
                "not_after": status.get("notAfter"),
                "not_before": status.get("notBefore"),
                "renewal_time": status.get("renewalTime"),
                "revision": status.get("revision"),
                "conditions": status.get("conditions", []),
            }
        except Exception as e:
            self._handle_api_error(e, "Certificate", name, ns)

    def renew_certificate(
        self,
        name: str,
        namespace: str | None = None,
    ) -> dict[str, Any]:
        """Trigger renewal of a Certificate.

        Adds the ``cert-manager.io/issuing-trigger`` annotation to force
        cert-manager to re-issue the certificate.

        Args:
            name: Certificate name.
            namespace: Target namespace.

        Returns:
            Dict with operation details.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("renewing_certificate", name=name, namespace=ns)
        try:
            patch: dict[str, Any] = {
                "metadata": {
                    "annotations": {
                        "cert-manager.io/renew": "",
                    },
                },
            }
            self._client.custom_objects.patch_namespaced_custom_object(
                CERT_MANAGER_GROUP,
                CERT_MANAGER_VERSION,
                ns,
                CERTIFICATE_PLURAL,
                name,
                patch,
            )
            self._log.info("renewed_certificate", name=name, namespace=ns)
            return {"name": name, "namespace": ns, "renewed": True}
        except Exception as e:
            self._handle_api_error(e, "Certificate", name, ns)

    # =========================================================================
    # Issuer Operations (namespaced)
    # =========================================================================

    def list_issuers(
        self,
        namespace: str | None = None,
        *,
        label_selector: str | None = None,
    ) -> list[IssuerSummary]:
        """List Issuers in a namespace.

        Args:
            namespace: Target namespace.
            label_selector: Filter by label selector.

        Returns:
            List of issuer summaries.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("listing_issuers", namespace=ns)
        try:
            kwargs: dict[str, Any] = {}
            if label_selector:
                kwargs["label_selector"] = label_selector

            result = self._client.custom_objects.list_namespaced_custom_object(
                CERT_MANAGER_GROUP,
                CERT_MANAGER_VERSION,
                ns,
                ISSUER_PLURAL,
                **kwargs,
            )
            items: list[dict[str, Any]] = result.get("items", [])
            issuers = [IssuerSummary.from_k8s_object(item) for item in items]
            self._log.debug("listed_issuers", count=len(issuers), namespace=ns)
            return issuers
        except Exception as e:
            self._handle_api_error(e, "Issuer", None, ns)

    def get_issuer(
        self,
        name: str,
        namespace: str | None = None,
    ) -> IssuerSummary:
        """Get a single Issuer by name.

        Args:
            name: Issuer name.
            namespace: Target namespace.

        Returns:
            Issuer summary.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("getting_issuer", name=name, namespace=ns)
        try:
            result = self._client.custom_objects.get_namespaced_custom_object(
                CERT_MANAGER_GROUP,
                CERT_MANAGER_VERSION,
                ns,
                ISSUER_PLURAL,
                name,
            )
            return IssuerSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "Issuer", name, ns)

    def create_issuer(
        self,
        name: str,
        namespace: str | None = None,
        *,
        issuer_type: str,
        config: dict[str, Any],
        labels: dict[str, str] | None = None,
    ) -> IssuerSummary:
        """Create a new Issuer.

        Args:
            name: Issuer name.
            namespace: Target namespace.
            issuer_type: Issuer type (acme, ca, selfSigned, vault).
            config: Type-specific configuration dict.
            labels: Optional labels.

        Returns:
            Created issuer summary.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("creating_issuer", name=name, namespace=ns, issuer_type=issuer_type)
        body: dict[str, Any] = {
            "apiVersion": f"{CERT_MANAGER_GROUP}/{CERT_MANAGER_VERSION}",
            "kind": "Issuer",
            "metadata": {
                "name": name,
                "namespace": ns,
                "labels": labels or {},
            },
            "spec": {
                issuer_type: config,
            },
        }
        try:
            result = self._client.custom_objects.create_namespaced_custom_object(
                CERT_MANAGER_GROUP,
                CERT_MANAGER_VERSION,
                ns,
                ISSUER_PLURAL,
                body,
            )
            self._log.info("created_issuer", name=name, namespace=ns)
            return IssuerSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "Issuer", name, ns)

    def delete_issuer(
        self,
        name: str,
        namespace: str | None = None,
    ) -> None:
        """Delete an Issuer.

        Args:
            name: Issuer name to delete.
            namespace: Target namespace.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("deleting_issuer", name=name, namespace=ns)
        try:
            self._client.custom_objects.delete_namespaced_custom_object(
                CERT_MANAGER_GROUP,
                CERT_MANAGER_VERSION,
                ns,
                ISSUER_PLURAL,
                name,
            )
            self._log.info("deleted_issuer", name=name, namespace=ns)
        except Exception as e:
            self._handle_api_error(e, "Issuer", name, ns)

    def get_issuer_status(
        self,
        name: str,
        namespace: str | None = None,
    ) -> dict[str, Any]:
        """Get detailed status for an Issuer.

        Args:
            name: Issuer name.
            namespace: Target namespace.

        Returns:
            Dict with conditions and ACME registration details.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("getting_issuer_status", name=name, namespace=ns)
        try:
            result = self._client.custom_objects.get_namespaced_custom_object(
                CERT_MANAGER_GROUP,
                CERT_MANAGER_VERSION,
                ns,
                ISSUER_PLURAL,
                name,
            )
            status: dict[str, Any] = result.get("status", {})
            acme_status: dict[str, Any] = status.get("acme", {})

            return {
                "name": name,
                "namespace": ns,
                "conditions": status.get("conditions", []),
                "acme_uri": acme_status.get("uri"),
                "acme_last_registered_email": acme_status.get("lastRegisteredEmail"),
            }
        except Exception as e:
            self._handle_api_error(e, "Issuer", name, ns)

    # =========================================================================
    # ClusterIssuer Operations (cluster-scoped)
    # =========================================================================

    def list_cluster_issuers(
        self,
        *,
        label_selector: str | None = None,
    ) -> list[IssuerSummary]:
        """List ClusterIssuers.

        Args:
            label_selector: Filter by label selector.

        Returns:
            List of cluster issuer summaries.
        """
        self._log.debug("listing_cluster_issuers")
        try:
            kwargs: dict[str, Any] = {}
            if label_selector:
                kwargs["label_selector"] = label_selector

            result = self._client.custom_objects.list_cluster_custom_object(
                CERT_MANAGER_GROUP,
                CERT_MANAGER_VERSION,
                CLUSTER_ISSUER_PLURAL,
                **kwargs,
            )
            items: list[dict[str, Any]] = result.get("items", [])
            issuers = [
                IssuerSummary.from_k8s_object(item, is_cluster_issuer=True) for item in items
            ]
            self._log.debug("listed_cluster_issuers", count=len(issuers))
            return issuers
        except Exception as e:
            self._handle_api_error(e, "ClusterIssuer")

    def get_cluster_issuer(self, name: str) -> IssuerSummary:
        """Get a single ClusterIssuer by name.

        Args:
            name: ClusterIssuer name.

        Returns:
            Cluster issuer summary.
        """
        self._log.debug("getting_cluster_issuer", name=name)
        try:
            result = self._client.custom_objects.get_cluster_custom_object(
                CERT_MANAGER_GROUP,
                CERT_MANAGER_VERSION,
                CLUSTER_ISSUER_PLURAL,
                name,
            )
            return IssuerSummary.from_k8s_object(result, is_cluster_issuer=True)
        except Exception as e:
            self._handle_api_error(e, "ClusterIssuer", name)

    def create_cluster_issuer(
        self,
        name: str,
        *,
        issuer_type: str,
        config: dict[str, Any],
        labels: dict[str, str] | None = None,
    ) -> IssuerSummary:
        """Create a new ClusterIssuer.

        Args:
            name: ClusterIssuer name.
            issuer_type: Issuer type (acme, ca, selfSigned, vault).
            config: Type-specific configuration dict.
            labels: Optional labels.

        Returns:
            Created cluster issuer summary.
        """
        self._log.debug("creating_cluster_issuer", name=name, issuer_type=issuer_type)
        body: dict[str, Any] = {
            "apiVersion": f"{CERT_MANAGER_GROUP}/{CERT_MANAGER_VERSION}",
            "kind": "ClusterIssuer",
            "metadata": {
                "name": name,
                "labels": labels or {},
            },
            "spec": {
                issuer_type: config,
            },
        }
        try:
            result = self._client.custom_objects.create_cluster_custom_object(
                CERT_MANAGER_GROUP,
                CERT_MANAGER_VERSION,
                CLUSTER_ISSUER_PLURAL,
                body,
            )
            self._log.info("created_cluster_issuer", name=name)
            return IssuerSummary.from_k8s_object(result, is_cluster_issuer=True)
        except Exception as e:
            self._handle_api_error(e, "ClusterIssuer", name)

    def delete_cluster_issuer(self, name: str) -> None:
        """Delete a ClusterIssuer.

        Args:
            name: ClusterIssuer name to delete.
        """
        self._log.debug("deleting_cluster_issuer", name=name)
        try:
            self._client.custom_objects.delete_cluster_custom_object(
                CERT_MANAGER_GROUP,
                CERT_MANAGER_VERSION,
                CLUSTER_ISSUER_PLURAL,
                name,
            )
            self._log.info("deleted_cluster_issuer", name=name)
        except Exception as e:
            self._handle_api_error(e, "ClusterIssuer", name)

    def get_cluster_issuer_status(self, name: str) -> dict[str, Any]:
        """Get detailed status for a ClusterIssuer.

        Args:
            name: ClusterIssuer name.

        Returns:
            Dict with conditions and ACME registration details.
        """
        self._log.debug("getting_cluster_issuer_status", name=name)
        try:
            result = self._client.custom_objects.get_cluster_custom_object(
                CERT_MANAGER_GROUP,
                CERT_MANAGER_VERSION,
                CLUSTER_ISSUER_PLURAL,
                name,
            )
            status: dict[str, Any] = result.get("status", {})
            acme_status: dict[str, Any] = status.get("acme", {})

            return {
                "name": name,
                "conditions": status.get("conditions", []),
                "acme_uri": acme_status.get("uri"),
                "acme_last_registered_email": acme_status.get("lastRegisteredEmail"),
            }
        except Exception as e:
            self._handle_api_error(e, "ClusterIssuer", name)

    # =========================================================================
    # ACME Helper Methods
    # =========================================================================

    def create_acme_issuer(
        self,
        name: str,
        namespace: str | None = None,
        *,
        email: str,
        server: str = LETSENCRYPT_STAGING,
        private_key_secret: str = "",
        solver_type: str = "http01",
        ingress_class: str | None = None,
        labels: dict[str, str] | None = None,
    ) -> IssuerSummary:
        """Create an ACME Issuer (e.g. Let's Encrypt).

        Convenience method that builds the ACME configuration from
        simple parameters.

        Args:
            name: Issuer name.
            namespace: Target namespace.
            email: ACME registration email.
            server: ACME server URL (defaults to LE staging).
            private_key_secret: Name of the Secret for the ACME account key.
            solver_type: Solver type (http01 or dns01).
            ingress_class: Ingress class for HTTP-01 solver.
            labels: Optional labels.

        Returns:
            Created issuer summary.
        """
        private_key_ref = private_key_secret or f"{name}-account-key"

        solvers: list[dict[str, Any]] = []
        if solver_type == "http01":
            solver_config: dict[str, Any] = {"http01": {"ingress": {}}}
            if ingress_class:
                solver_config["http01"]["ingress"]["class"] = ingress_class
            solvers.append(solver_config)
        elif solver_type == "dns01":
            solvers.append({"dns01": {}})

        acme_config: dict[str, Any] = {
            "server": server,
            "email": email,
            "privateKeySecretRef": {"name": private_key_ref},
            "solvers": solvers,
        }

        return self.create_issuer(
            name,
            namespace=namespace,
            issuer_type="acme",
            config=acme_config,
            labels=labels,
        )

    def create_acme_cluster_issuer(
        self,
        name: str,
        *,
        email: str,
        server: str = LETSENCRYPT_STAGING,
        private_key_secret: str = "",
        solver_type: str = "http01",
        ingress_class: str | None = None,
        labels: dict[str, str] | None = None,
    ) -> IssuerSummary:
        """Create an ACME ClusterIssuer (e.g. Let's Encrypt).

        Convenience method that builds the ACME configuration from
        simple parameters.

        Args:
            name: ClusterIssuer name.
            email: ACME registration email.
            server: ACME server URL (defaults to LE staging).
            private_key_secret: Name of the Secret for the ACME account key.
            solver_type: Solver type (http01 or dns01).
            ingress_class: Ingress class for HTTP-01 solver.
            labels: Optional labels.

        Returns:
            Created cluster issuer summary.
        """
        private_key_ref = private_key_secret or f"{name}-account-key"

        solvers: list[dict[str, Any]] = []
        if solver_type == "http01":
            solver_config: dict[str, Any] = {"http01": {"ingress": {}}}
            if ingress_class:
                solver_config["http01"]["ingress"]["class"] = ingress_class
            solvers.append(solver_config)
        elif solver_type == "dns01":
            solvers.append({"dns01": {}})

        acme_config: dict[str, Any] = {
            "server": server,
            "email": email,
            "privateKeySecretRef": {"name": private_key_ref},
            "solvers": solvers,
        }

        return self.create_cluster_issuer(
            name,
            issuer_type="acme",
            config=acme_config,
            labels=labels,
        )

    # =========================================================================
    # CertificateRequest Operations (namespaced, read-only)
    # =========================================================================

    def list_certificate_requests(
        self,
        namespace: str | None = None,
        *,
        label_selector: str | None = None,
    ) -> list[CertificateRequestSummary]:
        """List CertificateRequests in a namespace.

        Args:
            namespace: Target namespace.
            label_selector: Filter by label selector.

        Returns:
            List of certificate request summaries.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("listing_certificate_requests", namespace=ns)
        try:
            kwargs: dict[str, Any] = {}
            if label_selector:
                kwargs["label_selector"] = label_selector

            result = self._client.custom_objects.list_namespaced_custom_object(
                CERT_MANAGER_GROUP,
                CERT_MANAGER_VERSION,
                ns,
                CERTIFICATE_REQUEST_PLURAL,
                **kwargs,
            )
            items: list[dict[str, Any]] = result.get("items", [])
            requests = [CertificateRequestSummary.from_k8s_object(item) for item in items]
            self._log.debug("listed_certificate_requests", count=len(requests), namespace=ns)
            return requests
        except Exception as e:
            self._handle_api_error(e, "CertificateRequest", None, ns)

    def get_certificate_request(
        self,
        name: str,
        namespace: str | None = None,
    ) -> CertificateRequestSummary:
        """Get a single CertificateRequest by name.

        Args:
            name: CertificateRequest name.
            namespace: Target namespace.

        Returns:
            Certificate request summary.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("getting_certificate_request", name=name, namespace=ns)
        try:
            result = self._client.custom_objects.get_namespaced_custom_object(
                CERT_MANAGER_GROUP,
                CERT_MANAGER_VERSION,
                ns,
                CERTIFICATE_REQUEST_PLURAL,
                name,
            )
            return CertificateRequestSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "CertificateRequest", name, ns)

    # =========================================================================
    # Order Operations (namespaced, read-only)
    # =========================================================================

    def list_orders(
        self,
        namespace: str | None = None,
        *,
        label_selector: str | None = None,
    ) -> list[OrderSummary]:
        """List ACME Orders in a namespace.

        Args:
            namespace: Target namespace.
            label_selector: Filter by label selector.

        Returns:
            List of order summaries.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("listing_orders", namespace=ns)
        try:
            kwargs: dict[str, Any] = {}
            if label_selector:
                kwargs["label_selector"] = label_selector

            result = self._client.custom_objects.list_namespaced_custom_object(
                ACME_GROUP,
                ACME_VERSION,
                ns,
                ORDER_PLURAL,
                **kwargs,
            )
            items: list[dict[str, Any]] = result.get("items", [])
            orders = [OrderSummary.from_k8s_object(item) for item in items]
            self._log.debug("listed_orders", count=len(orders), namespace=ns)
            return orders
        except Exception as e:
            self._handle_api_error(e, "Order", None, ns)

    # =========================================================================
    # Challenge Operations (namespaced, read-only + troubleshoot)
    # =========================================================================

    def list_challenges(
        self,
        namespace: str | None = None,
        *,
        label_selector: str | None = None,
    ) -> list[ChallengeSummary]:
        """List ACME Challenges in a namespace.

        Args:
            namespace: Target namespace.
            label_selector: Filter by label selector.

        Returns:
            List of challenge summaries.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("listing_challenges", namespace=ns)
        try:
            kwargs: dict[str, Any] = {}
            if label_selector:
                kwargs["label_selector"] = label_selector

            result = self._client.custom_objects.list_namespaced_custom_object(
                ACME_GROUP,
                ACME_VERSION,
                ns,
                CHALLENGE_PLURAL,
                **kwargs,
            )
            items: list[dict[str, Any]] = result.get("items", [])
            challenges = [ChallengeSummary.from_k8s_object(item) for item in items]
            self._log.debug("listed_challenges", count=len(challenges), namespace=ns)
            return challenges
        except Exception as e:
            self._handle_api_error(e, "Challenge", None, ns)

    def get_challenge(
        self,
        name: str,
        namespace: str | None = None,
    ) -> ChallengeSummary:
        """Get a single ACME Challenge by name.

        Args:
            name: Challenge name.
            namespace: Target namespace.

        Returns:
            Challenge summary.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("getting_challenge", name=name, namespace=ns)
        try:
            result = self._client.custom_objects.get_namespaced_custom_object(
                ACME_GROUP,
                ACME_VERSION,
                ns,
                CHALLENGE_PLURAL,
                name,
            )
            return ChallengeSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "Challenge", name, ns)

    def troubleshoot_challenge(
        self,
        name: str,
        namespace: str | None = None,
    ) -> dict[str, Any]:
        """Get troubleshooting information for an ACME Challenge.

        Returns detailed challenge information including the solver
        configuration, status, and any failure reasons.

        Args:
            name: Challenge name.
            namespace: Target namespace.

        Returns:
            Dict with comprehensive troubleshooting information.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("troubleshooting_challenge", name=name, namespace=ns)
        try:
            result = self._client.custom_objects.get_namespaced_custom_object(
                ACME_GROUP,
                ACME_VERSION,
                ns,
                CHALLENGE_PLURAL,
                name,
            )
            metadata: dict[str, Any] = result.get("metadata", {})
            spec: dict[str, Any] = result.get("spec", {})
            status: dict[str, Any] = result.get("status", {})
            issuer_ref: dict[str, Any] = spec.get("issuerRef", {})
            solver: dict[str, Any] = spec.get("solver", {})

            # Determine solver type
            solver_type = "unknown"
            solver_details: dict[str, Any] = {}
            if "http01" in solver:
                solver_type = "http-01"
                solver_details = solver["http01"]
            elif "dns01" in solver:
                solver_type = "dns-01"
                solver_details = solver["dns01"]

            # Find owning order
            owner_refs: list[dict[str, Any]] = metadata.get("ownerReferences", [])
            order_name = None
            for ref in owner_refs:
                if ref.get("kind") == "Order":
                    order_name = ref.get("name")
                    break

            return {
                "name": name,
                "namespace": ns,
                "dns_name": spec.get("dnsName", ""),
                "solver_type": solver_type,
                "solver_details": solver_details,
                "issuer": f"{issuer_ref.get('kind', 'Issuer')}/{issuer_ref.get('name', '')}",
                "state": status.get("state", ""),
                "presented": status.get("presented", False),
                "processing": status.get("processing", False),
                "reason": status.get("reason"),
                "token": spec.get("token", ""),
                "url": spec.get("url", ""),
                "order": order_name,
                "conditions": status.get("conditions", []),
            }
        except Exception as e:
            self._handle_api_error(e, "Challenge", name, ns)
