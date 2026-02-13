"""Kustomize CLI wrapper for rendering Kubernetes manifests.

Wraps the kustomize binary via subprocess for build operations,
overlay discovery, and validation.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import structlog

from system_operations_manager.integrations.kubernetes.exceptions import KubernetesError

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

KUSTOMIZATION_FILENAMES = ("kustomization.yaml", "kustomization.yml", "Kustomization")
BUILD_TIMEOUT_SECONDS = 60
VERSION_TIMEOUT_SECONDS = 5


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class KustomizeError(KubernetesError):
    """Base exception for Kustomize operations."""

    def __init__(
        self,
        message: str,
        kustomization_path: str | None = None,
        stderr: str | None = None,
    ) -> None:
        super().__init__(message=message)
        self.kustomization_path = kustomization_path
        self.stderr = stderr


class KustomizeBinaryNotFoundError(KustomizeError):
    """Raised when kustomize binary is not found in PATH."""

    def __init__(self) -> None:
        super().__init__(
            message=(
                "kustomize binary not found in PATH. "
                "Install from: https://kubectl.docs.kubernetes.io/installation/kustomize/"
            ),
        )


class KustomizeBuildError(KustomizeError):
    """Raised when kustomize build fails."""


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class KustomizeBuildResult:
    """Result of a kustomize build operation."""

    rendered_yaml: str
    kustomization_path: str
    success: bool
    error: str | None = None


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class KustomizeClient:
    """Client for interacting with the kustomize CLI.

    Wraps kustomize binary execution and provides typed results.
    """

    def __init__(self, binary_path: str | None = None) -> None:
        """Initialize Kustomize client.

        Args:
            binary_path: Optional explicit path to kustomize binary.
                If None, searches PATH.

        Raises:
            KustomizeBinaryNotFoundError: If binary not found.
        """
        self._binary = self._find_binary(binary_path)
        self._log = logger.bind(binary=self._binary)
        self._log.debug("kustomize_client_initialized")

    @staticmethod
    def _find_binary(binary_path: str | None) -> str:
        """Locate kustomize binary.

        Args:
            binary_path: Explicit path or None to search PATH.

        Returns:
            Path to kustomize binary.

        Raises:
            KustomizeBinaryNotFoundError: If not found.
        """
        if binary_path:
            path = Path(binary_path)
            if not path.exists():
                raise KustomizeBinaryNotFoundError()
            return str(path.resolve())

        found = shutil.which("kustomize")
        if not found:
            raise KustomizeBinaryNotFoundError()

        return found

    def get_version(self) -> str:
        """Get kustomize version string.

        Returns:
            Version string (e.g., ``v5.8.0``).

        Raises:
            KustomizeError: If version command fails.
        """
        try:
            result = subprocess.run(
                [self._binary, "version", "--short"],
                capture_output=True,
                text=True,
                check=True,
                timeout=VERSION_TIMEOUT_SECONDS,
            )
            version_line = result.stdout.strip()
            # Parse output like "{kustomize/v5.8.0  2025-...}"
            if "/" in version_line:
                return version_line.split("/")[1].split()[0]
            return version_line
        except subprocess.CalledProcessError as e:
            raise KustomizeError(
                message=f"Failed to get kustomize version: {e.stderr}",
                stderr=e.stderr,
            ) from e
        except subprocess.TimeoutExpired as e:
            raise KustomizeError(message="kustomize version command timed out") from e

    def build(
        self,
        kustomization_dir: Path,
        *,
        enable_helm: bool = False,
        enable_alpha_plugins: bool = False,
    ) -> KustomizeBuildResult:
        """Run kustomize build to render manifests.

        Args:
            kustomization_dir: Directory containing kustomization.yaml.
            enable_helm: Enable Helm chart inflation generator.
            enable_alpha_plugins: Enable alpha plugin support.

        Returns:
            Build result with rendered YAML or error details.
        """
        if not kustomization_dir.exists():
            return KustomizeBuildResult(
                rendered_yaml="",
                kustomization_path=str(kustomization_dir),
                success=False,
                error=f"Directory not found: {kustomization_dir}",
            )

        if not self._has_kustomization_file(kustomization_dir):
            return KustomizeBuildResult(
                rendered_yaml="",
                kustomization_path=str(kustomization_dir),
                success=False,
                error=f"No kustomization file found in {kustomization_dir}",
            )

        cmd = [self._binary, "build", str(kustomization_dir)]
        if enable_helm:
            cmd.append("--enable-helm")
        if enable_alpha_plugins:
            cmd.append("--enable-alpha-plugins")

        try:
            self._log.debug(
                "running_kustomize_build",
                path=str(kustomization_dir),
                enable_helm=enable_helm,
            )
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=BUILD_TIMEOUT_SECONDS,
            )
            self._log.info("kustomize_build_success", path=str(kustomization_dir))
            return KustomizeBuildResult(
                rendered_yaml=result.stdout,
                kustomization_path=str(kustomization_dir),
                success=True,
            )

        except subprocess.CalledProcessError as e:
            self._log.error(
                "kustomize_build_failed",
                path=str(kustomization_dir),
                stderr=e.stderr,
                returncode=e.returncode,
            )
            return KustomizeBuildResult(
                rendered_yaml="",
                kustomization_path=str(kustomization_dir),
                success=False,
                error=e.stderr.strip() if e.stderr else f"Build failed with code {e.returncode}",
            )

        except subprocess.TimeoutExpired:
            self._log.error("kustomize_build_timeout", path=str(kustomization_dir))
            return KustomizeBuildResult(
                rendered_yaml="",
                kustomization_path=str(kustomization_dir),
                success=False,
                error=f"Build timed out after {BUILD_TIMEOUT_SECONDS} seconds",
            )

    def validate_kustomization(self, kustomization_dir: Path) -> tuple[bool, str | None]:
        """Check if directory contains a valid kustomization.

        Validates by checking for the kustomization file and
        attempting a build.

        Args:
            kustomization_dir: Directory to validate.

        Returns:
            Tuple of (is_valid, error_message).
        """
        if not kustomization_dir.exists():
            return False, f"Directory not found: {kustomization_dir}"

        if not kustomization_dir.is_dir():
            return False, f"Not a directory: {kustomization_dir}"

        if not self._has_kustomization_file(kustomization_dir):
            return False, f"No kustomization file found in {kustomization_dir}"

        result = self.build(kustomization_dir)
        if not result.success:
            return False, result.error

        return True, None

    @staticmethod
    def _has_kustomization_file(directory: Path) -> bool:
        """Check if a directory contains a kustomization file."""
        return any((directory / name).exists() for name in KUSTOMIZATION_FILENAMES)
