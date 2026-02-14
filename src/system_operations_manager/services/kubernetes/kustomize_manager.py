"""Kustomize manager for Kubernetes manifest operations.

Orchestrates kustomize build operations and delegates to ManifestManager
for apply/diff/validate operations on the rendered output.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from system_operations_manager.integrations.kubernetes.kustomize_client import (
    KUSTOMIZATION_FILENAMES,
    KustomizeClient,
    KustomizeError,
)
from system_operations_manager.services.kubernetes.base import K8sBaseManager

if TYPE_CHECKING:
    from system_operations_manager.integrations.kubernetes.client import KubernetesClient
    from system_operations_manager.services.kubernetes.manifest_manager import (
        ApplyResult,
        DiffResult,
        ManifestManager,
    )


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass
class OverlayInfo:
    """Information about a Kustomize overlay directory."""

    name: str
    path: str
    valid: bool
    error: str | None = None
    resources: list[str] = field(default_factory=list)


@dataclass
class KustomizeBuildOutput:
    """Result of building a kustomization."""

    path: str
    rendered_yaml: str
    success: bool
    error: str | None = None
    output_file: str | None = None


# ---------------------------------------------------------------------------
# KustomizeManager
# ---------------------------------------------------------------------------


class KustomizeManager(K8sBaseManager):
    """Manager for Kustomize operations.

    Handles building kustomizations and delegates to ManifestManager
    for cluster operations (apply, diff).
    """

    _entity_name: str = "kustomize"

    def __init__(
        self,
        client: KubernetesClient,
        kustomize_client: KustomizeClient | None = None,
    ) -> None:
        """Initialize Kustomize manager.

        Args:
            client: Kubernetes API client.
            kustomize_client: Optional KustomizeClient (auto-created if None).
        """
        super().__init__(client)
        self._kustomize = kustomize_client or KustomizeClient()
        self._manifest_manager: ManifestManager | None = None

    def _get_manifest_manager(self) -> ManifestManager:
        """Lazy-load ManifestManager to avoid circular imports."""
        if self._manifest_manager is None:
            from system_operations_manager.services.kubernetes.manifest_manager import (
                ManifestManager,
            )

            self._manifest_manager = ManifestManager(self._client)
        return self._manifest_manager

    # -----------------------------------------------------------------------
    # Build
    # -----------------------------------------------------------------------

    def build(
        self,
        path: Path,
        *,
        enable_helm: bool = False,
        enable_alpha_plugins: bool = False,
        output_file: Path | None = None,
    ) -> KustomizeBuildOutput:
        """Build kustomization and render manifests.

        Args:
            path: Directory containing kustomization.yaml.
            enable_helm: Enable Helm chart inflation.
            enable_alpha_plugins: Enable alpha plugins.
            output_file: Optional file to write rendered YAML.

        Returns:
            Build output with rendered YAML.
        """
        self._log.debug("building_kustomization", path=str(path))

        result = self._kustomize.build(
            path,
            enable_helm=enable_helm,
            enable_alpha_plugins=enable_alpha_plugins,
        )

        if not result.success:
            self._log.error("kustomize_build_failed", path=str(path), error=result.error)
            return KustomizeBuildOutput(
                path=str(path),
                rendered_yaml="",
                success=False,
                error=result.error,
            )

        output_path: str | None = None
        if output_file:
            try:
                output_file.write_text(result.rendered_yaml, encoding="utf-8")
                output_path = str(output_file)
                self._log.info("wrote_kustomize_output", file=output_path)
            except OSError as e:
                self._log.error("failed_to_write_output", file=str(output_file), error=str(e))
                return KustomizeBuildOutput(
                    path=str(path),
                    rendered_yaml=result.rendered_yaml,
                    success=False,
                    error=f"Failed to write output: {e}",
                )

        self._log.info("kustomize_build_success", path=str(path))
        return KustomizeBuildOutput(
            path=str(path),
            rendered_yaml=result.rendered_yaml,
            success=True,
            output_file=output_path,
        )

    # -----------------------------------------------------------------------
    # Apply
    # -----------------------------------------------------------------------

    def apply(
        self,
        path: Path,
        namespace: str | None = None,
        *,
        dry_run: bool = False,
        server_dry_run: bool = False,
        force: bool = False,
        enable_helm: bool = False,
    ) -> list[ApplyResult]:
        """Build kustomization and apply to cluster.

        Runs ``kustomize build`` then delegates to ManifestManager
        for applying the rendered manifests.

        Args:
            path: Path to kustomization directory.
            namespace: Override namespace for all resources.
            dry_run: Client-side dry run.
            server_dry_run: Server-side dry run.
            force: Skip validation errors.
            enable_helm: Enable Helm chart inflation.

        Returns:
            List of apply results (one per resource).
        """
        build_result = self.build(path, enable_helm=enable_helm)
        if not build_result.success:
            from system_operations_manager.services.kubernetes.manifest_manager import ApplyResult

            return [
                ApplyResult(
                    resource="kustomization",
                    action="failed",
                    namespace=namespace or self._resolve_namespace(None),
                    success=False,
                    message=build_result.error or "Build failed",
                )
            ]

        manifests = self._parse_rendered_yaml(build_result.rendered_yaml, str(path))
        manager = self._get_manifest_manager()
        return manager.apply_manifests(
            manifests,
            namespace=namespace,
            dry_run=dry_run,
            server_dry_run=server_dry_run,
            force=force,
        )

    # -----------------------------------------------------------------------
    # Diff
    # -----------------------------------------------------------------------

    def diff(
        self,
        path: Path,
        namespace: str | None = None,
        *,
        enable_helm: bool = False,
    ) -> list[DiffResult]:
        """Build kustomization and diff against cluster.

        Runs ``kustomize build`` then delegates to ManifestManager
        for diffing each resource against live cluster state.

        Args:
            path: Path to kustomization directory.
            namespace: Override namespace.
            enable_helm: Enable Helm chart inflation.

        Returns:
            List of diff results (one per resource).
        """
        build_result = self.build(path, enable_helm=enable_helm)
        if not build_result.success:
            from system_operations_manager.services.kubernetes.manifest_manager import DiffResult

            return [
                DiffResult(
                    resource="kustomization",
                    namespace=namespace or self._resolve_namespace(None),
                    diff=f"Build error: {build_result.error}",
                    exists_on_cluster=False,
                    identical=False,
                )
            ]

        manifests = self._parse_rendered_yaml(build_result.rendered_yaml, str(path))
        manager = self._get_manifest_manager()
        return manager.diff_manifests(manifests, namespace=namespace)

    # -----------------------------------------------------------------------
    # Validate
    # -----------------------------------------------------------------------

    def validate(self, path: Path) -> tuple[bool, str | None]:
        """Validate kustomization directory.

        Checks for kustomization.yaml and attempts a build.

        Args:
            path: Path to kustomization directory.

        Returns:
            Tuple of (is_valid, error_message).
        """
        return self._kustomize.validate_kustomization(path)

    # -----------------------------------------------------------------------
    # Overlay discovery
    # -----------------------------------------------------------------------

    def list_overlays(self, base_path: Path) -> list[OverlayInfo]:
        """Discover Kustomize overlays in a directory structure.

        Searches for directories containing kustomization files.
        Common layout: ``base/``, ``overlays/{dev,staging,prod}/``.

        Args:
            base_path: Root directory to search.

        Returns:
            List of discovered overlay information.
        """
        if not base_path.exists() or not base_path.is_dir():
            self._log.warning("overlay_discovery_failed", path=str(base_path))
            return []

        overlays: list[OverlayInfo] = []
        seen: set[str] = set()

        # Check base_path itself
        self._maybe_add_overlay(base_path, overlays, seen)

        # Check base/ subdirectory
        base_dir = base_path / "base"
        if base_dir.is_dir():
            self._maybe_add_overlay(base_dir, overlays, seen)

        # Check overlays/ subdirectory
        overlays_dir = base_path / "overlays"
        if overlays_dir.is_dir():
            for subdir in sorted(overlays_dir.iterdir()):
                if subdir.is_dir():
                    self._maybe_add_overlay(subdir, overlays, seen)

        self._log.info("discovered_overlays", count=len(overlays), path=str(base_path))
        return overlays

    def _maybe_add_overlay(
        self,
        directory: Path,
        overlays: list[OverlayInfo],
        seen: set[str],
    ) -> None:
        """Add a directory as an overlay if it contains a kustomization file."""
        resolved = str(directory.resolve())
        if resolved in seen:
            return
        if not self._has_kustomization_file(directory):
            return

        seen.add(resolved)
        valid, error = self._kustomize.validate_kustomization(directory)

        resources: list[str] = []
        if valid:
            try:
                build = self._kustomize.build(directory)
                if build.success:
                    manifests = self._parse_rendered_yaml(build.rendered_yaml, str(directory))
                    resources = [
                        f"{m.get('kind', 'Unknown')}/{m.get('metadata', {}).get('name', 'unnamed')}"
                        for m in manifests
                    ]
            except Exception:
                self._log.warning("overlay_resource_extraction_failed", path=str(directory))

        overlays.append(
            OverlayInfo(
                name=directory.name,
                path=str(directory),
                valid=valid,
                error=error,
                resources=resources,
            )
        )

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    @staticmethod
    def _has_kustomization_file(directory: Path) -> bool:
        """Check if a directory contains a kustomization file."""
        return any((directory / name).exists() for name in KUSTOMIZATION_FILENAMES)

    @staticmethod
    def _parse_rendered_yaml(rendered_yaml: str, source_path: str) -> list[dict[str, Any]]:
        """Parse multi-document YAML output from kustomize build.

        Args:
            rendered_yaml: YAML string from kustomize.
            source_path: Source path for tracking.

        Returns:
            List of manifest dictionaries.

        Raises:
            KustomizeError: If YAML parsing fails.
        """
        from ruamel.yaml import YAML
        from ruamel.yaml.error import YAMLError

        yaml = YAML(typ="safe")
        try:
            documents = list(yaml.load_all(rendered_yaml))
        except YAMLError as e:
            raise KustomizeError(
                message=f"Failed to parse rendered YAML: {e}",
                kustomization_path=source_path,
            ) from e

        manifests: list[dict[str, Any]] = []
        for doc in documents:
            if doc is None:
                continue
            if not isinstance(doc, dict):
                continue
            doc["_source_file"] = source_path
            manifests.append(doc)

        return manifests
