"""Kubernetes CLI command modules."""

from system_operations_manager.plugins.kubernetes.commands.argocd import (
    register_argocd_commands,
)
from system_operations_manager.plugins.kubernetes.commands.certs import (
    register_certs_commands,
)
from system_operations_manager.plugins.kubernetes.commands.clusters import (
    register_cluster_commands,
)
from system_operations_manager.plugins.kubernetes.commands.config_resources import (
    register_config_commands,
)
from system_operations_manager.plugins.kubernetes.commands.externalsecrets import (
    register_external_secrets_commands,
)
from system_operations_manager.plugins.kubernetes.commands.flux import (
    register_flux_commands,
)
from system_operations_manager.plugins.kubernetes.commands.helm import (
    register_helm_commands,
)
from system_operations_manager.plugins.kubernetes.commands.jobs import register_job_commands
from system_operations_manager.plugins.kubernetes.commands.kustomize import (
    register_kustomize_commands,
)
from system_operations_manager.plugins.kubernetes.commands.manifests import (
    register_manifest_commands,
)
from system_operations_manager.plugins.kubernetes.commands.multicluster import (
    register_multicluster_commands,
)
from system_operations_manager.plugins.kubernetes.commands.namespaces import (
    register_namespace_commands,
)
from system_operations_manager.plugins.kubernetes.commands.networking import (
    register_networking_commands,
)
from system_operations_manager.plugins.kubernetes.commands.optimize import (
    register_optimization_commands,
)
from system_operations_manager.plugins.kubernetes.commands.policies import (
    register_policy_commands,
)
from system_operations_manager.plugins.kubernetes.commands.rbac import register_rbac_commands
from system_operations_manager.plugins.kubernetes.commands.rollouts import (
    register_rollout_commands,
)
from system_operations_manager.plugins.kubernetes.commands.storage import register_storage_commands
from system_operations_manager.plugins.kubernetes.commands.streaming import (
    register_streaming_commands,
)
from system_operations_manager.plugins.kubernetes.commands.workflows import (
    register_workflow_commands,
)
from system_operations_manager.plugins.kubernetes.commands.workloads import (
    register_workload_commands,
)

__all__ = [
    "register_argocd_commands",
    "register_certs_commands",
    "register_cluster_commands",
    "register_config_commands",
    "register_external_secrets_commands",
    "register_flux_commands",
    "register_helm_commands",
    "register_job_commands",
    "register_kustomize_commands",
    "register_manifest_commands",
    "register_multicluster_commands",
    "register_namespace_commands",
    "register_networking_commands",
    "register_optimization_commands",
    "register_policy_commands",
    "register_rbac_commands",
    "register_rollout_commands",
    "register_storage_commands",
    "register_streaming_commands",
    "register_workflow_commands",
    "register_workload_commands",
]
