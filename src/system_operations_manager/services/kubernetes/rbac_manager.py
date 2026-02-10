"""Kubernetes RBAC resource manager.

Manages ServiceAccounts, Roles, ClusterRoles, RoleBindings,
and ClusterRoleBindings through the Kubernetes API.
"""

from __future__ import annotations

from typing import Any

from system_operations_manager.integrations.kubernetes.models.rbac import (
    RoleBindingSummary,
    RoleSummary,
    ServiceAccountSummary,
)
from system_operations_manager.services.kubernetes.base import K8sBaseManager


class RBACManager(K8sBaseManager):
    """Manager for Kubernetes RBAC resources.

    Provides CRUD operations for ServiceAccounts, Roles, ClusterRoles,
    RoleBindings, and ClusterRoleBindings.
    """

    _entity_name = "rbac"

    # =========================================================================
    # ServiceAccount Operations
    # =========================================================================

    def list_service_accounts(
        self,
        namespace: str | None = None,
        *,
        all_namespaces: bool = False,
        label_selector: str | None = None,
    ) -> list[ServiceAccountSummary]:
        """List service accounts.

        Args:
            namespace: Target namespace.
            all_namespaces: List across all namespaces.
            label_selector: Filter by label selector.

        Returns:
            List of service account summaries.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("listing_service_accounts", namespace=ns)
        try:
            kwargs: dict[str, Any] = {}
            if label_selector:
                kwargs["label_selector"] = label_selector

            if all_namespaces:
                result = self._client.core_v1.list_service_account_for_all_namespaces(**kwargs)
            else:
                result = self._client.core_v1.list_namespaced_service_account(
                    namespace=ns, **kwargs
                )

            items = [ServiceAccountSummary.from_k8s_object(sa) for sa in result.items]
            self._log.debug("listed_service_accounts", count=len(items))
            return items
        except Exception as e:
            self._handle_api_error(e, "ServiceAccount", None, ns)

    def get_service_account(self, name: str, namespace: str | None = None) -> ServiceAccountSummary:
        """Get a single service account by name.

        Args:
            name: ServiceAccount name.
            namespace: Target namespace.

        Returns:
            ServiceAccount summary.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("getting_service_account", name=name, namespace=ns)
        try:
            result = self._client.core_v1.read_namespaced_service_account(name=name, namespace=ns)
            return ServiceAccountSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "ServiceAccount", name, ns)

    def create_service_account(
        self,
        name: str,
        namespace: str | None = None,
        *,
        labels: dict[str, str] | None = None,
    ) -> ServiceAccountSummary:
        """Create a service account.

        Args:
            name: ServiceAccount name.
            namespace: Target namespace.
            labels: ServiceAccount labels.

        Returns:
            Created service account summary.
        """
        from kubernetes.client import V1ObjectMeta, V1ServiceAccount

        ns = self._resolve_namespace(namespace)

        body = V1ServiceAccount(
            metadata=V1ObjectMeta(name=name, namespace=ns, labels=labels),
        )

        self._log.info("creating_service_account", name=name, namespace=ns)
        try:
            result = self._client.core_v1.create_namespaced_service_account(namespace=ns, body=body)
            self._log.info("created_service_account", name=name, namespace=ns)
            return ServiceAccountSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "ServiceAccount", name, ns)

    def delete_service_account(self, name: str, namespace: str | None = None) -> None:
        """Delete a service account.

        Args:
            name: ServiceAccount name.
            namespace: Target namespace.
        """
        ns = self._resolve_namespace(namespace)
        self._log.info("deleting_service_account", name=name, namespace=ns)
        try:
            self._client.core_v1.delete_namespaced_service_account(name=name, namespace=ns)
            self._log.info("deleted_service_account", name=name, namespace=ns)
        except Exception as e:
            self._handle_api_error(e, "ServiceAccount", name, ns)

    # =========================================================================
    # Role Operations (Namespaced)
    # =========================================================================

    def list_roles(
        self,
        namespace: str | None = None,
        *,
        label_selector: str | None = None,
    ) -> list[RoleSummary]:
        """List roles in a namespace.

        Args:
            namespace: Target namespace.
            label_selector: Filter by label selector.

        Returns:
            List of role summaries.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("listing_roles", namespace=ns)
        try:
            kwargs: dict[str, Any] = {}
            if label_selector:
                kwargs["label_selector"] = label_selector

            result = self._client.rbac_v1.list_namespaced_role(namespace=ns, **kwargs)
            items = [RoleSummary.from_k8s_object(r) for r in result.items]
            self._log.debug("listed_roles", count=len(items))
            return items
        except Exception as e:
            self._handle_api_error(e, "Role", None, ns)

    def get_role(self, name: str, namespace: str | None = None) -> RoleSummary:
        """Get a single role by name.

        Args:
            name: Role name.
            namespace: Target namespace.

        Returns:
            Role summary.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("getting_role", name=name, namespace=ns)
        try:
            result = self._client.rbac_v1.read_namespaced_role(name=name, namespace=ns)
            return RoleSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "Role", name, ns)

    def create_role(
        self,
        name: str,
        namespace: str | None = None,
        *,
        rules: list[dict[str, Any]] | None = None,
        labels: dict[str, str] | None = None,
    ) -> RoleSummary:
        """Create a role.

        Args:
            name: Role name.
            namespace: Target namespace.
            rules: List of policy rules, each with 'verbs', 'api_groups', 'resources'.
            labels: Role labels.

        Returns:
            Created role summary.
        """
        from kubernetes.client import V1ObjectMeta, V1PolicyRule, V1Role

        ns = self._resolve_namespace(namespace)

        policy_rules = [
            V1PolicyRule(
                verbs=r.get("verbs", []),
                api_groups=r.get("api_groups", [""]),
                resources=r.get("resources", []),
                resource_names=r.get("resource_names"),
            )
            for r in (rules or [])
        ]

        body = V1Role(
            metadata=V1ObjectMeta(name=name, namespace=ns, labels=labels),
            rules=policy_rules or None,
        )

        self._log.info("creating_role", name=name, namespace=ns)
        try:
            result = self._client.rbac_v1.create_namespaced_role(namespace=ns, body=body)
            self._log.info("created_role", name=name, namespace=ns)
            return RoleSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "Role", name, ns)

    def delete_role(self, name: str, namespace: str | None = None) -> None:
        """Delete a role.

        Args:
            name: Role name.
            namespace: Target namespace.
        """
        ns = self._resolve_namespace(namespace)
        self._log.info("deleting_role", name=name, namespace=ns)
        try:
            self._client.rbac_v1.delete_namespaced_role(name=name, namespace=ns)
            self._log.info("deleted_role", name=name, namespace=ns)
        except Exception as e:
            self._handle_api_error(e, "Role", name, ns)

    # =========================================================================
    # ClusterRole Operations (Cluster-Scoped)
    # =========================================================================

    def list_cluster_roles(
        self,
        *,
        label_selector: str | None = None,
    ) -> list[RoleSummary]:
        """List cluster roles.

        Args:
            label_selector: Filter by label selector.

        Returns:
            List of role summaries (with is_cluster_role=True).
        """
        self._log.debug("listing_cluster_roles")
        try:
            kwargs: dict[str, Any] = {}
            if label_selector:
                kwargs["label_selector"] = label_selector

            result = self._client.rbac_v1.list_cluster_role(**kwargs)
            items = [RoleSummary.from_k8s_object(r, is_cluster_role=True) for r in result.items]
            self._log.debug("listed_cluster_roles", count=len(items))
            return items
        except Exception as e:
            self._handle_api_error(e, "ClusterRole", None, None)

    def get_cluster_role(self, name: str) -> RoleSummary:
        """Get a single cluster role by name.

        Args:
            name: ClusterRole name.

        Returns:
            Role summary (with is_cluster_role=True).
        """
        self._log.debug("getting_cluster_role", name=name)
        try:
            result = self._client.rbac_v1.read_cluster_role(name=name)
            return RoleSummary.from_k8s_object(result, is_cluster_role=True)
        except Exception as e:
            self._handle_api_error(e, "ClusterRole", name, None)

    def create_cluster_role(
        self,
        name: str,
        *,
        rules: list[dict[str, Any]] | None = None,
        labels: dict[str, str] | None = None,
    ) -> RoleSummary:
        """Create a cluster role.

        Args:
            name: ClusterRole name.
            rules: List of policy rules.
            labels: ClusterRole labels.

        Returns:
            Created role summary (with is_cluster_role=True).
        """
        from kubernetes.client import V1ClusterRole, V1ObjectMeta, V1PolicyRule

        policy_rules = [
            V1PolicyRule(
                verbs=r.get("verbs", []),
                api_groups=r.get("api_groups", [""]),
                resources=r.get("resources", []),
                resource_names=r.get("resource_names"),
            )
            for r in (rules or [])
        ]

        body = V1ClusterRole(
            metadata=V1ObjectMeta(name=name, labels=labels),
            rules=policy_rules or None,
        )

        self._log.info("creating_cluster_role", name=name)
        try:
            result = self._client.rbac_v1.create_cluster_role(body=body)
            self._log.info("created_cluster_role", name=name)
            return RoleSummary.from_k8s_object(result, is_cluster_role=True)
        except Exception as e:
            self._handle_api_error(e, "ClusterRole", name, None)

    def delete_cluster_role(self, name: str) -> None:
        """Delete a cluster role.

        Args:
            name: ClusterRole name.
        """
        self._log.info("deleting_cluster_role", name=name)
        try:
            self._client.rbac_v1.delete_cluster_role(name=name)
            self._log.info("deleted_cluster_role", name=name)
        except Exception as e:
            self._handle_api_error(e, "ClusterRole", name, None)

    # =========================================================================
    # RoleBinding Operations (Namespaced)
    # =========================================================================

    def list_role_bindings(
        self,
        namespace: str | None = None,
        *,
        label_selector: str | None = None,
    ) -> list[RoleBindingSummary]:
        """List role bindings in a namespace.

        Args:
            namespace: Target namespace.
            label_selector: Filter by label selector.

        Returns:
            List of role binding summaries.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("listing_role_bindings", namespace=ns)
        try:
            kwargs: dict[str, Any] = {}
            if label_selector:
                kwargs["label_selector"] = label_selector

            result = self._client.rbac_v1.list_namespaced_role_binding(namespace=ns, **kwargs)
            items = [RoleBindingSummary.from_k8s_object(rb) for rb in result.items]
            self._log.debug("listed_role_bindings", count=len(items))
            return items
        except Exception as e:
            self._handle_api_error(e, "RoleBinding", None, ns)

    def get_role_binding(self, name: str, namespace: str | None = None) -> RoleBindingSummary:
        """Get a single role binding by name.

        Args:
            name: RoleBinding name.
            namespace: Target namespace.

        Returns:
            RoleBinding summary.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("getting_role_binding", name=name, namespace=ns)
        try:
            result = self._client.rbac_v1.read_namespaced_role_binding(name=name, namespace=ns)
            return RoleBindingSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "RoleBinding", name, ns)

    def create_role_binding(
        self,
        name: str,
        namespace: str | None = None,
        *,
        role_ref: dict[str, str],
        subjects: list[dict[str, str]],
        labels: dict[str, str] | None = None,
    ) -> RoleBindingSummary:
        """Create a role binding.

        Args:
            name: RoleBinding name.
            namespace: Target namespace.
            role_ref: Role reference with 'kind' (Role/ClusterRole), 'name', 'api_group'.
            subjects: List of subjects, each with 'kind', 'name', 'namespace' (optional).
            labels: RoleBinding labels.

        Returns:
            Created role binding summary.
        """
        from kubernetes.client import (
            V1ObjectMeta,
            V1RoleBinding,
            V1RoleRef,
            V1Subject,
        )

        ns = self._resolve_namespace(namespace)

        body = V1RoleBinding(
            metadata=V1ObjectMeta(name=name, namespace=ns, labels=labels),
            role_ref=V1RoleRef(
                kind=role_ref.get("kind", "Role"),
                name=role_ref["name"],
                api_group=role_ref.get("api_group", "rbac.authorization.k8s.io"),
            ),
            subjects=[
                V1Subject(
                    kind=s.get("kind", "ServiceAccount"),
                    name=s["name"],
                    namespace=s.get("namespace"),
                    api_group=s.get("api_group"),
                )
                for s in subjects
            ],
        )

        self._log.info("creating_role_binding", name=name, namespace=ns)
        try:
            result = self._client.rbac_v1.create_namespaced_role_binding(namespace=ns, body=body)
            self._log.info("created_role_binding", name=name, namespace=ns)
            return RoleBindingSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "RoleBinding", name, ns)

    def delete_role_binding(self, name: str, namespace: str | None = None) -> None:
        """Delete a role binding.

        Args:
            name: RoleBinding name.
            namespace: Target namespace.
        """
        ns = self._resolve_namespace(namespace)
        self._log.info("deleting_role_binding", name=name, namespace=ns)
        try:
            self._client.rbac_v1.delete_namespaced_role_binding(name=name, namespace=ns)
            self._log.info("deleted_role_binding", name=name, namespace=ns)
        except Exception as e:
            self._handle_api_error(e, "RoleBinding", name, ns)

    # =========================================================================
    # ClusterRoleBinding Operations (Cluster-Scoped)
    # =========================================================================

    def list_cluster_role_bindings(
        self,
        *,
        label_selector: str | None = None,
    ) -> list[RoleBindingSummary]:
        """List cluster role bindings.

        Args:
            label_selector: Filter by label selector.

        Returns:
            List of role binding summaries (with is_cluster_binding=True).
        """
        self._log.debug("listing_cluster_role_bindings")
        try:
            kwargs: dict[str, Any] = {}
            if label_selector:
                kwargs["label_selector"] = label_selector

            result = self._client.rbac_v1.list_cluster_role_binding(**kwargs)
            items = [
                RoleBindingSummary.from_k8s_object(rb, is_cluster_binding=True)
                for rb in result.items
            ]
            self._log.debug("listed_cluster_role_bindings", count=len(items))
            return items
        except Exception as e:
            self._handle_api_error(e, "ClusterRoleBinding", None, None)

    def get_cluster_role_binding(self, name: str) -> RoleBindingSummary:
        """Get a single cluster role binding by name.

        Args:
            name: ClusterRoleBinding name.

        Returns:
            RoleBinding summary (with is_cluster_binding=True).
        """
        self._log.debug("getting_cluster_role_binding", name=name)
        try:
            result = self._client.rbac_v1.read_cluster_role_binding(name=name)
            return RoleBindingSummary.from_k8s_object(result, is_cluster_binding=True)
        except Exception as e:
            self._handle_api_error(e, "ClusterRoleBinding", name, None)

    def create_cluster_role_binding(
        self,
        name: str,
        *,
        role_ref: dict[str, str],
        subjects: list[dict[str, str]],
        labels: dict[str, str] | None = None,
    ) -> RoleBindingSummary:
        """Create a cluster role binding.

        Args:
            name: ClusterRoleBinding name.
            role_ref: Role reference with 'kind' (ClusterRole), 'name', 'api_group'.
            subjects: List of subjects.
            labels: ClusterRoleBinding labels.

        Returns:
            Created cluster role binding summary.
        """
        from kubernetes.client import (
            V1ClusterRoleBinding,
            V1ObjectMeta,
            V1RoleRef,
            V1Subject,
        )

        body = V1ClusterRoleBinding(
            metadata=V1ObjectMeta(name=name, labels=labels),
            role_ref=V1RoleRef(
                kind=role_ref.get("kind", "ClusterRole"),
                name=role_ref["name"],
                api_group=role_ref.get("api_group", "rbac.authorization.k8s.io"),
            ),
            subjects=[
                V1Subject(
                    kind=s.get("kind", "ServiceAccount"),
                    name=s["name"],
                    namespace=s.get("namespace"),
                    api_group=s.get("api_group"),
                )
                for s in subjects
            ],
        )

        self._log.info("creating_cluster_role_binding", name=name)
        try:
            result = self._client.rbac_v1.create_cluster_role_binding(body=body)
            self._log.info("created_cluster_role_binding", name=name)
            return RoleBindingSummary.from_k8s_object(result, is_cluster_binding=True)
        except Exception as e:
            self._handle_api_error(e, "ClusterRoleBinding", name, None)

    def delete_cluster_role_binding(self, name: str) -> None:
        """Delete a cluster role binding.

        Args:
            name: ClusterRoleBinding name.
        """
        self._log.info("deleting_cluster_role_binding", name=name)
        try:
            self._client.rbac_v1.delete_cluster_role_binding(name=name)
            self._log.info("deleted_cluster_role_binding", name=name)
        except Exception as e:
            self._handle_api_error(e, "ClusterRoleBinding", name, None)
