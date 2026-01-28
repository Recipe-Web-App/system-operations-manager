"""Integration tests for certificate sync operations.

Tests that sync push and pull operations work correctly with certificate
entity types (certificates, SNIs, CA certificates, key sets, keys, vaults).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from system_operations_manager.integrations.kong.models.base import KongEntityReference
from system_operations_manager.integrations.kong.models.certificate import (
    SNI,
    Certificate,
)
from system_operations_manager.integrations.kong.models.key import Key, KeySet
from system_operations_manager.integrations.kong.models.unified import (
    EntitySource,
    UnifiedEntity,
    UnifiedEntityList,
)
from system_operations_manager.services.kong.sync_audit import SyncAuditService


@pytest.fixture
def audit_file(tmp_path: Path) -> Path:
    """Create a temporary audit file."""
    return tmp_path / "kong_sync_audit.jsonl"


@pytest.fixture
def audit_service(audit_file: Path) -> SyncAuditService:
    """Create an audit service with temporary file."""
    return SyncAuditService(audit_file=audit_file)


@pytest.fixture
def mock_unified_service_with_certificates() -> MagicMock:
    """Create a mock UnifiedQueryService with certificate entities."""
    service = MagicMock()

    # Certificate only in Gateway
    gateway_cert = Certificate(
        id="cert-gw-1",
        cert="-----BEGIN CERTIFICATE-----\nMIIC...\n-----END CERTIFICATE-----",
        key="<key>",
        tags=["production"],
    )

    entity = UnifiedEntity(
        entity=gateway_cert,
        source=EntitySource.GATEWAY,
        gateway_id="cert-gw-1",
        konnect_id=None,
        has_drift=False,
        gateway_entity=gateway_cert,
    )

    entities = UnifiedEntityList(entities=[entity])
    service.list_certificates.return_value = entities

    # Empty lists for other types
    service.list_services.return_value = UnifiedEntityList(entities=[])
    service.list_routes.return_value = UnifiedEntityList(entities=[])
    service.list_consumers.return_value = UnifiedEntityList(entities=[])
    service.list_plugins.return_value = UnifiedEntityList(entities=[])
    service.list_upstreams.return_value = UnifiedEntityList(entities=[])
    service.list_snis.return_value = UnifiedEntityList(entities=[])
    service.list_ca_certificates.return_value = UnifiedEntityList(entities=[])
    service.list_key_sets.return_value = UnifiedEntityList(entities=[])
    service.list_keys.return_value = UnifiedEntityList(entities=[])
    service.list_vaults.return_value = UnifiedEntityList(entities=[])

    return service


@pytest.fixture
def mock_unified_service_with_snis() -> MagicMock:
    """Create a mock UnifiedQueryService with SNI entities."""
    service = MagicMock()

    # SNI only in Gateway
    gateway_sni = SNI(
        id="sni-gw-1",
        name="example.com",
        certificate=KongEntityReference(id="cert-1"),
        tags=["api"],
    )

    entity = UnifiedEntity(
        entity=gateway_sni,
        source=EntitySource.GATEWAY,
        gateway_id="sni-gw-1",
        konnect_id=None,
        has_drift=False,
        gateway_entity=gateway_sni,
    )

    # Empty for other types
    service.list_certificates.return_value = UnifiedEntityList(entities=[])
    service.list_services.return_value = UnifiedEntityList(entities=[])
    service.list_routes.return_value = UnifiedEntityList(entities=[])
    service.list_consumers.return_value = UnifiedEntityList(entities=[])
    service.list_plugins.return_value = UnifiedEntityList(entities=[])
    service.list_upstreams.return_value = UnifiedEntityList(entities=[])
    service.list_snis.return_value = UnifiedEntityList(entities=[entity])
    service.list_ca_certificates.return_value = UnifiedEntityList(entities=[])
    service.list_key_sets.return_value = UnifiedEntityList(entities=[])
    service.list_keys.return_value = UnifiedEntityList(entities=[])
    service.list_vaults.return_value = UnifiedEntityList(entities=[])

    return service


@pytest.fixture
def mock_unified_service_with_keys() -> MagicMock:
    """Create a mock UnifiedQueryService with key entities."""
    service = MagicMock()

    # KeySet only in Gateway
    gateway_keyset = KeySet(
        id="keyset-gw-1",
        name="jwt-keys",
        tags=["jwt"],
    )

    keyset_entity = UnifiedEntity(
        entity=gateway_keyset,
        source=EntitySource.GATEWAY,
        gateway_id="keyset-gw-1",
        konnect_id=None,
        has_drift=False,
        gateway_entity=gateway_keyset,
    )

    # Key only in Gateway
    gateway_key = Key(
        id="key-gw-1",
        kid="key-id-1",
        name="signing-key",
        set=KongEntityReference(id="keyset-gw-1"),
        tags=["signing"],
    )

    key_entity = UnifiedEntity(
        entity=gateway_key,
        source=EntitySource.GATEWAY,
        gateway_id="key-gw-1",
        konnect_id=None,
        has_drift=False,
        gateway_entity=gateway_key,
    )

    # Empty for other types
    service.list_certificates.return_value = UnifiedEntityList(entities=[])
    service.list_services.return_value = UnifiedEntityList(entities=[])
    service.list_routes.return_value = UnifiedEntityList(entities=[])
    service.list_consumers.return_value = UnifiedEntityList(entities=[])
    service.list_plugins.return_value = UnifiedEntityList(entities=[])
    service.list_upstreams.return_value = UnifiedEntityList(entities=[])
    service.list_snis.return_value = UnifiedEntityList(entities=[])
    service.list_ca_certificates.return_value = UnifiedEntityList(entities=[])
    service.list_key_sets.return_value = UnifiedEntityList(entities=[keyset_entity])
    service.list_keys.return_value = UnifiedEntityList(entities=[key_entity])
    service.list_vaults.return_value = UnifiedEntityList(entities=[])

    return service


@pytest.fixture
def mock_unified_service_konnect_certificates() -> MagicMock:
    """Create a mock UnifiedQueryService with Konnect-only certificates."""
    service = MagicMock()

    # Certificate only in Konnect
    konnect_cert = Certificate(
        id="cert-konnect-1",
        cert="-----BEGIN CERTIFICATE-----\nKONNECT...\n-----END CERTIFICATE-----",
        key="<key>",
        tags=["konnect"],
    )

    entity = UnifiedEntity(
        entity=konnect_cert,
        source=EntitySource.KONNECT,
        gateway_id=None,
        konnect_id="cert-konnect-1",
        has_drift=False,
        konnect_entity=konnect_cert,
    )

    service.list_certificates.return_value = UnifiedEntityList(entities=[entity])

    # Empty for other types
    service.list_services.return_value = UnifiedEntityList(entities=[])
    service.list_routes.return_value = UnifiedEntityList(entities=[])
    service.list_consumers.return_value = UnifiedEntityList(entities=[])
    service.list_plugins.return_value = UnifiedEntityList(entities=[])
    service.list_upstreams.return_value = UnifiedEntityList(entities=[])
    service.list_snis.return_value = UnifiedEntityList(entities=[])
    service.list_ca_certificates.return_value = UnifiedEntityList(entities=[])
    service.list_key_sets.return_value = UnifiedEntityList(entities=[])
    service.list_keys.return_value = UnifiedEntityList(entities=[])
    service.list_vaults.return_value = UnifiedEntityList(entities=[])

    return service


@pytest.fixture
def mock_konnect_certificate_manager() -> MagicMock:
    """Create a mock Konnect certificate manager."""
    manager = MagicMock()
    manager.create.return_value = Certificate(
        id="konnect-new-cert",
        cert="-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----",
        key="<key>",
    )
    return manager


@pytest.fixture
def mock_gateway_certificate_manager() -> MagicMock:
    """Create a mock Gateway certificate manager."""
    manager = MagicMock()
    manager.create.return_value = Certificate(
        id="gw-new-cert",
        cert="-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----",
        key="<key>",
    )
    return manager


@pytest.fixture
def mock_konnect_key_set_manager() -> MagicMock:
    """Create a mock Konnect key set manager."""
    manager = MagicMock()
    manager.create.return_value = KeySet(
        id="konnect-new-keyset",
        name="jwt-keys",
    )
    return manager


@pytest.fixture
def mock_konnect_key_manager() -> MagicMock:
    """Create a mock Konnect key manager."""
    manager = MagicMock()
    manager.create.return_value = Key(
        id="konnect-new-key",
        kid="key-id-1",
        name="signing-key",
    )
    return manager


@pytest.mark.integration
class TestCertificateSyncPushIntegration:
    """Integration tests for certificate sync push operations."""

    def test_push_certificates_creates_in_konnect(
        self,
        audit_service: SyncAuditService,
        mock_unified_service_with_certificates: MagicMock,
        mock_konnect_certificate_manager: MagicMock,
    ) -> None:
        """Verify sync push creates certificates in Konnect."""
        from system_operations_manager.plugins.kong.commands.sync import (
            _push_entity_type,
        )

        sync_id = audit_service.start_sync("push", dry_run=False)

        created, updated, errors = _push_entity_type(
            entity_type="certificates",
            unified_service=mock_unified_service_with_certificates,
            konnect_managers={"certificates": mock_konnect_certificate_manager},
            dry_run=False,
            audit_service=audit_service,
            sync_id=sync_id,
        )

        assert created == 1
        assert updated == 0
        assert errors == 0

        # Verify Konnect manager was called
        mock_konnect_certificate_manager.create.assert_called_once()

        # Verify audit entry
        entries = audit_service.get_sync_details(sync_id)
        assert len(entries) == 1
        assert entries[0].entity_type == "certificates"
        assert entries[0].action == "create"
        assert entries[0].status == "success"

    def test_push_certificates_dry_run(
        self,
        audit_service: SyncAuditService,
        mock_unified_service_with_certificates: MagicMock,
        mock_konnect_certificate_manager: MagicMock,
    ) -> None:
        """Verify dry-run push doesn't create certificates."""
        from system_operations_manager.plugins.kong.commands.sync import (
            _push_entity_type,
        )

        sync_id = audit_service.start_sync("push", dry_run=True)

        created, _updated, _errors = _push_entity_type(
            entity_type="certificates",
            unified_service=mock_unified_service_with_certificates,
            konnect_managers={"certificates": mock_konnect_certificate_manager},
            dry_run=True,
            audit_service=audit_service,
            sync_id=sync_id,
        )

        assert created == 1
        mock_konnect_certificate_manager.create.assert_not_called()

        entries = audit_service.get_sync_details(sync_id)
        assert entries[0].status == "would_create"

    def test_push_snis_creates_in_konnect(
        self,
        audit_service: SyncAuditService,
        mock_unified_service_with_snis: MagicMock,
    ) -> None:
        """Verify sync push creates SNIs in Konnect."""
        from system_operations_manager.plugins.kong.commands.sync import (
            _push_entity_type,
        )

        mock_konnect_sni_manager = MagicMock()
        mock_konnect_sni_manager.create.return_value = SNI(
            id="konnect-new-sni",
            name="example.com",
            certificate=KongEntityReference(id="cert-1"),
        )

        sync_id = audit_service.start_sync("push", dry_run=False)

        created, updated, errors = _push_entity_type(
            entity_type="snis",
            unified_service=mock_unified_service_with_snis,
            konnect_managers={"snis": mock_konnect_sni_manager},
            dry_run=False,
            audit_service=audit_service,
            sync_id=sync_id,
        )

        assert created == 1
        assert updated == 0
        assert errors == 0

        entries = audit_service.get_sync_details(sync_id)
        assert entries[0].entity_type == "snis"
        assert entries[0].entity_name == "example.com"

    def test_push_key_sets_creates_in_konnect(
        self,
        audit_service: SyncAuditService,
        mock_unified_service_with_keys: MagicMock,
        mock_konnect_key_set_manager: MagicMock,
    ) -> None:
        """Verify sync push creates key sets in Konnect."""
        from system_operations_manager.plugins.kong.commands.sync import (
            _push_entity_type,
        )

        sync_id = audit_service.start_sync("push", dry_run=False)

        created, updated, errors = _push_entity_type(
            entity_type="key_sets",
            unified_service=mock_unified_service_with_keys,
            konnect_managers={"key_sets": mock_konnect_key_set_manager},
            dry_run=False,
            audit_service=audit_service,
            sync_id=sync_id,
        )

        assert created == 1
        assert updated == 0
        assert errors == 0

        mock_konnect_key_set_manager.create.assert_called_once()

    def test_push_keys_creates_in_konnect(
        self,
        audit_service: SyncAuditService,
        mock_unified_service_with_keys: MagicMock,
        mock_konnect_key_manager: MagicMock,
    ) -> None:
        """Verify sync push creates keys in Konnect."""
        from system_operations_manager.plugins.kong.commands.sync import (
            _push_entity_type,
        )

        sync_id = audit_service.start_sync("push", dry_run=False)

        created, updated, errors = _push_entity_type(
            entity_type="keys",
            unified_service=mock_unified_service_with_keys,
            konnect_managers={"keys": mock_konnect_key_manager},
            dry_run=False,
            audit_service=audit_service,
            sync_id=sync_id,
        )

        assert created == 1
        assert updated == 0
        assert errors == 0

        mock_konnect_key_manager.create.assert_called_once()


@pytest.mark.integration
class TestCertificateSyncPullIntegration:
    """Integration tests for certificate sync pull operations."""

    def test_pull_certificates_creates_in_gateway(
        self,
        audit_service: SyncAuditService,
        mock_unified_service_konnect_certificates: MagicMock,
        mock_gateway_certificate_manager: MagicMock,
    ) -> None:
        """Verify sync pull creates certificates in Gateway."""
        from system_operations_manager.plugins.kong.commands.sync import (
            _pull_entity_type,
        )

        sync_id = audit_service.start_sync("pull", dry_run=False)

        created, updated, errors = _pull_entity_type(
            entity_type="certificates",
            unified_service=mock_unified_service_konnect_certificates,
            gateway_managers={"certificates": mock_gateway_certificate_manager},
            dry_run=False,
            with_drift=False,
            audit_service=audit_service,
            sync_id=sync_id,
        )

        assert created == 1
        assert updated == 0
        assert errors == 0

        mock_gateway_certificate_manager.create.assert_called_once()

        entries = audit_service.get_sync_details(sync_id)
        assert len(entries) == 1
        assert entries[0].entity_type == "certificates"
        assert entries[0].action == "create"
        assert entries[0].source == "konnect"
        assert entries[0].target == "gateway"

    def test_pull_certificates_dry_run(
        self,
        audit_service: SyncAuditService,
        mock_unified_service_konnect_certificates: MagicMock,
        mock_gateway_certificate_manager: MagicMock,
    ) -> None:
        """Verify dry-run pull doesn't create certificates."""
        from system_operations_manager.plugins.kong.commands.sync import (
            _pull_entity_type,
        )

        sync_id = audit_service.start_sync("pull", dry_run=True)

        created, _updated, _errors = _pull_entity_type(
            entity_type="certificates",
            unified_service=mock_unified_service_konnect_certificates,
            gateway_managers={"certificates": mock_gateway_certificate_manager},
            dry_run=True,
            with_drift=False,
            audit_service=audit_service,
            sync_id=sync_id,
        )

        assert created == 1
        mock_gateway_certificate_manager.create.assert_not_called()

        entries = audit_service.get_sync_details(sync_id)
        assert entries[0].status == "would_create"


@pytest.mark.integration
class TestCertificateSyncErrorHandling:
    """Integration tests for error handling in certificate sync."""

    def test_push_certificate_failure_records_error(
        self,
        audit_service: SyncAuditService,
        mock_unified_service_with_certificates: MagicMock,
        mock_konnect_certificate_manager: MagicMock,
    ) -> None:
        """Verify failed certificate push records error in audit."""
        from system_operations_manager.plugins.kong.commands.sync import (
            _push_entity_type,
        )

        mock_konnect_certificate_manager.create.side_effect = Exception(
            "Certificate validation failed"
        )
        sync_id = audit_service.start_sync("push", dry_run=False)

        created, _updated, errors = _push_entity_type(
            entity_type="certificates",
            unified_service=mock_unified_service_with_certificates,
            konnect_managers={"certificates": mock_konnect_certificate_manager},
            dry_run=False,
            audit_service=audit_service,
            sync_id=sync_id,
        )

        assert created == 0
        assert errors == 1

        entries = audit_service.get_sync_details(sync_id)
        assert entries[0].status == "failed"
        assert entries[0].error is not None
        assert "Certificate validation failed" in entries[0].error

    def test_pull_certificate_failure_records_error(
        self,
        audit_service: SyncAuditService,
        mock_unified_service_konnect_certificates: MagicMock,
        mock_gateway_certificate_manager: MagicMock,
    ) -> None:
        """Verify failed certificate pull records error in audit."""
        from system_operations_manager.plugins.kong.commands.sync import (
            _pull_entity_type,
        )

        mock_gateway_certificate_manager.create.side_effect = Exception(
            "Gateway rejected certificate"
        )
        sync_id = audit_service.start_sync("pull", dry_run=False)

        created, _updated, errors = _pull_entity_type(
            entity_type="certificates",
            unified_service=mock_unified_service_konnect_certificates,
            gateway_managers={"certificates": mock_gateway_certificate_manager},
            dry_run=False,
            with_drift=False,
            audit_service=audit_service,
            sync_id=sync_id,
        )

        assert created == 0
        assert errors == 1

        entries = audit_service.get_sync_details(sync_id)
        assert entries[0].status == "failed"
        assert entries[0].error is not None
        assert "Gateway rejected certificate" in entries[0].error
