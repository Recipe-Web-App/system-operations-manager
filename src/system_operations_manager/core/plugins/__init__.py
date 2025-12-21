"""Plugin system for system_operations_manager."""

from system_operations_manager.core.plugins.base import Plugin, hookimpl, hookspec
from system_operations_manager.core.plugins.manager import PluginManager

__all__ = ["Plugin", "PluginManager", "hookimpl", "hookspec"]
