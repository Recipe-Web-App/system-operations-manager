"""Unit tests for Kong Certificate managers."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from system_operations_manager.integrations.kong.models.base import KongEntityReference
from system_operations_manager.integrations.kong.models.certificate import (
    SNI,
    CACertificate,
    Certificate,
)
from system_operations_manager.services.kong.certificate_manager import (
    CACertificateManager,
    CertificateManager,
    SNIManager,
)


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock Kong Admin client."""
    return MagicMock()


class TestCertificateManagerInit:
    """Tests for CertificateManager initialization."""

    @pytest.mark.unit
    def test_certificate_manager_initialization(self, mock_client: MagicMock) -> None:
        """Manager should initialize with client."""
        manager = CertificateManager(mock_client)

        assert manager._client is mock_client
        assert manager._endpoint == "certificates"
        assert manager._entity_name == "certificate"
        assert manager._model_class is Certificate


class TestCertificateManagerCRUD:
    """Tests for CertificateManager CRUD operations."""

    @pytest.fixture
    def manager(self, mock_client: MagicMock) -> CertificateManager:
        """Create a CertificateManager with mocked client."""
        return CertificateManager(mock_client)

    @pytest.mark.unit
    def test_list_certificates(self, manager: CertificateManager, mock_client: MagicMock) -> None:
        """list should return certificates."""
        mock_client.get.return_value = {
            "data": [
                {
                    "id": "cert-1",
                    "cert": "-----BEGIN CERTIFICATE-----\nMIIC...\n-----END CERTIFICATE-----",
                    "key": "<key>",
                    "tags": ["production"],
                },
                {
                    "id": "cert-2",
                    "cert": "-----BEGIN CERTIFICATE-----\nMIID...\n-----END CERTIFICATE-----",
                    "key": "<key>",
                    "tags": ["staging"],
                },
            ]
        }

        certs, _offset = manager.list()

        assert len(certs) == 2
        assert certs[0].id == "cert-1"
        assert certs[1].id == "cert-2"
        mock_client.get.assert_called_once()

    @pytest.mark.unit
    def test_list_certificates_with_tags(
        self, manager: CertificateManager, mock_client: MagicMock
    ) -> None:
        """list should filter by tags."""
        mock_client.get.return_value = {
            "data": [
                {
                    "id": "cert-1",
                    "cert": "-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----",
                    "key": "<key>",
                    "tags": ["production"],
                },
            ]
        }

        certs, _offset = manager.list(tags=["production"])

        assert len(certs) == 1
        call_args = mock_client.get.call_args
        assert "tags" in call_args[1]["params"]

    @pytest.mark.unit
    def test_get_certificate(self, manager: CertificateManager, mock_client: MagicMock) -> None:
        """get should return certificate by ID."""
        mock_client.get.return_value = {
            "id": "cert-1",
            "cert": "-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----",
            "key": "<key>",
            "tags": ["production"],
        }

        cert = manager.get("cert-1")

        assert cert.id == "cert-1"
        assert cert.tags == ["production"]
        mock_client.get.assert_called_once_with("certificates/cert-1")

    @pytest.mark.unit
    def test_create_certificate(self, manager: CertificateManager, mock_client: MagicMock) -> None:
        """create should create a new certificate."""
        mock_client.post.return_value = {
            "id": "cert-new",
            "cert": "-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----",
            "key": "<key>",
            "tags": ["new"],
            "created_at": 1234567890,
        }

        cert = Certificate(
            cert="-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----",
            key="<key>",
            tags=["new"],
        )
        created = manager.create(cert)

        assert created.id == "cert-new"
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "certificates"

    @pytest.mark.unit
    def test_update_certificate(self, manager: CertificateManager, mock_client: MagicMock) -> None:
        """update should update an existing certificate."""
        mock_client.patch.return_value = {
            "id": "cert-1",
            "cert": "-----BEGIN CERTIFICATE-----\nupdated\n-----END CERTIFICATE-----",
            "key": "<key>",
            "tags": ["updated"],
        }

        cert = Certificate(
            cert="-----BEGIN CERTIFICATE-----\nupdated\n-----END CERTIFICATE-----",
            key="<key>",
            tags=["updated"],
        )
        updated = manager.update("cert-1", cert)

        assert updated.tags == ["updated"]
        mock_client.patch.assert_called_once()

    @pytest.mark.unit
    def test_delete_certificate(self, manager: CertificateManager, mock_client: MagicMock) -> None:
        """delete should remove certificate."""
        manager.delete("cert-1")

        mock_client.delete.assert_called_once_with("certificates/cert-1")

    @pytest.mark.unit
    def test_exists_returns_true(self, manager: CertificateManager, mock_client: MagicMock) -> None:
        """exists should return True when certificate exists."""
        mock_client.get.return_value = {
            "id": "cert-1",
            "cert": "...",
            "key": "<key>",
        }

        result = manager.exists("cert-1")

        assert result is True

    @pytest.mark.unit
    def test_get_snis(self, manager: CertificateManager, mock_client: MagicMock) -> None:
        """get_snis should return SNIs for a certificate."""
        mock_client.get.return_value = {
            "data": [
                {
                    "id": "sni-1",
                    "name": "example.com",
                    "certificate": {"id": "cert-1"},
                },
                {
                    "id": "sni-2",
                    "name": "www.example.com",
                    "certificate": {"id": "cert-1"},
                },
            ]
        }

        snis = manager.get_snis("cert-1")

        assert len(snis) == 2
        assert snis[0].name == "example.com"
        assert snis[1].name == "www.example.com"
        mock_client.get.assert_called_once_with("certificates/cert-1/snis")


class TestSNIManagerInit:
    """Tests for SNIManager initialization."""

    @pytest.mark.unit
    def test_sni_manager_initialization(self, mock_client: MagicMock) -> None:
        """Manager should initialize with client."""
        manager = SNIManager(mock_client)

        assert manager._client is mock_client
        assert manager._endpoint == "snis"
        assert manager._entity_name == "sni"
        assert manager._model_class is SNI


class TestSNIManagerCRUD:
    """Tests for SNIManager CRUD operations."""

    @pytest.fixture
    def manager(self, mock_client: MagicMock) -> SNIManager:
        """Create a SNIManager with mocked client."""
        return SNIManager(mock_client)

    @pytest.mark.unit
    def test_list_snis(self, manager: SNIManager, mock_client: MagicMock) -> None:
        """list should return SNIs."""
        mock_client.get.return_value = {
            "data": [
                {
                    "id": "sni-1",
                    "name": "example.com",
                    "certificate": {"id": "cert-1"},
                },
                {
                    "id": "sni-2",
                    "name": "api.example.com",
                    "certificate": {"id": "cert-1"},
                },
            ]
        }

        snis, _offset = manager.list()

        assert len(snis) == 2
        assert snis[0].name == "example.com"
        assert snis[1].name == "api.example.com"

    @pytest.mark.unit
    def test_get_sni(self, manager: SNIManager, mock_client: MagicMock) -> None:
        """get should return SNI by name or ID."""
        mock_client.get.return_value = {
            "id": "sni-1",
            "name": "example.com",
            "certificate": {"id": "cert-1"},
        }

        sni = manager.get("example.com")

        assert sni.name == "example.com"
        mock_client.get.assert_called_once_with("snis/example.com")

    @pytest.mark.unit
    def test_create_sni(self, manager: SNIManager, mock_client: MagicMock) -> None:
        """create should create a new SNI."""
        mock_client.post.return_value = {
            "id": "sni-new",
            "name": "new.example.com",
            "certificate": {"id": "cert-1"},
            "created_at": 1234567890,
        }

        sni = SNI(
            name="new.example.com",
            certificate=KongEntityReference(id="cert-1"),
        )
        created = manager.create(sni)

        assert created.name == "new.example.com"
        mock_client.post.assert_called_once()

    @pytest.mark.unit
    def test_delete_sni(self, manager: SNIManager, mock_client: MagicMock) -> None:
        """delete should remove SNI."""
        manager.delete("example.com")

        mock_client.delete.assert_called_once_with("snis/example.com")


class TestCACertificateManagerInit:
    """Tests for CACertificateManager initialization."""

    @pytest.mark.unit
    def test_ca_certificate_manager_initialization(self, mock_client: MagicMock) -> None:
        """Manager should initialize with client."""
        manager = CACertificateManager(mock_client)

        assert manager._client is mock_client
        assert manager._endpoint == "ca_certificates"
        assert manager._entity_name == "ca_certificate"
        assert manager._model_class is CACertificate


class TestCACertificateManagerCRUD:
    """Tests for CACertificateManager CRUD operations."""

    @pytest.fixture
    def manager(self, mock_client: MagicMock) -> CACertificateManager:
        """Create a CACertificateManager with mocked client."""
        return CACertificateManager(mock_client)

    @pytest.mark.unit
    def test_list_ca_certificates(
        self, manager: CACertificateManager, mock_client: MagicMock
    ) -> None:
        """list should return CA certificates."""
        mock_client.get.return_value = {
            "data": [
                {
                    "id": "ca-1",
                    "cert": "-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----",
                    "cert_digest": "abc123",
                    "tags": ["root-ca"],
                },
                {
                    "id": "ca-2",
                    "cert": "-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----",
                    "cert_digest": "def456",
                    "tags": ["intermediate-ca"],
                },
            ]
        }

        cas, _offset = manager.list()

        assert len(cas) == 2
        assert cas[0].id == "ca-1"
        assert cas[1].id == "ca-2"

    @pytest.mark.unit
    def test_get_ca_certificate(
        self, manager: CACertificateManager, mock_client: MagicMock
    ) -> None:
        """get should return CA certificate by ID."""
        mock_client.get.return_value = {
            "id": "ca-1",
            "cert": "-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----",
            "cert_digest": "abc123",
            "tags": ["root-ca"],
        }

        ca = manager.get("ca-1")

        assert ca.id == "ca-1"
        assert ca.cert_digest == "abc123"
        mock_client.get.assert_called_once_with("ca_certificates/ca-1")

    @pytest.mark.unit
    def test_create_ca_certificate(
        self, manager: CACertificateManager, mock_client: MagicMock
    ) -> None:
        """create should create a new CA certificate."""
        mock_client.post.return_value = {
            "id": "ca-new",
            "cert": "-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----",
            "cert_digest": "new123",
            "tags": ["new-ca"],
            "created_at": 1234567890,
        }

        ca = CACertificate(
            cert="-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----",
            tags=["new-ca"],
        )
        created = manager.create(ca)

        assert created.id == "ca-new"
        mock_client.post.assert_called_once()

    @pytest.mark.unit
    def test_delete_ca_certificate(
        self, manager: CACertificateManager, mock_client: MagicMock
    ) -> None:
        """delete should remove CA certificate."""
        manager.delete("ca-1")

        mock_client.delete.assert_called_once_with("ca_certificates/ca-1")

    @pytest.mark.unit
    def test_get_by_digest_found(
        self, manager: CACertificateManager, mock_client: MagicMock
    ) -> None:
        """get_by_digest should return the matching CA certificate."""
        mock_client.get.return_value = {
            "data": [
                {
                    "id": "ca-1",
                    "cert": "-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----",
                    "cert_digest": "abc123",
                    "tags": ["root-ca"],
                },
                {
                    "id": "ca-2",
                    "cert": "-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----",
                    "cert_digest": "def456",
                    "tags": ["intermediate-ca"],
                },
            ],
            "offset": None,
        }

        result = manager.get_by_digest("abc123")

        assert result is not None
        assert result.id == "ca-1"
        assert result.cert_digest == "abc123"

    @pytest.mark.unit
    def test_get_by_digest_not_found(
        self, manager: CACertificateManager, mock_client: MagicMock
    ) -> None:
        """get_by_digest should return None when digest does not match."""
        mock_client.get.return_value = {
            "data": [
                {
                    "id": "ca-1",
                    "cert": "-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----",
                    "cert_digest": "abc123",
                    "tags": ["root-ca"],
                },
            ],
            "offset": None,
        }

        result = manager.get_by_digest("nonexistent-digest")

        assert result is None


class TestSNIManagerExtended:
    """Additional tests for SNIManager missing coverage."""

    @pytest.fixture
    def manager(self, mock_client: MagicMock) -> SNIManager:
        """Create a SNIManager with mocked client."""
        return SNIManager(mock_client)

    @pytest.mark.unit
    def test_list_by_certificate(self, manager: SNIManager, mock_client: MagicMock) -> None:
        """list_by_certificate should return all SNIs for a certificate."""
        mock_client.get.return_value = {
            "data": [
                {
                    "id": "sni-1",
                    "name": "api.example.com",
                    "certificate": {"id": "cert-1"},
                },
                {
                    "id": "sni-2",
                    "name": "www.example.com",
                    "certificate": {"id": "cert-1"},
                },
            ]
        }

        snis = manager.list_by_certificate("cert-1")

        assert len(snis) == 2
        assert snis[0].name == "api.example.com"
        assert snis[1].name == "www.example.com"
        mock_client.get.assert_called_once_with("certificates/cert-1/snis")
