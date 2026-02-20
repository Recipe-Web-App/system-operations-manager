"""Unit tests for Konnect certificate manager classes."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from system_operations_manager.integrations.kong.models.certificate import (
    SNI,
    CACertificate,
    Certificate,
)
from system_operations_manager.integrations.konnect.exceptions import KonnectNotFoundError
from system_operations_manager.services.konnect.certificate_manager import (
    KonnectCACertificateManager,
    KonnectCertificateManager,
    KonnectSNIManager,
)

CONTROL_PLANE_ID = "cp-12345"


# ---------------------------------------------------------------------------
# KonnectCertificateManager
# ---------------------------------------------------------------------------


class TestKonnectCertificateManager:
    """Tests for KonnectCertificateManager."""

    @pytest.fixture
    def manager(self, mock_konnect_client: MagicMock) -> KonnectCertificateManager:
        """Create a KonnectCertificateManager with mock client."""
        return KonnectCertificateManager(mock_konnect_client, CONTROL_PLANE_ID)

    @pytest.mark.unit
    def test_init(self, mock_konnect_client: MagicMock) -> None:
        """control_plane_id property should return the ID set at init."""
        manager = KonnectCertificateManager(mock_konnect_client, CONTROL_PLANE_ID)
        assert manager.control_plane_id == CONTROL_PLANE_ID

    @pytest.mark.unit
    def test_list(
        self,
        manager: KonnectCertificateManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """list should delegate to client.list_certificates with default args."""
        mock_cert = MagicMock(spec=Certificate)
        mock_konnect_client.list_certificates.return_value = ([mock_cert], None)

        certs, next_offset = manager.list()

        mock_konnect_client.list_certificates.assert_called_once_with(
            CONTROL_PLANE_ID, tags=None, limit=None, offset=None
        )
        assert certs == [mock_cert]
        assert next_offset is None

    @pytest.mark.unit
    def test_list_with_params(
        self,
        manager: KonnectCertificateManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """list should pass tags, limit, and offset through to the client."""
        mock_konnect_client.list_certificates.return_value = ([], "next-token")

        certs, next_offset = manager.list(tags=["prod"], limit=25, offset="tok-abc")

        mock_konnect_client.list_certificates.assert_called_once_with(
            CONTROL_PLANE_ID, tags=["prod"], limit=25, offset="tok-abc"
        )
        assert certs == []
        assert next_offset == "next-token"

    @pytest.mark.unit
    def test_get(
        self,
        manager: KonnectCertificateManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """get should delegate to client.get_certificate with the correct args."""
        mock_cert = MagicMock(spec=Certificate)
        mock_konnect_client.get_certificate.return_value = mock_cert

        result = manager.get("cert-uuid-001")

        mock_konnect_client.get_certificate.assert_called_once_with(
            CONTROL_PLANE_ID, "cert-uuid-001"
        )
        assert result is mock_cert

    @pytest.mark.unit
    def test_exists_true(
        self,
        manager: KonnectCertificateManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """exists should return True when get_certificate succeeds."""
        mock_konnect_client.get_certificate.return_value = MagicMock(spec=Certificate)

        assert manager.exists("cert-uuid-001") is True

    @pytest.mark.unit
    def test_exists_false(
        self,
        manager: KonnectCertificateManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """exists should return False when get_certificate raises KonnectNotFoundError."""
        mock_konnect_client.get_certificate.side_effect = KonnectNotFoundError(
            "not found", status_code=404
        )

        assert manager.exists("cert-uuid-missing") is False

    @pytest.mark.unit
    def test_create(
        self,
        manager: KonnectCertificateManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """create should delegate to client.create_certificate with the correct args."""
        cert_input = MagicMock(spec=Certificate)
        cert_created = MagicMock(spec=Certificate)
        mock_konnect_client.create_certificate.return_value = cert_created

        result = manager.create(cert_input)

        mock_konnect_client.create_certificate.assert_called_once_with(CONTROL_PLANE_ID, cert_input)
        assert result is cert_created

    @pytest.mark.unit
    def test_update(
        self,
        manager: KonnectCertificateManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """update should delegate to client.update_certificate with the correct args."""
        cert_input = MagicMock(spec=Certificate)
        cert_updated = MagicMock(spec=Certificate)
        mock_konnect_client.update_certificate.return_value = cert_updated

        result = manager.update("cert-uuid-001", cert_input)

        mock_konnect_client.update_certificate.assert_called_once_with(
            CONTROL_PLANE_ID, "cert-uuid-001", cert_input
        )
        assert result is cert_updated

    @pytest.mark.unit
    def test_delete(
        self,
        manager: KonnectCertificateManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """delete should delegate to client.delete_certificate with the correct args."""
        manager.delete("cert-uuid-001")

        mock_konnect_client.delete_certificate.assert_called_once_with(
            CONTROL_PLANE_ID, "cert-uuid-001"
        )


# ---------------------------------------------------------------------------
# KonnectSNIManager
# ---------------------------------------------------------------------------


class TestKonnectSNIManager:
    """Tests for KonnectSNIManager."""

    @pytest.fixture
    def manager(self, mock_konnect_client: MagicMock) -> KonnectSNIManager:
        """Create a KonnectSNIManager with mock client."""
        return KonnectSNIManager(mock_konnect_client, CONTROL_PLANE_ID)

    @pytest.mark.unit
    def test_init(self, mock_konnect_client: MagicMock) -> None:
        """control_plane_id property should return the ID set at init."""
        manager = KonnectSNIManager(mock_konnect_client, CONTROL_PLANE_ID)
        assert manager.control_plane_id == CONTROL_PLANE_ID

    @pytest.mark.unit
    def test_list(
        self,
        manager: KonnectSNIManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """list should delegate to client.list_snis with default args."""
        mock_sni = MagicMock(spec=SNI)
        mock_konnect_client.list_snis.return_value = ([mock_sni], None)

        snis, next_offset = manager.list()

        mock_konnect_client.list_snis.assert_called_once_with(
            CONTROL_PLANE_ID, tags=None, limit=None, offset=None
        )
        assert snis == [mock_sni]
        assert next_offset is None

    @pytest.mark.unit
    def test_list_with_params(
        self,
        manager: KonnectSNIManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """list should pass tags, limit, and offset through to the client."""
        mock_konnect_client.list_snis.return_value = ([], "next-token")

        snis, next_offset = manager.list(tags=["staging"], limit=50, offset="tok-xyz")

        mock_konnect_client.list_snis.assert_called_once_with(
            CONTROL_PLANE_ID, tags=["staging"], limit=50, offset="tok-xyz"
        )
        assert snis == []
        assert next_offset == "next-token"

    @pytest.mark.unit
    def test_get(
        self,
        manager: KonnectSNIManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """get should delegate to client.get_sni with the correct args."""
        mock_sni = MagicMock(spec=SNI)
        mock_konnect_client.get_sni.return_value = mock_sni

        result = manager.get("api.example.com")

        mock_konnect_client.get_sni.assert_called_once_with(CONTROL_PLANE_ID, "api.example.com")
        assert result is mock_sni

    @pytest.mark.unit
    def test_exists_true(
        self,
        manager: KonnectSNIManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """exists should return True when get_sni succeeds."""
        mock_konnect_client.get_sni.return_value = MagicMock(spec=SNI)

        assert manager.exists("api.example.com") is True

    @pytest.mark.unit
    def test_exists_false(
        self,
        manager: KonnectSNIManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """exists should return False when get_sni raises KonnectNotFoundError."""
        mock_konnect_client.get_sni.side_effect = KonnectNotFoundError("not found", status_code=404)

        assert manager.exists("missing.example.com") is False

    @pytest.mark.unit
    def test_create(
        self,
        manager: KonnectSNIManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """create should delegate to client.create_sni with the correct args."""
        sni_input = MagicMock(spec=SNI)
        sni_created = MagicMock(spec=SNI)
        mock_konnect_client.create_sni.return_value = sni_created

        result = manager.create(sni_input)

        mock_konnect_client.create_sni.assert_called_once_with(CONTROL_PLANE_ID, sni_input)
        assert result is sni_created

    @pytest.mark.unit
    def test_update(
        self,
        manager: KonnectSNIManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """update should delegate to client.update_sni with the correct args."""
        sni_input = MagicMock(spec=SNI)
        sni_updated = MagicMock(spec=SNI)
        mock_konnect_client.update_sni.return_value = sni_updated

        result = manager.update("api.example.com", sni_input)

        mock_konnect_client.update_sni.assert_called_once_with(
            CONTROL_PLANE_ID, "api.example.com", sni_input
        )
        assert result is sni_updated

    @pytest.mark.unit
    def test_delete(
        self,
        manager: KonnectSNIManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """delete should delegate to client.delete_sni with the correct args."""
        manager.delete("api.example.com")

        mock_konnect_client.delete_sni.assert_called_once_with(CONTROL_PLANE_ID, "api.example.com")


# ---------------------------------------------------------------------------
# KonnectCACertificateManager
# ---------------------------------------------------------------------------


class TestKonnectCACertificateManager:
    """Tests for KonnectCACertificateManager."""

    @pytest.fixture
    def manager(self, mock_konnect_client: MagicMock) -> KonnectCACertificateManager:
        """Create a KonnectCACertificateManager with mock client."""
        return KonnectCACertificateManager(mock_konnect_client, CONTROL_PLANE_ID)

    @pytest.mark.unit
    def test_init(self, mock_konnect_client: MagicMock) -> None:
        """control_plane_id property should return the ID set at init."""
        manager = KonnectCACertificateManager(mock_konnect_client, CONTROL_PLANE_ID)
        assert manager.control_plane_id == CONTROL_PLANE_ID

    @pytest.mark.unit
    def test_list(
        self,
        manager: KonnectCACertificateManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """list should delegate to client.list_ca_certificates with default args."""
        mock_ca_cert = MagicMock(spec=CACertificate)
        mock_konnect_client.list_ca_certificates.return_value = ([mock_ca_cert], None)

        ca_certs, next_offset = manager.list()

        mock_konnect_client.list_ca_certificates.assert_called_once_with(
            CONTROL_PLANE_ID, tags=None, limit=None, offset=None
        )
        assert ca_certs == [mock_ca_cert]
        assert next_offset is None

    @pytest.mark.unit
    def test_list_with_params(
        self,
        manager: KonnectCACertificateManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """list should pass tags, limit, and offset through to the client."""
        mock_konnect_client.list_ca_certificates.return_value = ([], "next-token")

        ca_certs, next_offset = manager.list(tags=["mtls"], limit=10, offset="tok-def")

        mock_konnect_client.list_ca_certificates.assert_called_once_with(
            CONTROL_PLANE_ID, tags=["mtls"], limit=10, offset="tok-def"
        )
        assert ca_certs == []
        assert next_offset == "next-token"

    @pytest.mark.unit
    def test_get(
        self,
        manager: KonnectCACertificateManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """get should delegate to client.get_ca_certificate with the correct args."""
        mock_ca_cert = MagicMock(spec=CACertificate)
        mock_konnect_client.get_ca_certificate.return_value = mock_ca_cert

        result = manager.get("ca-cert-uuid-001")

        mock_konnect_client.get_ca_certificate.assert_called_once_with(
            CONTROL_PLANE_ID, "ca-cert-uuid-001"
        )
        assert result is mock_ca_cert

    @pytest.mark.unit
    def test_exists_true(
        self,
        manager: KonnectCACertificateManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """exists should return True when get_ca_certificate succeeds."""
        mock_konnect_client.get_ca_certificate.return_value = MagicMock(spec=CACertificate)

        assert manager.exists("ca-cert-uuid-001") is True

    @pytest.mark.unit
    def test_exists_false(
        self,
        manager: KonnectCACertificateManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """exists should return False when get_ca_certificate raises KonnectNotFoundError."""
        mock_konnect_client.get_ca_certificate.side_effect = KonnectNotFoundError(
            "not found", status_code=404
        )

        assert manager.exists("ca-cert-uuid-missing") is False

    @pytest.mark.unit
    def test_create(
        self,
        manager: KonnectCACertificateManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """create should delegate to client.create_ca_certificate with the correct args."""
        ca_cert_input = MagicMock(spec=CACertificate)
        ca_cert_created = MagicMock(spec=CACertificate)
        mock_konnect_client.create_ca_certificate.return_value = ca_cert_created

        result = manager.create(ca_cert_input)

        mock_konnect_client.create_ca_certificate.assert_called_once_with(
            CONTROL_PLANE_ID, ca_cert_input
        )
        assert result is ca_cert_created

    @pytest.mark.unit
    def test_update(
        self,
        manager: KonnectCACertificateManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """update should delegate to client.update_ca_certificate with the correct args."""
        ca_cert_input = MagicMock(spec=CACertificate)
        ca_cert_updated = MagicMock(spec=CACertificate)
        mock_konnect_client.update_ca_certificate.return_value = ca_cert_updated

        result = manager.update("ca-cert-uuid-001", ca_cert_input)

        mock_konnect_client.update_ca_certificate.assert_called_once_with(
            CONTROL_PLANE_ID, "ca-cert-uuid-001", ca_cert_input
        )
        assert result is ca_cert_updated

    @pytest.mark.unit
    def test_delete(
        self,
        manager: KonnectCACertificateManager,
        mock_konnect_client: MagicMock,
    ) -> None:
        """delete should delegate to client.delete_ca_certificate with the correct args."""
        manager.delete("ca-cert-uuid-001")

        mock_konnect_client.delete_ca_certificate.assert_called_once_with(
            CONTROL_PLANE_ID, "ca-cert-uuid-001"
        )
