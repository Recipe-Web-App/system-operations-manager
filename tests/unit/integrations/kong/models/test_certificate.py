"""Unit tests for Kong certificate models."""

from __future__ import annotations

import pytest

from system_operations_manager.integrations.kong.models.base import KongEntityReference
from system_operations_manager.integrations.kong.models.certificate import (
    SNI,
    CACertificate,
    Certificate,
    CertificateSummary,
)


@pytest.mark.unit
class TestCertificate:
    """Tests for Certificate model."""

    def test_create_minimal_certificate(self) -> None:
        """Should create certificate with required fields."""
        cert = Certificate(
            cert="FAKE-CERT-PEM-DATA",
            key="FAKE-KEY-PEM-DATA",
        )

        assert cert.cert == "FAKE-CERT-PEM-DATA"
        assert cert.key == "FAKE-KEY-PEM-DATA"
        assert cert.cert_alt is None
        assert cert.key_alt is None
        assert cert.snis is None

    def test_create_certificate_with_all_fields(self) -> None:
        """Should create certificate with optional fields."""
        cert = Certificate(
            cert="FAKE-RSA-CERT-PEM",
            key="FAKE-RSA-KEY-PEM",
            cert_alt="FAKE-ECDSA-CERT-PEM",
            key_alt="FAKE-ECDSA-KEY-PEM",
            snis=["api.example.com", "www.example.com"],
            tags=["production"],
        )

        assert cert.cert_alt is not None
        assert cert.key_alt is not None
        assert cert.snis == ["api.example.com", "www.example.com"]
        assert cert.tags == ["production"]

    def test_to_create_payload_excludes_snis(self) -> None:
        """to_create_payload should exclude snis field."""
        cert = Certificate(
            cert="FAKE-CERT-PEM",
            key="FAKE-KEY-PEM",
            snis=["api.example.com"],
            tags=["production"],
        )

        payload = cert.to_create_payload()

        assert "snis" not in payload
        assert "cert" in payload
        assert "key" in payload
        assert "tags" in payload

    def test_to_create_payload_excludes_id_and_timestamps(self) -> None:
        """to_create_payload should exclude id, created_at, updated_at."""
        cert = Certificate(
            id="cert-uuid-123",
            created_at=1704067200,
            updated_at=1704067200,
            cert="FAKE-CERT-PEM",
            key="FAKE-KEY-PEM",
        )

        payload = cert.to_create_payload()

        assert "id" not in payload
        assert "created_at" not in payload
        assert "updated_at" not in payload

    def test_to_create_payload_excludes_none_values(self) -> None:
        """to_create_payload should exclude None optional fields."""
        cert = Certificate(
            cert="FAKE-CERT-PEM",
            key="FAKE-KEY-PEM",
        )

        payload = cert.to_create_payload()

        assert "cert_alt" not in payload
        assert "key_alt" not in payload


@pytest.mark.unit
class TestCertificateSummary:
    """Tests for CertificateSummary model."""

    def test_create_empty_summary(self) -> None:
        """Should create summary with all defaults."""
        summary = CertificateSummary()

        assert summary.cert is None
        assert summary.snis is None
        assert summary.id is None

    def test_create_summary_with_fields(self) -> None:
        """Should create summary with cert and snis."""
        summary = CertificateSummary(
            id="cert-uuid-456",
            cert="FAKE-CERT-PEM\n...\nFAKE-CERT-PEM-END",
            snis=["api.example.com"],
        )

        assert summary.id == "cert-uuid-456"
        assert summary.snis == ["api.example.com"]


@pytest.mark.unit
class TestSNI:
    """Tests for SNI model."""

    def test_create_sni(self) -> None:
        """Should create SNI with name and certificate reference."""
        sni = SNI(
            name="api.example.com",
            certificate=KongEntityReference.from_id("cert-uuid-here"),
        )

        assert sni.name == "api.example.com"
        assert sni.certificate.id == "cert-uuid-here"

    def test_identifier_returns_name(self) -> None:
        """identifier property should return the SNI hostname (line 110)."""
        sni = SNI(
            name="api.example.com",
            certificate=KongEntityReference.from_id("cert-uuid-here"),
        )

        assert sni.identifier == "api.example.com"

    def test_identifier_with_different_name(self) -> None:
        """identifier property should return whatever name is set."""
        sni = SNI(
            name="internal.service.local",
            certificate=KongEntityReference.from_name("my-cert"),
        )

        assert sni.identifier == "internal.service.local"


@pytest.mark.unit
class TestCACertificate:
    """Tests for CACertificate model."""

    def test_create_ca_certificate(self) -> None:
        """Should create CA certificate with required cert field."""
        ca_cert = CACertificate(
            cert="FAKE-CERT-PEM\nCA...\nFAKE-CERT-PEM-END",
        )

        assert ca_cert.cert.startswith("FAKE-CERT-PEM")
        assert ca_cert.cert_digest is None

    def test_create_ca_certificate_with_digest(self) -> None:
        """Should create CA certificate with digest."""
        ca_cert = CACertificate(
            cert="FAKE-CERT-PEM\nCA...\nFAKE-CERT-PEM-END",
            cert_digest="abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        )

        assert ca_cert.cert_digest is not None

    def test_identifier_with_cert_digest_returns_truncated_digest(self) -> None:
        """identifier should return first 16 chars of digest plus '...' when digest present (lines 144-145)."""
        digest = "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
        ca_cert = CACertificate(
            cert="FAKE-CERT-PEM\nCA...\nFAKE-CERT-PEM-END",
            cert_digest=digest,
        )

        result = ca_cert.identifier

        assert result == digest[:16] + "..."
        assert result == "abcdef1234567890..."

    def test_identifier_without_digest_returns_id(self) -> None:
        """identifier should return self.id when cert_digest is absent and id is set (line 146)."""
        ca_cert = CACertificate(
            id="ca-cert-uuid-789",
            cert="FAKE-CERT-PEM\nCA...\nFAKE-CERT-PEM-END",
        )

        assert ca_cert.identifier == "ca-cert-uuid-789"

    def test_identifier_without_digest_and_id_returns_unknown(self) -> None:
        """identifier should return 'unknown' when both cert_digest and id are absent (line 146)."""
        ca_cert = CACertificate(
            cert="FAKE-CERT-PEM\nCA...\nFAKE-CERT-PEM-END",
        )

        assert ca_cert.identifier == "unknown"

    def test_to_create_payload_excludes_none_values(self) -> None:
        """to_create_payload should exclude None cert_digest."""
        ca_cert = CACertificate(
            cert="FAKE-CERT-PEM\nCA...\nFAKE-CERT-PEM-END",
            tags=["mtls"],
        )

        payload = ca_cert.to_create_payload()

        assert "cert_digest" not in payload
        assert "cert" in payload
        assert "tags" in payload
