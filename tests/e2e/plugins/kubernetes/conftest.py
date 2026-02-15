"""Kubernetes E2E test fixtures using testcontainers K3S.

Bridges testcontainers K3S infrastructure with CLI testing via CliRunner.
Follows the same pattern as tests/e2e/plugins/kong/conftest.py.
"""

from __future__ import annotations

import contextlib
import subprocess
import time
import uuid
from collections.abc import Callable, Generator
from pathlib import Path
from typing import Any

import pytest
import typer
import yaml
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs
from typer.testing import CliRunner

# ============================================================================
# Docker Availability Check
# ============================================================================


def _docker_available() -> bool:
    """Check if Docker daemon is running."""
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except FileNotFoundError, subprocess.TimeoutExpired:
        return False


# Module-level markers: skip if Docker unavailable
pytestmark = [
    pytest.mark.kubernetes,
    pytest.mark.e2e,
    pytest.mark.skipif(
        not _docker_available(),
        reason="Docker not available -- skipping Kubernetes E2E tests",
    ),
]


# ============================================================================
# K3S Container Class (duplicated from integration for isolation)
# ============================================================================

K3S_IMAGE = "rancher/k3s:v1.31.4-k3s1"


class K3SContainer(DockerContainer):  # type: ignore[misc]
    """K3S (lightweight Kubernetes) container for E2E testing.

    Runs a single-node K3S cluster inside Docker. E2E tests create
    their own resources via CLI commands.
    """

    K8S_API_PORT = 6443

    def __init__(self, image: str = K3S_IMAGE) -> None:
        super().__init__(image)

        self.with_command(
            "server"
            " --disable=traefik"
            " --disable=metrics-server"
            " --tls-san=0.0.0.0"
            " --write-kubeconfig-mode=644"
        )
        self.with_exposed_ports(self.K8S_API_PORT)
        self.with_kwargs(
            privileged=True,
            tmpfs={"/run": "", "/var/run": ""},
        )

    def get_kubeconfig(self) -> str:
        """Extract kubeconfig YAML with rewritten server address."""
        exit_code, output = self.exec("cat /etc/rancher/k3s/k3s.yaml")
        if exit_code != 0:
            raise RuntimeError(f"Failed to read kubeconfig: {output}")

        kubeconfig_yaml = output.decode("utf-8")
        config = yaml.safe_load(kubeconfig_yaml)

        host = self.get_container_host_ip()
        port = self.get_exposed_port(self.K8S_API_PORT)
        for cluster in config.get("clusters", []):
            cluster_data = cluster.get("cluster", {})
            cluster_data["server"] = f"https://{host}:{port}"

        return yaml.dump(config)


# ============================================================================
# K3S Cluster Fixtures (Session-Scoped)
# ============================================================================


@pytest.fixture(scope="session")
def k3s_container() -> Generator[K3SContainer]:
    """Session-scoped K3S container for E2E tests."""
    container = K3SContainer()

    with container:
        wait_for_logs(container, "Node controller sync successful", timeout=120)
        time.sleep(2)
        yield container


@pytest.fixture(scope="session")
def k3s_kubeconfig_path(
    k3s_container: K3SContainer,
    tmp_path_factory: pytest.TempPathFactory,
) -> Path:
    """Write K3S kubeconfig to a temp file."""
    kubeconfig_yaml = k3s_container.get_kubeconfig()
    kubeconfig_path = tmp_path_factory.mktemp("k3s-e2e") / "kubeconfig.yaml"
    kubeconfig_path.write_text(kubeconfig_yaml)
    return kubeconfig_path


# ============================================================================
# Typer App Factory (mirrors Kong's create_kong_app pattern)
# ============================================================================


def create_k8s_app(kubeconfig_path: str) -> typer.Typer:
    """Create a Typer app with K8s plugin commands for E2E testing.

    Manually registers the core command groups needed for E2E testing,
    avoiding CRD-dependent commands (ArgoCD, Flux, etc.).

    Args:
        kubeconfig_path: Path to the K3S kubeconfig file.

    Returns:
        A Typer app with Kubernetes commands registered.
    """
    from system_operations_manager.integrations.kubernetes.client import KubernetesClient
    from system_operations_manager.integrations.kubernetes.config import (
        ClusterConfig,
        KubernetesPluginConfig,
    )
    from system_operations_manager.plugins.kubernetes.commands import (
        register_cluster_commands,
        register_config_commands,
        register_job_commands,
        register_namespace_commands,
        register_networking_commands,
        register_rbac_commands,
        register_storage_commands,
        register_streaming_commands,
        register_workload_commands,
    )
    from system_operations_manager.services.kubernetes import (
        ConfigurationManager,
        JobManager,
        NamespaceClusterManager,
        NetworkingManager,
        RBACManager,
        StorageManager,
        StreamingManager,
        WorkloadManager,
    )

    # Create client pointing to K3S
    plugin_config = KubernetesPluginConfig(
        clusters={
            "test": ClusterConfig(kubeconfig=kubeconfig_path),
        },
        active_cluster="test",
    )
    client = KubernetesClient(plugin_config)

    # Manager factory functions
    def get_workload_manager() -> WorkloadManager:
        return WorkloadManager(client)

    def get_networking_manager() -> NetworkingManager:
        return NetworkingManager(client)

    def get_config_manager() -> ConfigurationManager:
        return ConfigurationManager(client)

    def get_namespace_cluster_manager() -> NamespaceClusterManager:
        return NamespaceClusterManager(client)

    def get_job_manager() -> JobManager:
        return JobManager(client)

    def get_storage_manager() -> StorageManager:
        return StorageManager(client)

    def get_rbac_manager() -> RBACManager:
        return RBACManager(client)

    def get_streaming_manager() -> StreamingManager:
        return StreamingManager(client)

    # Build Typer app hierarchy
    app = typer.Typer(
        name="ops",
        help="System Control CLI for E2E testing.",
        add_completion=False,
    )

    k8s_app = typer.Typer(
        name="k8s",
        help="Kubernetes management commands",
        no_args_is_help=True,
    )

    # Register core entity commands
    register_workload_commands(k8s_app, get_workload_manager)
    register_networking_commands(k8s_app, get_networking_manager)
    register_config_commands(k8s_app, get_config_manager)
    register_cluster_commands(k8s_app, get_namespace_cluster_manager)
    register_namespace_commands(k8s_app, get_namespace_cluster_manager)
    register_job_commands(k8s_app, get_job_manager)
    register_storage_commands(k8s_app, get_storage_manager)
    register_rbac_commands(k8s_app, get_rbac_manager)
    register_streaming_commands(k8s_app, get_streaming_manager)

    app.add_typer(k8s_app, name="k8s")

    return app


@pytest.fixture(scope="session")
def k8s_app(k3s_kubeconfig_path: Path) -> typer.Typer:
    """Session-scoped Typer app connected to K3S cluster."""
    return create_k8s_app(str(k3s_kubeconfig_path))


# ============================================================================
# CLI Helper Fixtures
# ============================================================================


@pytest.fixture
def cli_runner() -> CliRunner:
    """Function-scoped CLI runner for clean state."""
    return CliRunner()


@pytest.fixture
def invoke_k8s(cli_runner: CliRunner, k8s_app: typer.Typer) -> Callable[..., Any]:
    """Helper to invoke K8s CLI commands.

    Example:
        result = invoke_k8s("pods", "list")
        result = invoke_k8s("deployments", "create", "my-dep", "--image", "nginx")
    """

    def _invoke(*args: str, input: str | None = None) -> Any:
        cmd = ["k8s", *args]
        return cli_runner.invoke(k8s_app, cmd, input=input)

    return _invoke


@pytest.fixture
def unique_prefix() -> str:
    """Unique prefix for test entity names."""
    return f"e2e-{uuid.uuid4().hex[:8]}"


# ============================================================================
# E2E Namespace Isolation
# ============================================================================


@pytest.fixture(scope="module")
def e2e_namespace(k3s_kubeconfig_path: Path) -> Generator[str]:
    """Module-scoped unique namespace for E2E test isolation."""
    from kubernetes import client, config

    config.load_kube_config(config_file=str(k3s_kubeconfig_path))

    ns_name = f"e2e-{uuid.uuid4().hex[:8]}"
    core_v1 = client.CoreV1Api()
    core_v1.create_namespace(body=client.V1Namespace(metadata=client.V1ObjectMeta(name=ns_name)))

    # Wait for namespace to be active
    for _ in range(30):
        ns = core_v1.read_namespace(name=ns_name)
        if ns.status.phase == "Active":
            break
        time.sleep(0.5)

    yield ns_name

    with contextlib.suppress(Exception):
        core_v1.delete_namespace(name=ns_name)


@pytest.fixture
def temp_config_dir(tmp_path: Path) -> Path:
    """Temporary directory for config files."""
    return tmp_path
