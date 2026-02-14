"""Unit tests for CertManagerManager."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from system_operations_manager.services.kubernetes.certmanager_manager import (
    ACME_GROUP,
    ACME_VERSION,
    CERT_MANAGER_GROUP,
    CERT_MANAGER_VERSION,
    CERTIFICATE_PLURAL,
    CERTIFICATE_REQUEST_PLURAL,
    CHALLENGE_PLURAL,
    CLUSTER_ISSUER_PLURAL,
    ISSUER_PLURAL,
    LETSENCRYPT_STAGING,
    ORDER_PLURAL,
    CertManagerManager,
)


@pytest.fixture
def mock_k8s_client() -> MagicMock:
    """Create a mock Kubernetes client."""
    mock_client = MagicMock()
    mock_client.default_namespace = "default"
    return mock_client


@pytest.fixture
def manager(mock_k8s_client: MagicMock) -> CertManagerManager:
    """Create a CertManagerManager with mocked client."""
    return CertManagerManager(mock_k8s_client)


# =============================================================================
# Sample CRD objects for testing
# =============================================================================

SAMPLE_CERTIFICATE = {
    "metadata": {
        "name": "my-tls",
        "namespace": "default",
        "uid": "uid-cert-123",
        "creationTimestamp": "2026-01-01T00:00:00Z",
    },
    "spec": {
        "secretName": "my-tls-secret",
        "issuerRef": {
            "name": "letsencrypt-prod",
            "kind": "ClusterIssuer",
            "group": "cert-manager.io",
        },
        "dnsNames": ["example.com", "www.example.com"],
        "duration": "2160h",
        "renewBefore": "360h",
    },
    "status": {
        "conditions": [
            {
                "type": "Ready",
                "status": "True",
                "reason": "Ready",
                "message": "Certificate is up to date and has not expired",
            },
        ],
        "notAfter": "2026-04-01T00:00:00Z",
        "notBefore": "2026-01-01T00:00:00Z",
        "renewalTime": "2026-03-17T00:00:00Z",
        "revision": 1,
    },
}

SAMPLE_ISSUER = {
    "metadata": {
        "name": "letsencrypt-staging",
        "namespace": "default",
        "uid": "uid-issuer-123",
        "creationTimestamp": "2026-01-01T00:00:00Z",
    },
    "spec": {
        "acme": {
            "server": LETSENCRYPT_STAGING,
            "email": "admin@example.com",
            "privateKeySecretRef": {"name": "letsencrypt-staging-key"},
            "solvers": [{"http01": {"ingress": {"class": "nginx"}}}],
        },
    },
    "status": {
        "conditions": [
            {
                "type": "Ready",
                "status": "True",
                "reason": "ACMEAccountRegistered",
                "message": "The ACME account was registered",
            },
        ],
        "acme": {
            "uri": "https://acme-staging-v02.api.letsencrypt.org/acme/acct/123",
            "lastRegisteredEmail": "admin@example.com",
        },
    },
}

SAMPLE_CLUSTER_ISSUER = {
    "metadata": {
        "name": "letsencrypt-prod",
        "uid": "uid-ci-123",
        "creationTimestamp": "2026-01-01T00:00:00Z",
    },
    "spec": {
        "acme": {
            "server": "https://acme-v02.api.letsencrypt.org/directory",
            "email": "admin@example.com",
            "privateKeySecretRef": {"name": "letsencrypt-prod-key"},
            "solvers": [{"http01": {"ingress": {"class": "nginx"}}}],
        },
    },
    "status": {
        "conditions": [
            {
                "type": "Ready",
                "status": "True",
                "reason": "ACMEAccountRegistered",
                "message": "The ACME account was registered",
            },
        ],
        "acme": {
            "uri": "https://acme-v02.api.letsencrypt.org/acme/acct/456",
            "lastRegisteredEmail": "admin@example.com",
        },
    },
}

SAMPLE_CERTIFICATE_REQUEST = {
    "metadata": {
        "name": "my-tls-1",
        "namespace": "default",
        "uid": "uid-cr-123",
        "creationTimestamp": "2026-01-01T00:00:00Z",
    },
    "spec": {
        "issuerRef": {
            "name": "letsencrypt-prod",
            "kind": "ClusterIssuer",
            "group": "cert-manager.io",
        },
    },
    "status": {
        "conditions": [
            {"type": "Approved", "status": "True", "reason": "AutoApproved"},
            {"type": "Ready", "status": "True", "reason": "Issued"},
        ],
    },
}

SAMPLE_ORDER = {
    "metadata": {
        "name": "my-tls-1-order",
        "namespace": "default",
        "uid": "uid-order-123",
        "creationTimestamp": "2026-01-01T00:00:00Z",
    },
    "spec": {
        "dnsNames": ["example.com"],
    },
    "status": {
        "state": "valid",
        "url": "https://acme-v02.api.letsencrypt.org/acme/order/123/456",
        "conditions": [],
    },
}

SAMPLE_CHALLENGE = {
    "metadata": {
        "name": "my-tls-1-challenge",
        "namespace": "default",
        "uid": "uid-challenge-123",
        "creationTimestamp": "2026-01-01T00:00:00Z",
        "ownerReferences": [
            {"kind": "Order", "name": "my-tls-1-order"},
        ],
    },
    "spec": {
        "dnsName": "example.com",
        "issuerRef": {"name": "letsencrypt-prod", "kind": "ClusterIssuer"},
        "solver": {"http01": {"ingress": {"class": "nginx"}}},
        "token": "abc123",
        "url": "https://acme-v02.api.letsencrypt.org/acme/chall/123",
    },
    "status": {
        "state": "valid",
        "presented": True,
        "processing": False,
        "conditions": [],
    },
}


# =============================================================================
# Certificate Operations
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestCertificateOperations:
    """Tests for Certificate CRUD operations."""

    def test_list_certificates(
        self,
        manager: CertManagerManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_certificates should call custom_objects API with correct CRD coordinates."""
        mock_k8s_client.custom_objects.list_namespaced_custom_object.return_value = {
            "items": [SAMPLE_CERTIFICATE]
        }

        certs = manager.list_certificates()

        assert len(certs) == 1
        assert certs[0].name == "my-tls"
        assert certs[0].secret_name == "my-tls-secret"
        assert certs[0].issuer_name == "letsencrypt-prod"
        assert certs[0].ready is True
        mock_k8s_client.custom_objects.list_namespaced_custom_object.assert_called_once_with(
            CERT_MANAGER_GROUP,
            CERT_MANAGER_VERSION,
            "default",
            CERTIFICATE_PLURAL,
        )

    def test_list_certificates_with_namespace(
        self,
        manager: CertManagerManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_certificates should use provided namespace."""
        mock_k8s_client.custom_objects.list_namespaced_custom_object.return_value = {"items": []}

        manager.list_certificates(namespace="production")

        mock_k8s_client.custom_objects.list_namespaced_custom_object.assert_called_once_with(
            CERT_MANAGER_GROUP,
            CERT_MANAGER_VERSION,
            "production",
            CERTIFICATE_PLURAL,
        )

    def test_list_certificates_with_label_selector(
        self,
        manager: CertManagerManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_certificates should pass label_selector to API."""
        mock_k8s_client.custom_objects.list_namespaced_custom_object.return_value = {"items": []}

        manager.list_certificates(label_selector="app=myapp")

        mock_k8s_client.custom_objects.list_namespaced_custom_object.assert_called_once_with(
            CERT_MANAGER_GROUP,
            CERT_MANAGER_VERSION,
            "default",
            CERTIFICATE_PLURAL,
            label_selector="app=myapp",
        )

    def test_get_certificate(
        self,
        manager: CertManagerManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_certificate should return a CertificateSummary."""
        mock_k8s_client.custom_objects.get_namespaced_custom_object.return_value = (
            SAMPLE_CERTIFICATE
        )

        cert = manager.get_certificate("my-tls")

        assert cert.name == "my-tls"
        assert cert.secret_name == "my-tls-secret"
        assert cert.issuer_name == "letsencrypt-prod"
        assert cert.issuer_kind == "ClusterIssuer"
        assert cert.dns_names == ["example.com", "www.example.com"]
        assert cert.duration == "2160h"
        assert cert.renew_before == "360h"
        assert cert.ready is True
        assert cert.not_after == "2026-04-01T00:00:00Z"
        assert cert.renewal_time == "2026-03-17T00:00:00Z"
        assert cert.revision == 1
        mock_k8s_client.custom_objects.get_namespaced_custom_object.assert_called_once_with(
            CERT_MANAGER_GROUP,
            CERT_MANAGER_VERSION,
            "default",
            CERTIFICATE_PLURAL,
            "my-tls",
        )

    def test_create_certificate(
        self,
        manager: CertManagerManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_certificate should build correct CRD body."""
        mock_k8s_client.custom_objects.create_namespaced_custom_object.return_value = (
            SAMPLE_CERTIFICATE
        )

        cert = manager.create_certificate(
            "my-tls",
            secret_name="my-tls-secret",
            issuer_name="letsencrypt-prod",
            dns_names=["example.com", "www.example.com"],
            issuer_kind="ClusterIssuer",
            duration="2160h",
            renew_before="360h",
        )

        assert cert.name == "my-tls"
        call_args = mock_k8s_client.custom_objects.create_namespaced_custom_object.call_args
        body = call_args[0][4]
        assert body["kind"] == "Certificate"
        assert body["apiVersion"] == f"{CERT_MANAGER_GROUP}/{CERT_MANAGER_VERSION}"
        assert body["spec"]["secretName"] == "my-tls-secret"
        assert body["spec"]["issuerRef"]["name"] == "letsencrypt-prod"
        assert body["spec"]["issuerRef"]["kind"] == "ClusterIssuer"
        assert body["spec"]["dnsNames"] == ["example.com", "www.example.com"]
        assert body["spec"]["duration"] == "2160h"
        assert body["spec"]["renewBefore"] == "360h"

    def test_create_certificate_minimal(
        self,
        manager: CertManagerManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_certificate with minimal args should omit optional fields."""
        mock_k8s_client.custom_objects.create_namespaced_custom_object.return_value = (
            SAMPLE_CERTIFICATE
        )

        manager.create_certificate(
            "my-tls",
            secret_name="my-tls-secret",
            issuer_name="letsencrypt-prod",
            dns_names=["example.com"],
        )

        call_args = mock_k8s_client.custom_objects.create_namespaced_custom_object.call_args
        body = call_args[0][4]
        assert "commonName" not in body["spec"]
        assert "duration" not in body["spec"]
        assert "renewBefore" not in body["spec"]

    def test_delete_certificate(
        self,
        manager: CertManagerManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """delete_certificate should call delete API."""
        manager.delete_certificate("my-tls")

        mock_k8s_client.custom_objects.delete_namespaced_custom_object.assert_called_once_with(
            CERT_MANAGER_GROUP,
            CERT_MANAGER_VERSION,
            "default",
            CERTIFICATE_PLURAL,
            "my-tls",
        )

    def test_get_certificate_status(
        self,
        manager: CertManagerManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_certificate_status should return detailed status dict."""
        mock_k8s_client.custom_objects.get_namespaced_custom_object.return_value = (
            SAMPLE_CERTIFICATE
        )

        status = manager.get_certificate_status("my-tls")

        assert status["name"] == "my-tls"
        assert status["not_after"] == "2026-04-01T00:00:00Z"
        assert status["renewal_time"] == "2026-03-17T00:00:00Z"
        assert status["revision"] == 1
        assert status["issuer"] == "ClusterIssuer/letsencrypt-prod"

    def test_renew_certificate(
        self,
        manager: CertManagerManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """renew_certificate should patch with renewal annotation."""
        mock_k8s_client.custom_objects.patch_namespaced_custom_object.return_value = {}

        result = manager.renew_certificate("my-tls")

        assert result["renewed"] is True
        call_args = mock_k8s_client.custom_objects.patch_namespaced_custom_object.call_args
        patch = call_args[0][5]
        assert patch["metadata"]["annotations"]["cert-manager.io/renew"] == ""

    def test_error_handling_delegates_to_base(
        self,
        manager: CertManagerManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """API errors should be translated via _handle_api_error."""
        api_error = Exception("API Error")
        mock_k8s_client.custom_objects.get_namespaced_custom_object.side_effect = api_error
        mock_k8s_client.translate_api_exception.side_effect = RuntimeError("translated")

        with pytest.raises(RuntimeError, match="translated"):
            manager.get_certificate("my-tls")

        mock_k8s_client.translate_api_exception.assert_called_once()


# =============================================================================
# Issuer Operations
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestIssuerOperations:
    """Tests for Issuer CRUD operations."""

    def test_list_issuers(
        self,
        manager: CertManagerManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_issuers should call custom_objects API."""
        mock_k8s_client.custom_objects.list_namespaced_custom_object.return_value = {
            "items": [SAMPLE_ISSUER]
        }

        issuers = manager.list_issuers()

        assert len(issuers) == 1
        assert issuers[0].name == "letsencrypt-staging"
        assert issuers[0].issuer_type == "acme"
        assert issuers[0].acme_server == LETSENCRYPT_STAGING
        assert issuers[0].acme_email == "admin@example.com"
        assert issuers[0].ready is True
        mock_k8s_client.custom_objects.list_namespaced_custom_object.assert_called_once_with(
            CERT_MANAGER_GROUP,
            CERT_MANAGER_VERSION,
            "default",
            ISSUER_PLURAL,
        )

    def test_get_issuer(
        self,
        manager: CertManagerManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_issuer should return an IssuerSummary."""
        mock_k8s_client.custom_objects.get_namespaced_custom_object.return_value = SAMPLE_ISSUER

        issuer = manager.get_issuer("letsencrypt-staging")

        assert issuer.name == "letsencrypt-staging"
        assert issuer.issuer_type == "acme"
        assert issuer.is_cluster_issuer is False

    def test_create_issuer(
        self,
        manager: CertManagerManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_issuer should build correct CRD body."""
        mock_k8s_client.custom_objects.create_namespaced_custom_object.return_value = SAMPLE_ISSUER

        issuer = manager.create_issuer(
            "self-signed",
            issuer_type="selfSigned",
            config={},
        )

        assert issuer.name == "letsencrypt-staging"
        call_args = mock_k8s_client.custom_objects.create_namespaced_custom_object.call_args
        body = call_args[0][4]
        assert body["kind"] == "Issuer"
        assert "selfSigned" in body["spec"]

    def test_delete_issuer(
        self,
        manager: CertManagerManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """delete_issuer should call delete API."""
        manager.delete_issuer("letsencrypt-staging")

        mock_k8s_client.custom_objects.delete_namespaced_custom_object.assert_called_once_with(
            CERT_MANAGER_GROUP,
            CERT_MANAGER_VERSION,
            "default",
            ISSUER_PLURAL,
            "letsencrypt-staging",
        )

    def test_get_issuer_status(
        self,
        manager: CertManagerManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_issuer_status should return ACME registration details."""
        mock_k8s_client.custom_objects.get_namespaced_custom_object.return_value = SAMPLE_ISSUER

        status = manager.get_issuer_status("letsencrypt-staging")

        assert status["name"] == "letsencrypt-staging"
        assert status["acme_last_registered_email"] == "admin@example.com"
        assert status["acme_uri"] is not None


# =============================================================================
# ClusterIssuer Operations
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestClusterIssuerOperations:
    """Tests for ClusterIssuer CRUD operations."""

    def test_list_cluster_issuers(
        self,
        manager: CertManagerManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_cluster_issuers should call cluster-scoped API."""
        mock_k8s_client.custom_objects.list_cluster_custom_object.return_value = {
            "items": [SAMPLE_CLUSTER_ISSUER]
        }

        issuers = manager.list_cluster_issuers()

        assert len(issuers) == 1
        assert issuers[0].name == "letsencrypt-prod"
        assert issuers[0].is_cluster_issuer is True
        mock_k8s_client.custom_objects.list_cluster_custom_object.assert_called_once_with(
            CERT_MANAGER_GROUP,
            CERT_MANAGER_VERSION,
            CLUSTER_ISSUER_PLURAL,
        )

    def test_get_cluster_issuer(
        self,
        manager: CertManagerManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_cluster_issuer should return an IssuerSummary with is_cluster_issuer=True."""
        mock_k8s_client.custom_objects.get_cluster_custom_object.return_value = (
            SAMPLE_CLUSTER_ISSUER
        )

        issuer = manager.get_cluster_issuer("letsencrypt-prod")

        assert issuer.name == "letsencrypt-prod"
        assert issuer.is_cluster_issuer is True
        assert issuer.issuer_type == "acme"

    def test_create_cluster_issuer(
        self,
        manager: CertManagerManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_cluster_issuer should build correct cluster-scoped body."""
        mock_k8s_client.custom_objects.create_cluster_custom_object.return_value = (
            SAMPLE_CLUSTER_ISSUER
        )

        manager.create_cluster_issuer(
            "letsencrypt-prod",
            issuer_type="acme",
            config={"server": "https://acme-v02.api.letsencrypt.org/directory"},
        )

        call_args = mock_k8s_client.custom_objects.create_cluster_custom_object.call_args
        body = call_args[0][3]
        assert body["kind"] == "ClusterIssuer"
        assert "namespace" not in body["metadata"]

    def test_delete_cluster_issuer(
        self,
        manager: CertManagerManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """delete_cluster_issuer should call cluster-scoped delete API."""
        manager.delete_cluster_issuer("letsencrypt-prod")

        mock_k8s_client.custom_objects.delete_cluster_custom_object.assert_called_once_with(
            CERT_MANAGER_GROUP,
            CERT_MANAGER_VERSION,
            CLUSTER_ISSUER_PLURAL,
            "letsencrypt-prod",
        )


# =============================================================================
# ACME Helper Operations
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestACMEHelpers:
    """Tests for ACME convenience methods."""

    def test_create_acme_issuer(
        self,
        manager: CertManagerManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_acme_issuer should build ACME config from simple params."""
        mock_k8s_client.custom_objects.create_namespaced_custom_object.return_value = SAMPLE_ISSUER

        manager.create_acme_issuer(
            "letsencrypt-staging",
            email="admin@example.com",
            ingress_class="nginx",
        )

        call_args = mock_k8s_client.custom_objects.create_namespaced_custom_object.call_args
        body = call_args[0][4]
        acme_spec = body["spec"]["acme"]
        assert acme_spec["server"] == LETSENCRYPT_STAGING
        assert acme_spec["email"] == "admin@example.com"
        assert acme_spec["privateKeySecretRef"]["name"] == "letsencrypt-staging-account-key"
        assert len(acme_spec["solvers"]) == 1
        assert "http01" in acme_spec["solvers"][0]
        assert acme_spec["solvers"][0]["http01"]["ingress"]["class"] == "nginx"

    def test_create_acme_issuer_dns01(
        self,
        manager: CertManagerManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_acme_issuer with dns01 solver should use dns01 config."""
        mock_k8s_client.custom_objects.create_namespaced_custom_object.return_value = SAMPLE_ISSUER

        manager.create_acme_issuer(
            "letsencrypt-staging",
            email="admin@example.com",
            solver_type="dns01",
        )

        call_args = mock_k8s_client.custom_objects.create_namespaced_custom_object.call_args
        body = call_args[0][4]
        acme_spec = body["spec"]["acme"]
        assert "dns01" in acme_spec["solvers"][0]

    def test_create_acme_cluster_issuer(
        self,
        manager: CertManagerManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """create_acme_cluster_issuer should create cluster-scoped ACME issuer."""
        mock_k8s_client.custom_objects.create_cluster_custom_object.return_value = (
            SAMPLE_CLUSTER_ISSUER
        )

        manager.create_acme_cluster_issuer(
            "letsencrypt-prod",
            email="admin@example.com",
        )

        call_args = mock_k8s_client.custom_objects.create_cluster_custom_object.call_args
        body = call_args[0][3]
        assert body["kind"] == "ClusterIssuer"
        assert body["spec"]["acme"]["email"] == "admin@example.com"


# =============================================================================
# CertificateRequest, Order, Challenge Operations
# =============================================================================


@pytest.mark.unit
@pytest.mark.kubernetes
class TestReadOnlyOperations:
    """Tests for read-only CertificateRequest, Order, and Challenge operations."""

    def test_list_certificate_requests(
        self,
        manager: CertManagerManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_certificate_requests should return parsed summaries."""
        mock_k8s_client.custom_objects.list_namespaced_custom_object.return_value = {
            "items": [SAMPLE_CERTIFICATE_REQUEST]
        }

        requests = manager.list_certificate_requests()

        assert len(requests) == 1
        assert requests[0].name == "my-tls-1"
        assert requests[0].approved is True
        assert requests[0].ready is True
        mock_k8s_client.custom_objects.list_namespaced_custom_object.assert_called_once_with(
            CERT_MANAGER_GROUP,
            CERT_MANAGER_VERSION,
            "default",
            CERTIFICATE_REQUEST_PLURAL,
        )

    def test_get_certificate_request(
        self,
        manager: CertManagerManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_certificate_request should return a CertificateRequestSummary."""
        mock_k8s_client.custom_objects.get_namespaced_custom_object.return_value = (
            SAMPLE_CERTIFICATE_REQUEST
        )

        req = manager.get_certificate_request("my-tls-1")

        assert req.name == "my-tls-1"
        assert req.issuer_name == "letsencrypt-prod"
        assert req.issuer_kind == "ClusterIssuer"
        assert req.approved is True

    def test_list_orders(
        self,
        manager: CertManagerManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_orders should use ACME group and version."""
        mock_k8s_client.custom_objects.list_namespaced_custom_object.return_value = {
            "items": [SAMPLE_ORDER]
        }

        orders = manager.list_orders()

        assert len(orders) == 1
        assert orders[0].name == "my-tls-1-order"
        assert orders[0].state == "valid"
        mock_k8s_client.custom_objects.list_namespaced_custom_object.assert_called_once_with(
            ACME_GROUP,
            ACME_VERSION,
            "default",
            ORDER_PLURAL,
        )

    def test_list_challenges(
        self,
        manager: CertManagerManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """list_challenges should use ACME group and version."""
        mock_k8s_client.custom_objects.list_namespaced_custom_object.return_value = {
            "items": [SAMPLE_CHALLENGE]
        }

        challenges = manager.list_challenges()

        assert len(challenges) == 1
        assert challenges[0].name == "my-tls-1-challenge"
        assert challenges[0].dns_name == "example.com"
        assert challenges[0].challenge_type == "http-01"
        assert challenges[0].presented is True
        mock_k8s_client.custom_objects.list_namespaced_custom_object.assert_called_once_with(
            ACME_GROUP,
            ACME_VERSION,
            "default",
            CHALLENGE_PLURAL,
        )

    def test_get_challenge(
        self,
        manager: CertManagerManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """get_challenge should return a ChallengeSummary."""
        mock_k8s_client.custom_objects.get_namespaced_custom_object.return_value = SAMPLE_CHALLENGE

        challenge = manager.get_challenge("my-tls-1-challenge")

        assert challenge.name == "my-tls-1-challenge"
        assert challenge.state == "valid"

    def test_troubleshoot_challenge(
        self,
        manager: CertManagerManager,
        mock_k8s_client: MagicMock,
    ) -> None:
        """troubleshoot_challenge should return comprehensive troubleshooting dict."""
        mock_k8s_client.custom_objects.get_namespaced_custom_object.return_value = SAMPLE_CHALLENGE

        info = manager.troubleshoot_challenge("my-tls-1-challenge")

        assert info["name"] == "my-tls-1-challenge"
        assert info["dns_name"] == "example.com"
        assert info["solver_type"] == "http-01"
        assert info["presented"] is True
        assert info["order"] == "my-tls-1-order"
        assert info["issuer"] == "ClusterIssuer/letsencrypt-prod"
