"""Helm manager for chart and release operations.

Orchestrates Helm CLI operations with namespace resolution,
structured logging, and error translation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from system_operations_manager.integrations.kubernetes.helm_client import HelmClient
from system_operations_manager.integrations.kubernetes.models.helm import (
    HelmChart,
    HelmCommandResult,
    HelmRelease,
    HelmReleaseHistory,
    HelmReleaseStatus,
    HelmRepo,
    HelmTemplateResult,
)
from system_operations_manager.services.kubernetes.base import K8sBaseManager

if TYPE_CHECKING:
    from system_operations_manager.integrations.kubernetes.client import KubernetesClient


class HelmManager(K8sBaseManager):
    """Manager for Helm chart and release operations.

    Wraps HelmClient with namespace resolution and structured logging.
    """

    _entity_name: str = "helm"

    def __init__(
        self,
        client: KubernetesClient,
        helm_client: HelmClient | None = None,
    ) -> None:
        """Initialize Helm manager.

        Args:
            client: Kubernetes API client.
            helm_client: Optional HelmClient (auto-created if None).
        """
        super().__init__(client)
        self._helm = helm_client or HelmClient()

    # -----------------------------------------------------------------------
    # Release management
    # -----------------------------------------------------------------------

    def install(
        self,
        release_name: str,
        chart: str,
        *,
        namespace: str | None = None,
        values_files: list[str] | None = None,
        set_values: list[str] | None = None,
        version: str | None = None,
        create_namespace: bool = False,
        wait: bool = False,
        timeout: str | None = None,
        dry_run: bool = False,
    ) -> HelmCommandResult:
        """Install a Helm chart.

        Args:
            release_name: Name for the release.
            chart: Chart reference (repo/chart, path, or URL).
            namespace: Target namespace (defaults to config namespace).
            values_files: Paths to values YAML files.
            set_values: Individual value overrides (key=value).
            version: Chart version constraint.
            create_namespace: Create namespace if it doesn't exist.
            wait: Wait for resources to be ready.
            timeout: Timeout for --wait.
            dry_run: Simulate the install.

        Returns:
            Command result.
        """
        ns = self._resolve_namespace(namespace)
        self._log.info(
            "installing_helm_chart",
            release=release_name,
            chart=chart,
            namespace=ns,
            dry_run=dry_run,
        )

        return self._helm.install(
            release_name,
            chart,
            namespace=ns,
            values_files=values_files,
            set_values=set_values,
            version=version,
            create_namespace=create_namespace,
            wait=wait,
            timeout=timeout,
            dry_run=dry_run,
        )

    def upgrade(
        self,
        release_name: str,
        chart: str,
        *,
        namespace: str | None = None,
        values_files: list[str] | None = None,
        set_values: list[str] | None = None,
        version: str | None = None,
        install: bool = False,
        create_namespace: bool = False,
        wait: bool = False,
        timeout: str | None = None,
        dry_run: bool = False,
        reuse_values: bool = False,
        reset_values: bool = False,
    ) -> HelmCommandResult:
        """Upgrade a Helm release.

        Args:
            release_name: Name of the release.
            chart: Chart reference.
            namespace: Target namespace.
            values_files: Paths to values YAML files.
            set_values: Individual value overrides.
            version: Chart version constraint.
            install: Install if release doesn't exist.
            create_namespace: Create namespace if needed.
            wait: Wait for resources to be ready.
            timeout: Timeout for --wait.
            dry_run: Simulate the upgrade.
            reuse_values: Reuse the last release's values.
            reset_values: Reset values to chart defaults.

        Returns:
            Command result.
        """
        ns = self._resolve_namespace(namespace)
        self._log.info(
            "upgrading_helm_release",
            release=release_name,
            chart=chart,
            namespace=ns,
            dry_run=dry_run,
        )

        return self._helm.upgrade(
            release_name,
            chart,
            namespace=ns,
            values_files=values_files,
            set_values=set_values,
            version=version,
            install=install,
            create_namespace=create_namespace,
            wait=wait,
            timeout=timeout,
            dry_run=dry_run,
            reuse_values=reuse_values,
            reset_values=reset_values,
        )

    def rollback(
        self,
        release_name: str,
        revision: int | None = None,
        *,
        namespace: str | None = None,
        wait: bool = False,
        timeout: str | None = None,
        dry_run: bool = False,
    ) -> HelmCommandResult:
        """Rollback a release to a previous revision.

        Args:
            release_name: Name of the release.
            revision: Revision to roll back to (default: previous).
            namespace: Target namespace.
            wait: Wait for resources to be ready.
            timeout: Timeout for --wait.
            dry_run: Simulate the rollback.

        Returns:
            Command result.
        """
        ns = self._resolve_namespace(namespace)
        self._log.info(
            "rolling_back_helm_release",
            release=release_name,
            revision=revision,
            namespace=ns,
        )

        return self._helm.rollback(
            release_name,
            revision,
            namespace=ns,
            wait=wait,
            timeout=timeout,
            dry_run=dry_run,
        )

    def uninstall(
        self,
        release_name: str,
        *,
        namespace: str | None = None,
        keep_history: bool = False,
        dry_run: bool = False,
    ) -> HelmCommandResult:
        """Uninstall a release.

        Args:
            release_name: Name of the release.
            namespace: Target namespace.
            keep_history: Keep release history.
            dry_run: Simulate the uninstall.

        Returns:
            Command result.
        """
        ns = self._resolve_namespace(namespace)
        self._log.info(
            "uninstalling_helm_release",
            release=release_name,
            namespace=ns,
            dry_run=dry_run,
        )

        return self._helm.uninstall(
            release_name,
            namespace=ns,
            keep_history=keep_history,
            dry_run=dry_run,
        )

    def list_releases(
        self,
        *,
        namespace: str | None = None,
        all_namespaces: bool = False,
        all_releases: bool = False,
        filter_pattern: str | None = None,
    ) -> list[HelmRelease]:
        """List Helm releases.

        Args:
            namespace: Namespace to list releases from.
            all_namespaces: List across all namespaces.
            all_releases: Include releases in all states.
            filter_pattern: Filter by name pattern.

        Returns:
            List of releases.
        """
        ns = None if all_namespaces else self._resolve_namespace(namespace)
        self._log.debug(
            "listing_helm_releases",
            namespace=ns,
            all_namespaces=all_namespaces,
        )

        return self._helm.list_releases(
            namespace=ns,
            all_namespaces=all_namespaces,
            all_releases=all_releases,
            filter_pattern=filter_pattern,
        )

    def history(
        self,
        release_name: str,
        *,
        namespace: str | None = None,
        max_revisions: int | None = None,
    ) -> list[HelmReleaseHistory]:
        """Get release history.

        Args:
            release_name: Name of the release.
            namespace: Target namespace.
            max_revisions: Maximum revisions to return.

        Returns:
            List of revision history entries.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("getting_helm_history", release=release_name, namespace=ns)

        return self._helm.history(
            release_name,
            namespace=ns,
            max_revisions=max_revisions,
        )

    def status(
        self,
        release_name: str,
        *,
        namespace: str | None = None,
        revision: int | None = None,
    ) -> HelmReleaseStatus:
        """Get release status.

        Args:
            release_name: Name of the release.
            namespace: Target namespace.
            revision: Specific revision to inspect.

        Returns:
            Release status details.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("getting_helm_status", release=release_name, namespace=ns)

        return self._helm.status(
            release_name,
            namespace=ns,
            revision=revision,
        )

    def get_values(
        self,
        release_name: str,
        *,
        namespace: str | None = None,
        all_values: bool = False,
        revision: int | None = None,
    ) -> str:
        """Get values for a release.

        Args:
            release_name: Name of the release.
            namespace: Target namespace.
            all_values: Include chart defaults.
            revision: Specific revision to inspect.

        Returns:
            YAML string of values.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("getting_helm_values", release=release_name, namespace=ns)

        return self._helm.get_values(
            release_name,
            namespace=ns,
            all_values=all_values,
            revision=revision,
        )

    # -----------------------------------------------------------------------
    # Repository management
    # -----------------------------------------------------------------------

    def repo_add(
        self,
        name: str,
        url: str,
        *,
        force_update: bool = False,
    ) -> HelmCommandResult:
        """Add a chart repository.

        Args:
            name: Repository name.
            url: Repository URL.
            force_update: Replace existing repo.

        Returns:
            Command result.
        """
        self._log.info("adding_helm_repo", name=name, url=url)
        return self._helm.repo_add(name, url, force_update=force_update)

    def repo_list(self) -> list[HelmRepo]:
        """List configured chart repositories.

        Returns:
            List of repositories.
        """
        self._log.debug("listing_helm_repos")
        return self._helm.repo_list()

    def repo_update(self, names: list[str] | None = None) -> HelmCommandResult:
        """Update chart repository indexes.

        Args:
            names: Specific repos to update (all if None).

        Returns:
            Command result.
        """
        self._log.info("updating_helm_repos", repos=names or "all")
        return self._helm.repo_update(names)

    def repo_remove(self, name: str) -> HelmCommandResult:
        """Remove a chart repository.

        Args:
            name: Repository name.

        Returns:
            Command result.
        """
        self._log.info("removing_helm_repo", name=name)
        return self._helm.repo_remove(name)

    # -----------------------------------------------------------------------
    # Template / Search
    # -----------------------------------------------------------------------

    def template(
        self,
        release_name: str,
        chart: str,
        *,
        namespace: str | None = None,
        values_files: list[str] | None = None,
        set_values: list[str] | None = None,
        version: str | None = None,
    ) -> HelmTemplateResult:
        """Render chart templates locally.

        Args:
            release_name: Release name for rendering.
            chart: Chart reference.
            namespace: Target namespace.
            values_files: Paths to values YAML files.
            set_values: Individual value overrides.
            version: Chart version constraint.

        Returns:
            Template result with rendered YAML.
        """
        ns = self._resolve_namespace(namespace)
        self._log.debug("rendering_helm_template", release=release_name, chart=chart)

        return self._helm.template(
            release_name,
            chart,
            namespace=ns,
            values_files=values_files,
            set_values=set_values,
            version=version,
        )

    def search_repo(
        self,
        keyword: str,
        *,
        version: str | None = None,
        all_versions: bool = False,
    ) -> list[HelmChart]:
        """Search chart repositories.

        Args:
            keyword: Search keyword.
            version: Chart version constraint.
            all_versions: Show all versions.

        Returns:
            List of matching charts.
        """
        self._log.debug("searching_helm_repos", keyword=keyword)
        return self._helm.search_repo(
            keyword,
            version=version,
            all_versions=all_versions,
        )
