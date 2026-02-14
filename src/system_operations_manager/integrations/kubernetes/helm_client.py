"""Helm CLI wrapper for chart and release management.

Wraps the helm binary via subprocess for install, upgrade, rollback,
list, uninstall, repo, template, and search operations.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import structlog

from system_operations_manager.integrations.kubernetes.exceptions import KubernetesError
from system_operations_manager.integrations.kubernetes.models.helm import (
    HelmChart,
    HelmCommandResult,
    HelmRelease,
    HelmReleaseHistory,
    HelmReleaseStatus,
    HelmRepo,
    HelmTemplateResult,
)

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HELM_TIMEOUT_SECONDS = 300
VERSION_TIMEOUT_SECONDS = 10
SHORT_TIMEOUT_SECONDS = 30


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class HelmError(KubernetesError):
    """Base exception for Helm operations."""

    def __init__(
        self,
        message: str,
        stderr: str | None = None,
    ) -> None:
        super().__init__(message=message)
        self.stderr = stderr


class HelmBinaryNotFoundError(HelmError):
    """Raised when helm binary is not found in PATH."""

    def __init__(self) -> None:
        super().__init__(
            message=(
                "helm binary not found in PATH. Install from: https://helm.sh/docs/intro/install/"
            ),
        )


class HelmCommandError(HelmError):
    """Raised when a helm command fails."""


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class HelmClient:
    """Client for interacting with the Helm CLI.

    Wraps helm binary execution and provides typed results.
    """

    def __init__(self, binary_path: str | None = None) -> None:
        """Initialize Helm client.

        Args:
            binary_path: Optional explicit path to helm binary.
                If None, searches PATH.

        Raises:
            HelmBinaryNotFoundError: If binary not found.
        """
        self._binary = self._find_binary(binary_path)
        self._log = logger.bind(binary=self._binary)
        self._log.debug("helm_client_initialized")

    @staticmethod
    def _find_binary(binary_path: str | None) -> str:
        """Locate helm binary.

        Args:
            binary_path: Explicit path or None to search PATH.

        Returns:
            Path to helm binary.

        Raises:
            HelmBinaryNotFoundError: If not found.
        """
        if binary_path:
            path = Path(binary_path)
            if not path.exists():
                raise HelmBinaryNotFoundError()
            return str(path.resolve())

        found = shutil.which("helm")
        if not found:
            raise HelmBinaryNotFoundError()

        return found

    def _run(
        self,
        args: list[str],
        *,
        timeout: int = HELM_TIMEOUT_SECONDS,
    ) -> subprocess.CompletedProcess[str]:
        """Run a helm command.

        Args:
            args: Command arguments (without the ``helm`` prefix).
            timeout: Timeout in seconds.

        Returns:
            CompletedProcess result.

        Raises:
            HelmCommandError: On non-zero exit.
            HelmError: On timeout.
        """
        cmd = [self._binary, *args]
        self._log.debug("running_helm_command", args=args)

        try:
            return subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=timeout,
            )
        except subprocess.CalledProcessError as e:
            raise HelmCommandError(
                message=f"Helm command failed: {e.stderr.strip() if e.stderr else f'exit code {e.returncode}'}",
                stderr=e.stderr,
            ) from e
        except subprocess.TimeoutExpired as e:
            raise HelmError(
                message=f"Helm command timed out after {timeout}s",
            ) from e

    # -----------------------------------------------------------------------
    # Version
    # -----------------------------------------------------------------------

    def get_version(self) -> str:
        """Get helm version string.

        Returns:
            Version string (e.g., ``v3.17.0``).

        Raises:
            HelmError: If version command fails.
        """
        result = self._run(["version", "--short"], timeout=VERSION_TIMEOUT_SECONDS)
        version = result.stdout.strip()
        # Strip build metadata (e.g., "v3.17.0+g301108e" -> "v3.17.0")
        if "+" in version:
            version = version.split("+")[0]
        return version

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
            namespace: Target Kubernetes namespace.
            values_files: Paths to values YAML files.
            set_values: Individual value overrides (key=value).
            version: Chart version constraint.
            create_namespace: Create namespace if it doesn't exist.
            wait: Wait for resources to be ready.
            timeout: Timeout for --wait (e.g., ``5m0s``).
            dry_run: Simulate the install.

        Returns:
            Command result.
        """
        args = ["install", release_name, chart]
        args.extend(
            self._build_common_args(
                namespace=namespace,
                values_files=values_files,
                set_values=set_values,
                version=version,
                wait=wait,
                timeout=timeout,
                dry_run=dry_run,
            )
        )
        if create_namespace:
            args.append("--create-namespace")

        result = self._run(args)
        self._log.info("helm_install_success", release=release_name, chart=chart)
        return HelmCommandResult(success=True, stdout=result.stdout, stderr=result.stderr)

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
            install: Install if release doesn't exist (--install).
            create_namespace: Create namespace if needed.
            wait: Wait for resources to be ready.
            timeout: Timeout for --wait.
            dry_run: Simulate the upgrade.
            reuse_values: Reuse the last release's values.
            reset_values: Reset values to chart defaults.

        Returns:
            Command result.
        """
        args = ["upgrade", release_name, chart]
        args.extend(
            self._build_common_args(
                namespace=namespace,
                values_files=values_files,
                set_values=set_values,
                version=version,
                wait=wait,
                timeout=timeout,
                dry_run=dry_run,
            )
        )
        if install:
            args.append("--install")
        if create_namespace:
            args.append("--create-namespace")
        if reuse_values:
            args.append("--reuse-values")
        if reset_values:
            args.append("--reset-values")

        result = self._run(args)
        self._log.info("helm_upgrade_success", release=release_name, chart=chart)
        return HelmCommandResult(success=True, stdout=result.stdout, stderr=result.stderr)

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
        args = ["rollback", release_name]
        if revision is not None:
            args.append(str(revision))
        if namespace:
            args.extend(["--namespace", namespace])
        if wait:
            args.append("--wait")
        if timeout:
            args.extend(["--timeout", timeout])
        if dry_run:
            args.append("--dry-run")

        result = self._run(args)
        self._log.info("helm_rollback_success", release=release_name, revision=revision)
        return HelmCommandResult(success=True, stdout=result.stdout, stderr=result.stderr)

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
        args = ["uninstall", release_name]
        if namespace:
            args.extend(["--namespace", namespace])
        if keep_history:
            args.append("--keep-history")
        if dry_run:
            args.append("--dry-run")

        result = self._run(args)
        self._log.info("helm_uninstall_success", release=release_name)
        return HelmCommandResult(success=True, stdout=result.stdout, stderr=result.stderr)

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
            all_namespaces: List releases across all namespaces.
            all_releases: Include releases in all states.
            filter_pattern: Filter releases by name pattern.

        Returns:
            List of releases.
        """
        args = ["list", "--output", "json"]
        if all_namespaces:
            args.append("--all-namespaces")
        elif namespace:
            args.extend(["--namespace", namespace])
        if all_releases:
            args.append("--all")
        if filter_pattern:
            args.extend(["--filter", filter_pattern])

        result = self._run(args, timeout=SHORT_TIMEOUT_SECONDS)
        data = json.loads(result.stdout) if result.stdout.strip() else []
        return [HelmRelease.from_json(entry) for entry in data]

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
            max_revisions: Maximum number of revisions to return.

        Returns:
            List of revision history entries.
        """
        args = ["history", release_name, "--output", "json"]
        if namespace:
            args.extend(["--namespace", namespace])
        if max_revisions is not None:
            args.extend(["--max", str(max_revisions)])

        result = self._run(args, timeout=SHORT_TIMEOUT_SECONDS)
        data = json.loads(result.stdout) if result.stdout.strip() else []
        return [HelmReleaseHistory.from_json(entry) for entry in data]

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
        args = ["status", release_name, "--output", "json"]
        if namespace:
            args.extend(["--namespace", namespace])
        if revision is not None:
            args.extend(["--revision", str(revision)])

        result = self._run(args, timeout=SHORT_TIMEOUT_SECONDS)
        data = json.loads(result.stdout)
        info = data.get("info", {})

        return HelmReleaseStatus(
            name=data.get("name", release_name),
            namespace=data.get("namespace", namespace or ""),
            revision=int(data.get("version", 0)),
            status=info.get("status", ""),
            description=info.get("description", ""),
            notes=info.get("notes", ""),
            raw=result.stdout,
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
            all_values: Show all values (including chart defaults).
            revision: Specific revision to inspect.

        Returns:
            YAML string of values.
        """
        args = ["get", "values", release_name, "--output", "yaml"]
        if namespace:
            args.extend(["--namespace", namespace])
        if all_values:
            args.append("--all")
        if revision is not None:
            args.extend(["--revision", str(revision)])

        result = self._run(args, timeout=SHORT_TIMEOUT_SECONDS)
        return result.stdout

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
            force_update: Replace existing repo with same name.

        Returns:
            Command result.
        """
        args = ["repo", "add", name, url]
        if force_update:
            args.append("--force-update")

        result = self._run(args, timeout=SHORT_TIMEOUT_SECONDS)
        self._log.info("helm_repo_added", name=name, url=url)
        return HelmCommandResult(success=True, stdout=result.stdout, stderr=result.stderr)

    def repo_list(self) -> list[HelmRepo]:
        """List configured chart repositories.

        Returns:
            List of repositories.
        """
        args = ["repo", "list", "--output", "json"]

        result = self._run(args, timeout=SHORT_TIMEOUT_SECONDS)
        data = json.loads(result.stdout) if result.stdout.strip() else []
        return [HelmRepo.from_json(entry) for entry in data]

    def repo_update(self, names: list[str] | None = None) -> HelmCommandResult:
        """Update chart repository indexes.

        Args:
            names: Specific repos to update (all if None).

        Returns:
            Command result.
        """
        args = ["repo", "update"]
        if names:
            args.extend(names)

        result = self._run(args, timeout=SHORT_TIMEOUT_SECONDS)
        self._log.info("helm_repo_updated", repos=names or "all")
        return HelmCommandResult(success=True, stdout=result.stdout, stderr=result.stderr)

    def repo_remove(self, name: str) -> HelmCommandResult:
        """Remove a chart repository.

        Args:
            name: Repository name.

        Returns:
            Command result.
        """
        args = ["repo", "remove", name]

        result = self._run(args, timeout=SHORT_TIMEOUT_SECONDS)
        self._log.info("helm_repo_removed", name=name)
        return HelmCommandResult(success=True, stdout=result.stdout, stderr=result.stderr)

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
            release_name: Release name for template rendering.
            chart: Chart reference.
            namespace: Target namespace.
            values_files: Paths to values YAML files.
            set_values: Individual value overrides.
            version: Chart version constraint.

        Returns:
            Template result with rendered YAML.
        """
        args = ["template", release_name, chart]
        if namespace:
            args.extend(["--namespace", namespace])
        if version:
            args.extend(["--version", version])
        if values_files:
            for f in values_files:
                args.extend(["--values", f])
        if set_values:
            for v in set_values:
                args.extend(["--set", v])

        try:
            result = self._run(args)
            return HelmTemplateResult(
                rendered_yaml=result.stdout,
                success=True,
            )
        except HelmCommandError as e:
            return HelmTemplateResult(
                rendered_yaml="",
                success=False,
                error=e.message,
            )

    def search_repo(
        self,
        keyword: str,
        *,
        version: str | None = None,
        all_versions: bool = False,
    ) -> list[HelmChart]:
        """Search chart repositories for a keyword.

        Args:
            keyword: Search keyword.
            version: Chart version constraint.
            all_versions: Show all versions, not just latest.

        Returns:
            List of matching charts.
        """
        args = ["search", "repo", keyword, "--output", "json"]
        if version:
            args.extend(["--version", version])
        if all_versions:
            args.append("--versions")

        result = self._run(args, timeout=SHORT_TIMEOUT_SECONDS)
        data = json.loads(result.stdout) if result.stdout.strip() else []
        return [HelmChart.from_json(entry) for entry in data]

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    @staticmethod
    def _build_common_args(
        *,
        namespace: str | None = None,
        values_files: list[str] | None = None,
        set_values: list[str] | None = None,
        version: str | None = None,
        wait: bool = False,
        timeout: str | None = None,
        dry_run: bool = False,
    ) -> list[str]:
        """Build common Helm CLI arguments.

        Returns:
            List of CLI argument strings.
        """
        args: list[str] = []
        if namespace:
            args.extend(["--namespace", namespace])
        if version:
            args.extend(["--version", version])
        if values_files:
            for f in values_files:
                args.extend(["--values", f])
        if set_values:
            for v in set_values:
                args.extend(["--set", v])
        if wait:
            args.append("--wait")
        if timeout:
            args.extend(["--timeout", timeout])
        if dry_run:
            args.append("--dry-run")
        return args
