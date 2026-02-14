"""Shared fixtures for cert-manager command tests."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def mock_certmanager_manager() -> MagicMock:
    """Create a mock CertManagerManager."""
    manager = MagicMock()

    # Certificates
    manager.list_certificates.return_value = []
    manager.get_certificate.return_value = MagicMock(
        model_dump=lambda **kwargs: {
            "name": "my-tls",
            "namespace": "default",
            "secret_name": "my-tls-secret",
            "issuer_name": "letsencrypt-prod",
            "issuer_kind": "ClusterIssuer",
            "dns_names": ["example.com"],
            "ready": True,
        }
    )
    manager.create_certificate.return_value = MagicMock(
        model_dump=lambda **kwargs: {
            "name": "my-tls",
            "namespace": "default",
            "secret_name": "my-tls-secret",
        }
    )
    manager.delete_certificate.return_value = None
    manager.get_certificate_status.return_value = {
        "name": "my-tls",
        "namespace": "default",
        "not_after": "2026-04-01T00:00:00Z",
        "renewal_time": "2026-03-17T00:00:00Z",
        "revision": 1,
        "conditions": [],
    }
    manager.renew_certificate.return_value = {
        "name": "my-tls",
        "namespace": "default",
        "renewed": True,
    }

    # Issuers
    manager.list_issuers.return_value = []
    manager.get_issuer.return_value = MagicMock(
        model_dump=lambda **kwargs: {
            "name": "letsencrypt-staging",
            "namespace": "default",
            "issuer_type": "acme",
            "ready": True,
        }
    )
    manager.create_issuer.return_value = MagicMock(
        model_dump=lambda **kwargs: {
            "name": "letsencrypt-staging",
            "namespace": "default",
            "issuer_type": "acme",
        }
    )
    manager.delete_issuer.return_value = None
    manager.get_issuer_status.return_value = {
        "name": "letsencrypt-staging",
        "namespace": "default",
        "conditions": [],
        "acme_uri": None,
        "acme_last_registered_email": None,
    }

    # ClusterIssuers
    manager.list_cluster_issuers.return_value = []
    manager.get_cluster_issuer.return_value = MagicMock(
        model_dump=lambda **kwargs: {
            "name": "letsencrypt-prod",
            "issuer_type": "acme",
            "ready": True,
        }
    )
    manager.create_cluster_issuer.return_value = MagicMock(
        model_dump=lambda **kwargs: {
            "name": "letsencrypt-prod",
            "issuer_type": "acme",
        }
    )
    manager.delete_cluster_issuer.return_value = None
    manager.get_cluster_issuer_status.return_value = {
        "name": "letsencrypt-prod",
        "conditions": [],
        "acme_uri": None,
        "acme_last_registered_email": None,
    }

    # ACME helpers
    manager.create_acme_issuer.return_value = MagicMock(
        model_dump=lambda **kwargs: {
            "name": "letsencrypt-staging",
            "namespace": "default",
            "issuer_type": "acme",
        }
    )
    manager.create_acme_cluster_issuer.return_value = MagicMock(
        model_dump=lambda **kwargs: {
            "name": "letsencrypt-prod",
            "issuer_type": "acme",
        }
    )

    # CertificateRequests
    manager.list_certificate_requests.return_value = []
    manager.get_certificate_request.return_value = MagicMock(
        model_dump=lambda **kwargs: {
            "name": "my-tls-1",
            "namespace": "default",
            "issuer_name": "letsencrypt-prod",
            "ready": True,
            "approved": True,
        }
    )

    # Challenges
    manager.list_challenges.return_value = []
    manager.get_challenge.return_value = MagicMock(
        model_dump=lambda **kwargs: {
            "name": "my-challenge",
            "namespace": "default",
            "challenge_type": "http-01",
            "dns_name": "example.com",
            "state": "valid",
        }
    )
    manager.troubleshoot_challenge.return_value = {
        "name": "my-challenge",
        "namespace": "default",
        "dns_name": "example.com",
        "solver_type": "http-01",
        "state": "valid",
        "presented": True,
        "processing": False,
        "reason": None,
        "conditions": [],
    }

    return manager


@pytest.fixture
def get_certmanager_manager(
    mock_certmanager_manager: MagicMock,
) -> Callable[[], MagicMock]:
    """Factory function returning the mock CertManager manager."""
    return lambda: mock_certmanager_manager
