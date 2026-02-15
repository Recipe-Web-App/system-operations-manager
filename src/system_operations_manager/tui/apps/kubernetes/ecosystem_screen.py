"""Ecosystem tools overview screen for the Kubernetes TUI.

Displays status panels for ArgoCD applications, Flux CD resources,
Cert-Manager certificates, and Argo Rollouts in a unified dashboard.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from textual import on, work
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import DataTable, Label

from system_operations_manager.integrations.kubernetes.exceptions import (
    KubernetesNotFoundError,
)
from system_operations_manager.tui.apps.kubernetes.widgets import RefreshTimer
from system_operations_manager.tui.base import BaseScreen

if TYPE_CHECKING:
    from system_operations_manager.integrations.kubernetes.client import (
        KubernetesClient,
    )
    from system_operations_manager.services.kubernetes.argocd_manager import (
        ArgoCDManager,
    )
    from system_operations_manager.services.kubernetes.certmanager_manager import (
        CertManagerManager,
    )
    from system_operations_manager.services.kubernetes.flux_manager import FluxManager
    from system_operations_manager.services.kubernetes.rollouts_manager import (
        RolloutsManager,
    )

logger = structlog.get_logger()

# ============================================================================
# Column Definitions
# ============================================================================

ARGOCD_COLUMNS: list[tuple[str, int]] = [
    ("Name", 25),
    ("Namespace", 15),
    ("Project", 12),
    ("Sync", 10),
    ("Health", 10),
    ("Repo", 30),
]

FLUX_COLUMNS: list[tuple[str, int]] = [
    ("Name", 25),
    ("Namespace", 15),
    ("Type", 12),
    ("Ready", 8),
    ("Status", 15),
    ("Revision", 20),
]

CERT_COLUMNS: list[tuple[str, int]] = [
    ("Name", 25),
    ("Namespace", 15),
    ("Ready", 8),
    ("Expiry", 20),
    ("Issuer", 20),
    ("DNS Names", 25),
]

ROLLOUT_COLUMNS: list[tuple[str, int]] = [
    ("Name", 25),
    ("Namespace", 15),
    ("Strategy", 10),
    ("Phase", 12),
    ("Ready", 10),
    ("Weight", 8),
]

# ============================================================================
# Color Maps
# ============================================================================

SYNC_STATUS_COLORS: dict[str, str] = {
    "Synced": "green",
    "OutOfSync": "yellow",
    "Unknown": "dim",
}

HEALTH_STATUS_COLORS: dict[str, str] = {
    "Healthy": "green",
    "Degraded": "red",
    "Progressing": "yellow",
    "Suspended": "dim",
    "Missing": "red",
    "Unknown": "dim",
}

PHASE_COLORS: dict[str, str] = {
    "Healthy": "green",
    "Paused": "yellow",
    "Degraded": "red",
    "Progressing": "cyan",
    "Abort": "red",
    "Error": "red",
}


# ============================================================================
# EcosystemScreen
# ============================================================================


class EcosystemScreen(BaseScreen[None]):
    """Dashboard for ecosystem tools: ArgoCD, Flux, Cert-Manager, Rollouts.

    Presents a 2x2 grid of DataTables, each showing resources from one
    ecosystem tool. Panels load independently and gracefully handle
    missing CRDs.

    Args:
        client: Kubernetes API client instance.
    """

    BINDINGS = [
        ("escape", "back", "Back"),
        ("r", "refresh", "Refresh"),
        ("1", "focus_argocd", "ArgoCD"),
        ("2", "focus_flux", "Flux"),
        ("3", "focus_certs", "Certs"),
        ("4", "focus_rollouts", "Rollouts"),
    ]

    def __init__(self, client: KubernetesClient) -> None:
        """Initialize the ecosystem screen.

        Args:
            client: Kubernetes API client for cluster communication.
        """
        super().__init__()
        self._client = client
        self.__argocd_mgr: ArgoCDManager | None = None
        self.__flux_mgr: FluxManager | None = None
        self.__cert_mgr: CertManagerManager | None = None
        self.__rollouts_mgr: RolloutsManager | None = None

    # =========================================================================
    # Lazy Manager Properties
    # =========================================================================

    @property
    def _argocd_mgr(self) -> ArgoCDManager:
        """Lazy-loaded ArgoCD manager instance."""
        if self.__argocd_mgr is None:
            from system_operations_manager.services.kubernetes.argocd_manager import (
                ArgoCDManager,
            )

            self.__argocd_mgr = ArgoCDManager(self._client)
        return self.__argocd_mgr

    @property
    def _flux_mgr(self) -> FluxManager:
        """Lazy-loaded Flux manager instance."""
        if self.__flux_mgr is None:
            from system_operations_manager.services.kubernetes.flux_manager import (
                FluxManager,
            )

            self.__flux_mgr = FluxManager(self._client)
        return self.__flux_mgr

    @property
    def _cert_mgr(self) -> CertManagerManager:
        """Lazy-loaded Cert-Manager manager instance."""
        if self.__cert_mgr is None:
            from system_operations_manager.services.kubernetes.certmanager_manager import (
                CertManagerManager,
            )

            self.__cert_mgr = CertManagerManager(self._client)
        return self.__cert_mgr

    @property
    def _rollouts_mgr(self) -> RolloutsManager:
        """Lazy-loaded Argo Rollouts manager instance."""
        if self.__rollouts_mgr is None:
            from system_operations_manager.services.kubernetes.rollouts_manager import (
                RolloutsManager,
            )

            self.__rollouts_mgr = RolloutsManager(self._client)
        return self.__rollouts_mgr

    # =========================================================================
    # Layout
    # =========================================================================

    def compose(self) -> ComposeResult:
        """Compose the ecosystem dashboard layout."""
        yield Container(
            Label(
                "[bold]Ecosystem Tools Overview[/bold]",
                id="ecosystem-header",
            ),
            Horizontal(
                Container(
                    Label(
                        "[bold]ArgoCD Applications[/bold]",
                        classes="panel-title",
                    ),
                    DataTable(id="argocd-table"),
                    id="argocd-panel",
                    classes="ecosystem-panel",
                ),
                Container(
                    Label(
                        "[bold]Flux Resources[/bold]",
                        classes="panel-title",
                    ),
                    DataTable(id="flux-table"),
                    id="flux-panel",
                    classes="ecosystem-panel",
                ),
                id="ecosystem-top-row",
            ),
            Horizontal(
                Container(
                    Label(
                        "[bold]Cert-Manager Certificates[/bold]",
                        classes="panel-title",
                    ),
                    DataTable(id="cert-table"),
                    id="cert-panel",
                    classes="ecosystem-panel",
                ),
                Container(
                    Label(
                        "[bold]Argo Rollouts[/bold]",
                        classes="panel-title",
                    ),
                    DataTable(id="rollouts-table"),
                    id="rollouts-panel",
                    classes="ecosystem-panel",
                ),
                id="ecosystem-bottom-row",
            ),
            RefreshTimer(interval=30),
            id="ecosystem-container",
        )

    def on_mount(self) -> None:
        """Configure tables and load initial data."""
        self._setup_tables()
        self._refresh_all()

    # =========================================================================
    # Table Setup
    # =========================================================================

    def _setup_tables(self) -> None:
        """Configure DataTable columns for all four panels."""
        for table_id, columns in [
            ("argocd-table", ARGOCD_COLUMNS),
            ("flux-table", FLUX_COLUMNS),
            ("cert-table", CERT_COLUMNS),
            ("rollouts-table", ROLLOUT_COLUMNS),
        ]:
            table = self.query_one(f"#{table_id}", DataTable)
            table.cursor_type = "row"
            table.zebra_stripes = True
            for col_label, width in columns:
                table.add_column(col_label, width=width)

    # =========================================================================
    # Refresh
    # =========================================================================

    def _refresh_all(self) -> None:
        """Trigger background data loading for all panels."""
        self._load_argocd()
        self._load_flux()
        self._load_certs()
        self._load_rollouts()

    @on(RefreshTimer.RefreshTriggered)
    def handle_auto_refresh(self, event: RefreshTimer.RefreshTriggered) -> None:
        """Handle auto-refresh timer firing."""
        self._refresh_all()

    @on(RefreshTimer.IntervalChanged)
    def handle_interval_changed(self, event: RefreshTimer.IntervalChanged) -> None:
        """Handle refresh interval change."""
        self.notify_user(f"Refresh interval: {event.interval}s")

    # =========================================================================
    # Panel Loaders
    # =========================================================================

    @work(thread=True)
    def _load_argocd(self) -> None:
        """Load ArgoCD application data in a background thread."""
        table = self.query_one("#argocd-table", DataTable)
        self.app.call_from_thread(table.clear)
        try:
            apps = self._argocd_mgr.list_applications()
            if not apps:
                self.app.call_from_thread(
                    self._add_info_row,
                    "argocd-table",
                    "No applications found",
                    len(ARGOCD_COLUMNS),
                )
                return
            for app in apps:
                self.app.call_from_thread(
                    table.add_row,
                    app.name,
                    app.namespace or "",
                    app.project,
                    _colorize(app.sync_status, SYNC_STATUS_COLORS),
                    _colorize(app.health_status, HEALTH_STATUS_COLORS),
                    app.repo_url,
                )
        except KubernetesNotFoundError:
            logger.debug("argocd_not_installed")
            self.app.call_from_thread(
                self._add_info_row,
                "argocd-table",
                "ArgoCD not installed",
                len(ARGOCD_COLUMNS),
            )
        except Exception as e:
            logger.warning("argocd_load_error", error=str(e))
            self.app.call_from_thread(
                self._add_info_row,
                "argocd-table",
                f"Error: {e}",
                len(ARGOCD_COLUMNS),
            )

    @work(thread=True)
    def _load_flux(self) -> None:
        """Load Flux CD resource data in a background thread."""
        table = self.query_one("#flux-table", DataTable)
        self.app.call_from_thread(table.clear)
        try:
            rows: list[tuple[str, ...]] = []

            git_repos = self._flux_mgr.list_git_repositories()
            for repo in git_repos:
                rows.append(
                    (
                        repo.name,
                        repo.namespace or "",
                        "GitRepo",
                        _ready_indicator(repo.ready),
                        _flux_status(repo.ready, repo.reconciling, repo.suspended),
                        repo.artifact_revision or "-",
                    )
                )

            kustomizations = self._flux_mgr.list_kustomizations()
            for ks in kustomizations:
                rows.append(
                    (
                        ks.name,
                        ks.namespace or "",
                        "Kustomization",
                        _ready_indicator(ks.ready),
                        _flux_status(ks.ready, ks.reconciling, ks.suspended),
                        ks.last_applied_revision or "-",
                    )
                )

            helm_releases = self._flux_mgr.list_helm_releases()
            for hr in helm_releases:
                rows.append(
                    (
                        hr.name,
                        hr.namespace or "",
                        "HelmRelease",
                        _ready_indicator(hr.ready),
                        _flux_status(hr.ready, hr.reconciling, hr.suspended),
                        hr.chart_name,
                    )
                )

            if not rows:
                self.app.call_from_thread(
                    self._add_info_row,
                    "flux-table",
                    "No Flux resources found",
                    len(FLUX_COLUMNS),
                )
                return
            for row in rows:
                self.app.call_from_thread(table.add_row, *row)
        except KubernetesNotFoundError:
            logger.debug("flux_not_installed")
            self.app.call_from_thread(
                self._add_info_row,
                "flux-table",
                "Flux CD not installed",
                len(FLUX_COLUMNS),
            )
        except Exception as e:
            logger.warning("flux_load_error", error=str(e))
            self.app.call_from_thread(
                self._add_info_row,
                "flux-table",
                f"Error: {e}",
                len(FLUX_COLUMNS),
            )

    @work(thread=True)
    def _load_certs(self) -> None:
        """Load Cert-Manager certificate data in a background thread."""
        table = self.query_one("#cert-table", DataTable)
        self.app.call_from_thread(table.clear)
        try:
            certs = self._cert_mgr.list_certificates()
            if not certs:
                self.app.call_from_thread(
                    self._add_info_row,
                    "cert-table",
                    "No certificates found",
                    len(CERT_COLUMNS),
                )
                return
            for cert in certs:
                dns_display = ", ".join(cert.dns_names[:3])
                if len(cert.dns_names) > 3:
                    dns_display += f" (+{len(cert.dns_names) - 3})"
                self.app.call_from_thread(
                    table.add_row,
                    cert.name,
                    cert.namespace or "",
                    _ready_indicator(cert.ready),
                    cert.not_after or "N/A",
                    cert.issuer_name,
                    dns_display,
                )
        except KubernetesNotFoundError:
            logger.debug("certmanager_not_installed")
            self.app.call_from_thread(
                self._add_info_row,
                "cert-table",
                "Cert-Manager not installed",
                len(CERT_COLUMNS),
            )
        except Exception as e:
            logger.warning("certmanager_load_error", error=str(e))
            self.app.call_from_thread(
                self._add_info_row,
                "cert-table",
                f"Error: {e}",
                len(CERT_COLUMNS),
            )

    @work(thread=True)
    def _load_rollouts(self) -> None:
        """Load Argo Rollouts data in a background thread."""
        table = self.query_one("#rollouts-table", DataTable)
        self.app.call_from_thread(table.clear)
        try:
            rollouts = self._rollouts_mgr.list_rollouts()
            if not rollouts:
                self.app.call_from_thread(
                    self._add_info_row,
                    "rollouts-table",
                    "No rollouts found",
                    len(ROLLOUT_COLUMNS),
                )
                return
            for ro in rollouts:
                ready_str = f"{ro.ready_replicas}/{ro.replicas}"
                weight_str = f"{ro.canary_weight}%" if ro.strategy == "canary" else "-"
                self.app.call_from_thread(
                    table.add_row,
                    ro.name,
                    ro.namespace or "",
                    ro.strategy,
                    _colorize(ro.phase, PHASE_COLORS),
                    ready_str,
                    weight_str,
                )
        except KubernetesNotFoundError:
            logger.debug("rollouts_not_installed")
            self.app.call_from_thread(
                self._add_info_row,
                "rollouts-table",
                "Argo Rollouts not installed",
                len(ROLLOUT_COLUMNS),
            )
        except Exception as e:
            logger.warning("rollouts_load_error", error=str(e))
            self.app.call_from_thread(
                self._add_info_row,
                "rollouts-table",
                f"Error: {e}",
                len(ROLLOUT_COLUMNS),
            )

    # =========================================================================
    # Helpers
    # =========================================================================

    def _add_info_row(self, table_id: str, message: str, col_count: int) -> None:
        """Add a single informational row spanning the first column.

        Args:
            table_id: ID of the DataTable (without '#').
            message: Message text to display.
            col_count: Number of columns in the table.
        """
        table = self.query_one(f"#{table_id}", DataTable)
        cells = [f"[dim]{message}[/dim]"] + [""] * (col_count - 1)
        table.add_row(*cells)

    # =========================================================================
    # Keyboard Actions
    # =========================================================================

    def action_back(self) -> None:
        """Navigate back to previous screen."""
        self.go_back()

    def action_refresh(self) -> None:
        """Manually refresh all panels."""
        self._refresh_all()

    def action_focus_argocd(self) -> None:
        """Focus the ArgoCD panel."""
        self.query_one("#argocd-table", DataTable).focus()

    def action_focus_flux(self) -> None:
        """Focus the Flux panel."""
        self.query_one("#flux-table", DataTable).focus()

    def action_focus_certs(self) -> None:
        """Focus the Cert-Manager panel."""
        self.query_one("#cert-table", DataTable).focus()

    def action_focus_rollouts(self) -> None:
        """Focus the Argo Rollouts panel."""
        self.query_one("#rollouts-table", DataTable).focus()


# ============================================================================
# Module-level Helpers
# ============================================================================


def _colorize(text: str, color_map: dict[str, str]) -> str:
    """Apply Rich markup color to text based on a color map.

    Args:
        text: The text to colorize.
        color_map: Mapping of text values to Rich color names.

    Returns:
        Rich-markup formatted string, or the original text if no mapping found.
    """
    color = color_map.get(text)
    if color:
        return f"[{color}]{text}[/{color}]"
    return text


def _ready_indicator(ready: bool) -> str:
    """Return a colorized ready/not-ready indicator.

    Args:
        ready: Whether the resource is ready.

    Returns:
        Rich-markup formatted indicator string.
    """
    if ready:
        return "[green]Yes[/green]"
    return "[red]No[/red]"


def _flux_status(ready: bool, reconciling: bool, suspended: bool) -> str:
    """Derive a human-readable status string for a Flux resource.

    Args:
        ready: Whether the resource is ready.
        reconciling: Whether the resource is reconciling.
        suspended: Whether the resource is suspended.

    Returns:
        Colorized status string.
    """
    if suspended:
        return "[dim]Suspended[/dim]"
    if reconciling:
        return "[cyan]Reconciling[/cyan]"
    if ready:
        return "[green]Ready[/green]"
    return "[red]Not Ready[/red]"
