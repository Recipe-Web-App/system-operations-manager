"""Unit tests for Kyverno policy CLI commands (gap-fill coverage)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import typer
import yaml
from typer.testing import CliRunner

from system_operations_manager.integrations.kubernetes.exceptions import (
    KubernetesAuthError,
    KubernetesConnectionError,
    KubernetesError,
    KubernetesNotFoundError,
    KubernetesTimeoutError,
)
from system_operations_manager.plugins.kubernetes.commands.policies import (
    _parse_labels,
    _parse_rules,
    register_policy_commands,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def mock_kyverno_manager() -> MagicMock:
    """Create a mock KyvernoManager."""
    manager = MagicMock()

    manager.list_cluster_policies.return_value = []
    manager.get_cluster_policy.return_value = MagicMock(
        model_dump=lambda **kwargs: {"name": "require-labels", "rules_count": 1}
    )
    manager.create_cluster_policy.return_value = MagicMock(
        model_dump=lambda **kwargs: {"name": "require-labels", "rules_count": 0}
    )
    manager.delete_cluster_policy.return_value = None

    manager.list_policies.return_value = []
    manager.get_policy.return_value = MagicMock(
        model_dump=lambda **kwargs: {
            "name": "restrict-images",
            "namespace": "default",
            "rules_count": 1,
        }
    )
    manager.create_policy.return_value = MagicMock(
        model_dump=lambda **kwargs: {
            "name": "restrict-images",
            "namespace": "default",
        }
    )
    manager.delete_policy.return_value = None
    manager.validate_policy.return_value = {
        "valid": True,
        "policy": MagicMock(model_dump=lambda **kwargs: {"name": "my-policy"}),
    }

    manager.list_cluster_policy_reports.return_value = []
    manager.get_cluster_policy_report.return_value = MagicMock(
        model_dump=lambda **kwargs: {"name": "cpolr-require-labels", "pass_count": 5}
    )

    manager.list_policy_reports.return_value = []
    manager.get_policy_report.return_value = MagicMock(
        model_dump=lambda **kwargs: {
            "name": "polr-restrict-images",
            "namespace": "default",
            "pass_count": 3,
        }
    )

    manager.get_admission_status.return_value = {
        "running": True,
        "replicas": 2,
        "ready_replicas": 2,
    }

    return manager


@pytest.fixture
def get_kyverno_manager(mock_kyverno_manager: MagicMock) -> Callable[[], MagicMock]:
    """Factory returning the mock KyvernoManager."""
    return lambda: mock_kyverno_manager


@pytest.fixture
def app(get_kyverno_manager: Callable[[], MagicMock]) -> typer.Typer:
    """Create a test Typer app with policy commands registered."""
    test_app = typer.Typer()
    register_policy_commands(test_app, get_kyverno_manager)
    return test_app


# =============================================================================
# Tests for _parse_labels helper  (line 31, 88-90)
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestParseLabels:
    """Tests for the _parse_labels helper function in policies module."""

    def test_returns_none_for_none_input(self) -> None:
        """Should return None when labels is None (line 31 TYPE_CHECKING branch)."""
        result = _parse_labels(None)
        assert result is None

    def test_returns_none_for_empty_list(self) -> None:
        """Should return None when labels is an empty list."""
        result = _parse_labels([])
        assert result is None

    def test_parses_valid_labels(self) -> None:
        """Should parse valid key=value labels into a dict."""
        result = _parse_labels(["app=security", "env=prod"])
        assert result == {"app": "security", "env": "prod"}

    def test_invalid_label_format_prints_error_and_exits(self) -> None:
        """Should print error and raise typer.Exit(1) on bad label (lines 88-90)."""
        with pytest.raises(typer.Exit) as exc_info:
            _parse_labels(["invalid-label"])
        assert exc_info.value.exit_code == 1

    def test_invalid_label_no_separator_exits(self) -> None:
        """Should exit when label string has no = separator."""
        with pytest.raises(typer.Exit):
            _parse_labels(["keyonly"])


# =============================================================================
# Tests for _parse_rules helper  (lines 103-105)
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestParseRules:
    """Tests for the _parse_rules helper function."""

    def test_returns_none_for_none_input(self) -> None:
        """Should return None when rule_strings is None."""
        result = _parse_rules(None)
        assert result is None

    def test_returns_none_for_empty_list(self) -> None:
        """Should return None when rule_strings is an empty list."""
        result = _parse_rules([])
        assert result is None

    def test_parses_valid_json_rules(self) -> None:
        """Should parse valid JSON rule strings into list of dicts."""
        rules = ['{"name": "rule1"}', '{"name": "rule2"}']
        result = _parse_rules(rules)
        assert result == [{"name": "rule1"}, {"name": "rule2"}]

    def test_invalid_json_rule_prints_error_and_exits(self) -> None:
        """Should print error and raise typer.Exit(1) on bad JSON (lines 103-105)."""
        with pytest.raises(typer.Exit) as exc_info:
            _parse_rules(["{invalid-json}"])
        assert exc_info.value.exit_code == 1

    def test_valid_complex_rule(self) -> None:
        """Should handle complex nested JSON rule strings."""
        rule_str = '{"name": "check", "match": {"any": [{"resources": {"kinds": ["Pod"]}}]}}'
        result = _parse_rules([rule_str])
        assert result is not None
        assert len(result) == 1
        assert result[0]["name"] == "check"


# =============================================================================
# Tests for ClusterPolicy commands  (lines 148-149, 209-210, 225, 229-230)
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestClusterPolicyCommandErrors:
    """Tests for error-path coverage in cluster-policy commands."""

    def test_list_cluster_policies_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
    ) -> None:
        """list_cluster_policies should handle KubernetesError (lines 148-149)."""
        mock_kyverno_manager.list_cluster_policies.side_effect = KubernetesConnectionError(
            "Cannot connect"
        )

        result = cli_runner.invoke(app, ["cluster-policies", "list"])

        assert result.exit_code == 1

    def test_create_cluster_policy_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
    ) -> None:
        """create_cluster_policy should handle KubernetesError (lines 209-210)."""
        mock_kyverno_manager.create_cluster_policy.side_effect = KubernetesError(
            "Server error", status_code=500
        )

        result = cli_runner.invoke(
            app,
            ["cluster-policies", "create", "require-labels"],
        )

        assert result.exit_code == 1

    def test_create_cluster_policy_with_invalid_label(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
    ) -> None:
        """create_cluster_policy should exit on invalid label format."""
        result = cli_runner.invoke(
            app,
            ["cluster-policies", "create", "require-labels", "--label", "invalid-no-equals"],
        )

        assert result.exit_code == 1
        mock_kyverno_manager.create_cluster_policy.assert_not_called()

    def test_create_cluster_policy_with_invalid_rule_json(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
    ) -> None:
        """create_cluster_policy should exit on invalid JSON rule."""
        result = cli_runner.invoke(
            app,
            [
                "cluster-policies",
                "create",
                "require-labels",
                "--rule",
                "{invalid-json}",
            ],
        )

        assert result.exit_code == 1
        mock_kyverno_manager.create_cluster_policy.assert_not_called()

    def test_delete_cluster_policy_user_aborts(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
    ) -> None:
        """delete_cluster_policy should abort when user does not confirm (line 225)."""
        with patch(
            "system_operations_manager.plugins.kubernetes.commands.base.typer.confirm",
            return_value=False,
        ):
            result = cli_runner.invoke(app, ["cluster-policies", "delete", "require-labels"])

        assert result.exit_code != 0
        mock_kyverno_manager.delete_cluster_policy.assert_not_called()

    def test_delete_cluster_policy_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
    ) -> None:
        """delete_cluster_policy should handle KubernetesError (lines 229-230)."""
        mock_kyverno_manager.delete_cluster_policy.side_effect = KubernetesNotFoundError(
            resource_type="ClusterPolicy", resource_name="require-labels"
        )

        result = cli_runner.invoke(app, ["cluster-policies", "delete", "require-labels", "--force"])

        assert result.exit_code == 1


# =============================================================================
# Tests for namespaced Policy commands  (lines 264-265, 328-329, 345, 349-350)
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestPolicyCommandErrors:
    """Tests for error-path coverage in namespaced policy commands."""

    def test_list_policies_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
    ) -> None:
        """list_policies should handle KubernetesError (lines 264-265)."""
        mock_kyverno_manager.list_policies.side_effect = KubernetesAuthError(
            "Forbidden", status_code=403
        )

        result = cli_runner.invoke(app, ["policies", "list"])

        assert result.exit_code == 1

    def test_create_policy_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
    ) -> None:
        """create_policy should handle KubernetesError (lines 328-329)."""
        mock_kyverno_manager.create_policy.side_effect = KubernetesError(
            "Server error", status_code=500
        )

        result = cli_runner.invoke(
            app,
            ["policies", "create", "restrict-images"],
        )

        assert result.exit_code == 1

    def test_create_policy_with_invalid_label(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
    ) -> None:
        """create_policy should exit on invalid label format."""
        result = cli_runner.invoke(
            app,
            ["policies", "create", "restrict-images", "--label", "invalid-no-equals"],
        )

        assert result.exit_code == 1
        mock_kyverno_manager.create_policy.assert_not_called()

    def test_create_policy_with_invalid_rule_json(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
    ) -> None:
        """create_policy should exit on invalid JSON rule."""
        result = cli_runner.invoke(
            app,
            ["policies", "create", "restrict-images", "--rule", "{invalid-json}"],
        )

        assert result.exit_code == 1
        mock_kyverno_manager.create_policy.assert_not_called()

    def test_delete_policy_user_aborts(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
    ) -> None:
        """delete_policy should abort when user does not confirm (line 345)."""
        with patch(
            "system_operations_manager.plugins.kubernetes.commands.base.typer.confirm",
            return_value=False,
        ):
            result = cli_runner.invoke(app, ["policies", "delete", "restrict-images"])

        assert result.exit_code != 0
        mock_kyverno_manager.delete_policy.assert_not_called()

    def test_delete_policy_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
    ) -> None:
        """delete_policy should handle KubernetesError (lines 349-350)."""
        mock_kyverno_manager.delete_policy.side_effect = KubernetesNotFoundError(
            resource_type="Policy", resource_name="restrict-images"
        )

        result = cli_runner.invoke(app, ["policies", "delete", "restrict-images", "--force"])

        assert result.exit_code == 1


# =============================================================================
# Tests for validate_policy command  (lines 387-388, 397)
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestValidatePolicyCommand:
    """Tests for validate_policy command edge cases."""

    def test_validate_policy_invalid_yaml(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """validate_policy should handle invalid YAML content."""
        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text("key: [unclosed bracket\n")

        result = cli_runner.invoke(app, ["policies", "validate", "--file", str(bad_yaml)])

        assert result.exit_code == 1
        mock_kyverno_manager.validate_policy.assert_not_called()

    def test_validate_policy_non_dict_yaml(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """validate_policy should exit when YAML is not a dict (line 377-378)."""
        list_yaml = tmp_path / "list.yaml"
        list_yaml.write_text("- item1\n- item2\n")

        result = cli_runner.invoke(app, ["policies", "validate", "--file", str(list_yaml)])

        assert result.exit_code == 1
        mock_kyverno_manager.validate_policy.assert_not_called()

    def test_validate_policy_invalid_result(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """validate_policy should exit when manager returns invalid result (lines 390-392)."""
        policy_file = tmp_path / "policy.yaml"
        policy_file.write_text(yaml.dump({"apiVersion": "kyverno.io/v1", "kind": "Policy"}))
        mock_kyverno_manager.validate_policy.return_value = {
            "valid": False,
            "error": "Schema validation failed",
        }

        result = cli_runner.invoke(app, ["policies", "validate", "--file", str(policy_file)])

        assert result.exit_code == 1

    def test_validate_policy_handles_kubernetes_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """validate_policy should handle KubernetesError from manager (line 397)."""
        policy_file = tmp_path / "policy.yaml"
        policy_file.write_text(yaml.dump({"apiVersion": "kyverno.io/v1", "kind": "Policy"}))
        mock_kyverno_manager.validate_policy.side_effect = KubernetesError(
            "Server error", status_code=500
        )

        result = cli_runner.invoke(app, ["policies", "validate", "--file", str(policy_file)])

        assert result.exit_code == 1

    def test_validate_policy_valid_with_non_table_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """validate_policy should format policy when output is non-TABLE and valid (lines 387-388)."""
        policy_file = tmp_path / "policy.yaml"
        policy_file.write_text(yaml.dump({"apiVersion": "kyverno.io/v1", "kind": "Policy"}))
        policy_obj: Any = MagicMock()
        policy_obj.model_dump = lambda **kwargs: {"name": "my-policy"}
        mock_kyverno_manager.validate_policy.return_value = {
            "valid": True,
            "policy": policy_obj,
        }

        result = cli_runner.invoke(
            app,
            ["policies", "validate", "--file", str(policy_file), "--output", "json"],
        )

        assert result.exit_code == 0


# =============================================================================
# Tests for ClusterPolicyReport commands  (lines 429-430)
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestClusterPolicyReportCommandErrors:
    """Tests for error-path coverage in cluster-policy-report commands."""

    def test_list_cluster_policy_reports_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
    ) -> None:
        """list_cluster_policy_reports should handle KubernetesError (lines 429-430)."""
        mock_kyverno_manager.list_cluster_policy_reports.side_effect = KubernetesConnectionError(
            "Cannot connect"
        )

        result = cli_runner.invoke(app, ["cluster-policy-reports", "list"])

        assert result.exit_code == 1

    def test_get_cluster_policy_report_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
    ) -> None:
        """get_cluster_policy_report should handle KubernetesError."""
        mock_kyverno_manager.get_cluster_policy_report.side_effect = KubernetesNotFoundError(
            resource_type="ClusterPolicyReport", resource_name="cpolr-require-labels"
        )

        result = cli_runner.invoke(app, ["cluster-policy-reports", "get", "cpolr-require-labels"])

        assert result.exit_code == 1


# =============================================================================
# Tests for PolicyReport commands  (lines 479-480, 499-500)
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestPolicyReportCommandErrors:
    """Tests for error-path coverage in policy-report commands."""

    def test_list_policy_reports_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
    ) -> None:
        """list_policy_reports should handle KubernetesError (lines 479-480)."""
        mock_kyverno_manager.list_policy_reports.side_effect = KubernetesAuthError(
            "Forbidden", status_code=403
        )

        result = cli_runner.invoke(app, ["policy-reports", "list"])

        assert result.exit_code == 1

    def test_get_policy_report_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
    ) -> None:
        """get_policy_report should handle KubernetesError (lines 499-500)."""
        mock_kyverno_manager.get_policy_report.side_effect = KubernetesNotFoundError(
            resource_type="PolicyReport", resource_name="polr-restrict-images"
        )

        result = cli_runner.invoke(app, ["policy-reports", "get", "polr-restrict-images"])

        assert result.exit_code == 1

    def test_admission_status_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
    ) -> None:
        """admission_status should handle KubernetesError."""
        mock_kyverno_manager.get_admission_status.side_effect = KubernetesTimeoutError(
            "Operation timed out"
        )

        result = cli_runner.invoke(app, ["admission", "status"])

        assert result.exit_code == 1


# =============================================================================
# Happy-path tests to cover success branches
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestClusterPolicyHappyPaths:
    """Happy-path tests for ClusterPolicy command success branches."""

    def test_list_cluster_policies_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
    ) -> None:
        """list_cluster_policies should succeed and call formatter (lines 146-147)."""
        result = cli_runner.invoke(app, ["cluster-policies", "list"])

        assert result.exit_code == 0
        mock_kyverno_manager.list_cluster_policies.assert_called_once()

    def test_get_cluster_policy_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
    ) -> None:
        """get_cluster_policy should succeed and format the resource (lines 162-168)."""
        result = cli_runner.invoke(app, ["cluster-policies", "get", "require-labels"])

        assert result.exit_code == 0
        mock_kyverno_manager.get_cluster_policy.assert_called_once_with("require-labels")

    def test_get_cluster_policy_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
    ) -> None:
        """get_cluster_policy should handle KubernetesError."""
        mock_kyverno_manager.get_cluster_policy.side_effect = KubernetesNotFoundError(
            resource_type="ClusterPolicy", resource_name="require-labels"
        )

        result = cli_runner.invoke(app, ["cluster-policies", "get", "require-labels"])

        assert result.exit_code == 1

    def test_create_cluster_policy_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
    ) -> None:
        """create_cluster_policy should succeed and format the resource (lines 207-208)."""
        result = cli_runner.invoke(
            app,
            ["cluster-policies", "create", "require-labels"],
        )

        assert result.exit_code == 0
        mock_kyverno_manager.create_cluster_policy.assert_called_once()

    def test_delete_cluster_policy_force_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
    ) -> None:
        """delete_cluster_policy with --force should delete without confirmation (line 228)."""
        result = cli_runner.invoke(app, ["cluster-policies", "delete", "require-labels", "--force"])

        assert result.exit_code == 0
        mock_kyverno_manager.delete_cluster_policy.assert_called_once_with("require-labels")


@pytest.mark.unit
@pytest.mark.kubernetes
class TestPolicyHappyPaths:
    """Happy-path tests for namespaced Policy command success branches."""

    def test_list_policies_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
    ) -> None:
        """list_policies should succeed and call formatter (lines 262-263)."""
        result = cli_runner.invoke(app, ["policies", "list"])

        assert result.exit_code == 0
        mock_kyverno_manager.list_policies.assert_called_once()

    def test_get_policy_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
    ) -> None:
        """get_policy should succeed and format the resource (lines 279-285)."""
        result = cli_runner.invoke(app, ["policies", "get", "restrict-images"])

        assert result.exit_code == 0
        mock_kyverno_manager.get_policy.assert_called_once_with("restrict-images", namespace=None)

    def test_get_policy_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
    ) -> None:
        """get_policy should handle KubernetesError."""
        mock_kyverno_manager.get_policy.side_effect = KubernetesNotFoundError(
            resource_type="Policy", resource_name="restrict-images"
        )

        result = cli_runner.invoke(app, ["policies", "get", "restrict-images"])

        assert result.exit_code == 1

    def test_create_policy_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
    ) -> None:
        """create_policy should succeed and format the resource (lines 326-327)."""
        result = cli_runner.invoke(
            app,
            ["policies", "create", "restrict-images"],
        )

        assert result.exit_code == 0
        mock_kyverno_manager.create_policy.assert_called_once()

    def test_delete_policy_force_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
    ) -> None:
        """delete_policy with --force should delete without confirmation (line 348)."""
        result = cli_runner.invoke(app, ["policies", "delete", "restrict-images", "--force"])

        assert result.exit_code == 0
        mock_kyverno_manager.delete_policy.assert_called_once_with(
            "restrict-images", namespace=None
        )

    def test_validate_policy_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """validate_policy should print valid and succeed (lines 383-384)."""
        policy_file = tmp_path / "policy.yaml"
        policy_file.write_text(yaml.dump({"apiVersion": "kyverno.io/v1", "kind": "Policy"}))
        mock_kyverno_manager.validate_policy.return_value = {
            "valid": True,
            "policy": None,
        }

        result = cli_runner.invoke(app, ["policies", "validate", "--file", str(policy_file)])

        assert result.exit_code == 0
        assert "valid" in result.stdout.lower()


@pytest.mark.unit
@pytest.mark.kubernetes
class TestPolicyReportHappyPaths:
    """Happy-path tests for PolicyReport and admission command success branches."""

    def test_list_cluster_policy_reports_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
    ) -> None:
        """list_cluster_policy_reports should succeed (lines 423-424)."""
        result = cli_runner.invoke(app, ["cluster-policy-reports", "list"])

        assert result.exit_code == 0
        mock_kyverno_manager.list_cluster_policy_reports.assert_called_once()

    def test_get_cluster_policy_report_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
    ) -> None:
        """get_cluster_policy_report should succeed (lines 446-447)."""
        result = cli_runner.invoke(app, ["cluster-policy-reports", "get", "cpolr-require-labels"])

        assert result.exit_code == 0
        mock_kyverno_manager.get_cluster_policy_report.assert_called_once_with(
            "cpolr-require-labels"
        )

    def test_list_policy_reports_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
    ) -> None:
        """list_policy_reports should succeed (lines 477-478)."""
        result = cli_runner.invoke(app, ["policy-reports", "list"])

        assert result.exit_code == 0
        mock_kyverno_manager.list_policy_reports.assert_called_once()

    def test_get_policy_report_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
    ) -> None:
        """get_policy_report should succeed (lines 497-498)."""
        result = cli_runner.invoke(app, ["policy-reports", "get", "polr-restrict-images"])

        assert result.exit_code == 0
        mock_kyverno_manager.get_policy_report.assert_called_once_with(
            "polr-restrict-images", namespace=None
        )

    def test_admission_status_success(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_kyverno_manager: MagicMock,
    ) -> None:
        """admission_status should succeed and format status dict (lines 529-530)."""
        result = cli_runner.invoke(app, ["admission", "status"])

        assert result.exit_code == 0
        mock_kyverno_manager.get_admission_status.assert_called_once()
