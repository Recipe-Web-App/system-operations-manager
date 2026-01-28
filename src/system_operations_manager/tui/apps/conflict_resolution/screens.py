"""Screen definitions for conflict resolution TUI.

This module provides the main screens:
- ConflictListScreen: Shows all conflicts with resolution status
- ConflictDetailScreen: Shows diff and resolution options for one conflict
- SummaryScreen: Shows preview of all resolutions before applying
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.message import Message
from textual.screen import Screen
from textual.widgets import DataTable, Label, Static

from system_operations_manager.services.kong.conflict_resolver import (
    Conflict,
    ConflictResolutionService,
    Resolution,
    ResolutionAction,
)
from system_operations_manager.tui.apps.conflict_resolution.widgets import (
    ResolutionPicker,
)
from system_operations_manager.tui.components import DiffViewer, Modal

if TYPE_CHECKING:
    from system_operations_manager.utils.merge import MergeAnalysis


class ConflictListScreen(Screen[None]):
    """Screen showing list of all conflicts.

    Displays a table of conflicts with their type, name, and resolution
    status. Users can select a conflict to view details and resolve it.
    """

    BINDINGS = [
        ("j", "cursor_down", "Down"),
        ("k", "cursor_up", "Up"),
        ("enter", "select", "Select"),
        ("s", "keep_source_all", "Keep All Source"),
        ("t", "keep_target_all", "Keep All Target"),
        ("m", "merge_all_auto", "Auto-merge All"),
    ]

    class ConflictSelected(Message):
        """Message sent when a conflict is selected."""

        def __init__(self, conflict: Conflict) -> None:
            self.conflict = conflict
            super().__init__()

    def __init__(
        self,
        conflicts: list[Conflict],
        direction: Literal["push", "pull"],
        service: ConflictResolutionService,
    ) -> None:
        """Initialize the conflict list screen.

        Args:
            conflicts: List of conflicts to display.
            direction: Sync direction for labels.
            service: Service for tracking resolutions.
        """
        super().__init__()
        self.conflicts = conflicts
        self.direction = direction
        self.service = service

    def compose(self) -> ComposeResult:
        """Compose the screen layout."""
        source_label = "Gateway" if self.direction == "push" else "Konnect"
        target_label = "Konnect" if self.direction == "push" else "Gateway"

        yield Container(
            Label(
                f"[bold]Conflicts Found:[/bold] {len(self.conflicts)} entities differ between {source_label} and {target_label}",
                id="header-label",
            ),
            DataTable(id="conflict-table"),
            Label(
                "[dim]j/k: navigate | Enter: view details | s: keep all source | t: keep all target | m: auto-merge all | a: apply[/dim]",
                id="footer-hint",
            ),
            id="conflict-list-container",
        )

    def on_mount(self) -> None:
        """Populate the table when mounted."""
        table = self.query_one("#conflict-table", DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True

        # Add columns
        table.add_column("Type", width=15)
        table.add_column("Name", width=30)
        table.add_column("Drift Fields", width=35)
        table.add_column("Status", width=15)

        # Add rows
        for conflict in self.conflicts:
            resolution = self.service.get_resolution(conflict)
            status = resolution.action.value if resolution else "pending"
            status_display = (
                f"[green]{status}[/green]" if resolution else f"[yellow]{status}[/yellow]"
            )

            drift_display = ", ".join(conflict.drift_fields[:3])
            if len(conflict.drift_fields) > 3:
                drift_display += f" (+{len(conflict.drift_fields) - 3} more)"

            table.add_row(
                conflict.entity_type,
                conflict.entity_name,
                drift_display,
                status_display,
            )

    def action_cursor_down(self) -> None:
        """Move cursor down."""
        table = self.query_one("#conflict-table", DataTable)
        table.action_cursor_down()

    def action_cursor_up(self) -> None:
        """Move cursor up."""
        table = self.query_one("#conflict-table", DataTable)
        table.action_cursor_up()

    def action_select(self) -> None:
        """Select the current conflict."""
        table = self.query_one("#conflict-table", DataTable)
        if table.cursor_row is not None and table.cursor_row < len(self.conflicts):
            conflict = self.conflicts[table.cursor_row]
            self.post_message(self.ConflictSelected(conflict))

    @on(DataTable.RowSelected)
    def handle_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection from DataTable (Enter key on focused row)."""
        if event.cursor_row is not None and event.cursor_row < len(self.conflicts):
            conflict = self.conflicts[event.cursor_row]
            self.post_message(self.ConflictSelected(conflict))

    def action_keep_source_all(self) -> None:
        """Apply keep_source to all pending conflicts."""
        # Filter to only pending (unresolved) conflicts
        pending = [c for c in self.conflicts if not self.service.get_resolution(c)]
        count = self.service.apply_batch_resolution(pending, ResolutionAction.KEEP_SOURCE)
        self.notify(f"Applied 'keep source' to {count} conflicts")
        self._refresh_table()

    def action_keep_target_all(self) -> None:
        """Apply keep_target to all pending conflicts."""
        # Filter to only pending (unresolved) conflicts
        pending = [c for c in self.conflicts if not self.service.get_resolution(c)]
        count = self.service.apply_batch_resolution(pending, ResolutionAction.KEEP_TARGET)
        self.notify(f"Applied 'keep target' to {count} conflicts")
        self._refresh_table()

    def action_merge_all_auto(self) -> None:
        """Auto-merge all conflicts that have non-overlapping changes."""
        from system_operations_manager.utils.merge import (
            analyze_merge_potential,
            compute_auto_merge,
        )

        merged_count = 0
        skipped_count = 0

        for conflict in self.conflicts:
            # Skip already resolved conflicts
            if self.service.get_resolution(conflict):
                continue

            # Analyze merge potential
            analysis = analyze_merge_potential(
                conflict.source_state,
                conflict.target_state,
            )

            if analysis.can_auto_merge:
                # Compute merged state and create resolution
                merged_state = compute_auto_merge(
                    conflict.source_state,
                    conflict.target_state,
                    analysis,
                )
                resolution = Resolution(
                    conflict=conflict,
                    action=ResolutionAction.MERGE,
                    merged_state=merged_state,
                )
                self.service.set_resolution(resolution)
                merged_count += 1
            else:
                skipped_count += 1

        if merged_count > 0:
            self.notify(f"Auto-merged {merged_count} conflicts")
        if skipped_count > 0:
            self.notify(f"Skipped {skipped_count} conflicts with overlapping changes")

        self._refresh_table()

    def _refresh_table(self) -> None:
        """Refresh the table to show updated resolution status."""
        table = self.query_one("#conflict-table", DataTable)
        table.clear()

        for conflict in self.conflicts:
            resolution = self.service.get_resolution(conflict)
            status = resolution.action.value if resolution else "pending"
            status_display = (
                f"[green]{status}[/green]" if resolution else f"[yellow]{status}[/yellow]"
            )

            drift_display = ", ".join(conflict.drift_fields[:3])
            if len(conflict.drift_fields) > 3:
                drift_display += f" (+{len(conflict.drift_fields) - 3} more)"

            table.add_row(
                conflict.entity_type,
                conflict.entity_name,
                drift_display,
                status_display,
            )


class ConflictDetailScreen(Screen[None]):
    """Screen showing details of a single conflict.

    Displays a side-by-side or unified diff of the conflict, along with
    resolution options for the user to choose from.
    """

    BINDINGS = [
        ("1", "keep_source", "Keep Source"),
        ("2", "keep_target", "Keep Target"),
        ("3", "skip", "Skip"),
        ("4", "merge", "Merge"),
        ("d", "toggle_diff_mode", "Toggle Diff Mode"),
        ("escape", "back", "Back"),
    ]

    class ResolutionMade(Message):
        """Message sent when user makes a resolution."""

        def __init__(self, resolution: Resolution) -> None:
            self.resolution = resolution
            super().__init__()

    def __init__(
        self,
        conflict: Conflict,
        service: ConflictResolutionService,
    ) -> None:
        """Initialize the detail screen.

        Args:
            conflict: The conflict to display.
            service: Service for resolution tracking.
        """
        super().__init__()
        self.conflict = conflict
        self.service = service
        self._diff_mode: Literal["side_by_side", "unified"] = "side_by_side"

    def compose(self) -> ComposeResult:
        """Compose the screen layout."""
        yield Container(
            # Header with conflict info
            Vertical(
                Label(
                    f"[bold]{self.conflict.entity_type}:[/bold] {self.conflict.entity_name}",
                    id="conflict-title",
                ),
                Label(
                    f"[dim]Drift in: {', '.join(self.conflict.drift_fields)}[/dim]",
                    id="drift-fields",
                ),
                id="detail-header",
            ),
            # Diff viewer
            DiffViewer(
                source_state=self.conflict.source_state,
                target_state=self.conflict.target_state,
                source_label=self.conflict.source_label,
                target_label=self.conflict.target_label,
                drift_fields=self.conflict.drift_fields,
                id="diff-viewer",
            ),
            # Resolution picker
            ResolutionPicker(
                source_label=self.conflict.source_label,
                target_label=self.conflict.target_label,
                id="resolution-picker",
            ),
            id="detail-container",
        )

    def action_keep_source(self) -> None:
        """Resolve by keeping source."""
        self._make_resolution(ResolutionAction.KEEP_SOURCE)

    def action_keep_target(self) -> None:
        """Resolve by keeping target."""
        self._make_resolution(ResolutionAction.KEEP_TARGET)

    def action_skip(self) -> None:
        """Skip this conflict."""
        self._make_resolution(ResolutionAction.SKIP)

    def action_merge(self) -> None:
        """Merge changes from both source and target."""
        from system_operations_manager.utils.merge import (
            analyze_merge_potential,
            compute_auto_merge,
        )

        # Analyze merge potential
        analysis = analyze_merge_potential(
            self.conflict.source_state,
            self.conflict.target_state,
        )

        if analysis.can_auto_merge:
            # Auto-merge possible - compute and apply
            merged_state = compute_auto_merge(
                self.conflict.source_state,
                self.conflict.target_state,
                analysis,
            )
            resolution = Resolution(
                conflict=self.conflict,
                action=ResolutionAction.MERGE,
                merged_state=merged_state,
            )
            self.post_message(self.ResolutionMade(resolution))
            self.notify("Auto-merged successfully")
        else:
            # Manual merge required - push to MergePreviewScreen
            self.app.push_screen(
                MergePreviewScreen(
                    conflict=self.conflict,
                    analysis=analysis,
                ),
                callback=self._handle_merge_result,
            )

    def _handle_merge_result(self, resolution: Resolution | None) -> None:
        """Handle the result from MergePreviewScreen."""
        if resolution is not None:
            self.post_message(self.ResolutionMade(resolution))

    def action_toggle_diff_mode(self) -> None:
        """Toggle between side-by-side and unified diff."""
        diff_viewer = self.query_one("#diff-viewer", DiffViewer)
        diff_viewer.toggle_mode()

    def action_back(self) -> None:
        """Go back to list."""
        self.app.pop_screen()

    def _make_resolution(self, action: ResolutionAction) -> None:
        """Create and post a resolution."""
        resolution = Resolution(conflict=self.conflict, action=action)
        self.post_message(self.ResolutionMade(resolution))

    @on(ResolutionPicker.ResolutionChosen)
    def handle_resolution_chosen(self, event: ResolutionPicker.ResolutionChosen) -> None:
        """Handle resolution from picker widget."""
        if event.action == ResolutionAction.MERGE:
            # Merge needs special handling
            self.action_merge()
        else:
            self._make_resolution(event.action)


class SummaryScreen(Screen[None]):
    """Screen showing summary of all resolutions before applying.

    Displays what will happen when resolutions are applied and allows
    the user to confirm or cancel via a Modal dialog.
    """

    BINDINGS = [
        ("enter", "show_confirm_modal", "Confirm"),
        ("escape", "cancel", "Cancel"),
    ]

    class ApplyConfirmed(Message):
        """Message sent when user confirms apply."""

        def __init__(self, resolutions: list[Resolution]) -> None:
            self.resolutions = resolutions
            super().__init__()

    class ApplyCancelled(Message):
        """Message sent when user cancels."""

        pass

    def __init__(
        self,
        resolutions: list[Resolution],
        direction: Literal["push", "pull"],
        dry_run: bool = False,
    ) -> None:
        """Initialize the summary screen.

        Args:
            resolutions: List of resolutions to preview.
            direction: Sync direction for labels.
            dry_run: Whether this is a dry-run.
        """
        super().__init__()
        self.resolutions = resolutions
        self.direction = direction
        self.dry_run = dry_run

    def compose(self) -> ComposeResult:
        """Compose the screen layout."""
        # Count by action
        keep_source = sum(1 for r in self.resolutions if r.action == ResolutionAction.KEEP_SOURCE)
        keep_target = sum(1 for r in self.resolutions if r.action == ResolutionAction.KEEP_TARGET)
        skip = sum(1 for r in self.resolutions if r.action == ResolutionAction.SKIP)
        merge = sum(1 for r in self.resolutions if r.action == ResolutionAction.MERGE)

        source_label = "Gateway" if self.direction == "push" else "Konnect"
        target_label = "Konnect" if self.direction == "push" else "Gateway"

        mode_label = "[yellow](DRY RUN)[/yellow]" if self.dry_run else ""

        yield Container(
            Label(
                f"[bold]Resolution Summary[/bold] {mode_label}",
                id="summary-title",
            ),
            Static(
                f"""
[bold]Actions to be taken:[/bold]

  [green]Keep {source_label}:[/green] {keep_source} entities will be synced to {target_label}
  [blue]Keep {target_label}:[/blue] {keep_target} entities will be left unchanged
  [magenta]Merge:[/magenta] {merge} entities will be merged and synced
  [dim]Skip:[/dim] {skip} entities will be skipped

[bold]Total:[/bold] {len(self.resolutions)} resolutions
                """,
                id="summary-stats",
            ),
            Label(
                "[dim]Press Enter to confirm, Escape to cancel[/dim]",
                id="summary-hint",
            ),
            id="summary-container",
        )

    def action_show_confirm_modal(self) -> None:
        """Show confirmation modal."""
        action = "preview" if self.dry_run else "apply"
        body = f"This will {action} {len(self.resolutions)} resolution(s).\n\nContinue?"

        modal = Modal(
            title="Confirm Apply",
            body=body,
            buttons=[
                ("Apply", "apply", "success"),
                ("Cancel", "cancel", "default"),
            ],
            show_cancel=False,  # We already have a cancel button
        )
        self.app.push_screen(modal, self._handle_modal_result)

    def _handle_modal_result(self, result: str | None) -> None:
        """Handle the modal result."""
        if result == "apply":
            self.post_message(self.ApplyConfirmed(self.resolutions))
        # If cancelled (result is None or "cancel"), just close the modal

    def action_cancel(self) -> None:
        """Cancel via keyboard."""
        self.post_message(self.ApplyCancelled())


class MergePreviewScreen(Screen[Resolution | None]):
    """Screen for previewing and editing a merge before confirming.

    Shows the proposed merged state and allows the user to edit it
    in their configured editor if needed.
    """

    BINDINGS = [
        ("e", "edit_merge", "Edit in Editor"),
        ("c", "confirm_merge", "Confirm"),
        ("escape", "cancel", "Cancel"),
    ]

    def __init__(
        self,
        conflict: Conflict,
        analysis: MergeAnalysis,
    ) -> None:
        """Initialize the merge preview screen.

        Args:
            conflict: The conflict being merged.
            analysis: Merge analysis showing conflicting fields.
        """

        super().__init__()
        self.conflict = conflict
        self.analysis: MergeAnalysis = analysis
        self._merged_state: dict[str, Any] | None = None

        # Initialize with source state as base for manual editing
        self._merged_state = dict(conflict.source_state)

    def compose(self) -> ComposeResult:
        """Compose the screen layout."""
        yield Container(
            Label(
                f"[bold]Manual Merge Required:[/bold] {self.conflict.entity_name}",
                id="merge-title",
            ),
            Static(
                f"""
[yellow]The following fields have conflicting changes:[/yellow]
{chr(10).join(f"  - {field}" for field in self.analysis.conflicting_fields)}

[dim]Source-only changes: {len(self.analysis.source_only_fields)} fields[/dim]
[dim]Target-only changes: {len(self.analysis.target_only_fields)} fields[/dim]

Press [bold]e[/bold] to edit the merged result in your editor.
Press [bold]c[/bold] to confirm the current merge.
Press [bold]Escape[/bold] to cancel.
                """,
                id="merge-info",
            ),
            DiffViewer(
                source_state=self.conflict.source_state,
                target_state=self.conflict.target_state,
                source_label=self.conflict.source_label,
                target_label=self.conflict.target_label,
                drift_fields=self.conflict.drift_fields,
                id="merge-diff-viewer",
            ),
            id="merge-container",
        )

    def action_edit_merge(self) -> None:
        """Open editor to edit merged state."""
        import shlex
        import subprocess
        import tempfile
        from pathlib import Path

        from system_operations_manager.utils.editor import (
            create_merge_template,
            get_editor,
            parse_merge_result,
        )
        from system_operations_manager.utils.merge import validate_merged_state

        # Create template with conflict info
        template = create_merge_template(self.conflict)

        # Write to temp file
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            delete=False,
        ) as f:
            f.write(template)
            temp_path = f.name

        try:
            editor = get_editor()

            # Suspend TUI and run editor
            with self.app.suspend():
                subprocess.run([*shlex.split(editor), temp_path], check=False)

            # Read result
            with Path(temp_path).open() as f:
                edited_content = f.read()

            # Parse and validate
            try:
                merged_state = parse_merge_result(edited_content)
                validation = validate_merged_state(
                    merged_state,
                    self.conflict.entity_type,
                    self.conflict.source_state,
                    self.conflict.target_state,
                )

                if not validation.is_valid:
                    self.notify(
                        f"Validation errors: {', '.join(validation.errors)}",
                        severity="error",
                    )
                    return

                if validation.warnings:
                    self.notify(
                        f"Warnings: {', '.join(validation.warnings)}",
                        severity="warning",
                    )

                self._merged_state = merged_state
                self.notify("Merge edited successfully")

            except Exception as e:
                self.notify(f"Failed to parse: {e}", severity="error")

        finally:
            Path(temp_path).unlink()

    def action_confirm_merge(self) -> None:
        """Confirm the merge and return resolution."""
        if self._merged_state is None:
            self.notify("No merged state to confirm", severity="error")
            return

        resolution = Resolution(
            conflict=self.conflict,
            action=ResolutionAction.MERGE,
            merged_state=self._merged_state,
        )
        self.dismiss(resolution)

    def action_cancel(self) -> None:
        """Cancel merge and return to detail screen."""
        self.dismiss(None)
