"""Unit tests for core.plugins.manager module."""

from __future__ import annotations

from typing import cast
from unittest.mock import MagicMock, patch

import pytest

from system_operations_manager.core.plugins.manager import PluginManager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_plugin(name: str = "test", version: str = "1.0.0") -> MagicMock:
    """Return a MagicMock that looks like a Plugin instance."""
    plugin = MagicMock()
    plugin.name = name
    plugin.version = version
    plugin.description = f"{name} plugin"
    plugin.is_initialized = False
    return plugin


def _make_entry_point(name: str, plugin_instance: MagicMock) -> MagicMock:
    """Return a MagicMock that acts as an importlib.metadata EntryPoint."""
    ep = MagicMock()
    ep.name = name
    ep.value = f"fake.module:{name.capitalize()}Plugin"
    plugin_class = MagicMock(return_value=plugin_instance)
    ep.load.return_value = plugin_class
    return ep


# ---------------------------------------------------------------------------
# Tests for PluginManager.__init__
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPluginManagerInit:
    """Tests for PluginManager construction."""

    def test_initial_state(self) -> None:
        """PluginManager starts with empty plugin registry and uninitialised flag."""
        manager = PluginManager()
        assert manager._plugins == {}
        assert manager._initialized is False

    def test_namespace_constant(self) -> None:
        """PluginManager.NAMESPACE has the expected value."""
        assert PluginManager.NAMESPACE == "system_operations_manager.plugins"


# ---------------------------------------------------------------------------
# Tests for discover_plugins
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDiscoverPlugins:
    """Tests for PluginManager.discover_plugins."""

    def test_returns_names_from_entry_points(self) -> None:
        """discover_plugins lists names from the plugin entry points group."""
        ep1 = MagicMock()
        ep1.name = "alpha"
        ep1.value = "pkg.alpha:AlphaPlugin"
        ep2 = MagicMock()
        ep2.name = "beta"
        ep2.value = "pkg.beta:BetaPlugin"

        with patch(
            "system_operations_manager.core.plugins.manager.importlib.metadata.entry_points",
            return_value=[ep1, ep2],
        ):
            manager = PluginManager()
            result = manager.discover_plugins()

        assert result == ["alpha", "beta"]

    def test_returns_empty_list_when_no_entry_points(self) -> None:
        """discover_plugins returns [] when there are no entry points."""
        with patch(
            "system_operations_manager.core.plugins.manager.importlib.metadata.entry_points",
            return_value=[],
        ):
            manager = PluginManager()
            result = manager.discover_plugins()

        assert result == []

    def test_returns_empty_list_and_logs_on_exception(self) -> None:
        """discover_plugins catches exceptions and returns an empty list."""
        with patch(
            "system_operations_manager.core.plugins.manager.importlib.metadata.entry_points",
            side_effect=RuntimeError("metadata error"),
        ):
            manager = PluginManager()
            result = manager.discover_plugins()

        assert result == []


# ---------------------------------------------------------------------------
# Tests for load_plugin
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLoadPlugin:
    """Tests for PluginManager.load_plugin."""

    def test_returns_true_when_plugin_already_loaded(self) -> None:
        """load_plugin returns True immediately if the plugin is already registered."""
        plugin = _make_plugin("existing")
        manager = PluginManager()
        manager._plugins["existing"] = plugin

        result = manager.load_plugin("existing")

        assert result is True

    def test_loads_plugin_successfully(self) -> None:
        """load_plugin registers the plugin and returns True on success."""
        plugin_instance = _make_plugin("fresh")
        ep = _make_entry_point("fresh", plugin_instance)

        with patch(
            "system_operations_manager.core.plugins.manager.importlib.metadata.entry_points",
            return_value=[ep],
        ):
            manager = PluginManager()
            result = manager.load_plugin("fresh")

        assert result is True
        assert "fresh" in manager._plugins

    def test_returns_false_when_plugin_not_found(self) -> None:
        """load_plugin returns False when no matching entry point exists."""
        with patch(
            "system_operations_manager.core.plugins.manager.importlib.metadata.entry_points",
            return_value=[],
        ):
            manager = PluginManager()
            result = manager.load_plugin("nonexistent")

        assert result is False

    def test_returns_false_on_load_exception(self) -> None:
        """load_plugin returns False when loading the entry point raises an exception."""
        ep = MagicMock()
        ep.name = "broken"
        ep.load.side_effect = ImportError("cannot import")

        with patch(
            "system_operations_manager.core.plugins.manager.importlib.metadata.entry_points",
            return_value=[ep],
        ):
            manager = PluginManager()
            result = manager.load_plugin("broken")

        assert result is False


# ---------------------------------------------------------------------------
# Tests for initialize_all
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestInitializeAll:
    """Tests for PluginManager.initialize_all."""

    def test_sets_initialized_flag(self) -> None:
        """initialize_all marks the manager as initialized after running."""
        plugin = _make_plugin("p1")
        manager = PluginManager()
        manager._plugins["p1"] = plugin

        manager.initialize_all({})

        assert manager._initialized is True

    def test_passes_plugin_specific_config(self) -> None:
        """initialize_all extracts per-plugin config from the global config dict."""
        plugin = _make_plugin("p1")
        manager = PluginManager()
        manager._plugins["p1"] = plugin

        global_config = {"plugins": {"p1": {"key": "val"}}}
        manager.initialize_all(global_config)

        plugin.initialize.assert_called_once_with({"key": "val"})

    def test_logs_error_and_continues_on_exception(self) -> None:
        """initialize_all handles per-plugin exceptions without propagating them."""
        good_plugin = _make_plugin("good")
        bad_plugin = _make_plugin("bad")
        bad_plugin.initialize.side_effect = RuntimeError("init failed")

        manager = PluginManager()
        manager._plugins["good"] = good_plugin
        manager._plugins["bad"] = bad_plugin

        # Should not raise
        manager.initialize_all({})

        assert manager._initialized is True
        good_plugin.initialize.assert_called_once()


# ---------------------------------------------------------------------------
# Tests for register_commands
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRegisterCommands:
    """Tests for PluginManager.register_commands."""

    def test_delegates_to_hook(self) -> None:
        """register_commands calls the pluggy hook."""
        manager = PluginManager()
        mock_app = MagicMock()
        object.__setattr__(manager._pm.hook, "register_commands", MagicMock())

        manager.register_commands(mock_app)

        cast(MagicMock, manager._pm.hook.register_commands).assert_called_once_with(app=mock_app)

    def test_swallows_hook_exception(self) -> None:
        """register_commands catches exceptions from the pluggy hook."""
        manager = PluginManager()
        object.__setattr__(
            manager._pm.hook, "register_commands", MagicMock(side_effect=RuntimeError("hook error"))
        )
        mock_app = MagicMock()

        # Should not raise
        manager.register_commands(mock_app)


# ---------------------------------------------------------------------------
# Tests for cleanup_all
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCleanupAll:
    """Tests for PluginManager.cleanup_all."""

    def test_resets_initialized_flag(self) -> None:
        """cleanup_all sets _initialized back to False."""
        manager = PluginManager()
        manager._initialized = True

        manager.cleanup_all()

        assert manager._initialized is False

    def test_swallows_hook_exception(self) -> None:
        """cleanup_all catches exceptions from the cleanup hook."""
        manager = PluginManager()
        object.__setattr__(
            manager._pm.hook, "cleanup", MagicMock(side_effect=RuntimeError("cleanup error"))
        )

        # Should not raise
        manager.cleanup_all()

        assert manager._initialized is False


# ---------------------------------------------------------------------------
# Tests for get_plugin
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetPlugin:
    """Tests for PluginManager.get_plugin."""

    def test_returns_plugin_when_present(self) -> None:
        """get_plugin returns the plugin instance for a registered name."""
        plugin = _make_plugin("alpha")
        manager = PluginManager()
        manager._plugins["alpha"] = plugin

        result = manager.get_plugin("alpha")

        assert result is plugin

    def test_returns_none_when_absent(self) -> None:
        """get_plugin returns None for an unknown plugin name."""
        manager = PluginManager()

        result = manager.get_plugin("missing")

        assert result is None


# ---------------------------------------------------------------------------
# Tests for list_plugins
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestListPlugins:
    """Tests for PluginManager.list_plugins."""

    def test_returns_empty_list_when_no_plugins(self) -> None:
        """list_plugins returns [] when no plugins are registered."""
        manager = PluginManager()
        assert manager.list_plugins() == []

    def test_returns_info_dicts_for_registered_plugins(self) -> None:
        """list_plugins returns a list of info dicts for every registered plugin."""
        plugin = _make_plugin("my_plugin")
        plugin.is_initialized = True
        manager = PluginManager()
        manager._plugins["my_plugin"] = plugin

        result = manager.list_plugins()

        assert result is not None

        assert len(result) == 1
        info = result[0]
        assert info["name"] == "my_plugin"
        assert info["version"] == "1.0.0"
        assert info["description"] == "my_plugin plugin"
        assert info["initialized"] is True
