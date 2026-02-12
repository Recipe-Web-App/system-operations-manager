"""Unit tests for Kubernetes resource optimization commands."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from system_operations_manager.integrations.kubernetes.exceptions import (
    KubernetesConnectionError,
    KubernetesNotFoundError,
)
from system_operations_manager.integrations.kubernetes.models.optimization import (
    OptimizationSummary,
    OrphanPod,
    RightsizingRecommendation,
    StaleJob,
    WorkloadResourceAnalysis,
)
from system_operations_manager.plugins.kubernetes.commands.optimize import (
    register_optimization_commands,
)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestAnalyzeCommand:
    """Tests for optimize analyze command."""

    @pytest.fixture
    def app(self, get_optimization_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with optimization commands."""
        app = typer.Typer()
        register_optimization_commands(app, get_optimization_manager)
        return app

    def test_analyze_displays_results(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_optimization_manager: MagicMock,
        sample_analysis: WorkloadResourceAnalysis,
    ) -> None:
        """optimize analyze should display workload analysis."""
        mock_optimization_manager.analyze_workloads.return_value = [sample_analysis]

        result = cli_runner.invoke(app, ["optimize", "analyze"])

        assert result.exit_code == 0
        mock_optimization_manager.analyze_workloads.assert_called_once()
        assert "default" in result.output

    def test_analyze_empty_results(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_optimization_manager: MagicMock,
    ) -> None:
        """optimize analyze should show message when no workloads found."""
        mock_optimization_manager.analyze_workloads.return_value = []

        result = cli_runner.invoke(app, ["optimize", "analyze"])

        assert result.exit_code == 0
        assert "No workloads found" in result.output

    def test_analyze_with_namespace(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_optimization_manager: MagicMock,
    ) -> None:
        """optimize analyze -n should pass namespace."""
        mock_optimization_manager.analyze_workloads.return_value = []

        result = cli_runner.invoke(app, ["optimize", "analyze", "-n", "production"])

        assert result.exit_code == 0
        call_kwargs = mock_optimization_manager.analyze_workloads.call_args[1]
        assert call_kwargs["namespace"] == "production"

    def test_analyze_all_namespaces(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_optimization_manager: MagicMock,
    ) -> None:
        """optimize analyze -A should pass all_namespaces."""
        mock_optimization_manager.analyze_workloads.return_value = []

        result = cli_runner.invoke(app, ["optimize", "analyze", "-A"])

        assert result.exit_code == 0
        call_kwargs = mock_optimization_manager.analyze_workloads.call_args[1]
        assert call_kwargs["all_namespaces"] is True

    def test_analyze_with_threshold(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_optimization_manager: MagicMock,
    ) -> None:
        """optimize analyze --threshold should pass custom threshold."""
        mock_optimization_manager.analyze_workloads.return_value = []

        result = cli_runner.invoke(app, ["optimize", "analyze", "--threshold", "0.3"])

        assert result.exit_code == 0
        call_kwargs = mock_optimization_manager.analyze_workloads.call_args[1]
        assert call_kwargs["threshold"] == pytest.approx(0.3)

    def test_analyze_with_label_selector(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_optimization_manager: MagicMock,
    ) -> None:
        """optimize analyze -l should pass label selector."""
        mock_optimization_manager.analyze_workloads.return_value = []

        result = cli_runner.invoke(app, ["optimize", "analyze", "-l", "app=nginx"])

        assert result.exit_code == 0
        call_kwargs = mock_optimization_manager.analyze_workloads.call_args[1]
        assert call_kwargs["label_selector"] == "app=nginx"

    def test_analyze_connection_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_optimization_manager: MagicMock,
    ) -> None:
        """optimize analyze should handle connection errors."""
        mock_optimization_manager.analyze_workloads.side_effect = KubernetesConnectionError(
            message="Cannot connect"
        )

        result = cli_runner.invoke(app, ["optimize", "analyze"])

        assert result.exit_code == 1
        assert "Cannot connect" in result.output

    def test_analyze_json_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_optimization_manager: MagicMock,
        sample_analysis: WorkloadResourceAnalysis,
    ) -> None:
        """optimize analyze -o json should produce JSON output."""
        mock_optimization_manager.analyze_workloads.return_value = [sample_analysis]

        result = cli_runner.invoke(app, ["optimize", "analyze", "-o", "json"])

        assert result.exit_code == 0
        assert "test-deployment" in result.output


@pytest.mark.unit
@pytest.mark.kubernetes
class TestRecommendCommand:
    """Tests for optimize recommend command."""

    @pytest.fixture
    def app(self, get_optimization_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with optimization commands."""
        app = typer.Typer()
        register_optimization_commands(app, get_optimization_manager)
        return app

    def test_recommend_displays_result(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_optimization_manager: MagicMock,
        sample_recommendation: RightsizingRecommendation,
    ) -> None:
        """optimize recommend should display recommendation."""
        mock_optimization_manager.recommend.return_value = sample_recommendation

        result = cli_runner.invoke(app, ["optimize", "recommend", "test-deployment"])

        assert result.exit_code == 0
        mock_optimization_manager.recommend.assert_called_once()

    def test_recommend_with_namespace(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_optimization_manager: MagicMock,
        sample_recommendation: RightsizingRecommendation,
    ) -> None:
        """optimize recommend -n should pass namespace."""
        mock_optimization_manager.recommend.return_value = sample_recommendation

        result = cli_runner.invoke(app, ["optimize", "recommend", "my-app", "-n", "production"])

        assert result.exit_code == 0
        call_kwargs = mock_optimization_manager.recommend.call_args[1]
        assert call_kwargs["namespace"] == "production"

    def test_recommend_with_workload_type(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_optimization_manager: MagicMock,
        sample_recommendation: RightsizingRecommendation,
    ) -> None:
        """optimize recommend --type should pass workload type."""
        mock_optimization_manager.recommend.return_value = sample_recommendation

        result = cli_runner.invoke(
            app, ["optimize", "recommend", "my-sts", "--type", "StatefulSet"]
        )

        assert result.exit_code == 0
        call_kwargs = mock_optimization_manager.recommend.call_args[1]
        assert call_kwargs["workload_type"] == "StatefulSet"

    def test_recommend_not_found(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_optimization_manager: MagicMock,
    ) -> None:
        """optimize recommend should handle not found errors."""
        mock_optimization_manager.recommend.side_effect = KubernetesNotFoundError(
            resource_type="Deployment", resource_name="missing"
        )

        result = cli_runner.invoke(app, ["optimize", "recommend", "missing"])

        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_recommend_json_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_optimization_manager: MagicMock,
        sample_recommendation: RightsizingRecommendation,
    ) -> None:
        """optimize recommend -o json should produce JSON output."""
        mock_optimization_manager.recommend.return_value = sample_recommendation

        result = cli_runner.invoke(app, ["optimize", "recommend", "test-deployment", "-o", "json"])

        assert result.exit_code == 0
        assert "test-deployment" in result.output


@pytest.mark.unit
@pytest.mark.kubernetes
class TestUnusedCommand:
    """Tests for optimize unused command."""

    @pytest.fixture
    def app(self, get_optimization_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with optimization commands."""
        app = typer.Typer()
        register_optimization_commands(app, get_optimization_manager)
        return app

    def test_unused_clean_cluster(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_optimization_manager: MagicMock,
    ) -> None:
        """optimize unused should show clean message when nothing found."""
        mock_optimization_manager.find_unused.return_value = {
            "orphan_pods": [],
            "stale_jobs": [],
            "idle_workloads": [],
        }

        result = cli_runner.invoke(app, ["optimize", "unused"])

        assert result.exit_code == 0
        assert "clean" in result.output.lower()

    def test_unused_shows_orphan_pods(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_optimization_manager: MagicMock,
        sample_orphan_pod: OrphanPod,
    ) -> None:
        """optimize unused should display orphan pods."""
        mock_optimization_manager.find_unused.return_value = {
            "orphan_pods": [sample_orphan_pod],
            "stale_jobs": [],
            "idle_workloads": [],
        }

        result = cli_runner.invoke(app, ["optimize", "unused"])

        assert result.exit_code == 0
        assert "stray-pod" in result.output

    def test_unused_shows_stale_jobs(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_optimization_manager: MagicMock,
        sample_stale_job: StaleJob,
    ) -> None:
        """optimize unused should display stale jobs."""
        mock_optimization_manager.find_unused.return_value = {
            "orphan_pods": [],
            "stale_jobs": [sample_stale_job],
            "idle_workloads": [],
        }

        result = cli_runner.invoke(app, ["optimize", "unused"])

        assert result.exit_code == 0
        assert "old-migration" in result.output

    def test_unused_shows_idle_workloads(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_optimization_manager: MagicMock,
        sample_analysis: WorkloadResourceAnalysis,
    ) -> None:
        """optimize unused should display idle workloads."""
        mock_optimization_manager.find_unused.return_value = {
            "orphan_pods": [],
            "stale_jobs": [],
            "idle_workloads": [sample_analysis],
        }

        result = cli_runner.invoke(app, ["optimize", "unused"])

        assert result.exit_code == 0
        assert "Idle Workloads" in result.output

    def test_unused_with_stale_hours(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_optimization_manager: MagicMock,
    ) -> None:
        """optimize unused --stale-hours should pass custom threshold."""
        mock_optimization_manager.find_unused.return_value = {
            "orphan_pods": [],
            "stale_jobs": [],
            "idle_workloads": [],
        }

        result = cli_runner.invoke(app, ["optimize", "unused", "--stale-hours", "48"])

        assert result.exit_code == 0
        call_kwargs = mock_optimization_manager.find_unused.call_args[1]
        assert call_kwargs["stale_job_hours"] == pytest.approx(48.0)

    def test_unused_all_namespaces(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_optimization_manager: MagicMock,
    ) -> None:
        """optimize unused -A should pass all_namespaces."""
        mock_optimization_manager.find_unused.return_value = {
            "orphan_pods": [],
            "stale_jobs": [],
            "idle_workloads": [],
        }

        result = cli_runner.invoke(app, ["optimize", "unused", "-A"])

        assert result.exit_code == 0
        call_kwargs = mock_optimization_manager.find_unused.call_args[1]
        assert call_kwargs["all_namespaces"] is True

    def test_unused_connection_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_optimization_manager: MagicMock,
    ) -> None:
        """optimize unused should handle connection errors."""
        mock_optimization_manager.find_unused.side_effect = KubernetesConnectionError(
            message="Cannot connect"
        )

        result = cli_runner.invoke(app, ["optimize", "unused"])

        assert result.exit_code == 1


@pytest.mark.unit
@pytest.mark.kubernetes
class TestSummaryCommand:
    """Tests for optimize summary command."""

    @pytest.fixture
    def app(self, get_optimization_manager: Callable[[], MagicMock]) -> typer.Typer:
        """Create a test app with optimization commands."""
        app = typer.Typer()
        register_optimization_commands(app, get_optimization_manager)
        return app

    def test_summary_displays_results(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_optimization_manager: MagicMock,
        sample_summary: OptimizationSummary,
    ) -> None:
        """optimize summary should display optimization summary."""
        mock_optimization_manager.get_summary.return_value = sample_summary

        result = cli_runner.invoke(app, ["optimize", "summary"])

        assert result.exit_code == 0
        mock_optimization_manager.get_summary.assert_called_once()

    def test_summary_empty_cluster(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_optimization_manager: MagicMock,
    ) -> None:
        """optimize summary should handle empty clusters."""
        mock_optimization_manager.get_summary.return_value = OptimizationSummary()

        result = cli_runner.invoke(app, ["optimize", "summary"])

        assert result.exit_code == 0

    def test_summary_with_namespace(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_optimization_manager: MagicMock,
        sample_summary: OptimizationSummary,
    ) -> None:
        """optimize summary -n should pass namespace."""
        mock_optimization_manager.get_summary.return_value = sample_summary

        result = cli_runner.invoke(app, ["optimize", "summary", "-n", "production"])

        assert result.exit_code == 0
        call_kwargs = mock_optimization_manager.get_summary.call_args[1]
        assert call_kwargs["namespace"] == "production"

    def test_summary_all_namespaces(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_optimization_manager: MagicMock,
        sample_summary: OptimizationSummary,
    ) -> None:
        """optimize summary -A should pass all_namespaces."""
        mock_optimization_manager.get_summary.return_value = sample_summary

        result = cli_runner.invoke(app, ["optimize", "summary", "-A"])

        assert result.exit_code == 0
        call_kwargs = mock_optimization_manager.get_summary.call_args[1]
        assert call_kwargs["all_namespaces"] is True

    def test_summary_json_output(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_optimization_manager: MagicMock,
        sample_summary: OptimizationSummary,
    ) -> None:
        """optimize summary -o json should produce JSON output."""
        mock_optimization_manager.get_summary.return_value = sample_summary

        result = cli_runner.invoke(app, ["optimize", "summary", "-o", "json"])

        assert result.exit_code == 0
        assert "overprovisioned" in result.output

    def test_summary_connection_error(
        self,
        cli_runner: CliRunner,
        app: typer.Typer,
        mock_optimization_manager: MagicMock,
    ) -> None:
        """optimize summary should handle connection errors."""
        mock_optimization_manager.get_summary.side_effect = KubernetesConnectionError(
            message="Cannot connect"
        )

        result = cli_runner.invoke(app, ["optimize", "summary"])

        assert result.exit_code == 1
