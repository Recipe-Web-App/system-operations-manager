"""Unit tests for DiffViewer component.

Tests the reusable DiffViewer widget for showing differences.
"""

from __future__ import annotations

import pytest
from textual.app import App, ComposeResult
from textual.containers import Container

from system_operations_manager.tui.components.diff_viewer import DiffViewer


class DiffViewerTestApp(App[None]):
    """Test app for DiffViewer component."""

    def __init__(self, viewer: DiffViewer) -> None:
        super().__init__()
        self.viewer = viewer

    def compose(self) -> ComposeResult:
        with Container():
            yield self.viewer


# ============================================================================
# Initialization Tests
# ============================================================================


class TestDiffViewerInit:
    """Tests for DiffViewer initialization."""

    @pytest.mark.unit
    def test_diff_viewer_with_dicts(self) -> None:
        """DiffViewer can be created with dict states."""
        source = {"name": "test", "value": 1}
        target = {"name": "test", "value": 2}
        viewer = DiffViewer(source_state=source, target_state=target)

        assert viewer.source_state == source
        assert viewer.target_state == target

    @pytest.mark.unit
    def test_diff_viewer_default_labels(self) -> None:
        """DiffViewer has default source/target labels."""
        viewer = DiffViewer(source_state={}, target_state={})

        assert viewer.source_label == "Source"
        assert viewer.target_label == "Target"

    @pytest.mark.unit
    def test_diff_viewer_custom_labels(self) -> None:
        """DiffViewer accepts custom labels."""
        viewer = DiffViewer(
            source_state={},
            target_state={},
            source_label="Gateway",
            target_label="Konnect",
        )

        assert viewer.source_label == "Gateway"
        assert viewer.target_label == "Konnect"

    @pytest.mark.unit
    def test_diff_viewer_stores_drift_fields(self) -> None:
        """DiffViewer stores drift_fields."""
        viewer = DiffViewer(
            source_state={"a": 1},
            target_state={"a": 2},
            drift_fields=["a"],
        )
        assert viewer.drift_fields == ["a"]

    @pytest.mark.unit
    def test_diff_viewer_default_drift_fields_empty(self) -> None:
        """DiffViewer defaults to empty drift_fields."""
        viewer = DiffViewer(source_state={}, target_state={})
        assert viewer.drift_fields == []

    @pytest.mark.unit
    def test_diff_viewer_accepts_complex_states(self) -> None:
        """DiffViewer accepts complex nested states."""
        source = {
            "name": "test-service",
            "config": {"timeout": 30, "retries": 3},
            "tags": ["production", "api"],
        }
        target = {
            "name": "test-service",
            "config": {"timeout": 60, "retries": 3},
            "tags": ["production", "api", "v2"],
        }
        viewer = DiffViewer(
            source_state=source,
            target_state=target,
            drift_fields=["config", "tags"],
        )

        assert viewer.source_state == source
        assert viewer.target_state == target


# ============================================================================
# Async Tests - Rendering
# ============================================================================


class TestDiffViewerAsync:
    """Async tests for DiffViewer rendering."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_diff_viewer_renders(self) -> None:
        """DiffViewer renders without error."""
        source = {"name": "test"}
        target = {"name": "changed"}
        viewer = DiffViewer(source_state=source, target_state=target)
        app = DiffViewerTestApp(viewer)

        async with app.run_test():
            # Should render without exception
            queried = app.query_one(DiffViewer)
            assert queried is not None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_diff_viewer_stores_labels(self) -> None:
        """DiffViewer stores source and target labels."""
        viewer = DiffViewer(
            source_state={"a": 1},
            target_state={"a": 2},
            source_label="Left",
            target_label="Right",
        )
        app = DiffViewerTestApp(viewer)

        async with app.run_test():
            queried = app.query_one(DiffViewer)
            assert queried.source_label == "Left"
            assert queried.target_label == "Right"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_diff_viewer_toggle_mode_in_app(self) -> None:
        """DiffViewer can toggle mode within an app."""
        viewer = DiffViewer(source_state={"a": 1}, target_state={"a": 2})
        app = DiffViewerTestApp(viewer)

        async with app.run_test():
            queried = app.query_one(DiffViewer)
            initial_mode = queried.mode
            assert initial_mode == "side_by_side"

            queried.toggle_mode()
            mode_after_first_toggle = queried.mode
            assert mode_after_first_toggle == "unified"

            queried.toggle_mode()
            mode_after_second_toggle = queried.mode
            assert mode_after_second_toggle == "side_by_side"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_diff_viewer_with_drift_fields(self) -> None:
        """DiffViewer renders with drift fields highlighted."""
        source = {"host": "old.example.com", "port": 80}
        target = {"host": "new.example.com", "port": 80}
        viewer = DiffViewer(
            source_state=source,
            target_state=target,
            drift_fields=["host"],
        )
        app = DiffViewerTestApp(viewer)

        async with app.run_test():
            queried = app.query_one(DiffViewer)
            assert queried.drift_fields == ["host"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_diff_viewer_identical_states(self) -> None:
        """DiffViewer handles identical states."""
        data = {"name": "test", "value": 1}
        viewer = DiffViewer(
            source_state=data.copy(),
            target_state=data.copy(),
        )
        app = DiffViewerTestApp(viewer)

        async with app.run_test():
            queried = app.query_one(DiffViewer)
            assert queried.source_state == queried.target_state

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_diff_viewer_empty_states(self) -> None:
        """DiffViewer handles empty states."""
        viewer = DiffViewer(source_state={}, target_state={})
        app = DiffViewerTestApp(viewer)

        async with app.run_test():
            queried = app.query_one(DiffViewer)
            assert queried.source_state == {}
            assert queried.target_state == {}

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_diff_viewer_has_diff_content(self) -> None:
        """DiffViewer contains diff-content element."""
        viewer = DiffViewer(
            source_state={"a": 1},
            target_state={"a": 2},
        )
        app = DiffViewerTestApp(viewer)

        async with app.run_test():
            # Should have the diff-content container
            content = app.query_one("#diff-content")
            assert content is not None
