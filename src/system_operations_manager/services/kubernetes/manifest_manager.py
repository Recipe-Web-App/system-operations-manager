"""Kubernetes YAML manifest manager.

Provides load, validate, apply, and diff operations for Kubernetes
YAML manifests (single files, multi-document files, and directories).
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from system_operations_manager.services.kubernetes.base import K8sBaseManager

if TYPE_CHECKING:
    from system_operations_manager.integrations.kubernetes.client import KubernetesClient

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

YAML_EXTENSIONS = (".yaml", ".yml")
REQUIRED_MANIFEST_FIELDS = ("apiVersion", "kind", "metadata")
DIFF_CONTEXT_LINES = 3
SERVER_SIDE_DRY_RUN = "All"
FIELD_MANAGER = "ops-cli"

# Fields added by the Kubernetes API server that should be stripped for diff
SERVER_MANAGED_METADATA_FIELDS = (
    "creationTimestamp",
    "generation",
    "managedFields",
    "resourceVersion",
    "selfLink",
    "uid",
)

# Top-level fields added by the server
SERVER_MANAGED_TOP_LEVEL_FIELDS = ("status",)


# ---------------------------------------------------------------------------
# Result Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class ValidationResult:
    """Result of validating a single manifest."""

    file: str
    resource: str
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class ApplyResult:
    """Result of applying a single manifest."""

    resource: str
    action: str
    namespace: str
    success: bool
    message: str


@dataclass
class DiffResult:
    """Result of diffing a single manifest against the cluster."""

    resource: str
    namespace: str
    diff: str
    exists_on_cluster: bool
    identical: bool


# ---------------------------------------------------------------------------
# ManifestManager
# ---------------------------------------------------------------------------


class ManifestManager(K8sBaseManager):
    """Manager for Kubernetes YAML manifest operations.

    Supports loading, validating, applying, and diffing manifests
    from individual YAML files or directories.
    """

    _entity_name: str = "manifest"

    def __init__(self, client: KubernetesClient) -> None:
        super().__init__(client)

    # -----------------------------------------------------------------------
    # Load
    # -----------------------------------------------------------------------

    def load_manifests(self, path: Path) -> list[dict[str, Any]]:
        """Load Kubernetes manifests from a file or directory.

        Handles single files, multi-document YAML files (``---`` separated),
        and recursive directory scanning for ``*.yaml`` / ``*.yml`` files.

        Args:
            path: Path to a YAML file or a directory of manifests.

        Returns:
            A list of parsed manifest dictionaries.

        Raises:
            FileNotFoundError: If *path* does not exist.
            ValueError: If a YAML file cannot be parsed.
        """
        if not path.exists():
            raise FileNotFoundError(f"Manifest path not found: {path}")

        if path.is_file():
            manifests = self._load_file(path)
        elif path.is_dir():
            yaml_files = self._collect_yaml_files(path)
            if not yaml_files:
                self._log.warning("no_yaml_files_found", directory=str(path))
                return []
            manifests = []
            for yaml_file in yaml_files:
                manifests.extend(self._load_file(yaml_file))
        else:
            raise FileNotFoundError(f"Path is neither a file nor a directory: {path}")

        self._log.debug("loaded_manifests", count=len(manifests), path=str(path))
        return manifests

    def _load_file(self, file_path: Path) -> list[dict[str, Any]]:
        """Parse a single YAML file, handling multi-document YAML."""
        from ruamel.yaml import YAML
        from ruamel.yaml.error import YAMLError

        yaml = YAML(typ="safe")
        try:
            content = file_path.read_text(encoding="utf-8")
            documents = list(yaml.load_all(content))
        except YAMLError as e:
            raise ValueError(f"Failed to parse YAML file {file_path}: {e}") from e

        manifests: list[dict[str, Any]] = []
        for doc in documents:
            if doc is None:
                continue
            if not isinstance(doc, dict):
                self._log.warning(
                    "skipping_non_dict_document",
                    file=str(file_path),
                    type=type(doc).__name__,
                )
                continue
            doc["_source_file"] = str(file_path)
            manifests.append(doc)
        return manifests

    def _collect_yaml_files(self, directory: Path) -> list[Path]:
        """Recursively find YAML files in a directory, sorted for determinism."""
        files: list[Path] = []
        for ext in YAML_EXTENSIONS:
            files.extend(directory.rglob(f"*{ext}"))
        return sorted(files)

    # -----------------------------------------------------------------------
    # Validate
    # -----------------------------------------------------------------------

    def validate_manifests(
        self,
        manifests: list[dict[str, Any]],
        source_file: str = "",
    ) -> list[ValidationResult]:
        """Validate manifests client-side (no cluster connection required).

        Checks for required fields: ``apiVersion``, ``kind``,
        ``metadata``, and ``metadata.name``.

        Args:
            manifests: Parsed manifest dicts (from :meth:`load_manifests`).
            source_file: Default source file label for results.

        Returns:
            One :class:`ValidationResult` per manifest.
        """
        results: list[ValidationResult] = []
        for manifest in manifests:
            results.append(self._validate_single(manifest, source_file))
        self._log.debug(
            "validated_manifests",
            total=len(results),
            valid=sum(1 for r in results if r.valid),
        )
        return results

    def _validate_single(
        self,
        manifest: dict[str, Any],
        source_file: str,
    ) -> ValidationResult:
        """Validate a single manifest dictionary."""
        file_label = manifest.get("_source_file", source_file)
        resource_id = self._get_resource_identifier(manifest)
        errors: list[str] = []
        warnings: list[str] = []

        for req_field in REQUIRED_MANIFEST_FIELDS:
            if req_field not in manifest:
                errors.append(f"Missing required field: {req_field}")

        api_version = manifest.get("apiVersion")
        if api_version is not None and not isinstance(api_version, str):
            errors.append(f"apiVersion must be a string, got {type(api_version).__name__}")

        kind = manifest.get("kind")
        if kind is not None and not isinstance(kind, str):
            errors.append(f"kind must be a string, got {type(kind).__name__}")

        metadata = manifest.get("metadata")
        if isinstance(metadata, dict):
            if "name" not in metadata:
                errors.append("Missing required field: metadata.name")
            elif not isinstance(metadata["name"], str):
                errors.append("metadata.name must be a string")
        elif metadata is not None:
            errors.append(f"metadata must be a dict, got {type(metadata).__name__}")

        return ValidationResult(
            file=file_label,
            resource=resource_id,
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    # -----------------------------------------------------------------------
    # Apply
    # -----------------------------------------------------------------------

    def apply_manifests(
        self,
        manifests: list[dict[str, Any]],
        namespace: str | None = None,
        *,
        dry_run: bool = False,
        server_dry_run: bool = False,
        force: bool = False,
    ) -> list[ApplyResult]:
        """Apply manifests to the Kubernetes cluster.

        Uses ``kubernetes.utils.create_from_dict`` for initial creation.
        On 409 Conflict (resource already exists), falls back to a
        server-side apply via the dynamic client.

        Args:
            manifests: Parsed manifest dicts.
            namespace: Override namespace for namespaced resources.
            dry_run: Client-side dry run (skip all API calls).
            server_dry_run: Server-side dry run (``dry_run="All"``).
            force: Passed through for conflict resolution.

        Returns:
            One :class:`ApplyResult` per manifest.
        """
        results: list[ApplyResult] = []
        dry_run_strategy: str | None = None
        if server_dry_run:
            dry_run_strategy = SERVER_SIDE_DRY_RUN

        for manifest in manifests:
            clean = self._strip_source_metadata(manifest)
            ns = (
                namespace
                or clean.get("metadata", {}).get("namespace")
                or self._resolve_namespace(None)
            )
            resource_id = self._get_resource_identifier(clean)

            if dry_run:
                results.append(
                    ApplyResult(
                        resource=resource_id,
                        action="skipped (client dry-run)",
                        namespace=ns,
                        success=True,
                        message="Would apply to cluster",
                    )
                )
                continue

            # Override namespace if provided
            if namespace and "metadata" in clean:
                clean.setdefault("metadata", {})["namespace"] = namespace

            result = self._apply_single(clean, ns, dry_run_strategy=dry_run_strategy)
            results.append(result)

        applied_count = sum(1 for r in results if r.success)
        self._log.info(
            "applied_manifests",
            total=len(results),
            succeeded=applied_count,
            dry_run=dry_run or server_dry_run,
        )
        return results

    def _apply_single(
        self,
        manifest: dict[str, Any],
        namespace: str,
        *,
        dry_run_strategy: str | None,
    ) -> ApplyResult:
        """Apply a single manifest using create-or-patch semantics."""
        from kubernetes import utils
        from kubernetes.client import ApiClient, ApiException

        resource_id = self._get_resource_identifier(manifest)
        api_client = ApiClient()

        try:
            kwargs: dict[str, Any] = {"verbose": False}
            if dry_run_strategy:
                kwargs["namespace"] = namespace
            utils.create_from_dict(api_client, manifest, **kwargs)
            action = "created (server dry-run)" if dry_run_strategy else "created"
            self._log.info(
                "manifest_applied", resource=resource_id, action=action, namespace=namespace
            )
            return ApplyResult(
                resource=resource_id,
                action=action,
                namespace=namespace,
                success=True,
                message="",
            )
        except utils.FailToCreateError as e:
            # Check for 409 Conflict — resource already exists
            for api_exception in e.api_exceptions:
                if api_exception.status == 409:
                    return self._server_side_apply(
                        manifest, namespace, resource_id, dry_run_strategy=dry_run_strategy
                    )
            # Non-conflict errors
            error_msg = "; ".join(str(ex.reason) for ex in e.api_exceptions)
            self._log.error("manifest_apply_failed", resource=resource_id, error=error_msg)
            return ApplyResult(
                resource=resource_id,
                action="failed",
                namespace=namespace,
                success=False,
                message=error_msg,
            )
        except ApiException as e:
            self._log.error("manifest_apply_failed", resource=resource_id, error=str(e.reason))
            return ApplyResult(
                resource=resource_id,
                action="failed",
                namespace=namespace,
                success=False,
                message=str(e.reason),
            )
        except Exception as e:
            self._log.error("manifest_apply_failed", resource=resource_id, error=str(e))
            return ApplyResult(
                resource=resource_id,
                action="failed",
                namespace=namespace,
                success=False,
                message=str(e),
            )

    def _server_side_apply(
        self,
        manifest: dict[str, Any],
        namespace: str,
        resource_id: str,
        *,
        dry_run_strategy: str | None,
    ) -> ApplyResult:
        """Perform server-side apply via the dynamic client for existing resources."""
        try:
            dynamic = self._get_dynamic_client()
            api_version = manifest.get("apiVersion", "")
            kind = manifest.get("kind", "")
            resource_api = dynamic.resources.get(api_version=api_version, kind=kind)

            kwargs: dict[str, Any] = {
                "body": manifest,
                "field_manager": FIELD_MANAGER,
            }
            if namespace:
                kwargs["namespace"] = namespace
            if dry_run_strategy:
                kwargs["dry_run"] = dry_run_strategy

            resource_api.server_side_apply(**kwargs)
            action = "configured (server dry-run)" if dry_run_strategy else "configured"
            self._log.info(
                "manifest_applied", resource=resource_id, action=action, namespace=namespace
            )
            return ApplyResult(
                resource=resource_id,
                action=action,
                namespace=namespace,
                success=True,
                message="",
            )
        except Exception as e:
            self._log.error("manifest_ssa_failed", resource=resource_id, error=str(e))
            return ApplyResult(
                resource=resource_id,
                action="failed",
                namespace=namespace,
                success=False,
                message=str(e),
            )

    # -----------------------------------------------------------------------
    # Diff
    # -----------------------------------------------------------------------

    def diff_manifests(
        self,
        manifests: list[dict[str, Any]],
        namespace: str | None = None,
    ) -> list[DiffResult]:
        """Compare local manifests against live cluster state.

        For each manifest, fetches the live resource from the cluster
        (via the dynamic client), strips server-managed fields, and
        produces a unified diff.

        Args:
            manifests: Parsed manifest dicts.
            namespace: Override namespace.

        Returns:
            One :class:`DiffResult` per manifest.
        """
        results: list[DiffResult] = []
        for manifest in manifests:
            clean = self._strip_source_metadata(manifest)
            ns = (
                namespace
                or clean.get("metadata", {}).get("namespace")
                or self._resolve_namespace(None)
            )
            results.append(self._diff_single(clean, ns))

        changed = sum(1 for r in results if not r.identical)
        self._log.info("diffed_manifests", total=len(results), changed=changed)
        return results

    def _diff_single(self, manifest: dict[str, Any], namespace: str) -> DiffResult:
        """Diff a single manifest against its cluster counterpart."""
        from kubernetes.client import ApiException

        resource_id = self._get_resource_identifier(manifest)
        api_version = manifest.get("apiVersion", "")
        kind = manifest.get("kind", "")
        name = manifest.get("metadata", {}).get("name", "")

        try:
            dynamic = self._get_dynamic_client()
            resource_api = dynamic.resources.get(api_version=api_version, kind=kind)
            live_obj = resource_api.get(name=name, namespace=namespace)
            live_dict = live_obj.to_dict() if hasattr(live_obj, "to_dict") else dict(live_obj)
        except ApiException as e:
            if e.status == 404:
                local_yaml = self._serialize_for_diff(manifest)
                diff_lines = [f"+ {line}" for line in local_yaml.splitlines()]
                return DiffResult(
                    resource=resource_id,
                    namespace=namespace,
                    diff="\n".join(diff_lines),
                    exists_on_cluster=False,
                    identical=False,
                )
            self._log.error("diff_fetch_failed", resource=resource_id, error=str(e.reason))
            return DiffResult(
                resource=resource_id,
                namespace=namespace,
                diff=f"Error fetching resource: {e.reason}",
                exists_on_cluster=False,
                identical=False,
            )
        except Exception as e:
            self._log.error("diff_fetch_failed", resource=resource_id, error=str(e))
            return DiffResult(
                resource=resource_id,
                namespace=namespace,
                diff=f"Error: {e}",
                exists_on_cluster=False,
                identical=False,
            )

        # Strip server-managed fields for a clean comparison
        cleaned_live = self._strip_server_fields(live_dict)
        local_yaml = self._serialize_for_diff(manifest)
        live_yaml = self._serialize_for_diff(cleaned_live)

        if local_yaml == live_yaml:
            return DiffResult(
                resource=resource_id,
                namespace=namespace,
                diff="",
                exists_on_cluster=True,
                identical=True,
            )

        diff_text = "\n".join(
            difflib.unified_diff(
                live_yaml.splitlines(),
                local_yaml.splitlines(),
                fromfile=f"live/{resource_id}",
                tofile=f"local/{resource_id}",
                lineterm="",
                n=DIFF_CONTEXT_LINES,
            )
        )
        return DiffResult(
            resource=resource_id,
            namespace=namespace,
            diff=diff_text,
            exists_on_cluster=True,
            identical=False,
        )

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    @staticmethod
    def _get_resource_identifier(manifest: dict[str, Any]) -> str:
        """Return a ``Kind/name`` identifier for a manifest."""
        kind = manifest.get("kind", "Unknown")
        name = manifest.get("metadata", {}).get("name", "unnamed")
        return f"{kind}/{name}"

    @staticmethod
    def _strip_source_metadata(manifest: dict[str, Any]) -> dict[str, Any]:
        """Return a copy of *manifest* without internal tracking fields."""
        clean = dict(manifest)
        clean.pop("_source_file", None)
        return clean

    def _get_dynamic_client(self) -> Any:
        """Create a ``kubernetes.dynamic.DynamicClient``."""
        from kubernetes.client import ApiClient
        from kubernetes.dynamic import DynamicClient

        return DynamicClient(ApiClient())

    @staticmethod
    def _serialize_for_diff(resource: dict[str, Any]) -> str:
        """Serialize a resource dict to canonical YAML for diffing.

        Keys are sorted for deterministic comparison.
        """
        import yaml

        return yaml.dump(resource, default_flow_style=False, sort_keys=True)

    @staticmethod
    def _strip_server_fields(resource: dict[str, Any]) -> dict[str, Any]:
        """Remove server-managed fields for a clean diff comparison."""
        cleaned = dict(resource)

        # Remove top-level server fields
        for top_field in SERVER_MANAGED_TOP_LEVEL_FIELDS:
            cleaned.pop(top_field, None)

        # Remove server-managed metadata fields
        metadata = cleaned.get("metadata")
        if isinstance(metadata, dict):
            metadata = dict(metadata)
            for meta_field in SERVER_MANAGED_METADATA_FIELDS:
                metadata.pop(meta_field, None)
            cleaned["metadata"] = metadata

        return cleaned
