"""Plugin manager for loading and managing plugins."""

from __future__ import annotations

import importlib.metadata
from typing import TYPE_CHECKING, Any

import pluggy
import structlog

from system_operations_manager.core.plugins.base import Plugin, _PluginSpec

if TYPE_CHECKING:
    import typer

logger = structlog.get_logger()


class PluginManager:
    """Manages plugin discovery, loading, and lifecycle."""

    NAMESPACE = "system_operations_manager.plugins"

    def __init__(self) -> None:
        """Initialize the plugin manager."""
        self._pm = pluggy.PluginManager("system_operations_manager")
        self._pm.add_hookspecs(_PluginSpec)
        self._plugins: dict[str, Plugin] = {}
        self._initialized = False

    def discover_plugins(self) -> list[str]:
        """Discover available plugins from entry points.

        Returns:
            List of discovered plugin names.
        """
        discovered = []
        try:
            eps = importlib.metadata.entry_points(group=self.NAMESPACE)
            for ep in eps:
                discovered.append(ep.name)
                logger.debug("Discovered plugin", name=ep.name, value=ep.value)
        except Exception as e:
            logger.warning("Error discovering plugins", error=str(e))
        return discovered

    def load_plugin(self, name: str) -> bool:
        """Load a plugin by name from entry points.

        Args:
            name: The plugin name to load.

        Returns:
            True if loaded successfully, False otherwise.
        """
        if name in self._plugins:
            logger.debug("Plugin already loaded", name=name)
            return True

        try:
            eps = importlib.metadata.entry_points(group=self.NAMESPACE)
            for ep in eps:
                if ep.name == name:
                    plugin_class = ep.load()
                    plugin = plugin_class() if callable(plugin_class) else plugin_class

                    self._pm.register(plugin, name=name)
                    self._plugins[name] = plugin
                    logger.info("Loaded plugin", name=name, version=plugin.version)
                    return True

            logger.warning("Plugin not found", name=name)
            return False
        except Exception as e:
            logger.error("Failed to load plugin", name=name, error=str(e))
            return False

    def initialize_all(self, config: dict[str, Any]) -> None:
        """Initialize all loaded plugins with configuration.

        Args:
            config: Global configuration dictionary.
        """
        for name, plugin in self._plugins.items():
            plugin_config = config.get("plugins", {}).get(name, {})
            try:
                plugin.initialize(plugin_config)
                logger.info("Initialized plugin", name=name)
            except Exception as e:
                logger.error("Failed to initialize plugin", name=name, error=str(e))

        self._initialized = True

    def register_commands(self, app: typer.Typer) -> None:
        """Register commands from all loaded plugins.

        Args:
            app: The Typer application to register commands with.
        """
        try:
            self._pm.hook.register_commands(app=app)
        except Exception as e:
            logger.error("Error registering plugin commands", error=str(e))

    def cleanup_all(self) -> None:
        """Cleanup all loaded plugins."""
        try:
            self._pm.hook.cleanup()
        except Exception as e:
            logger.error("Error during plugin cleanup", error=str(e))
        self._initialized = False

    def get_plugin(self, name: str) -> Plugin | None:
        """Get a loaded plugin by name."""
        return self._plugins.get(name)

    def list_plugins(self) -> list[dict[str, Any]]:
        """List all loaded plugins with their info."""
        return [
            {
                "name": p.name,
                "version": p.version,
                "description": p.description,
                "initialized": p.is_initialized,
            }
            for p in self._plugins.values()
        ]
