"""Kubernetes integration test fixtures using testcontainers K3S.

Provides a real K3S (lightweight Kubernetes) cluster in Docker for integration
testing service managers against a live Kubernetes API server.
"""

from __future__ import annotations

import contextlib
import subprocess
import time
import uuid
from collections.abc import Callable, Generator
from typing import TYPE_CHECKING, Any

import pytest
import yaml
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs

from system_operations_manager.integrations.kubernetes.client import KubernetesClient
from system_operations_manager.integrations.kubernetes.config import (
    ClusterConfig,
    KubernetesPluginConfig,
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

if TYPE_CHECKING:
    from pathlib import Path


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
    pytest.mark.integration,
    pytest.mark.skipif(
        not _docker_available(),
        reason="Docker not available -- skipping Kubernetes integration tests",
    ),
]


# ============================================================================
# K3S Container Class
# ============================================================================

K3S_IMAGE = "rancher/k3s:v1.31.4-k3s1"


class K3SContainer(DockerContainer):  # type: ignore[misc]
    """K3S (lightweight Kubernetes) container for integration testing.

    Runs a single-node K3S cluster inside Docker with the API server
    exposed on a random port. Traefik is disabled for faster startup.
    """

    K8S_API_PORT = 6443

    def __init__(self, image: str = K3S_IMAGE) -> None:
        super().__init__(image)

        # K3S server configuration
        self.with_command(
            "server"
            " --disable=traefik"
            " --disable=metrics-server"
            " --tls-san=0.0.0.0"
            " --write-kubeconfig-mode=644"
        )

        # Expose the K8S API port
        self.with_exposed_ports(self.K8S_API_PORT)

        # K3S needs elevated privileges to run containerd
        self.with_kwargs(
            privileged=True,
            tmpfs={"/run": "", "/var/run": ""},
        )

    def get_kubeconfig(self) -> str:
        """Extract kubeconfig YAML from the running container.

        Reads /etc/rancher/k3s/k3s.yaml and rewrites the server address
        to use the mapped host:port so it's accessible from the host.
        """
        exit_code, output = self.exec("cat /etc/rancher/k3s/k3s.yaml")
        if exit_code != 0:
            raise RuntimeError(f"Failed to read kubeconfig: {output}")

        kubeconfig_yaml = output.decode("utf-8")
        config = yaml.safe_load(kubeconfig_yaml)

        # Rewrite the server address to use the mapped host:port
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
    """Session-scoped K3S container for integration tests.

    K3S starts in ~30-40 seconds. Session scope means the cluster
    is shared across ALL integration test modules for efficiency.
    """
    container = K3SContainer()

    with container:
        # Wait for K3S to be fully ready
        wait_for_logs(container, "Node controller sync successful", timeout=120)
        # Give a short buffer for API server to stabilize
        time.sleep(2)
        yield container


@pytest.fixture(scope="session")
def k3s_kubeconfig_path(
    k3s_container: K3SContainer,
    tmp_path_factory: pytest.TempPathFactory,
) -> Path:
    """Write K3S kubeconfig to a temp file for KubernetesClient."""
    kubeconfig_yaml = k3s_container.get_kubeconfig()
    kubeconfig_path = tmp_path_factory.mktemp("k3s") / "kubeconfig.yaml"
    kubeconfig_path.write_text(kubeconfig_yaml)
    return kubeconfig_path


@pytest.fixture(scope="session")
def k8s_plugin_config(k3s_kubeconfig_path: Path) -> KubernetesPluginConfig:
    """Create a KubernetesPluginConfig pointing to the K3S cluster."""
    return KubernetesPluginConfig(
        clusters={
            "test": ClusterConfig(
                kubeconfig=str(k3s_kubeconfig_path),
            ),
        },
        active_cluster="test",
    )


@pytest.fixture(scope="session")
def k8s_client(k8s_plugin_config: KubernetesPluginConfig) -> Generator[KubernetesClient]:
    """Session-scoped KubernetesClient connected to the K3S cluster."""
    client = KubernetesClient(k8s_plugin_config)
    yield client
    client.close()


# ============================================================================
# Namespace Isolation Fixtures
# ============================================================================


@pytest.fixture(scope="module")
def test_namespace(k8s_client: KubernetesClient) -> Generator[str]:
    """Module-scoped unique namespace for test isolation.

    Creates a unique namespace per test module. Deleting the namespace
    on teardown cascades to all resources within it.
    """
    ns_name = f"inttest-{uuid.uuid4().hex[:8]}"
    k8s_client.core_v1.create_namespace(
        body={
            "apiVersion": "v1",
            "kind": "Namespace",
            "metadata": {"name": ns_name},
        }
    )

    # Wait for namespace to be active
    for _ in range(30):
        ns = k8s_client.core_v1.read_namespace(name=ns_name)
        if ns.status.phase == "Active":
            break
        time.sleep(0.5)

    yield ns_name

    # Cleanup -- delete namespace (cascades to all resources)
    with contextlib.suppress(Exception):
        k8s_client.core_v1.delete_namespace(name=ns_name)


@pytest.fixture
def unique_name() -> str:
    """Generate a unique resource name for test isolation."""
    return f"test-{uuid.uuid4().hex[:8]}"


# ============================================================================
# Service Manager Fixtures (Function-Scoped)
# ============================================================================


@pytest.fixture
def workload_manager(k8s_client: KubernetesClient) -> WorkloadManager:
    """Create WorkloadManager instance."""
    return WorkloadManager(k8s_client)


@pytest.fixture
def namespace_manager(k8s_client: KubernetesClient) -> NamespaceClusterManager:
    """Create NamespaceClusterManager instance."""
    return NamespaceClusterManager(k8s_client)


@pytest.fixture
def networking_manager(k8s_client: KubernetesClient) -> NetworkingManager:
    """Create NetworkingManager instance."""
    return NetworkingManager(k8s_client)


@pytest.fixture
def config_manager(k8s_client: KubernetesClient) -> ConfigurationManager:
    """Create ConfigurationManager instance."""
    return ConfigurationManager(k8s_client)


@pytest.fixture
def job_manager(k8s_client: KubernetesClient) -> JobManager:
    """Create JobManager instance."""
    return JobManager(k8s_client)


@pytest.fixture
def rbac_manager(k8s_client: KubernetesClient) -> RBACManager:
    """Create RBACManager instance."""
    return RBACManager(k8s_client)


@pytest.fixture
def storage_manager(k8s_client: KubernetesClient) -> StorageManager:
    """Create StorageManager instance."""
    return StorageManager(k8s_client)


@pytest.fixture
def streaming_manager(k8s_client: KubernetesClient) -> StreamingManager:
    """Create StreamingManager instance."""
    return StreamingManager(k8s_client)


# ============================================================================
# Helper Fixtures
# ============================================================================


@pytest.fixture
def wait_for_pod_ready(k8s_client: KubernetesClient) -> Callable[..., Any]:
    """Helper to wait for a pod with given label selector to become Ready."""

    def _wait(
        namespace: str,
        label_selector: str,
        timeout: int = 120,
    ) -> Any:
        start = time.time()
        while time.time() - start < timeout:
            pods = k8s_client.core_v1.list_namespaced_pod(
                namespace=namespace,
                label_selector=label_selector,
            )
            for pod in pods.items:
                if pod.status.phase == "Running":
                    for cond in pod.status.conditions or []:
                        if cond.type == "Ready" and cond.status == "True":
                            return pod
            time.sleep(2)
        raise TimeoutError(
            f"Pod with selector '{label_selector}' in '{namespace}' not ready within {timeout}s"
        )

    return _wait


@pytest.fixture
def wait_for_job_complete(k8s_client: KubernetesClient) -> Callable[..., Any]:
    """Helper to wait for a job to complete."""

    def _wait(
        name: str,
        namespace: str,
        timeout: int = 120,
    ) -> Any:
        start = time.time()
        while time.time() - start < timeout:
            job = k8s_client.batch_v1.read_namespaced_job(name=name, namespace=namespace)
            if job.status.succeeded and job.status.succeeded >= 1:
                return job
            if job.status.failed and job.status.failed >= 1:
                raise RuntimeError(f"Job '{name}' failed")
            time.sleep(2)
        raise TimeoutError(f"Job '{name}' in '{namespace}' not complete within {timeout}s")

    return _wait
