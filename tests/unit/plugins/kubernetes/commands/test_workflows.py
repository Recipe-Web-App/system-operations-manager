"""Unit tests for Argo Workflows CLI commands (gap-fill coverage)."""

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
from system_operations_manager.plugins.kubernetes.commands.workflows import (
    _load_spec_from_file,
    _parse_arguments,
    _parse_labels,
    register_workflow_commands,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def mock_workflows_manager() -> MagicMock:
    """Create a mock WorkflowsManager."""
    manager = MagicMock()

    manager.list_workflows.return_value = []
    manager.get_workflow.return_value = MagicMock(
        model_dump=lambda **kwargs: {
            "name": "my-workflow",
            "namespace": "default",
            "phase": "Succeeded",
            "progress": "3/3",
            "duration": "2m30s",
            "entrypoint": "main",
        }
    )
    manager.create_workflow.return_value = MagicMock(
        model_dump=lambda **kwargs: {
            "name": "my-workflow",
            "namespace": "default",
            "phase": "Pending",
        }
    )
    manager.delete_workflow.return_value = None
    manager.get_workflow_logs.return_value = "workflow logs here"

    manager.list_workflow_templates.return_value = []
    manager.get_workflow_template.return_value = MagicMock(
        model_dump=lambda **kwargs: {
            "name": "my-template",
            "namespace": "default",
            "entrypoint": "main",
            "templates_count": 3,
            "description": "A workflow template",
        }
    )
    manager.create_workflow_template.return_value = MagicMock(
        model_dump=lambda **kwargs: {
            "name": "my-template",
            "namespace": "default",
        }
    )
    manager.delete_workflow_template.return_value = None

    manager.list_cron_workflows.return_value = []
    manager.get_cron_workflow.return_value = MagicMock(
        model_dump=lambda **kwargs: {
            "name": "my-cron",
            "namespace": "default",
            "schedule": "0 0 * * *",
            "suspend": False,
            "active_count": 0,
        }
    )
    manager.create_cron_workflow.return_value = MagicMock(
        model_dump=lambda **kwargs: {
            "name": "my-cron",
            "namespace": "default",
            "schedule": "0 0 * * *",
        }
    )
    manager.delete_cron_workflow.return_value = None
    manager.suspend_cron_workflow.return_value = MagicMock(
        model_dump=lambda **kwargs: {"name": "my-cron", "suspend": True}
    )
    manager.resume_cron_workflow.return_value = MagicMock(
        model_dump=lambda **kwargs: {"name": "my-cron", "suspend": False}
    )
    manager.list_workflow_artifacts.return_value = []

    return manager


@pytest.fixture
def get_workflows_manager(
    mock_workflows_manager: MagicMock,
) -> Callable[[], MagicMock]:
    """Factory returning the mock WorkflowsManager."""
    return lambda: mock_workflows_manager


@pytest.fixture
def app(get_workflows_manager: Callable[[], MagicMock]) -> typer.Typer:
    """Create a test Typer app with workflow commands registered."""
    test_app = typer.Typer()
    register_workflow_commands(test_app, get_workflows_manager)
    return test_app


# =============================================================================
# Tests for _parse_labels helper
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestParseLabels:
    """Tests for the _parse_labels helper function."""

    def test_returns_none_for_none_input(self) -> None:
        """Should return None when labels is None."""
        result = _parse_labels(None)
        assert result is None

    def test_returns_none_for_empty_list(self) -> None:
        """Should return None when labels is an empty list."""
        result = _parse_labels([])
        assert result is None

    def test_parses_valid_labels(self) -> None:
        """Should parse valid key=value labels into a dict."""
        result = _parse_labels(["app=nginx", "env=prod"])
        assert result == {"app": "nginx", "env": "prod"}

    def test_invalid_label_format_exits(self) -> None:
        """Should exit with code 1 on invalid label format (no = sign)."""
        with pytest.raises(typer.Exit) as exc_info:
            _parse_labels(["invalid-label"])
        assert exc_info.value.exit_code == 1

    def test_invalid_label_format_no_separator(self) -> None:
        """Should exit when label has no = separator."""
        with pytest.raises(typer.Exit):
            _parse_labels(["keyonly"])


# =============================================================================
# Tests for _parse_arguments helper
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestParseArguments:
    """Tests for the _parse_arguments helper function."""

    def test_returns_none_for_none_input(self) -> None:
        """Should return None when arguments is None."""
        result = _parse_arguments(None)
        assert result is None

    def test_returns_none_for_empty_list(self) -> None:
        """Should return None when arguments is empty list."""
        result = _parse_arguments([])
        assert result is None

    def test_parses_valid_arguments(self) -> None:
        """Should parse valid key=value arguments into a dict."""
        result = _parse_arguments(["message=hello", "count=5"])
        assert result == {"message": "hello", "count": "5"}

    def test_invalid_argument_format_exits(self) -> None:
        """Should exit with code 1 on invalid argument format (no = sign)."""
        with pytest.raises(typer.Exit) as exc_info:
            _parse_arguments(["invalidarg"])
        assert exc_info.value.exit_code == 1

    def test_invalid_argument_no_separator(self) -> None:
        """Should exit when argument has no = separator."""
        with pytest.raises(typer.Exit):
            _parse_arguments(["noequals"])


# =============================================================================
# Tests for _load_spec_from_file helper
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestLoadSpecFromFile:
    """Tests for the _load_spec_from_file helper function."""

    def test_loads_valid_yaml_dict(self, tmp_path: Path) -> None:
        """Should load and return a dict from a valid YAML file."""
        spec_file = tmp_path / "spec.yaml"
        spec_data: dict[str, Any] = {"entrypoint": "main", "templates": []}
        spec_file.write_text(yaml.dump(spec_data))

        result = _load_spec_from_file(spec_file)

        assert result == spec_data

    def test_exits_when_yaml_not_dict(self, tmp_path: Path) -> None:
        """Should exit when YAML content is not a dict (e.g. a list)."""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text("- item1\n- item2\n")

        with pytest.raises(typer.Exit) as exc_info:
            _load_spec_from_file(spec_file)
        assert exc_info.value.exit_code == 1

    def test_exits_when_file_not_found(self, tmp_path: Path) -> None:
        """Should exit when the spec file does not exist."""
        missing = tmp_path / "missing.yaml"

        with pytest.raises(typer.Exit) as exc_info:
            _load_spec_from_file(missing)
        assert exc_info.value.exit_code == 1

    def test_exits_on_yaml_parse_error(self, tmp_path: Path) -> None:
        """Should exit when the spec file contains invalid YAML."""
        spec_file = tmp_path / "bad.yaml"
        spec_file.write_text("key: [unclosed bracket\n")

        with pytest.raises(typer.Exit) as exc_info:
            _load_spec_from_file(spec_file)
        assert exc_info.value.exit_code == 1


# =============================================================================
# Tests for Workflow command error handling
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestWorkflowCommandErrors:
    """Tests for error-path coverage in workflow commands."""

    def test_list_workflows_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workflows_manager: MagicMock,
    ) -> None:
        """list_workflows should handle KubernetesError."""
        mock_workflows_manager.list_workflows.side_effect = KubernetesConnectionError(
            "Cannot connect"
        )

        result = cli_runner.invoke(app, ["workflows", "list"])

        assert result.exit_code == 1

    def test_create_workflow_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workflows_manager: MagicMock,
    ) -> None:
        """create_workflow should handle KubernetesError."""
        mock_workflows_manager.create_workflow.side_effect = KubernetesError(
            "Server error", status_code=500
        )

        result = cli_runner.invoke(
            app,
            [
                "workflows",
                "create",
                "my-workflow",
                "--template-ref",
                "my-template",
            ],
        )

        assert result.exit_code == 1

    def test_delete_workflow_user_aborts(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workflows_manager: MagicMock,
    ) -> None:
        """delete_workflow should abort when user does not confirm."""
        with patch(
            "system_operations_manager.plugins.kubernetes.commands.base.typer.confirm",
            return_value=False,
        ):
            result = cli_runner.invoke(app, ["workflows", "delete", "my-workflow"])

        assert result.exit_code != 0
        mock_workflows_manager.delete_workflow.assert_not_called()

    def test_delete_workflow_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workflows_manager: MagicMock,
    ) -> None:
        """delete_workflow should handle KubernetesError after confirmation."""
        mock_workflows_manager.delete_workflow.side_effect = KubernetesNotFoundError(
            resource_type="Workflow", resource_name="my-workflow"
        )

        result = cli_runner.invoke(app, ["workflows", "delete", "my-workflow", "--force"])

        assert result.exit_code == 1

    def test_workflow_logs_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workflows_manager: MagicMock,
    ) -> None:
        """workflow_logs should handle KubernetesError."""
        mock_workflows_manager.get_workflow_logs.side_effect = KubernetesTimeoutError("Timed out")

        result = cli_runner.invoke(app, ["workflows", "logs", "my-workflow"])

        assert result.exit_code == 1

    def test_workflow_logs_iterable_result(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workflows_manager: MagicMock,
    ) -> None:
        """workflow_logs should print each line when result is iterable."""
        mock_workflows_manager.get_workflow_logs.return_value = iter(["line one\n", "line two\n"])

        result = cli_runner.invoke(app, ["workflows", "logs", "my-workflow", "--follow"])

        assert result.exit_code == 0
        assert "line one" in result.stdout
        assert "line two" in result.stdout


# =============================================================================
# Tests for WorkflowTemplate command error handling
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestWorkflowTemplateCommandErrors:
    """Tests for error-path coverage in WorkflowTemplate commands."""

    def test_list_templates_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workflows_manager: MagicMock,
    ) -> None:
        """list_templates should handle KubernetesError."""
        mock_workflows_manager.list_workflow_templates.side_effect = KubernetesAuthError(
            "Forbidden", status_code=403
        )

        result = cli_runner.invoke(app, ["workflows", "templates", "list"])

        assert result.exit_code == 1

    def test_create_template_with_spec_file(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workflows_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """create_template should load spec from YAML file and call manager."""
        spec_data: dict[str, Any] = {"entrypoint": "main", "templates": []}
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(yaml.dump(spec_data))

        result = cli_runner.invoke(
            app,
            [
                "workflows",
                "templates",
                "create",
                "my-template",
                "--spec-file",
                str(spec_file),
            ],
        )

        assert result.exit_code == 0
        mock_workflows_manager.create_workflow_template.assert_called_once()
        call_args: Any = mock_workflows_manager.create_workflow_template.call_args
        assert call_args.args[0] == "my-template"
        assert call_args.kwargs["spec"] == spec_data

    def test_create_template_with_missing_spec_file(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workflows_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """create_template should exit when spec file does not exist."""
        missing = tmp_path / "missing.yaml"

        result = cli_runner.invoke(
            app,
            [
                "workflows",
                "templates",
                "create",
                "my-template",
                "--spec-file",
                str(missing),
            ],
        )

        assert result.exit_code == 1
        mock_workflows_manager.create_workflow_template.assert_not_called()

    def test_create_template_with_invalid_yaml(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workflows_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """create_template should exit when spec file has invalid YAML."""
        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text("key: [unclosed\n")

        result = cli_runner.invoke(
            app,
            [
                "workflows",
                "templates",
                "create",
                "my-template",
                "--spec-file",
                str(bad_yaml),
            ],
        )

        assert result.exit_code == 1
        mock_workflows_manager.create_workflow_template.assert_not_called()

    def test_create_template_with_non_dict_yaml(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workflows_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """create_template should exit when spec file YAML is not a dict."""
        list_yaml = tmp_path / "list.yaml"
        list_yaml.write_text("- item1\n- item2\n")

        result = cli_runner.invoke(
            app,
            [
                "workflows",
                "templates",
                "create",
                "my-template",
                "--spec-file",
                str(list_yaml),
            ],
        )

        assert result.exit_code == 1
        mock_workflows_manager.create_workflow_template.assert_not_called()

    def test_create_template_handles_kubernetes_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workflows_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """create_template should handle KubernetesError from manager."""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(yaml.dump({"entrypoint": "main"}))
        mock_workflows_manager.create_workflow_template.side_effect = KubernetesError(
            "Server error", status_code=500
        )

        result = cli_runner.invoke(
            app,
            [
                "workflows",
                "templates",
                "create",
                "my-template",
                "--spec-file",
                str(spec_file),
            ],
        )

        assert result.exit_code == 1

    def test_delete_template_user_aborts(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workflows_manager: MagicMock,
    ) -> None:
        """delete_template should abort when user does not confirm."""
        with patch(
            "system_operations_manager.plugins.kubernetes.commands.base.typer.confirm",
            return_value=False,
        ):
            result = cli_runner.invoke(app, ["workflows", "templates", "delete", "my-template"])

        assert result.exit_code != 0
        mock_workflows_manager.delete_workflow_template.assert_not_called()

    def test_delete_template_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workflows_manager: MagicMock,
    ) -> None:
        """delete_template should handle KubernetesError."""
        mock_workflows_manager.delete_workflow_template.side_effect = KubernetesNotFoundError(
            resource_type="WorkflowTemplate", resource_name="my-template"
        )

        result = cli_runner.invoke(
            app, ["workflows", "templates", "delete", "my-template", "--force"]
        )

        assert result.exit_code == 1


# =============================================================================
# Tests for CronWorkflow command error handling
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestCronWorkflowCommandErrors:
    """Tests for error-path coverage in CronWorkflow commands."""

    def test_list_cron_workflows_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workflows_manager: MagicMock,
    ) -> None:
        """list_cron_workflows should handle KubernetesError."""
        mock_workflows_manager.list_cron_workflows.side_effect = KubernetesConnectionError(
            "Cannot connect"
        )

        result = cli_runner.invoke(app, ["workflows", "cron", "list"])

        assert result.exit_code == 1

    def test_create_cron_workflow_with_labels(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workflows_manager: MagicMock,
    ) -> None:
        """create_cron_workflow should parse and pass labels."""
        result = cli_runner.invoke(
            app,
            [
                "workflows",
                "cron",
                "create",
                "my-cron",
                "--schedule",
                "0 0 * * *",
                "--template-ref",
                "my-template",
                "--label",
                "env=prod",
            ],
        )

        assert result.exit_code == 0
        call_args: Any = mock_workflows_manager.create_cron_workflow.call_args
        assert call_args.kwargs["labels"] == {"env": "prod"}

    def test_create_cron_workflow_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workflows_manager: MagicMock,
    ) -> None:
        """create_cron_workflow should handle KubernetesError."""
        mock_workflows_manager.create_cron_workflow.side_effect = KubernetesError(
            "Server error", status_code=500
        )

        result = cli_runner.invoke(
            app,
            [
                "workflows",
                "cron",
                "create",
                "my-cron",
                "--schedule",
                "0 0 * * *",
                "--template-ref",
                "my-template",
            ],
        )

        assert result.exit_code == 1

    def test_delete_cron_workflow_user_aborts(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workflows_manager: MagicMock,
    ) -> None:
        """delete_cron_workflow should abort when user does not confirm."""
        with patch(
            "system_operations_manager.plugins.kubernetes.commands.base.typer.confirm",
            return_value=False,
        ):
            result = cli_runner.invoke(app, ["workflows", "cron", "delete", "my-cron"])

        assert result.exit_code != 0
        mock_workflows_manager.delete_cron_workflow.assert_not_called()

    def test_delete_cron_workflow_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workflows_manager: MagicMock,
    ) -> None:
        """delete_cron_workflow should handle KubernetesError."""
        mock_workflows_manager.delete_cron_workflow.side_effect = KubernetesNotFoundError(
            resource_type="CronWorkflow", resource_name="my-cron"
        )

        result = cli_runner.invoke(app, ["workflows", "cron", "delete", "my-cron", "--force"])

        assert result.exit_code == 1

    def test_suspend_cron_workflow_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workflows_manager: MagicMock,
    ) -> None:
        """suspend_cron_workflow should handle KubernetesError."""
        mock_workflows_manager.suspend_cron_workflow.side_effect = KubernetesNotFoundError(
            resource_type="CronWorkflow", resource_name="my-cron"
        )

        result = cli_runner.invoke(app, ["workflows", "cron", "suspend", "my-cron"])

        assert result.exit_code == 1

    def test_resume_cron_workflow_handles_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workflows_manager: MagicMock,
    ) -> None:
        """resume_cron_workflow should handle KubernetesError."""
        mock_workflows_manager.resume_cron_workflow.side_effect = KubernetesNotFoundError(
            resource_type="CronWorkflow", resource_name="my-cron"
        )

        result = cli_runner.invoke(app, ["workflows", "cron", "resume", "my-cron"])

        assert result.exit_code == 1

    def test_create_cron_workflow_with_invalid_label(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workflows_manager: MagicMock,
    ) -> None:
        """create_cron_workflow should exit on invalid label format."""
        result = cli_runner.invoke(
            app,
            [
                "workflows",
                "cron",
                "create",
                "my-cron",
                "--schedule",
                "0 0 * * *",
                "--template-ref",
                "my-template",
                "--label",
                "invalid-no-equals",
            ],
        )

        assert result.exit_code == 1
        mock_workflows_manager.create_cron_workflow.assert_not_called()

    def test_create_workflow_with_invalid_label(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workflows_manager: MagicMock,
    ) -> None:
        """create_workflow should exit on invalid label format."""
        result = cli_runner.invoke(
            app,
            [
                "workflows",
                "create",
                "my-workflow",
                "--template-ref",
                "my-template",
                "--label",
                "invalid-no-equals",
            ],
        )

        assert result.exit_code == 1
        mock_workflows_manager.create_workflow.assert_not_called()

    def test_create_workflow_with_invalid_argument(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_workflows_manager: MagicMock,
    ) -> None:
        """create_workflow should exit on invalid argument format."""
        result = cli_runner.invoke(
            app,
            [
                "workflows",
                "create",
                "my-workflow",
                "--template-ref",
                "my-template",
                "--argument",
                "invalid-no-equals",
            ],
        )

        assert result.exit_code == 1
        mock_workflows_manager.create_workflow.assert_not_called()
