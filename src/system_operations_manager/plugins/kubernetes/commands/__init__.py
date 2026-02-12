"""Kubernetes CLI command modules."""

from system_operations_manager.plugins.kubernetes.commands.clusters import (
    register_cluster_commands,
)
from system_operations_manager.plugins.kubernetes.commands.config_resources import (
    register_config_commands,
)
from system_operations_manager.plugins.kubernetes.commands.jobs import register_job_commands
from system_operations_manager.plugins.kubernetes.commands.manifests import (
    register_manifest_commands,
)
from system_operations_manager.plugins.kubernetes.commands.namespaces import (
    register_namespace_commands,
)
from system_operations_manager.plugins.kubernetes.commands.networking import (
    register_networking_commands,
)
from system_operations_manager.plugins.kubernetes.commands.policies import (
    register_policy_commands,
)
from system_operations_manager.plugins.kubernetes.commands.rbac import register_rbac_commands
from system_operations_manager.plugins.kubernetes.commands.storage import register_storage_commands
from system_operations_manager.plugins.kubernetes.commands.workloads import (
    register_workload_commands,
)

__all__ = [
    "register_cluster_commands",
    "register_config_commands",
    "register_job_commands",
    "register_manifest_commands",
    "register_namespace_commands",
    "register_networking_commands",
    "register_policy_commands",
    "register_rbac_commands",
    "register_storage_commands",
    "register_workload_commands",
]
