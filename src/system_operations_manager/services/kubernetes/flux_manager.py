"""Flux CD resource manager.

Manages Flux GitRepositories, HelmRepositories, Kustomizations,
and HelmReleases through the Kubernetes ``CustomObjectsApi``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from system_operations_manager.integrations.kubernetes.models.flux import (
    GitRepositorySummary,
    HelmReleaseSummary,
    HelmRepositorySummary,
    KustomizationSummary,
)
from system_operations_manager.services.kubernetes.base import K8sBaseManager

# =============================================================================
# CRD Coordinates
# =============================================================================

# Source CRDs
SOURCE_GROUP = "source.toolkit.fluxcd.io"
SOURCE_VERSION = "v1"
GIT_REPOSITORY_PLURAL = "gitrepositories"
HELM_REPOSITORY_PLURAL = "helmrepositories"

# Kustomization CRD
KUSTOMIZE_GROUP = "kustomize.toolkit.fluxcd.io"
KUSTOMIZE_VERSION = "v1"
KUSTOMIZATION_PLURAL = "kustomizations"

# HelmRelease CRD
HELM_GROUP = "helm.toolkit.fluxcd.io"
HELM_VERSION = "v2"
HELM_RELEASE_PLURAL = "helmreleases"

# Default Flux namespace
FLUX_NAMESPACE = "flux-system"

# Annotation key used to trigger reconciliation
RECONCILE_ANNOTATION = "reconcile.fluxcd.io/requestedAt"


class FluxManager(K8sBaseManager):
    """Manager for Flux CD resources.

    Provides CRUD operations, suspend/resume, and reconciliation
    for GitRepositories, HelmRepositories, Kustomizations, and HelmReleases.
    All CRD resources are accessed via ``CustomObjectsApi``.
    """

    _entity_name = "flux"

    # =========================================================================
    # GitRepository Operations
    # =========================================================================

    def list_git_repositories(
        self,
        namespace: str | None = None,
        *,
        label_selector: str | None = None,
    ) -> list[GitRepositorySummary]:
        """List Flux GitRepositories in a namespace.

        Args:
            namespace: Target namespace (defaults to flux-system).
            label_selector: Filter by label selector.

        Returns:
            List of GitRepository summaries.
        """
        ns = namespace or FLUX_NAMESPACE
        self._log.debug("listing_git_repositories", namespace=ns)
        try:
            kwargs: dict[str, Any] = {}
            if label_selector:
                kwargs["label_selector"] = label_selector

            result = self._client.custom_objects.list_namespaced_custom_object(
                SOURCE_GROUP,
                SOURCE_VERSION,
                ns,
                GIT_REPOSITORY_PLURAL,
                **kwargs,
            )
            items: list[dict[str, Any]] = result.get("items", [])
            repos = [GitRepositorySummary.from_k8s_object(item) for item in items]
            self._log.debug("listed_git_repositories", count=len(repos), namespace=ns)
            return repos
        except Exception as e:
            self._handle_api_error(e, "GitRepository", None, ns)

    def get_git_repository(
        self,
        name: str,
        namespace: str | None = None,
    ) -> GitRepositorySummary:
        """Get a single Flux GitRepository by name.

        Args:
            name: GitRepository name.
            namespace: Target namespace (defaults to flux-system).

        Returns:
            GitRepository summary.
        """
        ns = namespace or FLUX_NAMESPACE
        self._log.debug("getting_git_repository", name=name, namespace=ns)
        try:
            result = self._client.custom_objects.get_namespaced_custom_object(
                SOURCE_GROUP,
                SOURCE_VERSION,
                ns,
                GIT_REPOSITORY_PLURAL,
                name,
            )
            return GitRepositorySummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "GitRepository", name, ns)

    def create_git_repository(
        self,
        name: str,
        namespace: str | None = None,
        *,
        url: str,
        ref_branch: str | None = None,
        ref_tag: str | None = None,
        ref_semver: str | None = None,
        ref_commit: str | None = None,
        interval: str = "1m",
        secret_ref: str | None = None,
        labels: dict[str, str] | None = None,
    ) -> GitRepositorySummary:
        """Create a new Flux GitRepository.

        Args:
            name: GitRepository name.
            namespace: Target namespace (defaults to flux-system).
            url: Git repository URL.
            ref_branch: Branch to track.
            ref_tag: Tag to track.
            ref_semver: Semver range to track.
            ref_commit: Specific commit SHA.
            interval: Reconciliation interval (e.g. '1m', '5m').
            secret_ref: Name of the Secret for authentication.
            labels: Optional labels.

        Returns:
            Created GitRepository summary.
        """
        ns = namespace or FLUX_NAMESPACE
        self._log.debug("creating_git_repository", name=name, namespace=ns)

        ref: dict[str, str] = {}
        if ref_branch:
            ref["branch"] = ref_branch
        if ref_tag:
            ref["tag"] = ref_tag
        if ref_semver:
            ref["semver"] = ref_semver
        if ref_commit:
            ref["commit"] = ref_commit
        if not ref:
            ref["branch"] = "main"

        spec: dict[str, Any] = {
            "url": url,
            "ref": ref,
            "interval": interval,
        }
        if secret_ref:
            spec["secretRef"] = {"name": secret_ref}

        body: dict[str, Any] = {
            "apiVersion": f"{SOURCE_GROUP}/{SOURCE_VERSION}",
            "kind": "GitRepository",
            "metadata": {
                "name": name,
                "namespace": ns,
                "labels": labels or {},
            },
            "spec": spec,
        }
        try:
            result = self._client.custom_objects.create_namespaced_custom_object(
                SOURCE_GROUP,
                SOURCE_VERSION,
                ns,
                GIT_REPOSITORY_PLURAL,
                body,
            )
            self._log.info("created_git_repository", name=name, namespace=ns)
            return GitRepositorySummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "GitRepository", name, ns)

    def delete_git_repository(
        self,
        name: str,
        namespace: str | None = None,
    ) -> None:
        """Delete a Flux GitRepository.

        Args:
            name: GitRepository name to delete.
            namespace: Target namespace (defaults to flux-system).
        """
        ns = namespace or FLUX_NAMESPACE
        self._log.debug("deleting_git_repository", name=name, namespace=ns)
        try:
            self._client.custom_objects.delete_namespaced_custom_object(
                SOURCE_GROUP,
                SOURCE_VERSION,
                ns,
                GIT_REPOSITORY_PLURAL,
                name,
            )
            self._log.info("deleted_git_repository", name=name, namespace=ns)
        except Exception as e:
            self._handle_api_error(e, "GitRepository", name, ns)

    def suspend_git_repository(
        self,
        name: str,
        namespace: str | None = None,
    ) -> dict[str, Any]:
        """Suspend reconciliation of a Flux GitRepository.

        Args:
            name: GitRepository name.
            namespace: Target namespace (defaults to flux-system).

        Returns:
            Dict with operation details.
        """
        ns = namespace or FLUX_NAMESPACE
        self._log.debug("suspending_git_repository", name=name, namespace=ns)
        try:
            patch: dict[str, Any] = {"spec": {"suspend": True}}
            self._client.custom_objects.patch_namespaced_custom_object(
                SOURCE_GROUP,
                SOURCE_VERSION,
                ns,
                GIT_REPOSITORY_PLURAL,
                name,
                patch,
            )
            self._log.info("suspended_git_repository", name=name, namespace=ns)
            return {"name": name, "namespace": ns, "suspended": True}
        except Exception as e:
            self._handle_api_error(e, "GitRepository", name, ns)

    def resume_git_repository(
        self,
        name: str,
        namespace: str | None = None,
    ) -> dict[str, Any]:
        """Resume reconciliation of a Flux GitRepository.

        Args:
            name: GitRepository name.
            namespace: Target namespace (defaults to flux-system).

        Returns:
            Dict with operation details.
        """
        ns = namespace or FLUX_NAMESPACE
        self._log.debug("resuming_git_repository", name=name, namespace=ns)
        try:
            patch: dict[str, Any] = {"spec": {"suspend": False}}
            self._client.custom_objects.patch_namespaced_custom_object(
                SOURCE_GROUP,
                SOURCE_VERSION,
                ns,
                GIT_REPOSITORY_PLURAL,
                name,
                patch,
            )
            self._log.info("resumed_git_repository", name=name, namespace=ns)
            return {"name": name, "namespace": ns, "suspended": False}
        except Exception as e:
            self._handle_api_error(e, "GitRepository", name, ns)

    def reconcile_git_repository(
        self,
        name: str,
        namespace: str | None = None,
    ) -> dict[str, Any]:
        """Trigger reconciliation of a Flux GitRepository.

        Annotates the resource with the current timestamp to request
        an immediate reconciliation.

        Args:
            name: GitRepository name.
            namespace: Target namespace (defaults to flux-system).

        Returns:
            Dict with operation details.
        """
        ns = namespace or FLUX_NAMESPACE
        requested_at = datetime.now(UTC).isoformat()
        self._log.debug("reconciling_git_repository", name=name, namespace=ns)
        try:
            patch: dict[str, Any] = {
                "metadata": {
                    "annotations": {RECONCILE_ANNOTATION: requested_at},
                },
            }
            self._client.custom_objects.patch_namespaced_custom_object(
                SOURCE_GROUP,
                SOURCE_VERSION,
                ns,
                GIT_REPOSITORY_PLURAL,
                name,
                patch,
            )
            self._log.info("reconciled_git_repository", name=name, namespace=ns)
            return {"name": name, "namespace": ns, "requested_at": requested_at}
        except Exception as e:
            self._handle_api_error(e, "GitRepository", name, ns)

    def get_git_repository_status(
        self,
        name: str,
        namespace: str | None = None,
    ) -> dict[str, Any]:
        """Get detailed status for a Flux GitRepository.

        Args:
            name: GitRepository name.
            namespace: Target namespace (defaults to flux-system).

        Returns:
            Dict with status details including conditions and artifact info.
        """
        ns = namespace or FLUX_NAMESPACE
        self._log.debug("getting_git_repository_status", name=name, namespace=ns)
        try:
            result = self._client.custom_objects.get_namespaced_custom_object(
                SOURCE_GROUP,
                SOURCE_VERSION,
                ns,
                GIT_REPOSITORY_PLURAL,
                name,
            )
            status: dict[str, Any] = result.get("status", {})
            artifact: dict[str, Any] = status.get("artifact", {})

            return {
                "name": name,
                "namespace": ns,
                "conditions": status.get("conditions", []),
                "artifact_revision": artifact.get("revision"),
                "artifact_digest": artifact.get("digest"),
                "last_handled_reconcile_at": status.get("lastHandledReconcileAt"),
                "observed_generation": status.get("observedGeneration"),
            }
        except Exception as e:
            self._handle_api_error(e, "GitRepository", name, ns)

    # =========================================================================
    # HelmRepository Operations
    # =========================================================================

    def list_helm_repositories(
        self,
        namespace: str | None = None,
        *,
        label_selector: str | None = None,
    ) -> list[HelmRepositorySummary]:
        """List Flux HelmRepositories in a namespace.

        Args:
            namespace: Target namespace (defaults to flux-system).
            label_selector: Filter by label selector.

        Returns:
            List of HelmRepository summaries.
        """
        ns = namespace or FLUX_NAMESPACE
        self._log.debug("listing_helm_repositories", namespace=ns)
        try:
            kwargs: dict[str, Any] = {}
            if label_selector:
                kwargs["label_selector"] = label_selector

            result = self._client.custom_objects.list_namespaced_custom_object(
                SOURCE_GROUP,
                SOURCE_VERSION,
                ns,
                HELM_REPOSITORY_PLURAL,
                **kwargs,
            )
            items: list[dict[str, Any]] = result.get("items", [])
            repos = [HelmRepositorySummary.from_k8s_object(item) for item in items]
            self._log.debug("listed_helm_repositories", count=len(repos), namespace=ns)
            return repos
        except Exception as e:
            self._handle_api_error(e, "HelmRepository", None, ns)

    def get_helm_repository(
        self,
        name: str,
        namespace: str | None = None,
    ) -> HelmRepositorySummary:
        """Get a single Flux HelmRepository by name.

        Args:
            name: HelmRepository name.
            namespace: Target namespace (defaults to flux-system).

        Returns:
            HelmRepository summary.
        """
        ns = namespace or FLUX_NAMESPACE
        self._log.debug("getting_helm_repository", name=name, namespace=ns)
        try:
            result = self._client.custom_objects.get_namespaced_custom_object(
                SOURCE_GROUP,
                SOURCE_VERSION,
                ns,
                HELM_REPOSITORY_PLURAL,
                name,
            )
            return HelmRepositorySummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "HelmRepository", name, ns)

    def create_helm_repository(
        self,
        name: str,
        namespace: str | None = None,
        *,
        url: str,
        repo_type: str = "default",
        interval: str = "1m",
        secret_ref: str | None = None,
        labels: dict[str, str] | None = None,
    ) -> HelmRepositorySummary:
        """Create a new Flux HelmRepository.

        Args:
            name: HelmRepository name.
            namespace: Target namespace (defaults to flux-system).
            url: Helm repository URL.
            repo_type: Repository type ('default' or 'oci').
            interval: Reconciliation interval.
            secret_ref: Name of the Secret for authentication.
            labels: Optional labels.

        Returns:
            Created HelmRepository summary.
        """
        ns = namespace or FLUX_NAMESPACE
        self._log.debug("creating_helm_repository", name=name, namespace=ns)

        spec: dict[str, Any] = {
            "url": url,
            "interval": interval,
        }
        if repo_type != "default":
            spec["type"] = repo_type
        if secret_ref:
            spec["secretRef"] = {"name": secret_ref}

        body: dict[str, Any] = {
            "apiVersion": f"{SOURCE_GROUP}/{SOURCE_VERSION}",
            "kind": "HelmRepository",
            "metadata": {
                "name": name,
                "namespace": ns,
                "labels": labels or {},
            },
            "spec": spec,
        }
        try:
            result = self._client.custom_objects.create_namespaced_custom_object(
                SOURCE_GROUP,
                SOURCE_VERSION,
                ns,
                HELM_REPOSITORY_PLURAL,
                body,
            )
            self._log.info("created_helm_repository", name=name, namespace=ns)
            return HelmRepositorySummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "HelmRepository", name, ns)

    def delete_helm_repository(
        self,
        name: str,
        namespace: str | None = None,
    ) -> None:
        """Delete a Flux HelmRepository.

        Args:
            name: HelmRepository name to delete.
            namespace: Target namespace (defaults to flux-system).
        """
        ns = namespace or FLUX_NAMESPACE
        self._log.debug("deleting_helm_repository", name=name, namespace=ns)
        try:
            self._client.custom_objects.delete_namespaced_custom_object(
                SOURCE_GROUP,
                SOURCE_VERSION,
                ns,
                HELM_REPOSITORY_PLURAL,
                name,
            )
            self._log.info("deleted_helm_repository", name=name, namespace=ns)
        except Exception as e:
            self._handle_api_error(e, "HelmRepository", name, ns)

    def suspend_helm_repository(
        self,
        name: str,
        namespace: str | None = None,
    ) -> dict[str, Any]:
        """Suspend reconciliation of a Flux HelmRepository.

        Args:
            name: HelmRepository name.
            namespace: Target namespace (defaults to flux-system).

        Returns:
            Dict with operation details.
        """
        ns = namespace or FLUX_NAMESPACE
        self._log.debug("suspending_helm_repository", name=name, namespace=ns)
        try:
            patch: dict[str, Any] = {"spec": {"suspend": True}}
            self._client.custom_objects.patch_namespaced_custom_object(
                SOURCE_GROUP,
                SOURCE_VERSION,
                ns,
                HELM_REPOSITORY_PLURAL,
                name,
                patch,
            )
            self._log.info("suspended_helm_repository", name=name, namespace=ns)
            return {"name": name, "namespace": ns, "suspended": True}
        except Exception as e:
            self._handle_api_error(e, "HelmRepository", name, ns)

    def resume_helm_repository(
        self,
        name: str,
        namespace: str | None = None,
    ) -> dict[str, Any]:
        """Resume reconciliation of a Flux HelmRepository.

        Args:
            name: HelmRepository name.
            namespace: Target namespace (defaults to flux-system).

        Returns:
            Dict with operation details.
        """
        ns = namespace or FLUX_NAMESPACE
        self._log.debug("resuming_helm_repository", name=name, namespace=ns)
        try:
            patch: dict[str, Any] = {"spec": {"suspend": False}}
            self._client.custom_objects.patch_namespaced_custom_object(
                SOURCE_GROUP,
                SOURCE_VERSION,
                ns,
                HELM_REPOSITORY_PLURAL,
                name,
                patch,
            )
            self._log.info("resumed_helm_repository", name=name, namespace=ns)
            return {"name": name, "namespace": ns, "suspended": False}
        except Exception as e:
            self._handle_api_error(e, "HelmRepository", name, ns)

    def reconcile_helm_repository(
        self,
        name: str,
        namespace: str | None = None,
    ) -> dict[str, Any]:
        """Trigger reconciliation of a Flux HelmRepository.

        Args:
            name: HelmRepository name.
            namespace: Target namespace (defaults to flux-system).

        Returns:
            Dict with operation details.
        """
        ns = namespace or FLUX_NAMESPACE
        requested_at = datetime.now(UTC).isoformat()
        self._log.debug("reconciling_helm_repository", name=name, namespace=ns)
        try:
            patch: dict[str, Any] = {
                "metadata": {
                    "annotations": {RECONCILE_ANNOTATION: requested_at},
                },
            }
            self._client.custom_objects.patch_namespaced_custom_object(
                SOURCE_GROUP,
                SOURCE_VERSION,
                ns,
                HELM_REPOSITORY_PLURAL,
                name,
                patch,
            )
            self._log.info("reconciled_helm_repository", name=name, namespace=ns)
            return {"name": name, "namespace": ns, "requested_at": requested_at}
        except Exception as e:
            self._handle_api_error(e, "HelmRepository", name, ns)

    def get_helm_repository_status(
        self,
        name: str,
        namespace: str | None = None,
    ) -> dict[str, Any]:
        """Get detailed status for a Flux HelmRepository.

        Args:
            name: HelmRepository name.
            namespace: Target namespace (defaults to flux-system).

        Returns:
            Dict with status details including conditions and artifact info.
        """
        ns = namespace or FLUX_NAMESPACE
        self._log.debug("getting_helm_repository_status", name=name, namespace=ns)
        try:
            result = self._client.custom_objects.get_namespaced_custom_object(
                SOURCE_GROUP,
                SOURCE_VERSION,
                ns,
                HELM_REPOSITORY_PLURAL,
                name,
            )
            status: dict[str, Any] = result.get("status", {})
            artifact: dict[str, Any] = status.get("artifact", {})

            return {
                "name": name,
                "namespace": ns,
                "conditions": status.get("conditions", []),
                "artifact_revision": artifact.get("revision"),
                "artifact_digest": artifact.get("digest"),
                "last_handled_reconcile_at": status.get("lastHandledReconcileAt"),
                "observed_generation": status.get("observedGeneration"),
            }
        except Exception as e:
            self._handle_api_error(e, "HelmRepository", name, ns)

    # =========================================================================
    # Kustomization Operations
    # =========================================================================

    def list_kustomizations(
        self,
        namespace: str | None = None,
        *,
        label_selector: str | None = None,
    ) -> list[KustomizationSummary]:
        """List Flux Kustomizations in a namespace.

        Args:
            namespace: Target namespace (defaults to flux-system).
            label_selector: Filter by label selector.

        Returns:
            List of Kustomization summaries.
        """
        ns = namespace or FLUX_NAMESPACE
        self._log.debug("listing_kustomizations", namespace=ns)
        try:
            kwargs: dict[str, Any] = {}
            if label_selector:
                kwargs["label_selector"] = label_selector

            result = self._client.custom_objects.list_namespaced_custom_object(
                KUSTOMIZE_GROUP,
                KUSTOMIZE_VERSION,
                ns,
                KUSTOMIZATION_PLURAL,
                **kwargs,
            )
            items: list[dict[str, Any]] = result.get("items", [])
            ks_list = [KustomizationSummary.from_k8s_object(item) for item in items]
            self._log.debug("listed_kustomizations", count=len(ks_list), namespace=ns)
            return ks_list
        except Exception as e:
            self._handle_api_error(e, "Kustomization", None, ns)

    def get_kustomization(
        self,
        name: str,
        namespace: str | None = None,
    ) -> KustomizationSummary:
        """Get a single Flux Kustomization by name.

        Args:
            name: Kustomization name.
            namespace: Target namespace (defaults to flux-system).

        Returns:
            Kustomization summary.
        """
        ns = namespace or FLUX_NAMESPACE
        self._log.debug("getting_kustomization", name=name, namespace=ns)
        try:
            result = self._client.custom_objects.get_namespaced_custom_object(
                KUSTOMIZE_GROUP,
                KUSTOMIZE_VERSION,
                ns,
                KUSTOMIZATION_PLURAL,
                name,
            )
            return KustomizationSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "Kustomization", name, ns)

    def create_kustomization(
        self,
        name: str,
        namespace: str | None = None,
        *,
        source_kind: str,
        source_name: str,
        source_namespace: str | None = None,
        path: str = "./",
        interval: str = "5m",
        prune: bool = True,
        target_namespace: str | None = None,
        labels: dict[str, str] | None = None,
    ) -> KustomizationSummary:
        """Create a new Flux Kustomization.

        Args:
            name: Kustomization name.
            namespace: Target namespace (defaults to flux-system).
            source_kind: Source reference kind (e.g. 'GitRepository').
            source_name: Source reference name.
            source_namespace: Source reference namespace.
            path: Path within the source.
            interval: Reconciliation interval.
            prune: Whether to prune resources not in source.
            target_namespace: Target namespace override.
            labels: Optional labels.

        Returns:
            Created Kustomization summary.
        """
        ns = namespace or FLUX_NAMESPACE
        self._log.debug("creating_kustomization", name=name, namespace=ns)

        source_ref: dict[str, Any] = {
            "kind": source_kind,
            "name": source_name,
        }
        if source_namespace:
            source_ref["namespace"] = source_namespace

        spec: dict[str, Any] = {
            "sourceRef": source_ref,
            "path": path,
            "interval": interval,
            "prune": prune,
        }
        if target_namespace:
            spec["targetNamespace"] = target_namespace

        body: dict[str, Any] = {
            "apiVersion": f"{KUSTOMIZE_GROUP}/{KUSTOMIZE_VERSION}",
            "kind": "Kustomization",
            "metadata": {
                "name": name,
                "namespace": ns,
                "labels": labels or {},
            },
            "spec": spec,
        }
        try:
            result = self._client.custom_objects.create_namespaced_custom_object(
                KUSTOMIZE_GROUP,
                KUSTOMIZE_VERSION,
                ns,
                KUSTOMIZATION_PLURAL,
                body,
            )
            self._log.info("created_kustomization", name=name, namespace=ns)
            return KustomizationSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "Kustomization", name, ns)

    def delete_kustomization(
        self,
        name: str,
        namespace: str | None = None,
    ) -> None:
        """Delete a Flux Kustomization.

        Args:
            name: Kustomization name to delete.
            namespace: Target namespace (defaults to flux-system).
        """
        ns = namespace or FLUX_NAMESPACE
        self._log.debug("deleting_kustomization", name=name, namespace=ns)
        try:
            self._client.custom_objects.delete_namespaced_custom_object(
                KUSTOMIZE_GROUP,
                KUSTOMIZE_VERSION,
                ns,
                KUSTOMIZATION_PLURAL,
                name,
            )
            self._log.info("deleted_kustomization", name=name, namespace=ns)
        except Exception as e:
            self._handle_api_error(e, "Kustomization", name, ns)

    def suspend_kustomization(
        self,
        name: str,
        namespace: str | None = None,
    ) -> dict[str, Any]:
        """Suspend reconciliation of a Flux Kustomization.

        Args:
            name: Kustomization name.
            namespace: Target namespace (defaults to flux-system).

        Returns:
            Dict with operation details.
        """
        ns = namespace or FLUX_NAMESPACE
        self._log.debug("suspending_kustomization", name=name, namespace=ns)
        try:
            patch: dict[str, Any] = {"spec": {"suspend": True}}
            self._client.custom_objects.patch_namespaced_custom_object(
                KUSTOMIZE_GROUP,
                KUSTOMIZE_VERSION,
                ns,
                KUSTOMIZATION_PLURAL,
                name,
                patch,
            )
            self._log.info("suspended_kustomization", name=name, namespace=ns)
            return {"name": name, "namespace": ns, "suspended": True}
        except Exception as e:
            self._handle_api_error(e, "Kustomization", name, ns)

    def resume_kustomization(
        self,
        name: str,
        namespace: str | None = None,
    ) -> dict[str, Any]:
        """Resume reconciliation of a Flux Kustomization.

        Args:
            name: Kustomization name.
            namespace: Target namespace (defaults to flux-system).

        Returns:
            Dict with operation details.
        """
        ns = namespace or FLUX_NAMESPACE
        self._log.debug("resuming_kustomization", name=name, namespace=ns)
        try:
            patch: dict[str, Any] = {"spec": {"suspend": False}}
            self._client.custom_objects.patch_namespaced_custom_object(
                KUSTOMIZE_GROUP,
                KUSTOMIZE_VERSION,
                ns,
                KUSTOMIZATION_PLURAL,
                name,
                patch,
            )
            self._log.info("resumed_kustomization", name=name, namespace=ns)
            return {"name": name, "namespace": ns, "suspended": False}
        except Exception as e:
            self._handle_api_error(e, "Kustomization", name, ns)

    def reconcile_kustomization(
        self,
        name: str,
        namespace: str | None = None,
    ) -> dict[str, Any]:
        """Trigger reconciliation of a Flux Kustomization.

        Args:
            name: Kustomization name.
            namespace: Target namespace (defaults to flux-system).

        Returns:
            Dict with operation details.
        """
        ns = namespace or FLUX_NAMESPACE
        requested_at = datetime.now(UTC).isoformat()
        self._log.debug("reconciling_kustomization", name=name, namespace=ns)
        try:
            patch: dict[str, Any] = {
                "metadata": {
                    "annotations": {RECONCILE_ANNOTATION: requested_at},
                },
            }
            self._client.custom_objects.patch_namespaced_custom_object(
                KUSTOMIZE_GROUP,
                KUSTOMIZE_VERSION,
                ns,
                KUSTOMIZATION_PLURAL,
                name,
                patch,
            )
            self._log.info("reconciled_kustomization", name=name, namespace=ns)
            return {"name": name, "namespace": ns, "requested_at": requested_at}
        except Exception as e:
            self._handle_api_error(e, "Kustomization", name, ns)

    def get_kustomization_status(
        self,
        name: str,
        namespace: str | None = None,
    ) -> dict[str, Any]:
        """Get detailed status for a Flux Kustomization.

        Args:
            name: Kustomization name.
            namespace: Target namespace (defaults to flux-system).

        Returns:
            Dict with status details including conditions and revision info.
        """
        ns = namespace or FLUX_NAMESPACE
        self._log.debug("getting_kustomization_status", name=name, namespace=ns)
        try:
            result = self._client.custom_objects.get_namespaced_custom_object(
                KUSTOMIZE_GROUP,
                KUSTOMIZE_VERSION,
                ns,
                KUSTOMIZATION_PLURAL,
                name,
            )
            status: dict[str, Any] = result.get("status", {})

            return {
                "name": name,
                "namespace": ns,
                "conditions": status.get("conditions", []),
                "last_applied_revision": status.get("lastAppliedRevision"),
                "last_attempted_revision": status.get("lastAttemptedRevision"),
                "last_handled_reconcile_at": status.get("lastHandledReconcileAt"),
                "observed_generation": status.get("observedGeneration"),
            }
        except Exception as e:
            self._handle_api_error(e, "Kustomization", name, ns)

    # =========================================================================
    # HelmRelease Operations
    # =========================================================================

    def list_helm_releases(
        self,
        namespace: str | None = None,
        *,
        label_selector: str | None = None,
    ) -> list[HelmReleaseSummary]:
        """List Flux HelmReleases in a namespace.

        Args:
            namespace: Target namespace (defaults to flux-system).
            label_selector: Filter by label selector.

        Returns:
            List of HelmRelease summaries.
        """
        ns = namespace or FLUX_NAMESPACE
        self._log.debug("listing_helm_releases", namespace=ns)
        try:
            kwargs: dict[str, Any] = {}
            if label_selector:
                kwargs["label_selector"] = label_selector

            result = self._client.custom_objects.list_namespaced_custom_object(
                HELM_GROUP,
                HELM_VERSION,
                ns,
                HELM_RELEASE_PLURAL,
                **kwargs,
            )
            items: list[dict[str, Any]] = result.get("items", [])
            releases = [HelmReleaseSummary.from_k8s_object(item) for item in items]
            self._log.debug("listed_helm_releases", count=len(releases), namespace=ns)
            return releases
        except Exception as e:
            self._handle_api_error(e, "HelmRelease", None, ns)

    def get_helm_release(
        self,
        name: str,
        namespace: str | None = None,
    ) -> HelmReleaseSummary:
        """Get a single Flux HelmRelease by name.

        Args:
            name: HelmRelease name.
            namespace: Target namespace (defaults to flux-system).

        Returns:
            HelmRelease summary.
        """
        ns = namespace or FLUX_NAMESPACE
        self._log.debug("getting_helm_release", name=name, namespace=ns)
        try:
            result = self._client.custom_objects.get_namespaced_custom_object(
                HELM_GROUP,
                HELM_VERSION,
                ns,
                HELM_RELEASE_PLURAL,
                name,
            )
            return HelmReleaseSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "HelmRelease", name, ns)

    def create_helm_release(
        self,
        name: str,
        namespace: str | None = None,
        *,
        chart_name: str,
        chart_source_kind: str,
        chart_source_name: str,
        chart_source_namespace: str | None = None,
        interval: str = "5m",
        target_namespace: str | None = None,
        values: dict[str, Any] | None = None,
        labels: dict[str, str] | None = None,
    ) -> HelmReleaseSummary:
        """Create a new Flux HelmRelease.

        Args:
            name: HelmRelease name.
            namespace: Target namespace (defaults to flux-system).
            chart_name: Helm chart name.
            chart_source_kind: Chart source reference kind (e.g. 'HelmRepository').
            chart_source_name: Chart source reference name.
            chart_source_namespace: Chart source reference namespace.
            interval: Reconciliation interval.
            target_namespace: Target namespace for deployed resources.
            values: Helm values to override.
            labels: Optional labels.

        Returns:
            Created HelmRelease summary.
        """
        ns = namespace or FLUX_NAMESPACE
        self._log.debug("creating_helm_release", name=name, namespace=ns)

        source_ref: dict[str, Any] = {
            "kind": chart_source_kind,
            "name": chart_source_name,
        }
        if chart_source_namespace:
            source_ref["namespace"] = chart_source_namespace

        spec: dict[str, Any] = {
            "chart": {
                "spec": {
                    "chart": chart_name,
                    "sourceRef": source_ref,
                },
            },
            "interval": interval,
        }
        if target_namespace:
            spec["targetNamespace"] = target_namespace
        if values:
            spec["values"] = values

        body: dict[str, Any] = {
            "apiVersion": f"{HELM_GROUP}/{HELM_VERSION}",
            "kind": "HelmRelease",
            "metadata": {
                "name": name,
                "namespace": ns,
                "labels": labels or {},
            },
            "spec": spec,
        }
        try:
            result = self._client.custom_objects.create_namespaced_custom_object(
                HELM_GROUP,
                HELM_VERSION,
                ns,
                HELM_RELEASE_PLURAL,
                body,
            )
            self._log.info("created_helm_release", name=name, namespace=ns)
            return HelmReleaseSummary.from_k8s_object(result)
        except Exception as e:
            self._handle_api_error(e, "HelmRelease", name, ns)

    def delete_helm_release(
        self,
        name: str,
        namespace: str | None = None,
    ) -> None:
        """Delete a Flux HelmRelease.

        Args:
            name: HelmRelease name to delete.
            namespace: Target namespace (defaults to flux-system).
        """
        ns = namespace or FLUX_NAMESPACE
        self._log.debug("deleting_helm_release", name=name, namespace=ns)
        try:
            self._client.custom_objects.delete_namespaced_custom_object(
                HELM_GROUP,
                HELM_VERSION,
                ns,
                HELM_RELEASE_PLURAL,
                name,
            )
            self._log.info("deleted_helm_release", name=name, namespace=ns)
        except Exception as e:
            self._handle_api_error(e, "HelmRelease", name, ns)

    def suspend_helm_release(
        self,
        name: str,
        namespace: str | None = None,
    ) -> dict[str, Any]:
        """Suspend reconciliation of a Flux HelmRelease.

        Args:
            name: HelmRelease name.
            namespace: Target namespace (defaults to flux-system).

        Returns:
            Dict with operation details.
        """
        ns = namespace or FLUX_NAMESPACE
        self._log.debug("suspending_helm_release", name=name, namespace=ns)
        try:
            patch: dict[str, Any] = {"spec": {"suspend": True}}
            self._client.custom_objects.patch_namespaced_custom_object(
                HELM_GROUP,
                HELM_VERSION,
                ns,
                HELM_RELEASE_PLURAL,
                name,
                patch,
            )
            self._log.info("suspended_helm_release", name=name, namespace=ns)
            return {"name": name, "namespace": ns, "suspended": True}
        except Exception as e:
            self._handle_api_error(e, "HelmRelease", name, ns)

    def resume_helm_release(
        self,
        name: str,
        namespace: str | None = None,
    ) -> dict[str, Any]:
        """Resume reconciliation of a Flux HelmRelease.

        Args:
            name: HelmRelease name.
            namespace: Target namespace (defaults to flux-system).

        Returns:
            Dict with operation details.
        """
        ns = namespace or FLUX_NAMESPACE
        self._log.debug("resuming_helm_release", name=name, namespace=ns)
        try:
            patch: dict[str, Any] = {"spec": {"suspend": False}}
            self._client.custom_objects.patch_namespaced_custom_object(
                HELM_GROUP,
                HELM_VERSION,
                ns,
                HELM_RELEASE_PLURAL,
                name,
                patch,
            )
            self._log.info("resumed_helm_release", name=name, namespace=ns)
            return {"name": name, "namespace": ns, "suspended": False}
        except Exception as e:
            self._handle_api_error(e, "HelmRelease", name, ns)

    def reconcile_helm_release(
        self,
        name: str,
        namespace: str | None = None,
    ) -> dict[str, Any]:
        """Trigger reconciliation of a Flux HelmRelease.

        Args:
            name: HelmRelease name.
            namespace: Target namespace (defaults to flux-system).

        Returns:
            Dict with operation details.
        """
        ns = namespace or FLUX_NAMESPACE
        requested_at = datetime.now(UTC).isoformat()
        self._log.debug("reconciling_helm_release", name=name, namespace=ns)
        try:
            patch: dict[str, Any] = {
                "metadata": {
                    "annotations": {RECONCILE_ANNOTATION: requested_at},
                },
            }
            self._client.custom_objects.patch_namespaced_custom_object(
                HELM_GROUP,
                HELM_VERSION,
                ns,
                HELM_RELEASE_PLURAL,
                name,
                patch,
            )
            self._log.info("reconciled_helm_release", name=name, namespace=ns)
            return {"name": name, "namespace": ns, "requested_at": requested_at}
        except Exception as e:
            self._handle_api_error(e, "HelmRelease", name, ns)

    def get_helm_release_status(
        self,
        name: str,
        namespace: str | None = None,
    ) -> dict[str, Any]:
        """Get detailed status for a Flux HelmRelease.

        Args:
            name: HelmRelease name.
            namespace: Target namespace (defaults to flux-system).

        Returns:
            Dict with status details including conditions and history.
        """
        ns = namespace or FLUX_NAMESPACE
        self._log.debug("getting_helm_release_status", name=name, namespace=ns)
        try:
            result = self._client.custom_objects.get_namespaced_custom_object(
                HELM_GROUP,
                HELM_VERSION,
                ns,
                HELM_RELEASE_PLURAL,
                name,
            )
            status: dict[str, Any] = result.get("status", {})

            return {
                "name": name,
                "namespace": ns,
                "conditions": status.get("conditions", []),
                "last_applied_revision": status.get("lastAppliedRevision"),
                "last_attempted_revision": status.get("lastAttemptedRevision"),
                "last_handled_reconcile_at": status.get("lastHandledReconcileAt"),
                "observed_generation": status.get("observedGeneration"),
                "history": status.get("history", []),
            }
        except Exception as e:
            self._handle_api_error(e, "HelmRelease", name, ns)
