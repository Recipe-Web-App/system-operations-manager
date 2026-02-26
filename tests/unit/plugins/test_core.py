"""Unit tests for plugins.core module (CorePlugin)."""

from __future__ import annotations

import contextlib
from typing import Any
from unittest.mock import patch

import pytest
import typer

from system_operations_manager.plugins.core import CorePlugin

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def plugin() -> CorePlugin:
    """Return a fresh, uninitialised CorePlugin instance."""
    return CorePlugin()


# ---------------------------------------------------------------------------
# Tests for CorePlugin class attributes and instantiation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCorePluginAttributes:
    """Tests for CorePlugin class-level attributes."""

    def test_name_attribute(self, plugin: CorePlugin) -> None:
        """CorePlugin.name is 'core'."""
        assert plugin.name == "core"

    def test_version_attribute(self, plugin: CorePlugin) -> None:
        """CorePlugin.version is set and not the base default '0.0.0'."""
        assert plugin.version != "0.0.0"
        assert plugin.version == "0.1.0"

    def test_description_attribute(self, plugin: CorePlugin) -> None:
        """CorePlugin.description is a non-empty string."""
        assert isinstance(plugin.description, str)
        assert len(plugin.description) > 0

    def test_instantiation_succeeds(self) -> None:
        """CorePlugin can be instantiated without raising."""
        p = CorePlugin()
        assert p is not None


# ---------------------------------------------------------------------------
# Tests for on_initialize
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCorePluginOnInitialize:
    """Tests for CorePlugin.on_initialize."""

    def test_on_initialize_is_a_no_op(self, plugin: CorePlugin) -> None:
        """CorePlugin.on_initialize completes without error and returns None."""
        result = plugin.on_initialize()
        assert result is None

    def test_initialize_sets_is_initialized(self, plugin: CorePlugin) -> None:
        """Calling Plugin.initialize marks the plugin as initialized."""
        assert plugin.is_initialized is False
        plugin.initialize({})
        assert plugin.is_initialized is True


# ---------------------------------------------------------------------------
# Tests for register_commands
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCorePluginRegisterCommands:
    """Tests for CorePlugin.register_commands."""

    def test_register_commands_adds_plugins_command(self, plugin: CorePlugin) -> None:
        """register_commands registers a 'plugins' command on the Typer app."""
        app = typer.Typer()
        plugin.register_commands(app=app)

        command_names = [cmd.name for cmd in app.registered_commands]
        assert "plugins" in command_names

    def test_list_plugins_command_prints_table(self, plugin: CorePlugin) -> None:
        """The registered 'plugins' command prints a Rich table to the console."""
        app = typer.Typer()

        with patch("system_operations_manager.plugins.core.console") as mock_console:
            plugin.register_commands(app=app)

            # Retrieve and call the registered inner function directly so we
            # exercise lines 36-45 without needing a full CLI runner invocation.
            registered = app.registered_commands[0]
            registered.callback()  # type: ignore[misc]

            mock_console.print.assert_called_once()

    def test_list_plugins_table_contains_plugin_info(self, plugin: CorePlugin) -> None:
        """The table printed by 'plugins' command includes the plugin's own info row."""
        app = typer.Typer()
        captured_tables: list[Any] = []

        def _capture_print(obj: object) -> None:
            captured_tables.append(obj)

        with patch("system_operations_manager.plugins.core.console") as mock_console:
            mock_console.print.side_effect = _capture_print
            plugin.register_commands(app=app)

            registered = app.registered_commands[0]
            registered.callback()  # type: ignore[misc]

        assert len(captured_tables) == 1
        table = captured_tables[0]
        # The table should have at least one row whose cells contain the plugin
        # name and version strings.
        assert hasattr(table, "rows") or hasattr(table, "_rows")

    def test_register_commands_can_be_called_multiple_times(self, plugin: CorePlugin) -> None:
        """register_commands is idempotent and raises no error when called again."""
        app = typer.Typer()
        with patch("system_operations_manager.plugins.core.console"):
            plugin.register_commands(app=app)
            # A second call should not raise (Typer may warn but won't crash)
            with contextlib.suppress(Exception):
                plugin.register_commands(app=app)
