"""ArgoCD resource manager.

Manages ArgoCD Applications and AppProjects
through the Kubernetes ``CustomObjectsApi``.
"""

from __future__ import annotations

from typing import Any

from system_operations_manager.integrations.kubernetes.models.argocd import (
    ApplicationSummary,
    AppProjectSummary,
)
from system_operations_manager.services.kubernetes.base import K8sBaseManager

# ArgoCD CRD coordinates
ARGOCD_GROUP = "argoproj.io"
ARGOCD_VERSION = "v1alpha1"
APPLICATION_PLURAL = "applications"
APP_PROJECT_PLURAL = "appprojects"

# Default ArgoCD namespace
ARGOCD_NAMESPACE = "argocd"


class ArgoCDManager(K8sBaseManager):
    """Manager for ArgoCD resources.

    Provides CRUD operations for Applications and AppProjects,
    plus sync, rollback, health, and diff operations.
    All CRD resources are accessed via ``CustomObjectsApi``.
    """

    _entity_name = "argocd"

    # =========================================================================
    # Application Operations
    # =========================================================================

    def list_applications(
        self,
        namespace: str | None = None,
        *,
        label_selector: str | None = None,
    ) -> list[ApplicationSummary]:
        """List ArgoCD Applications in a namespace.

        Args:
            namespace: Target namespace (defaults to argocd).
            label_selector: Filter by label selector.

        Returns:
            List of application summaries.
        """
        ns = namespace or ARGOCD_NAMESPACE
        self._log.debug("listing_applications", namespace=ns)
        try:
            kwargs: dict[str, Any] = {}
            if label_selector:
                kwargs["label_selector"] = label_selector

            result = self._client.custom_objects.list_namespaced_custom_object(
                ARGOCD_GROUP,
                ARGOCD_VERSION,
                ns,
                APPLICATION_PLURAL,
                **kwargs,
            )
            items: list[dict[str, Any]] = result.get("items", [])
            apps = [ApplicationSummary.from_k8s_object(item) for item in items]
            self._log.debug("listed_applications", count=len(apps), namespace=ns)
            return apps
        except Exception as e:
            self._handle_api_error(e, "Application", None, ns)

    def get_application(
        self,
        name: str,
        namespace: str | None = None,
    ) -> ApplicationSummary:
        """Get a single ArgoCD Application by name.

        Args:
            name: Application name.
            namespace: Target namespace (defaults to argocd).

        Returns:
            Application summary.
        """
        ns = namespace or ARGOCD_NAMESPACE
        self._log.debug("getting_application", name=name, namespace=ns)
        try:
            result = self._client.custom_objects.get_namespaced_custom_object(
                ARGOCD_GROUP,
                ARGOCD_VERSION,
                ns,
                APPLICATION_PLURAL,
                name,
            )
            return ApplicationSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "Application", name, ns)

    def create_application(
        self,
        name: str,
        namespace: str | None = None,
        *,
        project: str = "default",
        repo_url: str,
        path: str,
        target_revision: str = "HEAD",
        dest_server: str = "https://kubernetes.default.svc",
        dest_namespace: str = "default",
        auto_sync: bool = False,
        labels: dict[str, str] | None = None,
    ) -> ApplicationSummary:
        """Create a new ArgoCD Application.

        Args:
            name: Application name.
            namespace: Target namespace (defaults to argocd).
            project: ArgoCD project name.
            repo_url: Source Git repository URL.
            path: Path within the repository.
            target_revision: Branch, tag, or commit to track.
            dest_server: Destination cluster API server.
            dest_namespace: Destination namespace.
            auto_sync: Enable automated sync.
            labels: Optional labels.

        Returns:
            Created application summary.
        """
        ns = namespace or ARGOCD_NAMESPACE
        self._log.debug("creating_application", name=name, namespace=ns)

        sync_policy: dict[str, Any] = {}
        if auto_sync:
            sync_policy["automated"] = {"prune": True, "selfHeal": True}

        body: dict[str, Any] = {
            "apiVersion": f"{ARGOCD_GROUP}/{ARGOCD_VERSION}",
            "kind": "Application",
            "metadata": {
                "name": name,
                "namespace": ns,
                "labels": labels or {},
            },
            "spec": {
                "project": project,
                "source": {
                    "repoURL": repo_url,
                    "path": path,
                    "targetRevision": target_revision,
                },
                "destination": {
                    "server": dest_server,
                    "namespace": dest_namespace,
                },
                "syncPolicy": sync_policy,
            },
        }
        try:
            result = self._client.custom_objects.create_namespaced_custom_object(
                ARGOCD_GROUP,
                ARGOCD_VERSION,
                ns,
                APPLICATION_PLURAL,
                body,
            )
            self._log.info("created_application", name=name, namespace=ns)
            return ApplicationSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "Application", name, ns)

    def delete_application(
        self,
        name: str,
        namespace: str | None = None,
    ) -> None:
        """Delete an ArgoCD Application.

        Args:
            name: Application name to delete.
            namespace: Target namespace (defaults to argocd).
        """
        ns = namespace or ARGOCD_NAMESPACE
        self._log.debug("deleting_application", name=name, namespace=ns)
        try:
            self._client.custom_objects.delete_namespaced_custom_object(
                ARGOCD_GROUP,
                ARGOCD_VERSION,
                ns,
                APPLICATION_PLURAL,
                name,
            )
            self._log.info("deleted_application", name=name, namespace=ns)
        except Exception as e:
            self._handle_api_error(e, "Application", name, ns)

    def sync_application(
        self,
        name: str,
        namespace: str | None = None,
        *,
        revision: str | None = None,
        prune: bool = False,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Trigger a sync on an ArgoCD Application.

        Patches the Application CRD's ``.operation`` field to trigger a sync.

        Args:
            name: Application name.
            namespace: Target namespace (defaults to argocd).
            revision: Specific revision to sync to.
            prune: Whether to prune resources not in git.
            dry_run: Whether to perform a dry-run.

        Returns:
            Dict with sync operation details.
        """
        ns = namespace or ARGOCD_NAMESPACE
        self._log.debug("syncing_application", name=name, namespace=ns)
        try:
            sync_op: dict[str, Any] = {
                "prune": prune,
                "dryRun": dry_run,
            }
            if revision:
                sync_op["revision"] = revision

            patch: dict[str, Any] = {
                "operation": {
                    "initiatedBy": {"username": "ops-cli"},
                    "sync": sync_op,
                },
            }

            result = self._client.custom_objects.patch_namespaced_custom_object(
                ARGOCD_GROUP,
                ARGOCD_VERSION,
                ns,
                APPLICATION_PLURAL,
                name,
                patch,
            )
            self._log.info("synced_application", name=name, namespace=ns)
            operation: dict[str, Any] = result.get("operation", {})
            return {
                "name": name,
                "namespace": ns,
                "sync": operation.get("sync", {}),
                "initiated_by": operation.get("initiatedBy", {}),
            }
        except Exception as e:
            self._handle_api_error(e, "Application", name, ns)

    def rollback_application(
        self,
        name: str,
        namespace: str | None = None,
        *,
        revision_id: int = 0,
    ) -> dict[str, Any]:
        """Rollback an ArgoCD Application to a previous revision.

        Args:
            name: Application name.
            namespace: Target namespace (defaults to argocd).
            revision_id: History revision ID to rollback to (0 = previous).

        Returns:
            Dict with rollback details.
        """
        ns = namespace or ARGOCD_NAMESPACE
        self._log.debug(
            "rolling_back_application", name=name, namespace=ns, revision_id=revision_id
        )
        try:
            # Get current application to read history
            app = self._client.custom_objects.get_namespaced_custom_object(
                ARGOCD_GROUP,
                ARGOCD_VERSION,
                ns,
                APPLICATION_PLURAL,
                name,
            )
            status: dict[str, Any] = app.get("status", {})
            history: list[dict[str, Any]] = status.get("history", [])

            if not history:
                return {
                    "name": name,
                    "namespace": ns,
                    "error": "No deployment history available",
                }

            # Select target revision from history
            if revision_id > 0 and revision_id <= len(history):
                target = history[revision_id - 1]
            else:
                # Default to previous revision (second-to-last entry)
                target = history[-2] if len(history) >= 2 else history[-1]

            target_revision = target.get("revision", "")

            # Trigger sync with that revision
            patch: dict[str, Any] = {
                "operation": {
                    "initiatedBy": {"username": "ops-cli"},
                    "sync": {
                        "revision": target_revision,
                    },
                },
            }

            self._client.custom_objects.patch_namespaced_custom_object(
                ARGOCD_GROUP,
                ARGOCD_VERSION,
                ns,
                APPLICATION_PLURAL,
                name,
                patch,
            )
            self._log.info(
                "rolled_back_application", name=name, namespace=ns, revision=target_revision
            )
            return {
                "name": name,
                "namespace": ns,
                "target_revision": target_revision,
                "revision_id": revision_id,
            }
        except Exception as e:
            self._handle_api_error(e, "Application", name, ns)

    def get_application_health(
        self,
        name: str,
        namespace: str | None = None,
    ) -> dict[str, Any]:
        """Get detailed health status for an ArgoCD Application.

        Args:
            name: Application name.
            namespace: Target namespace (defaults to argocd).

        Returns:
            Dict with health status, resource statuses, and conditions.
        """
        ns = namespace or ARGOCD_NAMESPACE
        self._log.debug("getting_application_health", name=name, namespace=ns)
        try:
            result = self._client.custom_objects.get_namespaced_custom_object(
                ARGOCD_GROUP,
                ARGOCD_VERSION,
                ns,
                APPLICATION_PLURAL,
                name,
            )
            status: dict[str, Any] = result.get("status", {})
            health: dict[str, Any] = status.get("health", {})
            resources: list[dict[str, Any]] = status.get("resources", [])

            resource_summary = []
            for r in resources:
                resource_summary.append(
                    {
                        "kind": r.get("kind", ""),
                        "name": r.get("name", ""),
                        "namespace": r.get("namespace", ""),
                        "status": r.get("status", "Unknown"),
                        "health": r.get("health", {}).get("status", "Unknown"),
                    }
                )

            return {
                "name": name,
                "namespace": ns,
                "health_status": health.get("status", "Unknown"),
                "message": health.get("message"),
                "resources": resource_summary,
                "conditions": status.get("conditions", []),
            }
        except Exception as e:
            self._handle_api_error(e, "Application", name, ns)

    def diff_application(
        self,
        name: str,
        namespace: str | None = None,
    ) -> dict[str, Any]:
        """Get sync diff for an ArgoCD Application.

        Compares desired state with live state using the Application CRD status.

        Args:
            name: Application name.
            namespace: Target namespace (defaults to argocd).

        Returns:
            Dict with sync status, compared revision, and out-of-sync resources.
        """
        ns = namespace or ARGOCD_NAMESPACE
        self._log.debug("diffing_application", name=name, namespace=ns)
        try:
            result = self._client.custom_objects.get_namespaced_custom_object(
                ARGOCD_GROUP,
                ARGOCD_VERSION,
                ns,
                APPLICATION_PLURAL,
                name,
            )
            status: dict[str, Any] = result.get("status", {})
            sync: dict[str, Any] = status.get("sync", {})
            resources: list[dict[str, Any]] = status.get("resources", [])

            out_of_sync = [
                {
                    "kind": r.get("kind", ""),
                    "name": r.get("name", ""),
                    "namespace": r.get("namespace", ""),
                    "status": r.get("status", ""),
                }
                for r in resources
                if r.get("status") != "Synced"
            ]

            compared_to: dict[str, Any] = sync.get("comparedTo", {})

            return {
                "name": name,
                "namespace": ns,
                "sync_status": sync.get("status", "Unknown"),
                "revision": sync.get("revision", ""),
                "compared_source": compared_to.get("source", {}),
                "compared_destination": compared_to.get("destination", {}),
                "out_of_sync_resources": out_of_sync,
                "total_resources": len(resources),
                "synced_resources": len(resources) - len(out_of_sync),
            }
        except Exception as e:
            self._handle_api_error(e, "Application", name, ns)

    # =========================================================================
    # AppProject Operations
    # =========================================================================

    def list_projects(
        self,
        namespace: str | None = None,
        *,
        label_selector: str | None = None,
    ) -> list[AppProjectSummary]:
        """List ArgoCD AppProjects.

        Args:
            namespace: Target namespace (defaults to argocd).
            label_selector: Filter by label selector.

        Returns:
            List of project summaries.
        """
        ns = namespace or ARGOCD_NAMESPACE
        self._log.debug("listing_projects", namespace=ns)
        try:
            kwargs: dict[str, Any] = {}
            if label_selector:
                kwargs["label_selector"] = label_selector

            result = self._client.custom_objects.list_namespaced_custom_object(
                ARGOCD_GROUP,
                ARGOCD_VERSION,
                ns,
                APP_PROJECT_PLURAL,
                **kwargs,
            )
            items: list[dict[str, Any]] = result.get("items", [])
            projects = [AppProjectSummary.from_k8s_object(item) for item in items]
            self._log.debug("listed_projects", count=len(projects), namespace=ns)
            return projects
        except Exception as e:
            self._handle_api_error(e, "AppProject", None, ns)

    def get_project(
        self,
        name: str,
        namespace: str | None = None,
    ) -> AppProjectSummary:
        """Get a single ArgoCD AppProject by name.

        Args:
            name: Project name.
            namespace: Target namespace (defaults to argocd).

        Returns:
            Project summary.
        """
        ns = namespace or ARGOCD_NAMESPACE
        self._log.debug("getting_project", name=name, namespace=ns)
        try:
            result = self._client.custom_objects.get_namespaced_custom_object(
                ARGOCD_GROUP,
                ARGOCD_VERSION,
                ns,
                APP_PROJECT_PLURAL,
                name,
            )
            return AppProjectSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "AppProject", name, ns)

    def create_project(
        self,
        name: str,
        namespace: str | None = None,
        *,
        description: str = "",
        source_repos: list[str] | None = None,
        destinations: list[dict[str, str]] | None = None,
        labels: dict[str, str] | None = None,
    ) -> AppProjectSummary:
        """Create a new ArgoCD AppProject.

        Args:
            name: Project name.
            namespace: Target namespace (defaults to argocd).
            description: Project description.
            source_repos: Allowed source repository URLs.
            destinations: Allowed destinations (list of server/namespace dicts).
            labels: Optional labels.

        Returns:
            Created project summary.
        """
        ns = namespace or ARGOCD_NAMESPACE
        self._log.debug("creating_project", name=name, namespace=ns)
        body: dict[str, Any] = {
            "apiVersion": f"{ARGOCD_GROUP}/{ARGOCD_VERSION}",
            "kind": "AppProject",
            "metadata": {
                "name": name,
                "namespace": ns,
                "labels": labels or {},
            },
            "spec": {
                "description": description,
                "sourceRepos": source_repos or ["*"],
                "destinations": destinations or [{"server": "*", "namespace": "*"}],
            },
        }
        try:
            result = self._client.custom_objects.create_namespaced_custom_object(
                ARGOCD_GROUP,
                ARGOCD_VERSION,
                ns,
                APP_PROJECT_PLURAL,
                body,
            )
            self._log.info("created_project", name=name, namespace=ns)
            return AppProjectSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "AppProject", name, ns)

    def delete_project(
        self,
        name: str,
        namespace: str | None = None,
    ) -> None:
        """Delete an ArgoCD AppProject.

        Args:
            name: Project name to delete.
            namespace: Target namespace (defaults to argocd).
        """
        ns = namespace or ARGOCD_NAMESPACE
        self._log.debug("deleting_project", name=name, namespace=ns)
        try:
            self._client.custom_objects.delete_namespaced_custom_object(
                ARGOCD_GROUP,
                ARGOCD_VERSION,
                ns,
                APP_PROJECT_PLURAL,
                name,
            )
            self._log.info("deleted_project", name=name, namespace=ns)
        except Exception as e:
            self._handle_api_error(e, "AppProject", name, ns)
