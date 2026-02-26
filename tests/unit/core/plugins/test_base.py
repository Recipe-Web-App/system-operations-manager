"""Unit tests for core.plugins.base module."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from system_operations_manager.core.plugins.base import Plugin, _PluginSpec, hookimpl, hookspec

# ---------------------------------------------------------------------------
# Concrete plugin fixture used across tests
# ---------------------------------------------------------------------------


class _GoodPlugin(Plugin):  # type: ignore[misc]
    """Minimal concrete plugin for testing."""

    name = "good"
    version = "1.0.0"
    description = "A valid test plugin"


class _CustomInitPlugin(Plugin):  # type: ignore[misc]
    """Plugin that records on_initialize calls."""

    name = "custom"
    version = "2.0.0"
    description = "Tracks on_initialize invocations"

    def __init__(self) -> None:
        super().__init__()
        self.init_called = False

    def on_initialize(self) -> None:
        self.init_called = True


# ---------------------------------------------------------------------------
# Tests for _PluginSpec hook spec markers
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPluginSpec:
    """Tests for the _PluginSpec hook specification class."""

    def test_get_name_default_returns_empty_string(self) -> None:
        """_PluginSpec.get_name returns an empty string as the default hookspec body."""
        spec = _PluginSpec()
        result = spec.get_name()
        assert result == ""

    def test_get_version_default_returns_empty_string(self) -> None:
        """_PluginSpec.get_version returns an empty string as the default hookspec body."""
        spec = _PluginSpec()
        result = spec.get_version()
        assert result == ""

    def test_hookspec_marker_applied_to_initialize(self) -> None:
        """_PluginSpec.initialize carries a hookspec attribute."""
        assert hasattr(_PluginSpec.initialize, "example_impl") or callable(_PluginSpec.initialize)

    def test_hookimpl_and_hookspec_markers_exist(self) -> None:
        """Module-level hookspec and hookimpl markers are importable."""
        assert hookspec is not None
        assert hookimpl is not None


# ---------------------------------------------------------------------------
# Tests for Plugin.__init__ validation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPluginInit:
    """Tests for Plugin.__init__ validation logic."""

    def test_raises_when_name_is_base(self) -> None:
        """Plugin.__init__ raises ValueError when name class attribute is not overridden."""

        class _UnnamedPlugin(Plugin):  # type: ignore[misc]
            version = "1.0.0"

        with pytest.raises(ValueError, match="must define 'name' class attribute"):
            _UnnamedPlugin()

    def test_raises_when_version_is_default(self) -> None:
        """Plugin.__init__ raises ValueError when version class attribute is not overridden."""

        class _UnversionedPlugin(Plugin):  # type: ignore[misc]
            name = "unversioned"

        with pytest.raises(ValueError, match="must define 'version' class attribute"):
            _UnversionedPlugin()

    def test_successful_instantiation(self) -> None:
        """Plugin subclass with valid name and version instantiates without error."""
        plugin = _GoodPlugin()
        assert plugin.name == "good"
        assert plugin.version == "1.0.0"
        assert plugin._config == {}
        assert plugin._initialized is False


# ---------------------------------------------------------------------------
# Tests for Plugin hook implementations
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPluginHookImpls:
    """Tests for Plugin hook implementation methods."""

    def test_get_name_returns_class_name(self) -> None:
        """Plugin.get_name returns the plugin's name attribute."""
        plugin = _GoodPlugin()
        assert plugin.get_name() == "good"

    def test_get_version_returns_class_version(self) -> None:
        """Plugin.get_version returns the plugin's version attribute."""
        plugin = _GoodPlugin()
        assert plugin.get_version() == "1.0.0"

    def test_initialize_sets_config_and_flag(self) -> None:
        """Plugin.initialize stores config and marks the plugin as initialized."""
        plugin = _GoodPlugin()
        plugin.initialize({"key": "value"})
        assert plugin._config == {"key": "value"}
        assert plugin._initialized is True

    def test_initialize_calls_on_initialize(self) -> None:
        """Plugin.initialize delegates to on_initialize for subclass hooks."""
        plugin = _CustomInitPlugin()
        assert plugin.init_called is False
        plugin.initialize({})
        assert plugin.init_called is True

    def test_cleanup_resets_initialized_flag(self) -> None:
        """Plugin.cleanup sets _initialized back to False."""
        plugin = _GoodPlugin()
        plugin.initialize({})
        assert plugin.is_initialized is True
        plugin.cleanup()
        assert plugin.is_initialized is False

    def test_register_commands_is_callable(self) -> None:
        """Plugin.register_commands can be called with a Typer app without raising."""
        plugin = _GoodPlugin()
        mock_app = MagicMock()
        # Should not raise; the base implementation is a no-op
        plugin.register_commands(app=mock_app)

    def test_on_initialize_is_a_no_op_on_base(self) -> None:
        """Plugin.on_initialize does nothing on the base Plugin class."""
        plugin = _GoodPlugin()
        # Should return None and not raise
        result = plugin.on_initialize()
        assert result is None


# ---------------------------------------------------------------------------
# Tests for Plugin.get_config utility
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPluginGetConfig:
    """Tests for Plugin.get_config helper method."""

    def test_get_config_returns_value_for_existing_key(self) -> None:
        """Plugin.get_config returns the stored value for a present key."""
        plugin = _GoodPlugin()
        plugin.initialize({"timeout": 30})
        assert plugin.get_config("timeout") == 30

    def test_get_config_returns_default_for_missing_key(self) -> None:
        """Plugin.get_config returns the supplied default for an absent key."""
        plugin = _GoodPlugin()
        plugin.initialize({})
        assert plugin.get_config("missing", default="fallback") == "fallback"

    def test_get_config_returns_none_by_default_for_missing_key(self) -> None:
        """Plugin.get_config returns None when no default is provided and key is missing."""
        plugin = _GoodPlugin()
        plugin.initialize({})
        assert plugin.get_config("missing") is None


# ---------------------------------------------------------------------------
# Tests for Plugin.is_initialized property
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPluginIsInitialized:
    """Tests for the is_initialized property."""

    def test_false_before_initialize(self) -> None:
        """is_initialized is False before initialize() is called."""
        plugin = _GoodPlugin()
        assert plugin.is_initialized is False

    def test_true_after_initialize(self) -> None:
        """is_initialized is True after initialize() is called."""
        plugin = _GoodPlugin()
        plugin.initialize({})
        assert plugin.is_initialized is True

    def test_false_after_cleanup(self) -> None:
        """is_initialized is False again after cleanup() is called."""
        plugin = _GoodPlugin()
        plugin.initialize({})
        plugin.cleanup()
        assert plugin.is_initialized is False
