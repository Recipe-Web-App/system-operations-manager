"""Base plugin interface and specifications using pluggy."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pluggy

if TYPE_CHECKING:
    import typer

# Define the plugin hookspec namespace
hookspec = pluggy.HookspecMarker("system_operations_manager")
hookimpl = pluggy.HookimplMarker("system_operations_manager")


class _PluginSpec:
    """Plugin hook specifications - defines the plugin contract."""

    @hookspec
    def initialize(self, config: dict[str, Any]) -> None:
        """Initialize the plugin with configuration.

        Args:
            config: Plugin-specific configuration dictionary.
        """

    @hookspec
    def register_commands(self, app: typer.Typer) -> None:
        """Register CLI commands with the main application.

        Args:
            app: The main Typer application to register commands with.
        """

    @hookspec
    def cleanup(self) -> None:
        """Cleanup plugin resources on shutdown."""

    @hookspec
    def get_name(self) -> str:
        """Return the plugin name."""
        return ""

    @hookspec
    def get_version(self) -> str:
        """Return the plugin version."""
        return ""


class Plugin:
    """Base class for all plugins.

    Plugins should inherit from this class and implement the required methods.
    """

    name: str = "base"
    version: str = "0.0.0"
    description: str = ""

    def __init__(self) -> None:
        """Initialize the plugin instance."""
        if self.name == "base":
            raise ValueError(f"{self.__class__.__name__} must define 'name' class attribute")
        if self.version == "0.0.0":
            raise ValueError(f"{self.__class__.__name__} must define 'version' class attribute")
        self._config: dict[str, Any] = {}
        self._initialized: bool = False

    @hookimpl
    def get_name(self) -> str:
        """Return the plugin name."""
        return self.name

    @hookimpl
    def get_version(self) -> str:
        """Return the plugin version."""
        return self.version

    @hookimpl
    def initialize(self, config: dict[str, Any]) -> None:
        """Initialize the plugin with configuration."""
        self._config = config
        self._initialized = True
        self.on_initialize()

    def on_initialize(self) -> None:
        """Hook for subclasses to perform initialization logic."""

    @hookimpl
    def register_commands(self, app: typer.Typer) -> None:
        """Register CLI commands. Override in subclasses."""

    @hookimpl
    def cleanup(self) -> None:
        """Cleanup resources. Override in subclasses."""
        self._initialized = False

    def get_config(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self._config.get(key, default)

    @property
    def is_initialized(self) -> bool:
        """Check if the plugin is initialized."""
        return self._initialized
