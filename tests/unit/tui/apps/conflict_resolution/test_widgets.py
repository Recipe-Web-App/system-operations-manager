"""Unit tests for conflict resolution TUI widgets.

Tests the ResolutionPicker widget.
"""

from __future__ import annotations

import pytest
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import RadioButton

from system_operations_manager.services.kong.conflict_resolver import ResolutionAction
from system_operations_manager.tui.apps.conflict_resolution.widgets import (
    ResolutionPicker,
)


class ResolutionPickerTestApp(App[ResolutionAction | None]):
    """Test app for ResolutionPicker widget."""

    def __init__(
        self,
        source_label: str = "Source",
        target_label: str = "Target",
    ) -> None:
        super().__init__()
        self.source_label = source_label
        self.target_label = target_label
        self.chosen_action: ResolutionAction | None = None

    def compose(self) -> ComposeResult:
        with Container():
            yield ResolutionPicker(
                source_label=self.source_label,
                target_label=self.target_label,
            )

    def on_resolution_picker_resolution_chosen(
        self, event: ResolutionPicker.ResolutionChosen
    ) -> None:
        """Handle resolution choice."""
        self.chosen_action = event.action
        self.exit(event.action)


class TestResolutionPickerInit:
    """Tests for ResolutionPicker initialization."""

    @pytest.mark.unit
    def test_resolution_picker_default_labels(self) -> None:
        """ResolutionPicker has default labels."""
        picker = ResolutionPicker()
        assert picker.source_label == "Source"
        assert picker.target_label == "Target"

    @pytest.mark.unit
    def test_resolution_picker_custom_labels(self) -> None:
        """ResolutionPicker accepts custom labels."""
        picker = ResolutionPicker(source_label="Gateway", target_label="Konnect")
        assert picker.source_label == "Gateway"
        assert picker.target_label == "Konnect"


class TestResolutionPickerMessage:
    """Tests for ResolutionChosen message."""

    @pytest.mark.unit
    def test_resolution_chosen_message(self) -> None:
        """ResolutionChosen message stores action."""
        msg = ResolutionPicker.ResolutionChosen(ResolutionAction.KEEP_SOURCE)
        assert msg.action == ResolutionAction.KEEP_SOURCE

    @pytest.mark.unit
    def test_resolution_chosen_message_keep_target(self) -> None:
        """ResolutionChosen can hold KEEP_TARGET action."""
        msg = ResolutionPicker.ResolutionChosen(ResolutionAction.KEEP_TARGET)
        assert msg.action == ResolutionAction.KEEP_TARGET

    @pytest.mark.unit
    def test_resolution_chosen_message_skip(self) -> None:
        """ResolutionChosen can hold SKIP action."""
        msg = ResolutionPicker.ResolutionChosen(ResolutionAction.SKIP)
        assert msg.action == ResolutionAction.SKIP

    @pytest.mark.unit
    def test_resolution_chosen_message_merge(self) -> None:
        """ResolutionChosen can hold MERGE action."""
        msg = ResolutionPicker.ResolutionChosen(ResolutionAction.MERGE)
        assert msg.action == ResolutionAction.MERGE


class TestResolutionPickerAsync:
    """Async tests for ResolutionPicker interaction."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_picker_renders_four_options(self) -> None:
        """ResolutionPicker shows four radio options."""
        app = ResolutionPickerTestApp()

        async with app.run_test():
            radio_buttons = app.query(RadioButton)
            assert len(radio_buttons) == 4

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_picker_has_keep_source_option(self) -> None:
        """ResolutionPicker has keep-source option."""
        app = ResolutionPickerTestApp()

        async with app.run_test():
            keep_source = app.query_one("#keep-source", RadioButton)
            assert keep_source is not None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_picker_has_keep_target_option(self) -> None:
        """ResolutionPicker has keep-target option."""
        app = ResolutionPickerTestApp()

        async with app.run_test():
            keep_target = app.query_one("#keep-target", RadioButton)
            assert keep_target is not None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_picker_has_skip_option(self) -> None:
        """ResolutionPicker has skip option."""
        app = ResolutionPickerTestApp()

        async with app.run_test():
            skip = app.query_one("#skip", RadioButton)
            assert skip is not None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_selecting_keep_source_emits_message(self) -> None:
        """Selecting keep-source emits ResolutionChosen."""
        app = ResolutionPickerTestApp()

        async with app.run_test() as pilot:
            keep_source = app.query_one("#keep-source", RadioButton)
            await pilot.click(keep_source)

        assert app.chosen_action == ResolutionAction.KEEP_SOURCE

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_selecting_keep_target_emits_message(self) -> None:
        """Selecting keep-target emits ResolutionChosen."""
        app = ResolutionPickerTestApp()

        async with app.run_test() as pilot:
            keep_target = app.query_one("#keep-target", RadioButton)
            await pilot.click(keep_target)

        assert app.chosen_action == ResolutionAction.KEEP_TARGET

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_selecting_skip_emits_message(self) -> None:
        """Selecting skip emits ResolutionChosen."""
        app = ResolutionPickerTestApp()

        async with app.run_test() as pilot:
            skip = app.query_one("#skip", RadioButton)
            await pilot.click(skip)

        assert app.chosen_action == ResolutionAction.SKIP

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_picker_shows_custom_labels(self) -> None:
        """ResolutionPicker uses custom labels in options."""
        app = ResolutionPickerTestApp(source_label="Gateway", target_label="Konnect")

        async with app.run_test():
            keep_source = app.query_one("#keep-source", RadioButton)
            keep_target = app.query_one("#keep-target", RadioButton)

            # Labels should contain the custom source/target names
            source_label = str(keep_source.label)
            target_label = str(keep_target.label)

            assert "Gateway" in source_label
            assert "Konnect" in target_label

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_picker_shows_numbered_options(self) -> None:
        """ResolutionPicker options have keyboard numbers."""
        app = ResolutionPickerTestApp()

        async with app.run_test():
            keep_source = app.query_one("#keep-source", RadioButton)
            keep_target = app.query_one("#keep-target", RadioButton)
            skip = app.query_one("#skip", RadioButton)

            assert "[1]" in str(keep_source.label)
            assert "[2]" in str(keep_target.label)
            assert "[3]" in str(skip.label)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_merge_radio_button_present(self) -> None:
        """ResolutionPicker includes merge option as fourth radio button."""
        app = ResolutionPickerTestApp()

        async with app.run_test():
            radio_buttons = app.query(RadioButton)
            # Should now have 4 options: keep-source, keep-target, skip, merge
            assert len(radio_buttons) == 4

            merge = app.query_one("#merge", RadioButton)
            assert merge is not None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_merge_selection_emits_action(self) -> None:
        """Selecting merge option emits ResolutionChosen with MERGE action."""
        app = ResolutionPickerTestApp()

        async with app.run_test() as pilot:
            merge = app.query_one("#merge", RadioButton)
            await pilot.click(merge)

        assert app.chosen_action == ResolutionAction.MERGE

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_key_4_selects_merge(self) -> None:
        """Merge option has [4] in its label."""
        app = ResolutionPickerTestApp()

        async with app.run_test():
            merge = app.query_one("#merge", RadioButton)
            assert "[4]" in str(merge.label)
