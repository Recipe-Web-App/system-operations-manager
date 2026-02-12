"""Unit tests for Kyverno policy validation commands."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.plugins.kubernetes.commands.policies import (
    register_policy_commands,
)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestValidateCommands:
    """Tests for Kyverno policy validation commands."""

    @pytest.fixture
    def app(self, get_kyverno_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with policy commands."""
        app = typer.Typer()
        register_policy_commands(app, get_kyverno_manager)
        return app

    def test_validate_valid_policy(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
        tmp_path: object,
    ) -> None:
        """validate should report valid policy."""
        from pathlib import Path

        policy_yaml = """\
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-labels
spec:
  validationFailureAction: Audit
  rules:
    - name: check-labels
      match:
        any:
          - resources:
              kinds:
                - Pod
      validate:
        message: "Labels required"
        pattern:
          metadata:
            labels:
              app: "?*"
"""
        policy_file = Path(str(tmp_path)) / "policy.yaml"
        policy_file.write_text(policy_yaml)

        mock_kyverno_manager.validate_policy.return_value = {
            "valid": True,
            "policy": MagicMock(model_dump=lambda **kwargs: {"name": "require-labels"}),
        }

        result = cli_runner.invoke(app, ["policies", "validate", "--file", str(policy_file)])

        assert result.exit_code == 0
        assert "valid" in result.stdout.lower()
        mock_kyverno_manager.validate_policy.assert_called_once()

    def test_validate_invalid_policy(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
        tmp_path: object,
    ) -> None:
        """validate should report invalid policy."""
        from pathlib import Path

        policy_yaml = """\
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: bad-policy
spec:
  rules: []
"""
        policy_file = Path(str(tmp_path)) / "bad-policy.yaml"
        policy_file.write_text(policy_yaml)

        mock_kyverno_manager.validate_policy.return_value = {
            "valid": False,
            "error": "spec.rules: at least one rule is required",
        }

        result = cli_runner.invoke(app, ["policies", "validate", "--file", str(policy_file)])

        assert result.exit_code == 1
        assert "invalid" in result.stdout.lower()

    def test_validate_invalid_yaml(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        tmp_path: object,
    ) -> None:
        """validate should handle invalid YAML files."""
        from pathlib import Path

        bad_file = Path(str(tmp_path)) / "bad.yaml"
        bad_file.write_text("{{invalid: yaml: [}")

        result = cli_runner.invoke(app, ["policies", "validate", "--file", str(bad_file)])

        assert result.exit_code == 1

    def test_validate_non_dict_yaml(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        tmp_path: object,
    ) -> None:
        """validate should reject YAML that is not a dict."""
        from pathlib import Path

        list_file = Path(str(tmp_path)) / "list.yaml"
        list_file.write_text("- item1\n- item2\n")

        result = cli_runner.invoke(app, ["policies", "validate", "--file", str(list_file)])

        assert result.exit_code == 1
