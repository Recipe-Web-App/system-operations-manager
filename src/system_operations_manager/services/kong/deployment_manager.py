"""Kong Gateway deployment manager.

Handles installation, upgrade, and cleanup of Kong Gateway in Kubernetes
using the official Kubernetes Python client.
"""

from __future__ import annotations

import contextlib
import shutil
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog
import yaml

if TYPE_CHECKING:
    from kubernetes.client import AppsV1Api, CoreV1Api

logger = structlog.get_logger()


class DeploymentError(Exception):
    """Raised when a deployment operation fails."""

    def __init__(self, message: str, details: str | None = None) -> None:
        self.message = message
        self.details = details
        super().__init__(message)


class DeploymentStatus(StrEnum):
    """Status of Kong deployment."""

    NOT_INSTALLED = "not_installed"
    RUNNING = "running"
    DEGRADED = "degraded"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass
class PodInfo:
    """Information about a Kubernetes pod."""

    name: str
    phase: str
    ready: bool
    restarts: int = 0


@dataclass
class DeploymentInfo:
    """Information about a Kong deployment."""

    status: DeploymentStatus
    namespace: str
    chart: str | None = None
    chart_version: str | None = None
    app_version: str | None = None
    postgres_ready: bool = False
    gateway_ready: bool = False
    controller_ready: bool = False
    pods: list[PodInfo] = field(default_factory=list)


class KubernetesClient:
    """Wrapper for Kubernetes API operations."""

    def __init__(self) -> None:
        """Initialize Kubernetes client."""
        try:
            from kubernetes import client, config

            # Try in-cluster config first, fall back to kubeconfig
            try:
                config.load_incluster_config()
            except config.ConfigException:
                config.load_kube_config()

            self._core_v1 = client.CoreV1Api()
            self._apps_v1 = client.AppsV1Api()
            self._client = client
        except ImportError as e:
            raise DeploymentError(
                "Kubernetes client not installed",
                details="Install with: uv sync --extra kubernetes",
            ) from e
        except Exception as e:
            raise DeploymentError(
                "Failed to initialize Kubernetes client",
                details=str(e),
            ) from e

    @property
    def core_v1(self) -> CoreV1Api:
        """Get CoreV1 API client."""
        return self._core_v1

    @property
    def apps_v1(self) -> AppsV1Api:
        """Get AppsV1 API client."""
        return self._apps_v1

    def namespace_exists(self, name: str) -> bool:
        """Check if a namespace exists."""
        try:
            self._core_v1.read_namespace(name)
            return True
        except self._client.rest.ApiException as e:
            if e.status == 404:
                return False
            raise

    def create_namespace(self, name: str) -> None:
        """Create a namespace if it doesn't exist."""
        if self.namespace_exists(name):
            logger.debug("Namespace already exists", namespace=name)
            return

        body = self._client.V1Namespace(metadata=self._client.V1ObjectMeta(name=name))
        self._core_v1.create_namespace(body)
        logger.info("Namespace created", namespace=name)

    def secret_exists(self, name: str, namespace: str) -> bool:
        """Check if a secret exists."""
        try:
            self._core_v1.read_namespaced_secret(name, namespace)
            return True
        except self._client.rest.ApiException as e:
            if e.status == 404:
                return False
            raise

    def create_secret_from_env_file(
        self,
        name: str,
        namespace: str,
        env_file: Path,
        replace: bool = True,
    ) -> None:
        """Create a secret from an env file.

        Args:
            name: Secret name.
            namespace: Kubernetes namespace.
            env_file: Path to .env file.
            replace: Replace existing secret if it exists.
        """
        if not env_file.exists():
            raise DeploymentError(f"Env file not found: {env_file}")

        # Parse env file
        data = {}
        with env_file.open() as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    data[key.strip()] = value.strip()

        # Delete existing if replacing
        if replace and self.secret_exists(name, namespace):
            self._core_v1.delete_namespaced_secret(name, namespace)
            logger.debug("Deleted existing secret", name=name)

        # Create secret
        body = self._client.V1Secret(
            metadata=self._client.V1ObjectMeta(name=name),
            string_data=data,
        )
        self._core_v1.create_namespaced_secret(namespace, body)
        logger.info("Secret created", name=name, namespace=namespace)

    def apply_yaml_file(self, file_path: Path, namespace: str | None = None) -> list[str]:
        """Apply a YAML manifest file.

        Args:
            file_path: Path to YAML file.
            namespace: Override namespace for resources.

        Returns:
            List of created/updated resource names.
        """
        from kubernetes import utils

        if not file_path.exists():
            raise DeploymentError(f"Manifest file not found: {file_path}")

        with file_path.open() as f:
            manifests = list(yaml.safe_load_all(f))

        created = []
        k8s_client = self._client.ApiClient()

        for manifest in manifests:
            if manifest is None:
                continue

            # Override namespace if specified
            if namespace and "metadata" in manifest:
                manifest.setdefault("metadata", {})["namespace"] = namespace

            try:
                utils.create_from_dict(k8s_client, manifest, verbose=False)
                kind = manifest.get("kind", "unknown")
                name = manifest.get("metadata", {}).get("name", "unknown")
                created.append(f"{kind}/{name}")
                logger.debug("Created resource", kind=kind, name=name)
            except utils.FailToCreateError as e:
                # Try to update if create fails (resource exists)
                for api_exception in e.api_exceptions:
                    if api_exception.status == 409:  # Conflict = already exists
                        # Resource exists, this is OK for apply semantics
                        kind = manifest.get("kind", "unknown")
                        name = manifest.get("metadata", {}).get("name", "unknown")
                        created.append(f"{kind}/{name} (exists)")
                    else:
                        raise DeploymentError(
                            f"Failed to apply manifest: {api_exception.reason}",
                            details=str(api_exception.body),
                        ) from e

        return created

    def delete_yaml_file(self, file_path: Path, namespace: str | None = None) -> list[str]:
        """Delete resources defined in a YAML manifest.

        Args:
            file_path: Path to YAML file.
            namespace: Override namespace.

        Returns:
            List of deleted resource names.
        """
        if not file_path.exists():
            return []

        with file_path.open() as f:
            manifests = list(yaml.safe_load_all(f))

        deleted = []

        for manifest in manifests:
            if manifest is None:
                continue

            kind = manifest.get("kind", "").lower()
            name = manifest.get("metadata", {}).get("name")
            ns = namespace or manifest.get("metadata", {}).get("namespace", "default")

            if not name:
                continue

            try:
                if kind == "statefulset":
                    self._apps_v1.delete_namespaced_stateful_set(name, ns)
                elif kind == "deployment":
                    self._apps_v1.delete_namespaced_deployment(name, ns)
                elif kind == "service":
                    self._core_v1.delete_namespaced_service(name, ns)
                elif kind == "configmap":
                    self._core_v1.delete_namespaced_config_map(name, ns)
                elif kind == "persistentvolumeclaim":
                    self._core_v1.delete_namespaced_persistent_volume_claim(name, ns)
                elif kind == "secret":
                    self._core_v1.delete_namespaced_secret(name, ns)

                deleted.append(f"{kind}/{name}")
                logger.debug("Deleted resource", kind=kind, name=name)
            except self._client.rest.ApiException as e:
                if e.status != 404:  # Ignore not found
                    logger.warning("Failed to delete resource", kind=kind, name=name, error=str(e))

        return deleted

    def get_pods(self, namespace: str, label_selector: str | None = None) -> list[PodInfo]:
        """Get pods in a namespace.

        Args:
            namespace: Kubernetes namespace.
            label_selector: Optional label selector (e.g., "app=kong").

        Returns:
            List of PodInfo objects.
        """
        pods = self._core_v1.list_namespaced_pod(
            namespace,
            label_selector=label_selector or "",
        )

        result = []
        for pod in pods.items:
            # Check if all containers are ready
            containers = pod.status.container_statuses or []
            ready = all(c.ready for c in containers) if containers else False
            restarts = sum(c.restart_count for c in containers)

            result.append(
                PodInfo(
                    name=pod.metadata.name,
                    phase=pod.status.phase,
                    ready=ready,
                    restarts=restarts,
                )
            )

        return result

    def wait_for_pod_ready(
        self,
        namespace: str,
        label_selector: str,
        timeout: int = 120,
        poll_interval: int = 5,
    ) -> bool:
        """Wait for pods matching selector to be ready.

        Args:
            namespace: Kubernetes namespace.
            label_selector: Label selector for pods.
            timeout: Timeout in seconds.
            poll_interval: Poll interval in seconds.

        Returns:
            True if pods are ready, False if timeout.
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            pods = self.get_pods(namespace, label_selector)

            if pods and all(p.ready for p in pods):
                return True

            time.sleep(poll_interval)

        return False


class HelmClient:
    """Wrapper for Helm operations.

    Note: Uses helm CLI as there's no stable Python library for Helm 3.
    """

    REPO_NAME = "kong"
    REPO_URL = "https://charts.konghq.com"

    def __init__(self) -> None:
        """Initialize Helm client."""
        if not shutil.which("helm"):
            raise DeploymentError(
                "helm is not installed",
                details="Install from https://helm.sh/docs/intro/install/",
            )

    def _run(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        """Run helm command."""
        cmd = ["helm", *args]
        logger.debug("Running helm command", cmd=" ".join(cmd))

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )

        if check and result.returncode != 0:
            raise DeploymentError(
                f"Helm command failed: {' '.join(args)}",
                details=result.stderr,
            )

        return result

    def setup_repo(self) -> None:
        """Add and update Kong Helm repository."""
        # Add repo (ignore error if exists)
        self._run("repo", "add", self.REPO_NAME, self.REPO_URL, check=False)
        self._run("repo", "update")
        logger.info("Helm repository configured")

    def get_release(self, name: str, namespace: str) -> dict[str, Any] | None:
        """Get information about a Helm release.

        Returns:
            Release info dict, or None if not found.
        """
        import json

        result = self._run("list", "-n", namespace, "-o", "json", check=False)

        if result.returncode != 0:
            return None

        try:
            releases: list[dict[str, Any]] = json.loads(result.stdout)
            for release in releases:
                if release.get("name") == name:
                    return dict(release)
        except json.JSONDecodeError:
            pass

        return None

    def install_crds(self, chart: str) -> None:
        """Install CRDs from a Helm chart.

        Args:
            chart: Chart reference (e.g., "kong/ingress").
        """
        # Get CRDs from chart and apply them
        result = self._run("show", "crds", chart, check=True)
        if result.stdout.strip():
            # Apply CRDs via kubectl
            import subprocess

            apply_result = subprocess.run(
                ["kubectl", "apply", "-f", "-"],
                input=result.stdout,
                capture_output=True,
                text=True,
            )
            if apply_result.returncode != 0:
                raise DeploymentError(
                    "Failed to install CRDs",
                    details=apply_result.stderr,
                )
            logger.info("CRDs installed", chart=chart)

    def install(
        self,
        name: str,
        chart: str,
        namespace: str,
        values_file: Path,
        timeout: str = "10m",
        wait: bool = True,
        create_namespace: bool = True,
        skip_crds: bool = True,
    ) -> None:
        """Install a Helm chart.

        Args:
            name: Release name.
            chart: Chart reference (e.g., "kong/ingress").
            namespace: Kubernetes namespace.
            values_file: Path to values.yaml file.
            timeout: Timeout for installation.
            wait: Wait for resources to be ready.
            create_namespace: Create namespace if not exists.
            skip_crds: Skip CRD installation (manage separately).
        """
        if not values_file.exists():
            raise DeploymentError(f"Values file not found: {values_file}")

        args = [
            "install",
            name,
            chart,
            "-n",
            namespace,
            "-f",
            str(values_file),
            "--timeout",
            timeout,
        ]

        if wait:
            args.append("--wait")
        if create_namespace:
            args.append("--create-namespace")
        if skip_crds:
            args.append("--skip-crds")

        self._run(*args)
        logger.info("Helm chart installed", name=name, chart=chart)

    def upgrade(
        self,
        name: str,
        chart: str,
        namespace: str,
        values_file: Path,
        timeout: str = "10m",
        wait: bool = True,
    ) -> None:
        """Upgrade a Helm release.

        Args:
            name: Release name.
            chart: Chart reference.
            namespace: Kubernetes namespace.
            values_file: Path to values.yaml file.
            timeout: Timeout for upgrade.
            wait: Wait for resources to be ready.
        """
        if not values_file.exists():
            raise DeploymentError(f"Values file not found: {values_file}")

        args = [
            "upgrade",
            name,
            chart,
            "-n",
            namespace,
            "-f",
            str(values_file),
            "--timeout",
            timeout,
        ]

        if wait:
            args.append("--wait")

        self._run(*args)
        logger.info("Helm chart upgraded", name=name, chart=chart)

    def uninstall(self, name: str, namespace: str) -> bool:
        """Uninstall a Helm release.

        Args:
            name: Release name.
            namespace: Kubernetes namespace.

        Returns:
            True if uninstalled, False if not found.
        """
        result = self._run("uninstall", name, "-n", namespace, check=False)
        if result.returncode == 0:
            logger.info("Helm release uninstalled", name=name)
            return True
        return False


class KongDeploymentManager:
    """Manages Kong Gateway deployment in Kubernetes."""

    DEFAULT_NAMESPACE = "kong"
    DEFAULT_RELEASE_NAME = "kong"
    DEFAULT_CHART = "kong/ingress"

    def __init__(
        self,
        project_root: Path | None = None,
        namespace: str = DEFAULT_NAMESPACE,
        release_name: str = DEFAULT_RELEASE_NAME,
        progress_callback: Callable[[str], None] | None = None,
    ) -> None:
        """Initialize deployment manager.

        Args:
            project_root: Project root directory.
            namespace: Kubernetes namespace.
            release_name: Helm release name.
            progress_callback: Callback for progress updates.
        """
        self.project_root = project_root or self._find_project_root()
        self.namespace = namespace
        self.release_name = release_name
        self._progress = progress_callback or (lambda msg: None)

        self._k8s: KubernetesClient | None = None
        self._helm: HelmClient | None = None

    def _find_project_root(self) -> Path:
        """Find project root directory."""
        current = Path.cwd()
        while current != current.parent:
            if (current / "pyproject.toml").exists():
                return current
            current = current.parent
        return Path.cwd()

    @property
    def k8s(self) -> KubernetesClient:
        """Get Kubernetes client (lazy initialization)."""
        if self._k8s is None:
            self._k8s = KubernetesClient()
        return self._k8s

    @property
    def helm(self) -> HelmClient:
        """Get Helm client (lazy initialization)."""
        if self._helm is None:
            self._helm = HelmClient()
        return self._helm

    def _get_paths(self) -> dict[str, Path]:
        """Get paths to deployment files."""
        gateway_dir = self.project_root / "k8s" / "gateway"
        config_dir = self.project_root / "config"

        return {
            "values": gateway_dir / "kong-values.yaml",
            "postgres": gateway_dir / "postgres.yaml",
            "rbac_patch": gateway_dir / "kong-rbac-patch.yaml",
            "secrets": config_dir / ".env.kong.secrets",
            "secrets_example": config_dir / ".env.kong.secrets.example",
        }

    def get_status(self) -> DeploymentInfo:
        """Get current deployment status."""
        # Check namespace
        if not self.k8s.namespace_exists(self.namespace):
            return DeploymentInfo(
                status=DeploymentStatus.NOT_INSTALLED,
                namespace=self.namespace,
            )

        # Get helm release info
        release = self.helm.get_release(self.release_name, self.namespace)

        chart = None
        chart_version = None
        app_version = None

        if release:
            chart = release.get("chart", "")
            app_version = release.get("app_version")
            if "-" in chart:
                chart_version = chart.rsplit("-", 1)[-1]

        # Get pods
        pods = self.k8s.get_pods(self.namespace)

        postgres_ready = False
        gateway_ready = False
        controller_ready = False

        for pod in pods:
            if "postgres" in pod.name and pod.ready:
                postgres_ready = True
            elif "gateway" in pod.name and pod.ready:
                gateway_ready = True
            elif "controller" in pod.name and pod.ready:
                controller_ready = True

        # Determine status
        if not release:
            status = DeploymentStatus.NOT_INSTALLED
        elif gateway_ready and (controller_ready or postgres_ready):
            status = DeploymentStatus.RUNNING
        elif pods:
            status = DeploymentStatus.DEGRADED
        else:
            status = DeploymentStatus.FAILED

        return DeploymentInfo(
            status=status,
            namespace=self.namespace,
            chart=chart,
            chart_version=chart_version,
            app_version=app_version,
            postgres_ready=postgres_ready,
            gateway_ready=gateway_ready,
            controller_ready=controller_ready,
            pods=pods,
        )

    def install(self) -> None:
        """Full installation of Kong Gateway with PostgreSQL."""
        paths = self._get_paths()

        # Validate files exist
        if not paths["secrets"].exists():
            raise DeploymentError(
                f"Secrets file not found: {paths['secrets']}",
                details=f"Create with: cp {paths['secrets_example']} {paths['secrets']}",
            )

        if not paths["values"].exists():
            raise DeploymentError(f"Values file not found: {paths['values']}")

        if not paths["postgres"].exists():
            raise DeploymentError(f"PostgreSQL manifest not found: {paths['postgres']}")

        # Setup helm repo
        self._progress("Setting up Helm repository...")
        self.helm.setup_repo()

        # Create namespace
        self._progress(f"Creating namespace '{self.namespace}'...")
        self.k8s.create_namespace(self.namespace)

        # Create secret
        self._progress("Creating PostgreSQL secret...")
        self.k8s.create_secret_from_env_file(
            "kong-postgres-secret",
            self.namespace,
            paths["secrets"],
        )

        # Deploy PostgreSQL
        self._progress("Deploying PostgreSQL...")
        self.k8s.apply_yaml_file(paths["postgres"])

        self._progress("Waiting for PostgreSQL to be ready...")
        if not self.k8s.wait_for_pod_ready(self.namespace, "app=kong-postgres"):
            raise DeploymentError("PostgreSQL failed to become ready")

        # Install CRDs first (managed separately from helm release)
        self._progress("Installing Kong CRDs...")
        self.helm.install_crds(self.DEFAULT_CHART)

        # Install Kong (skip CRDs since we installed them separately)
        self._progress("Installing Kong Gateway...")
        self.helm.install(
            self.release_name,
            self.DEFAULT_CHART,
            self.namespace,
            paths["values"],
            create_namespace=False,  # Already created
            skip_crds=True,
        )

        self._progress("Kong Gateway installed successfully!")

    def _apply_rbac_patch(self, rbac_file: Path) -> None:
        """Apply RBAC patch for K8s 1.34+ endpoint discovery.

        The Kong Ingress Controller needs 'endpoints' permission in addition
        to 'endpointslices' for service discovery on K8s 1.34+.

        Args:
            rbac_file: Path to the RBAC patch YAML file.
        """
        import subprocess

        result = subprocess.run(
            ["kubectl", "apply", "-f", str(rbac_file)],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise DeploymentError(
                "Failed to apply RBAC patch",
                details=result.stderr,
            )

        logger.info("RBAC patch applied", file=str(rbac_file))

    def upgrade(self) -> None:
        """Upgrade existing Kong Gateway installation."""
        paths = self._get_paths()

        if not paths["values"].exists():
            raise DeploymentError(f"Values file not found: {paths['values']}")

        self._progress("Setting up Helm repository...")
        self.helm.setup_repo()

        self._progress("Upgrading Kong Gateway...")
        self.helm.upgrade(
            self.release_name,
            self.DEFAULT_CHART,
            self.namespace,
            paths["values"],
        )

        self._progress("Kong Gateway upgraded successfully!")

    def uninstall(
        self,
        keep_postgres: bool = False,
        keep_secrets: bool = True,
        keep_pvc: bool = True,
    ) -> None:
        """Uninstall Kong Gateway.

        Args:
            keep_postgres: Keep PostgreSQL after uninstall.
            keep_secrets: Keep secrets after uninstall.
            keep_pvc: Keep PVC after uninstall.
        """
        paths = self._get_paths()

        self._progress("Uninstalling Kong Gateway...")
        self.helm.uninstall(self.release_name, self.namespace)

        if not keep_postgres:
            self._progress("Removing PostgreSQL...")
            self.k8s.delete_yaml_file(paths["postgres"])

        if not keep_secrets:
            self._progress("Removing secrets...")
            with contextlib.suppress(Exception):
                self.k8s.core_v1.delete_namespaced_secret("kong-postgres-secret", self.namespace)

        if not keep_pvc:
            self._progress("Removing PVC...")
            with contextlib.suppress(Exception):
                self.k8s.core_v1.delete_namespaced_persistent_volume_claim(
                    "kong-postgres-pvc", self.namespace
                )

        self._progress("Kong Gateway uninstalled!")
