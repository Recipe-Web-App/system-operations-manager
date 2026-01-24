"""Konnect Certificate Managers for control plane certificate operations."""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from system_operations_manager.integrations.kong.models.certificate import (
    SNI,
    CACertificate,
    Certificate,
)
from system_operations_manager.integrations.konnect.exceptions import KonnectNotFoundError

if TYPE_CHECKING:
    from system_operations_manager.integrations.konnect.client import KonnectClient

logger = structlog.get_logger()


class KonnectCertificateManager:
    """Manager for Konnect Control Plane certificate operations.

    Provides CRUD operations for TLS certificates via the Konnect Control Plane
    Admin API. Designed to have a similar interface to Kong's CertificateManager
    for consistency.

    Args:
        client: Konnect API client.
        control_plane_id: Control plane ID to operate on.
    """

    def __init__(self, client: KonnectClient, control_plane_id: str) -> None:
        self._client = client
        self._control_plane_id = control_plane_id

    @property
    def control_plane_id(self) -> str:
        """Get the control plane ID."""
        return self._control_plane_id

    def list(
        self,
        *,
        tags: list[str] | None = None,
        limit: int | None = None,
        offset: str | None = None,
    ) -> tuple[list[Certificate], str | None]:
        """List all certificates in the control plane.

        Args:
            tags: Filter by tags.
            limit: Maximum number of certificates to return.
            offset: Pagination offset token.

        Returns:
            Tuple of (list of certificates, next offset for pagination).
        """
        return self._client.list_certificates(
            self._control_plane_id,
            tags=tags,
            limit=limit,
            offset=offset,
        )

    def get(self, certificate_id: str) -> Certificate:
        """Get a certificate by ID.

        Args:
            certificate_id: Certificate ID.

        Returns:
            Certificate details.

        Raises:
            KonnectNotFoundError: If certificate not found.
        """
        return self._client.get_certificate(self._control_plane_id, certificate_id)

    def exists(self, certificate_id: str) -> bool:
        """Check if a certificate exists.

        Args:
            certificate_id: Certificate ID.

        Returns:
            True if the certificate exists, False otherwise.
        """
        try:
            self._client.get_certificate(self._control_plane_id, certificate_id)
            return True
        except KonnectNotFoundError:
            return False

    def create(self, certificate: Certificate) -> Certificate:
        """Create a new certificate.

        Args:
            certificate: Certificate to create.

        Returns:
            Created certificate with ID and timestamps.
        """
        return self._client.create_certificate(self._control_plane_id, certificate)

    def update(self, certificate_id: str, certificate: Certificate) -> Certificate:
        """Update an existing certificate.

        Args:
            certificate_id: Certificate ID to update.
            certificate: Updated certificate data.

        Returns:
            Updated certificate.
        """
        return self._client.update_certificate(self._control_plane_id, certificate_id, certificate)

    def delete(self, certificate_id: str) -> None:
        """Delete a certificate.

        Args:
            certificate_id: Certificate ID to delete.
        """
        self._client.delete_certificate(self._control_plane_id, certificate_id)


class KonnectSNIManager:
    """Manager for Konnect Control Plane SNI operations.

    Provides CRUD operations for Server Name Indications via the Konnect
    Control Plane Admin API. Designed to have a similar interface to
    Kong's SNIManager for consistency.

    Args:
        client: Konnect API client.
        control_plane_id: Control plane ID to operate on.
    """

    def __init__(self, client: KonnectClient, control_plane_id: str) -> None:
        self._client = client
        self._control_plane_id = control_plane_id

    @property
    def control_plane_id(self) -> str:
        """Get the control plane ID."""
        return self._control_plane_id

    def list(
        self,
        *,
        tags: list[str] | None = None,
        limit: int | None = None,
        offset: str | None = None,
    ) -> tuple[list[SNI], str | None]:
        """List all SNIs in the control plane.

        Args:
            tags: Filter by tags.
            limit: Maximum number of SNIs to return.
            offset: Pagination offset token.

        Returns:
            Tuple of (list of SNIs, next offset for pagination).
        """
        return self._client.list_snis(
            self._control_plane_id,
            tags=tags,
            limit=limit,
            offset=offset,
        )

    def get(self, name_or_id: str) -> SNI:
        """Get an SNI by name or ID.

        Args:
            name_or_id: SNI name or ID.

        Returns:
            SNI details.

        Raises:
            KonnectNotFoundError: If SNI not found.
        """
        return self._client.get_sni(self._control_plane_id, name_or_id)

    def exists(self, name_or_id: str) -> bool:
        """Check if an SNI exists.

        Args:
            name_or_id: SNI name or ID.

        Returns:
            True if the SNI exists, False otherwise.
        """
        try:
            self._client.get_sni(self._control_plane_id, name_or_id)
            return True
        except KonnectNotFoundError:
            return False

    def create(self, sni: SNI) -> SNI:
        """Create a new SNI.

        Args:
            sni: SNI to create.

        Returns:
            Created SNI with ID and timestamps.
        """
        return self._client.create_sni(self._control_plane_id, sni)

    def update(self, name_or_id: str, sni: SNI) -> SNI:
        """Update an existing SNI.

        Args:
            name_or_id: SNI name or ID to update.
            sni: Updated SNI data.

        Returns:
            Updated SNI.
        """
        return self._client.update_sni(self._control_plane_id, name_or_id, sni)

    def delete(self, name_or_id: str) -> None:
        """Delete an SNI.

        Args:
            name_or_id: SNI name or ID to delete.
        """
        self._client.delete_sni(self._control_plane_id, name_or_id)


class KonnectCACertificateManager:
    """Manager for Konnect Control Plane CA certificate operations.

    Provides CRUD operations for CA certificates via the Konnect Control Plane
    Admin API. Designed to have a similar interface to Kong's CACertificateManager
    for consistency.

    Args:
        client: Konnect API client.
        control_plane_id: Control plane ID to operate on.
    """

    def __init__(self, client: KonnectClient, control_plane_id: str) -> None:
        self._client = client
        self._control_plane_id = control_plane_id

    @property
    def control_plane_id(self) -> str:
        """Get the control plane ID."""
        return self._control_plane_id

    def list(
        self,
        *,
        tags: list[str] | None = None,
        limit: int | None = None,
        offset: str | None = None,
    ) -> tuple[list[CACertificate], str | None]:
        """List all CA certificates in the control plane.

        Args:
            tags: Filter by tags.
            limit: Maximum number of CA certificates to return.
            offset: Pagination offset token.

        Returns:
            Tuple of (list of CA certificates, next offset for pagination).
        """
        return self._client.list_ca_certificates(
            self._control_plane_id,
            tags=tags,
            limit=limit,
            offset=offset,
        )

    def get(self, ca_certificate_id: str) -> CACertificate:
        """Get a CA certificate by ID.

        Args:
            ca_certificate_id: CA certificate ID.

        Returns:
            CA certificate details.

        Raises:
            KonnectNotFoundError: If CA certificate not found.
        """
        return self._client.get_ca_certificate(self._control_plane_id, ca_certificate_id)

    def exists(self, ca_certificate_id: str) -> bool:
        """Check if a CA certificate exists.

        Args:
            ca_certificate_id: CA certificate ID.

        Returns:
            True if the CA certificate exists, False otherwise.
        """
        try:
            self._client.get_ca_certificate(self._control_plane_id, ca_certificate_id)
            return True
        except KonnectNotFoundError:
            return False

    def create(self, ca_certificate: CACertificate) -> CACertificate:
        """Create a new CA certificate.

        Args:
            ca_certificate: CA certificate to create.

        Returns:
            Created CA certificate with ID and timestamps.
        """
        return self._client.create_ca_certificate(self._control_plane_id, ca_certificate)

    def update(self, ca_certificate_id: str, ca_certificate: CACertificate) -> CACertificate:
        """Update an existing CA certificate.

        Args:
            ca_certificate_id: CA certificate ID to update.
            ca_certificate: Updated CA certificate data.

        Returns:
            Updated CA certificate.
        """
        return self._client.update_ca_certificate(
            self._control_plane_id, ca_certificate_id, ca_certificate
        )

    def delete(self, ca_certificate_id: str) -> None:
        """Delete a CA certificate.

        Args:
            ca_certificate_id: CA certificate ID to delete.
        """
        self._client.delete_ca_certificate(self._control_plane_id, ca_certificate_id)
