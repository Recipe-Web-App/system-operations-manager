"""Tests for editor utility functions."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from system_operations_manager.utils.editor import (
    create_merge_template,
    get_editor,
    parse_merge_result,
    strip_json_comments,
)


@pytest.mark.unit
class TestGetEditor:
    """Tests for get_editor function."""

    def test_returns_profile_config_editor_first(self) -> None:
        """Test that profile config editor takes priority."""
        mock_config = MagicMock()
        mock_config.profiles = {"default": MagicMock(default_editor="code --wait")}

        with patch("system_operations_manager.core.config.load_config", return_value=mock_config):
            result = get_editor()
            assert result == "code --wait"

    def test_ops_default_editor_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test OPS_DEFAULT_EDITOR env var is used."""
        monkeypatch.setenv("OPS_DEFAULT_EDITOR", "nano")
        monkeypatch.delenv("EDITOR", raising=False)
        monkeypatch.delenv("VISUAL", raising=False)

        with patch("system_operations_manager.core.config.load_config", return_value=None):
            result = get_editor()
            assert result == "nano"

    def test_editor_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test EDITOR env var is used when OPS_DEFAULT_EDITOR not set."""
        monkeypatch.delenv("OPS_DEFAULT_EDITOR", raising=False)
        monkeypatch.setenv("EDITOR", "emacs")
        monkeypatch.delenv("VISUAL", raising=False)

        with patch("system_operations_manager.core.config.load_config", return_value=None):
            result = get_editor()
            assert result == "emacs"

    def test_visual_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test VISUAL env var is used as fallback."""
        monkeypatch.delenv("OPS_DEFAULT_EDITOR", raising=False)
        monkeypatch.delenv("EDITOR", raising=False)
        monkeypatch.setenv("VISUAL", "subl")

        with patch("system_operations_manager.core.config.load_config", return_value=None):
            result = get_editor()
            assert result == "subl"

    def test_vim_fallback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test vim is used as final fallback."""
        monkeypatch.delenv("OPS_DEFAULT_EDITOR", raising=False)
        monkeypatch.delenv("EDITOR", raising=False)
        monkeypatch.delenv("VISUAL", raising=False)

        with patch("system_operations_manager.core.config.load_config", return_value=None):
            result = get_editor()
            assert result == "vim"

    def test_import_error_falls_through(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that ImportError in config loading falls through to env vars."""
        monkeypatch.setenv("OPS_DEFAULT_EDITOR", "nano")
        monkeypatch.delenv("EDITOR", raising=False)
        monkeypatch.delenv("VISUAL", raising=False)

        import builtins

        real_import = builtins.__import__

        def failing_import(name: str, *args: Any, **kwargs: Any) -> Any:
            if name == "system_operations_manager.core.config":
                raise ImportError("no module")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=failing_import):
            result = get_editor()
            assert result == "nano"

    def test_config_no_default_profile(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test fallback when config has no default profile."""
        monkeypatch.setenv("EDITOR", "emacs")
        monkeypatch.delenv("OPS_DEFAULT_EDITOR", raising=False)
        monkeypatch.delenv("VISUAL", raising=False)

        mock_config = MagicMock()
        mock_config.profiles = {}

        with patch("system_operations_manager.core.config.load_config", return_value=mock_config):
            result = get_editor()
            assert result == "emacs"

    def test_config_profile_no_editor(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test fallback when default profile has no editor set."""
        monkeypatch.delenv("OPS_DEFAULT_EDITOR", raising=False)
        monkeypatch.delenv("EDITOR", raising=False)
        monkeypatch.delenv("VISUAL", raising=False)

        mock_config = MagicMock()
        mock_config.profiles = {"default": MagicMock(default_editor=None)}

        with patch("system_operations_manager.core.config.load_config", return_value=mock_config):
            result = get_editor()
            assert result == "vim"

    def test_priority_chain(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that config takes priority over all env vars."""
        monkeypatch.setenv("OPS_DEFAULT_EDITOR", "nano")
        monkeypatch.setenv("EDITOR", "emacs")
        monkeypatch.setenv("VISUAL", "subl")

        mock_config = MagicMock()
        mock_config.profiles = {"default": MagicMock(default_editor="code --wait")}

        with patch("system_operations_manager.core.config.load_config", return_value=mock_config):
            result = get_editor()
            assert result == "code --wait"


@pytest.mark.unit
class TestCreateMergeTemplate:
    """Tests for create_merge_template function."""

    @pytest.fixture
    def sample_conflict(self) -> Any:
        """Create a sample conflict for testing."""
        from system_operations_manager.services.kong.conflict_resolver import Conflict

        return Conflict(
            entity_type="services",
            entity_name="my-service",
            entity_id="svc-123",
            source_state={"host": "new-api.example.com", "port": 8080},
            target_state={"host": "old-api.example.com", "port": 8080},
            drift_fields=["host"],
            source_system_id="svc-123",
            target_system_id="svc-456",
            direction="push",
        )

    def test_includes_source_state(self, sample_conflict: Any) -> None:
        """Test that template includes source state."""
        template = create_merge_template(sample_conflict)
        assert "new-api.example.com" in template
        assert "Source (Gateway)" in template

    def test_includes_target_state(self, sample_conflict: Any) -> None:
        """Test that template includes target state."""
        template = create_merge_template(sample_conflict)
        assert "old-api.example.com" in template
        assert "Target (Konnect)" in template

    def test_includes_conflict_field_markers(self, sample_conflict: Any) -> None:
        """Test that drift fields are marked as CHANGED."""
        template = create_merge_template(sample_conflict)
        assert "CHANGED - Field: host" in template

    def test_valid_json_output(self, sample_conflict: Any) -> None:
        """Test that template produces valid JSON after stripping comments."""
        template = create_merge_template(sample_conflict)
        cleaned = strip_json_comments(template)
        result = json.loads(cleaned)
        assert isinstance(result, dict)
        assert "host" in result

    def test_multiline_value_handling(self) -> None:
        """Test that multi-line JSON values are indented properly in template."""
        from system_operations_manager.services.kong.conflict_resolver import Conflict

        conflict = Conflict(
            entity_type="services",
            entity_name="my-service",
            entity_id="svc-123",
            source_state={"tags": ["tag1", "tag2", "tag3"]},
            target_state={"tags": ["old-tag"]},
            drift_fields=["tags"],
            source_system_id="svc-123",
            target_system_id="svc-456",
            direction="push",
        )
        template = create_merge_template(conflict)
        # Multi-line array should be indented within the template
        assert '"tags": [\n' in template
        # Verify it still produces valid JSON after stripping comments
        cleaned = strip_json_comments(template)
        result = json.loads(cleaned)
        assert result["tags"] == ["tag1", "tag2", "tag3"]


@pytest.mark.unit
class TestParseMergeResult:
    """Tests for parse_merge_result function."""

    def test_strips_comments(self) -> None:
        """Test that comments are stripped from content."""
        content = """
        // This is a comment
        {
          "host": "api.example.com", // inline comment
          "port": 8080
        }
        """
        result = parse_merge_result(content)
        assert result["host"] == "api.example.com"
        assert result["port"] == 8080

    def test_parses_valid_json(self) -> None:
        """Test that valid JSON is parsed correctly."""
        content = '{"name": "test", "value": 123}'
        result = parse_merge_result(content)
        assert result["name"] == "test"
        assert result["value"] == 123

    def test_raises_on_invalid_json(self) -> None:
        """Test that invalid JSON raises exception."""
        content = "this is not json"
        with pytest.raises(json.JSONDecodeError):
            parse_merge_result(content)

    def test_handles_escaped_characters(self) -> None:
        """Test that escape sequences inside strings are handled properly."""
        content = '{"path": "C:\\\\server\\\\share"} // comment'
        result = parse_merge_result(content)
        assert result["path"] == "C:\\server\\share"

    def test_handles_backslash_before_quote(self) -> None:
        """Test that escaped quotes inside strings are handled properly."""
        content = '{"msg": "say \\"hello\\""} // trailing comment'
        result = parse_merge_result(content)
        assert result["msg"] == 'say "hello"'

    def test_raises_on_non_dict(self) -> None:
        """Test that non-dict JSON raises ValueError."""
        content = "[1, 2, 3]"
        with pytest.raises(ValueError, match="Expected a JSON object"):
            parse_merge_result(content)


@pytest.mark.unit
class TestStripJsonComments:
    """Tests for strip_json_comments function."""

    def test_strips_line_comments(self) -> None:
        """Test that line comments are stripped."""
        content = """// comment
{"key": "value"}"""
        result = strip_json_comments(content)
        assert "//" not in result
        assert '{"key": "value"}' in result

    def test_preserves_urls_in_strings(self) -> None:
        """Test that // in strings (like URLs) is preserved."""
        content = '{"url": "https://example.com"}'
        result = strip_json_comments(content)
        assert "https://example.com" in result

    def test_handles_escaped_characters(self) -> None:
        """Test that escaped characters in strings don't break comment detection."""
        content = '{"path": "C:\\\\server\\\\share"} // comment'
        result = strip_json_comments(content)
        assert "C:\\\\server\\\\share" in result
        assert "// comment" not in result

    def test_handles_escaped_quote_in_string(self) -> None:
        """Test that escaped quotes inside strings are handled correctly."""
        content = '{"msg": "say \\"hello\\""} // comment'
        result = strip_json_comments(content)
        assert '\\"hello\\"' in result
        assert "// comment" not in result
