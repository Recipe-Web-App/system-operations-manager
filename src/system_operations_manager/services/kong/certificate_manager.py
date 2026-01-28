"""Certificate managers for Kong TLS entities.

This module provides managers for Kong certificate-related entities:
- CertificateManager: TLS certificates for SSL termination
- SNIManager: Server Name Indications mapped to certificates
- CACertificateManager: CA certificates for mTLS
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from system_operations_manager.integrations.kong.models.certificate import (
    SNI,
    CACertificate,
    Certificate,
)
from system_operations_manager.services.kong.base import BaseEntityManager

if TYPE_CHECKING:
    pass


class CertificateManager(BaseEntityManager[Certificate]):
    """Manager for Kong TLS Certificate entities.

    Certificates are used for SSL/TLS termination on Kong routes and services.
    They contain a public certificate and private key pair.

    Example:
        >>> manager = CertificateManager(client)
        >>> cert = Certificate(
        ...     cert="-----BEGIN CERTIFICATE-----\\n...",
        ...     key="-----BEGIN PRIVATE KEY-----\\n...",  # pragma: allowlist secret
        ... )
        >>> created = manager.create(cert)
        >>> snis = manager.get_snis(created.id)
    """

    _endpoint = "certificates"
    _entity_name = "certificate"
    _model_class = Certificate

    def get_snis(self, cert_id_or_name: str) -> list[SNI]:
        """Get all SNIs associated with a certificate.

        Args:
            cert_id_or_name: Certificate ID or name.

        Returns:
            List of SNI entities associated with the certificate.
        """
        self._log.debug("getting_certificate_snis", certificate=cert_id_or_name)
        response = self._client.get(f"certificates/{cert_id_or_name}/snis")
        snis = [SNI.model_validate(s) for s in response.get("data", [])]
        self._log.debug("got_certificate_snis", certificate=cert_id_or_name, count=len(snis))
        return snis


class SNIManager(BaseEntityManager[SNI]):
    """Manager for Kong SNI (Server Name Indication) entities.

    SNIs map domain names to TLS certificates, allowing Kong to serve
    different certificates for different hostnames.

    Example:
        >>> manager = SNIManager(client)
        >>> sni = SNI(
        ...     name="api.example.com",
        ...     certificate=KongEntityReference.from_id("cert-uuid"),
        ... )
        >>> created = manager.create(sni)
    """

    _endpoint = "snis"
    _entity_name = "sni"
    _model_class = SNI

    def list_by_certificate(self, cert_id: str) -> list[SNI]:
        """List all SNIs for a specific certificate.

        Args:
            cert_id: Certificate ID.

        Returns:
            List of SNI entities for the certificate.
        """
        self._log.debug("listing_snis_by_certificate", certificate_id=cert_id)
        response = self._client.get(f"certificates/{cert_id}/snis")
        snis = [SNI.model_validate(s) for s in response.get("data", [])]
        self._log.debug("listed_snis_by_certificate", certificate_id=cert_id, count=len(snis))
        return snis


class CACertificateManager(BaseEntityManager[CACertificate]):
    """Manager for Kong CA Certificate entities.

    CA certificates are used to verify client certificates in mutual TLS
    (mTLS) authentication scenarios.

    Example:
        >>> manager = CACertificateManager(client)
        >>> ca_cert = CACertificate(
        ...     cert="-----BEGIN CERTIFICATE-----\\n...",
        ... )
        >>> created = manager.create(ca_cert)
    """

    _endpoint = "ca_certificates"
    _entity_name = "ca_certificate"
    _model_class = CACertificate

    def get_by_digest(self, cert_digest: str) -> CACertificate | None:
        """Get a CA certificate by its SHA256 digest.

        Args:
            cert_digest: SHA256 digest of the certificate.

        Returns:
            The CA certificate if found, None otherwise.
        """
        self._log.debug("getting_ca_certificate_by_digest", digest=cert_digest[:16])
        ca_certs, _ = self.list()
        for ca_cert in ca_certs:
            if ca_cert.cert_digest == cert_digest:
                return ca_cert
        return None
