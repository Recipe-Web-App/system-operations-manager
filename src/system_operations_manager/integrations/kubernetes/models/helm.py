"""Data models for Helm operations.

Typed dataclasses for Helm releases, repositories, charts,
and command results.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class HelmRelease:
    """A deployed Helm release."""

    name: str
    namespace: str
    revision: int
    status: str
    chart: str
    app_version: str
    updated: str

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> HelmRelease:
        """Create a HelmRelease from ``helm list --output json`` entry."""
        return cls(
            name=str(data.get("name", "")),
            namespace=str(data.get("namespace", "")),
            revision=int(data.get("revision", 0)),
            status=str(data.get("status", "")),
            chart=str(data.get("chart", "")),
            app_version=str(data.get("app_version", "")),
            updated=str(data.get("updated", "")),
        )


@dataclass
class HelmReleaseHistory:
    """A single revision entry from ``helm history``."""

    revision: int
    status: str
    chart: str
    app_version: str
    description: str
    updated: str

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> HelmReleaseHistory:
        """Create from ``helm history --output json`` entry."""
        return cls(
            revision=int(data.get("revision", 0)),
            status=str(data.get("status", "")),
            chart=str(data.get("chart", "")),
            app_version=str(data.get("app_version", "")),
            description=str(data.get("description", "")),
            updated=str(data.get("updated", "")),
        )


@dataclass
class HelmRepo:
    """A configured Helm chart repository."""

    name: str
    url: str

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> HelmRepo:
        """Create from ``helm repo list --output json`` entry."""
        return cls(
            name=str(data.get("name", "")),
            url=str(data.get("url", "")),
        )


@dataclass
class HelmChart:
    """A chart found via ``helm search``."""

    name: str
    chart_version: str
    app_version: str
    description: str

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> HelmChart:
        """Create from ``helm search --output json`` entry."""
        return cls(
            name=str(data.get("name", "")),
            chart_version=str(data.get("version", "")),
            app_version=str(data.get("app_version", "")),
            description=str(data.get("description", "")),
        )


@dataclass
class HelmCommandResult:
    """Generic result from a Helm command."""

    success: bool
    stdout: str
    stderr: str = ""

    @property
    def output(self) -> str:
        """Return the primary output (stdout)."""
        return self.stdout


@dataclass
class HelmTemplateResult:
    """Result from ``helm template``."""

    rendered_yaml: str
    success: bool
    error: str | None = None


@dataclass
class HelmReleaseStatus:
    """Detailed status of a Helm release."""

    name: str
    namespace: str
    revision: int
    status: str
    description: str
    notes: str = ""
    raw: str = ""
