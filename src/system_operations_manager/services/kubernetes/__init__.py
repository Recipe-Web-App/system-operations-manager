"""Kubernetes service module.

Provides centralized Kubernetes integration for the system operations manager.
Includes resource managers for all major Kubernetes resource types.
"""

from system_operations_manager.services.kubernetes.argocd_manager import ArgoCDManager
from system_operations_manager.services.kubernetes.certmanager_manager import CertManagerManager
from system_operations_manager.services.kubernetes.client import KubernetesService
from system_operations_manager.services.kubernetes.configuration_manager import (
    ConfigurationManager,
)
from system_operations_manager.services.kubernetes.externalsecrets_manager import (
    ExternalSecretsManager,
)
from system_operations_manager.services.kubernetes.flux_manager import FluxManager
from system_operations_manager.services.kubernetes.helm_manager import HelmManager
from system_operations_manager.services.kubernetes.job_manager import JobManager
from system_operations_manager.services.kubernetes.kustomize_manager import KustomizeManager
from system_operations_manager.services.kubernetes.kyverno_manager import KyvernoManager
from system_operations_manager.services.kubernetes.manifest_manager import ManifestManager
from system_operations_manager.services.kubernetes.multicluster_manager import MultiClusterManager
from system_operations_manager.services.kubernetes.namespace_manager import NamespaceClusterManager
from system_operations_manager.services.kubernetes.networking_manager import NetworkingManager
from system_operations_manager.services.kubernetes.optimization_manager import OptimizationManager
from system_operations_manager.services.kubernetes.rbac_manager import RBACManager
from system_operations_manager.services.kubernetes.rollouts_manager import RolloutsManager
from system_operations_manager.services.kubernetes.storage_manager import StorageManager
from system_operations_manager.services.kubernetes.streaming_manager import StreamingManager
from system_operations_manager.services.kubernetes.workflows_manager import WorkflowsManager
from system_operations_manager.services.kubernetes.workload_manager import WorkloadManager

__all__ = [
    "ArgoCDManager",
    "CertManagerManager",
    "ConfigurationManager",
    "ExternalSecretsManager",
    "FluxManager",
    "HelmManager",
    "JobManager",
    "KubernetesService",
    "KustomizeManager",
    "KyvernoManager",
    "ManifestManager",
    "MultiClusterManager",
    "NamespaceClusterManager",
    "NetworkingManager",
    "OptimizationManager",
    "RBACManager",
    "RolloutsManager",
    "StorageManager",
    "StreamingManager",
    "WorkflowsManager",
    "WorkloadManager",
]
