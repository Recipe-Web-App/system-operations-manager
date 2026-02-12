"""Kyverno policy resource manager.

Manages Kyverno ClusterPolicies, Policies, PolicyReports, and
ClusterPolicyReports through the Kubernetes ``CustomObjectsApi``.
"""

from __future__ import annotations

from typing import Any

from system_operations_manager.integrations.kubernetes.models.kyverno import (
    KyvernoPolicySummary,
    PolicyReportSummary,
)
from system_operations_manager.services.kubernetes.base import K8sBaseManager

# Kyverno CRD coordinates
KYVERNO_GROUP = "kyverno.io"
KYVERNO_VERSION = "v1"
CLUSTER_POLICY_PLURAL = "clusterpolicies"
POLICY_PLURAL = "policies"

# Policy Report CRD coordinates (wg-policy-prototypes)
POLICY_REPORT_GROUP = "wgpolicyk8s.io"
POLICY_REPORT_VERSION = "v1alpha2"
CLUSTER_POLICY_REPORT_PLURAL = "clusterpolicyreports"
POLICY_REPORT_PLURAL = "policyreports"


class KyvernoManager(K8sBaseManager):
    """Manager for Kyverno policy resources.

    Provides operations for Kyverno ClusterPolicies, Policies,
    ClusterPolicyReports, PolicyReports, and admission controller status.
    All CRD resources are accessed via ``CustomObjectsApi``.
    """

    _entity_name = "kyverno"

    # =========================================================================
    # ClusterPolicy Operations
    # =========================================================================

    def list_cluster_policies(
        self,
        *,
        label_selector: str | None = None,
    ) -> list[KyvernoPolicySummary]:
        """List Kyverno ClusterPolicies.

        Args:
            label_selector: Filter by label selector.

        Returns:
            List of cluster policy summaries.
        """
        self._log.debug("listing_cluster_policies")
        try:
            kwargs: dict[str, Any] = {}
            if label_selector:
                kwargs["label_selector"] = label_selector

            result = self._client.custom_objects.list_cluster_custom_object(
                KYVERNO_GROUP,
                KYVERNO_VERSION,
                CLUSTER_POLICY_PLURAL,
                **kwargs,
            )
            items: list[dict[str, Any]] = result.get("items", [])
            policies = [
                KyvernoPolicySummary.from_k8s_object(item, is_cluster_policy=True) for item in items
            ]
            self._log.debug("listed_cluster_policies", count=len(policies))
            return policies
        except Exception as e:
            self._handle_api_error(e, "ClusterPolicy")

    def get_cluster_policy(self, name: str) -> KyvernoPolicySummary:
        """Get a single ClusterPolicy by name.

        Args:
            name: ClusterPolicy name.

        Returns:
            Cluster policy summary.
        """
        self._log.debug("getting_cluster_policy", name=name)
        try:
            result = self._client.custom_objects.get_cluster_custom_object(
                KYVERNO_GROUP,
                KYVERNO_VERSION,
                CLUSTER_POLICY_PLURAL,
                name,
            )
            return KyvernoPolicySummary.from_k8s_object(result, is_cluster_policy=True)
        except Exception as e:
            self._handle_api_error(e, "ClusterPolicy", name)

    def create_cluster_policy(
        self,
        name: str,
        *,
        rules: list[dict[str, Any]] | None = None,
        background: bool = True,
        validation_failure_action: str = "Audit",
        labels: dict[str, str] | None = None,
    ) -> KyvernoPolicySummary:
        """Create a new ClusterPolicy.

        Args:
            name: Policy name.
            rules: List of Kyverno rule dicts.
            background: Enable background scanning.
            validation_failure_action: Action on failure (Audit or Enforce).
            labels: Optional labels.

        Returns:
            Created cluster policy summary.
        """
        self._log.debug("creating_cluster_policy", name=name)
        body: dict[str, Any] = {
            "apiVersion": f"{KYVERNO_GROUP}/{KYVERNO_VERSION}",
            "kind": "ClusterPolicy",
            "metadata": {
                "name": name,
                "labels": labels or {},
            },
            "spec": {
                "background": background,
                "validationFailureAction": validation_failure_action,
                "rules": rules or [],
            },
        }
        try:
            result = self._client.custom_objects.create_cluster_custom_object(
                KYVERNO_GROUP,
                KYVERNO_VERSION,
                CLUSTER_POLICY_PLURAL,
                body,
            )
            self._log.info("created_cluster_policy", name=name)
            return KyvernoPolicySummary.from_k8s_object(result, is_cluster_policy=True)
        except Exception as e:
            self._handle_api_error(e, "ClusterPolicy", name)

    def delete_cluster_policy(self, name: str) -> None:
        """Delete a ClusterPolicy.

        Args:
            name: ClusterPolicy name to delete.
        """
        self._log.debug("deleting_cluster_policy", name=name)
        try:
            self._client.custom_objects.delete_cluster_custom_object(
                KYVERNO_GROUP,
                KYVERNO_VERSION,
                CLUSTER_POLICY_PLURAL,
                name,
            )
            self._log.info("deleted_cluster_policy", name=name)
        except Exception as e:
            self._handle_api_error(e, "ClusterPolicy", name)

    # =========================================================================
    # Namespaced Policy Operations
    # =========================================================================

    def list_policies(
        self,
        namespace: str | None = None,
        *,
        label_selector: str | None = None,
    ) -> list[KyvernoPolicySummary]:
        """List Kyverno Policies in a namespace.

        Args:
            namespace: Target namespace.
            label_selector: Filter by label selector.

        Returns:
            List of policy summaries.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("listing_policies", namespace=ns)
        try:
            kwargs: dict[str, Any] = {}
            if label_selector:
                kwargs["label_selector"] = label_selector

            result = self._client.custom_objects.list_namespaced_custom_object(
                KYVERNO_GROUP,
                KYVERNO_VERSION,
                ns,
                POLICY_PLURAL,
                **kwargs,
            )
            items: list[dict[str, Any]] = result.get("items", [])
            policies = [KyvernoPolicySummary.from_k8s_object(item) for item in items]
            self._log.debug("listed_policies", count=len(policies), namespace=ns)
            return policies
        except Exception as e:
            self._handle_api_error(e, "Policy", None, ns)

    def get_policy(self, name: str, namespace: str | None = None) -> KyvernoPolicySummary:
        """Get a single namespaced Policy by name.

        Args:
            name: Policy name.
            namespace: Target namespace.

        Returns:
            Policy summary.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("getting_policy", name=name, namespace=ns)
        try:
            result = self._client.custom_objects.get_namespaced_custom_object(
                KYVERNO_GROUP,
                KYVERNO_VERSION,
                ns,
                POLICY_PLURAL,
                name,
            )
            return KyvernoPolicySummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "Policy", name, ns)

    def create_policy(
        self,
        name: str,
        namespace: str | None = None,
        *,
        rules: list[dict[str, Any]] | None = None,
        background: bool = True,
        validation_failure_action: str = "Audit",
        labels: dict[str, str] | None = None,
    ) -> KyvernoPolicySummary:
        """Create a new namespaced Policy.

        Args:
            name: Policy name.
            namespace: Target namespace.
            rules: List of Kyverno rule dicts.
            background: Enable background scanning.
            validation_failure_action: Action on failure (Audit or Enforce).
            labels: Optional labels.

        Returns:
            Created policy summary.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("creating_policy", name=name, namespace=ns)
        body: dict[str, Any] = {
            "apiVersion": f"{KYVERNO_GROUP}/{KYVERNO_VERSION}",
            "kind": "Policy",
            "metadata": {
                "name": name,
                "namespace": ns,
                "labels": labels or {},
            },
            "spec": {
                "background": background,
                "validationFailureAction": validation_failure_action,
                "rules": rules or [],
            },
        }
        try:
            result = self._client.custom_objects.create_namespaced_custom_object(
                KYVERNO_GROUP,
                KYVERNO_VERSION,
                ns,
                POLICY_PLURAL,
                body,
            )
            self._log.info("created_policy", name=name, namespace=ns)
            return KyvernoPolicySummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "Policy", name, ns)

    def delete_policy(self, name: str, namespace: str | None = None) -> None:
        """Delete a namespaced Policy.

        Args:
            name: Policy name to delete.
            namespace: Target namespace.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("deleting_policy", name=name, namespace=ns)
        try:
            self._client.custom_objects.delete_namespaced_custom_object(
                KYVERNO_GROUP,
                KYVERNO_VERSION,
                ns,
                POLICY_PLURAL,
                name,
            )
            self._log.info("deleted_policy", name=name, namespace=ns)
        except Exception as e:
            self._handle_api_error(e, "Policy", name, ns)

    # =========================================================================
    # ClusterPolicyReport Operations (read-only)
    # =========================================================================

    def list_cluster_policy_reports(self) -> list[PolicyReportSummary]:
        """List ClusterPolicyReports.

        Returns:
            List of cluster policy report summaries.
        """
        self._log.debug("listing_cluster_policy_reports")
        try:
            result = self._client.custom_objects.list_cluster_custom_object(
                POLICY_REPORT_GROUP,
                POLICY_REPORT_VERSION,
                CLUSTER_POLICY_REPORT_PLURAL,
            )
            items: list[dict[str, Any]] = result.get("items", [])
            reports = [
                PolicyReportSummary.from_k8s_object(item, is_cluster_report=True) for item in items
            ]
            self._log.debug("listed_cluster_policy_reports", count=len(reports))
            return reports
        except Exception as e:
            self._handle_api_error(e, "ClusterPolicyReport")

    def get_cluster_policy_report(self, name: str) -> PolicyReportSummary:
        """Get a single ClusterPolicyReport by name.

        Args:
            name: ClusterPolicyReport name.

        Returns:
            Cluster policy report summary.
        """
        self._log.debug("getting_cluster_policy_report", name=name)
        try:
            result = self._client.custom_objects.get_cluster_custom_object(
                POLICY_REPORT_GROUP,
                POLICY_REPORT_VERSION,
                CLUSTER_POLICY_REPORT_PLURAL,
                name,
            )
            return PolicyReportSummary.from_k8s_object(result, is_cluster_report=True)
        except Exception as e:
            self._handle_api_error(e, "ClusterPolicyReport", name)

    # =========================================================================
    # Namespaced PolicyReport Operations (read-only)
    # =========================================================================

    def list_policy_reports(
        self,
        namespace: str | None = None,
    ) -> list[PolicyReportSummary]:
        """List PolicyReports in a namespace.

        Args:
            namespace: Target namespace.

        Returns:
            List of policy report summaries.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("listing_policy_reports", namespace=ns)
        try:
            result = self._client.custom_objects.list_namespaced_custom_object(
                POLICY_REPORT_GROUP,
                POLICY_REPORT_VERSION,
                ns,
                POLICY_REPORT_PLURAL,
            )
            items: list[dict[str, Any]] = result.get("items", [])
            reports = [PolicyReportSummary.from_k8s_object(item) for item in items]
            self._log.debug("listed_policy_reports", count=len(reports), namespace=ns)
            return reports
        except Exception as e:
            self._handle_api_error(e, "PolicyReport", None, ns)

    def get_policy_report(
        self,
        name: str,
        namespace: str | None = None,
    ) -> PolicyReportSummary:
        """Get a single namespaced PolicyReport by name.

        Args:
            name: PolicyReport name.
            namespace: Target namespace.

        Returns:
            Policy report summary.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("getting_policy_report", name=name, namespace=ns)
        try:
            result = self._client.custom_objects.get_namespaced_custom_object(
                POLICY_REPORT_GROUP,
                POLICY_REPORT_VERSION,
                ns,
                POLICY_REPORT_PLURAL,
                name,
            )
            return PolicyReportSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "PolicyReport", name, ns)

    # =========================================================================
    # Admission Controller Status
    # =========================================================================

    def get_admission_status(self) -> dict[str, Any]:
        """Check Kyverno admission controller status.

        Looks for Kyverno pods in the ``kyverno`` namespace to determine
        whether the admission controller is running.

        Returns:
            Dict with ``running`` (bool), ``pods`` (list), and optionally
            ``version`` (str) keys.
        """
        self._log.debug("checking_admission_status")
        try:
            result = self._client.core_v1.list_namespaced_pod(
                namespace="kyverno",
                label_selector="app.kubernetes.io/component=admission-controller",
            )
            pods = []
            version = None
            for pod in result.items or []:
                pod_name = pod.metadata.name if pod.metadata else "unknown"
                pod_status = pod.status.phase if pod.status else "Unknown"
                pods.append({"name": pod_name, "status": pod_status})

                if version is None and pod.spec and pod.spec.containers:
                    image = pod.spec.containers[0].image or ""
                    if ":" in image:
                        version = image.rsplit(":", 1)[1]

            status: dict[str, Any] = {
                "running": len(pods) > 0 and all(p["status"] == "Running" for p in pods),
                "pods": pods,
            }
            if version:
                status["version"] = version

            self._log.debug("admission_status", running=status["running"], pod_count=len(pods))
            return status
        except Exception:
            return {"running": False, "pods": [], "error": "Could not reach kyverno namespace"}

    # =========================================================================
    # Policy Validation (dry-run)
    # =========================================================================

    def validate_policy(self, policy_dict: dict[str, Any]) -> dict[str, Any]:
        """Validate a Kyverno policy via dry-run create.

        Args:
            policy_dict: Full policy manifest as a dict.

        Returns:
            Dict with ``valid`` (bool) and either ``policy`` (KyvernoPolicySummary)
            on success or ``error`` (str) on failure.
        """
        kind = policy_dict.get("kind", "ClusterPolicy")
        is_cluster = kind == "ClusterPolicy"
        name = policy_dict.get("metadata", {}).get("name", "unknown")
        self._log.debug("validating_policy", name=name, kind=kind)

        try:
            if is_cluster:
                result = self._client.custom_objects.create_cluster_custom_object(
                    KYVERNO_GROUP,
                    KYVERNO_VERSION,
                    CLUSTER_POLICY_PLURAL,
                    policy_dict,
                    dry_run="All",
                )
            else:
                ns = policy_dict.get("metadata", {}).get("namespace") or self._resolve_namespace(
                    None
                )
                result = self._client.custom_objects.create_namespaced_custom_object(
                    KYVERNO_GROUP,
                    KYVERNO_VERSION,
                    ns,
                    POLICY_PLURAL,
                    policy_dict,
                    dry_run="All",
                )
            policy = KyvernoPolicySummary.from_k8s_object(result, is_cluster_policy=is_cluster)
            self._log.info("policy_valid", name=name)
            return {"valid": True, "policy": policy}
        except Exception as e:
            self._log.warning("policy_invalid", name=name, error=str(e))
            return {"valid": False, "error": str(e)}
