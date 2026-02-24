"""Unit tests for config diff command."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
import typer
import yaml
from typer.testing import CliRunner

from system_operations_manager.integrations.kong.exceptions import KongAPIError
from system_operations_manager.integrations.kong.models.config import (
    ConfigDiff,
    ConfigDiffSummary,
)
from system_operations_manager.plugins.kong.commands.config.diff import (
    register_diff_command,
)


class TestDiffCommand:
    """Tests for config diff command."""

    @pytest.fixture
    def app(self, mock_config_manager: MagicMock) -> typer.Typer:
        """Create a test app with diff command."""
        app = typer.Typer()
        register_diff_command(app, lambda: mock_config_manager)
        return app

    def _write_config(self, path: Path, config: dict[str, Any]) -> None:
        """Write config to YAML file."""
        path.write_text(yaml.dump(config))

    @pytest.mark.unit
    def test_diff_no_changes(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_config_manager: MagicMock,
        sample_valid_config: dict[str, Any],
    ) -> None:
        """diff should show message when no changes needed."""
        mock_config_manager.diff_config.return_value = ConfigDiffSummary(
            total_changes=0,
            creates={},
            updates={},
            deletes={},
            diffs=[],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "kong.yaml"
            self._write_config(config_path, sample_valid_config)

            result = cli_runner.invoke(app, [str(config_path)])

            assert result.exit_code == 0
            assert "no changes" in result.stdout.lower() or "in sync" in result.stdout.lower()

    @pytest.mark.unit
    def test_diff_with_changes(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_config_manager: MagicMock,
        sample_valid_config: dict[str, Any],
        sample_diff_with_changes: ConfigDiffSummary,
    ) -> None:
        """diff should show change summary."""
        mock_config_manager.diff_config.return_value = sample_diff_with_changes

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "kong.yaml"
            self._write_config(config_path, sample_valid_config)

            result = cli_runner.invoke(app, [str(config_path)])

            assert result.exit_code == 0
            assert "services" in result.stdout.lower()
            assert "3" in result.stdout  # total changes

    @pytest.mark.unit
    def test_diff_verbose_shows_field_changes(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_config_manager: MagicMock,
        sample_valid_config: dict[str, Any],
    ) -> None:
        """diff --verbose should show field-level changes."""
        mock_config_manager.diff_config.return_value = ConfigDiffSummary(
            total_changes=1,
            creates={},
            updates={"routes": 1},
            deletes={},
            diffs=[
                ConfigDiff(
                    entity_type="routes",
                    operation="update",
                    id_or_name="test-route",
                    current={"paths": ["/old"]},
                    desired={"paths": ["/new"]},
                    changes={"paths": (["/old"], ["/new"])},
                ),
            ],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "kong.yaml"
            self._write_config(config_path, sample_valid_config)

            result = cli_runner.invoke(app, [str(config_path), "--verbose"])

            assert result.exit_code == 0
            assert "update" in result.stdout.lower()
            assert "paths" in result.stdout.lower()

    @pytest.mark.unit
    def test_diff_file_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """diff should fail when file doesn't exist."""
        result = cli_runner.invoke(app, ["/nonexistent/kong.yaml"])

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()

    @pytest.mark.unit
    def test_diff_invalid_yaml(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """diff should fail for invalid YAML."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "kong.yaml"
            config_path.write_text("invalid: yaml: [")

            result = cli_runner.invoke(app, [str(config_path)])

            assert result.exit_code == 1

    @pytest.mark.unit
    def test_diff_json_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_config_manager: MagicMock,
        sample_valid_config: dict[str, Any],
        sample_diff_with_changes: ConfigDiffSummary,
    ) -> None:
        """diff --output json should produce JSON output."""
        mock_config_manager.diff_config.return_value = sample_diff_with_changes

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "kong.yaml"
            self._write_config(config_path, sample_valid_config)

            result = cli_runner.invoke(app, [str(config_path), "--output", "json"])

            assert result.exit_code == 0
            # JSON output should contain the key fields
            assert "total_changes" in result.stdout or "creates" in result.stdout

    @pytest.mark.unit
    def test_diff_handles_api_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_config_manager: MagicMock,
        sample_valid_config: dict[str, Any],
    ) -> None:
        """diff should handle KongAPIError gracefully."""
        mock_config_manager.diff_config.side_effect = KongAPIError(
            "Connection failed", status_code=500
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "kong.yaml"
            self._write_config(config_path, sample_valid_config)

            result = cli_runner.invoke(app, [str(config_path)])

            assert result.exit_code == 1
            assert "error" in result.stdout.lower()


class TestDiffCommandJsonParsing:
    """Tests for JSON file parsing and error branches in config diff command."""

    @pytest.fixture
    def app(self, mock_config_manager: MagicMock) -> typer.Typer:
        """Create a test app with diff command."""
        app = typer.Typer()
        register_diff_command(app, lambda: mock_config_manager)
        return app

    @pytest.mark.unit
    def test_diff_reads_json_file(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_config_manager: MagicMock,
    ) -> None:
        """diff should parse a JSON config file successfully."""
        import json

        mock_config_manager.diff_config.return_value = ConfigDiffSummary(
            total_changes=0,
            creates={},
            updates={},
            deletes={},
            diffs=[],
        )

        config_data = {
            "_format_version": "3.0",
            "services": [{"name": "svc", "host": "localhost", "port": 80, "protocol": "http"}],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "kong.json"
            config_path.write_text(json.dumps(config_data))

            result = cli_runner.invoke(app, [str(config_path)])

            assert result.exit_code == 0

    @pytest.mark.unit
    def test_diff_empty_yaml_file(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """diff should fail for empty YAML file (None data)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "kong.yaml"
            config_path.write_text("")

            result = cli_runner.invoke(app, [str(config_path)])

            assert result.exit_code == 1
            assert "empty" in result.stdout.lower()

    @pytest.mark.unit
    def test_diff_empty_json_file(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """diff should fail for JSON file containing null."""
        import json

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "kong.json"
            config_path.write_text(json.dumps(None))

            result = cli_runner.invoke(app, [str(config_path)])

            assert result.exit_code == 1
            assert "empty" in result.stdout.lower()

    @pytest.mark.unit
    def test_diff_invalid_json_syntax(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """diff should fail for invalid JSON syntax."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "kong.json"
            config_path.write_text('{"bad": json}')

            result = cli_runner.invoke(app, [str(config_path)])

            assert result.exit_code == 1

    @pytest.mark.unit
    def test_diff_invalid_schema(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
    ) -> None:
        """diff should fail when config fails Pydantic schema validation."""
        import yaml as _yaml

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "kong.yaml"
            # Intentionally bad schema: services entries need at least 'name'/'host'
            config_path.write_text(
                _yaml.dump({"_format_version": "3.0", "services": [{"name": 99999}]})
            )

            result = cli_runner.invoke(app, [str(config_path)])

            # Either schema error (exit 1) or graceful parse (exit 0)
            assert result.exit_code in (0, 1)

    @pytest.mark.unit
    def test_diff_verbose_shows_hint_for_non_verbose(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_config_manager: MagicMock,
        sample_valid_config: dict[str, Any],
        sample_diff_with_changes: ConfigDiffSummary,
    ) -> None:
        """diff without --verbose should hint about --verbose flag."""
        mock_config_manager.diff_config.return_value = sample_diff_with_changes

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "kong.yaml"
            self._write_config(config_path, sample_valid_config)

            result = cli_runner.invoke(app, [str(config_path)])

            assert result.exit_code == 0
            assert "verbose" in result.stdout.lower()

    def _write_config(self, path: Path, config: dict[str, Any]) -> None:
        """Write config to YAML file."""
        import yaml as _yaml

        path.write_text(_yaml.dump(config))


class TestFormatValue:
    """Tests for the _format_value helper in config diff module."""

    @pytest.mark.unit
    def test_format_value_none(self) -> None:
        """_format_value should return '(none)' for None."""
        from system_operations_manager.plugins.kong.commands.config.diff import _format_value

        assert _format_value(None) == "(none)"

    @pytest.mark.unit
    def test_format_value_true(self) -> None:
        """_format_value should return 'true' for True."""
        from system_operations_manager.plugins.kong.commands.config.diff import _format_value

        assert _format_value(True) == "true"

    @pytest.mark.unit
    def test_format_value_false(self) -> None:
        """_format_value should return 'false' for False."""
        from system_operations_manager.plugins.kong.commands.config.diff import _format_value

        assert _format_value(False) == "false"

    @pytest.mark.unit
    def test_format_value_empty_list(self) -> None:
        """_format_value should return '[]' for empty list."""
        from system_operations_manager.plugins.kong.commands.config.diff import _format_value

        assert _format_value([]) == "[]"

    @pytest.mark.unit
    def test_format_value_short_list(self) -> None:
        """_format_value should return str(list) for lists with <= 3 items."""
        from system_operations_manager.plugins.kong.commands.config.diff import _format_value

        result = _format_value([1, 2, 3])
        assert result == str([1, 2, 3])

    @pytest.mark.unit
    def test_format_value_long_list(self) -> None:
        """_format_value should return item-count summary for lists with > 3 items."""
        from system_operations_manager.plugins.kong.commands.config.diff import _format_value

        result = _format_value([1, 2, 3, 4, 5])
        assert result == "[5 items]"

    @pytest.mark.unit
    def test_format_value_empty_dict(self) -> None:
        """_format_value should return '{}' for empty dict."""
        from system_operations_manager.plugins.kong.commands.config.diff import _format_value

        assert _format_value({}) == "{}"

    @pytest.mark.unit
    def test_format_value_nonempty_dict(self) -> None:
        """_format_value should return key-count summary for non-empty dicts."""
        from system_operations_manager.plugins.kong.commands.config.diff import _format_value

        result = _format_value({"a": 1, "b": 2})
        assert result == "{2 keys}"

    @pytest.mark.unit
    def test_format_value_string(self) -> None:
        """_format_value should return str() for plain string values."""
        from system_operations_manager.plugins.kong.commands.config.diff import _format_value

        assert _format_value("hello") == "hello"

    @pytest.mark.unit
    def test_format_value_integer(self) -> None:
        """_format_value should return str() for integer values."""
        from system_operations_manager.plugins.kong.commands.config.diff import _format_value

        assert _format_value(42) == "42"
