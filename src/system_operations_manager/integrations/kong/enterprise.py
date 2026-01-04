"""Kong Enterprise edition detection and feature checking.

This module provides utilities for detecting Kong Enterprise edition
and checking which Enterprise features are available.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import structlog

from system_operations_manager.integrations.kong.exceptions import (
    KongAPIError,
    KongEnterpriseRequiredError,
    KongNotFoundError,
)

if TYPE_CHECKING:
    from system_operations_manager.integrations.kong.client import KongAdminClient

logger = structlog.get_logger()


@dataclass
class EnterpriseFeatures:
    """Available Kong Enterprise features.

    Attributes:
        workspaces: Whether workspaces are available.
        rbac: Whether RBAC is available.
        vaults: Whether vaults integration is available.
        developer_portal: Whether Developer Portal is available.
        license_expiration: License expiration timestamp (if available).
        edition: Detected Kong edition string.
    """

    workspaces: bool = False
    rbac: bool = False
    vaults: bool = False
    developer_portal: bool = False
    license_expiration: int | None = None
    edition: str = "community"
    _checked_features: set[str] = field(default_factory=set)

    @property
    def is_enterprise(self) -> bool:
        """Check if this is Kong Enterprise edition."""
        return self.edition.lower() in ("enterprise", "enterprise-edition")

    def __post_init__(self) -> None:
        """Initialize the checked features set."""
        if not isinstance(self._checked_features, set):
            object.__setattr__(self, "_checked_features", set())


class EnterpriseFeatureChecker:
    """Detects Kong Enterprise edition and available features.

    This class probes Kong Admin API endpoints to detect whether
    Enterprise features are available, allowing graceful degradation
    when running against Kong OSS.

    Example:
        ```python
        checker = EnterpriseFeatureChecker(client)
        if checker.is_enterprise():
            features = checker.get_available_features()
            if features.workspaces:
                # Use workspace feature
                pass
        ```
    """

    # Enterprise-only endpoints to probe
    _ENTERPRISE_ENDPOINTS = {
        "workspaces": "/workspaces",
        "rbac": "/rbac/roles",
        "vaults": "/vaults",
        "developer_portal": "/developers",
    }

    def __init__(self, client: KongAdminClient) -> None:
        """Initialize the enterprise feature checker.

        Args:
            client: Configured Kong Admin API client.
        """
        self._client = client
        self._features: EnterpriseFeatures | None = None
        self._cached = False

    def _probe_endpoint(self, endpoint: str) -> bool:
        """Probe an endpoint to check if it's available.

        Args:
            endpoint: The API endpoint to probe.

        Returns:
            True if the endpoint is available (returns 200/404),
            False if it returns 400/404 indicating feature not available.
        """
        try:
            self._client.get(endpoint)
            return True
        except KongNotFoundError:
            # 404 means the endpoint exists but no resources
            # This is normal for empty collections
            return True
        except KongAPIError as e:
            # Check for "not found" in message (older Kong versions)
            if e.status_code == 404:
                return False
            # Other errors might indicate auth issues, not feature availability
            logger.debug(
                "Enterprise endpoint probe failed",
                endpoint=endpoint,
                status=e.status_code,
                message=e.message,
            )
            return False

    def _detect_edition(self) -> str:
        """Detect Kong edition from node info.

        Returns:
            Edition string ("community", "enterprise", etc.)
        """
        try:
            info = self._client.get_info()
            # Kong Enterprise includes edition in the root info
            edition = str(info.get("edition", ""))
            if edition:
                return edition

            # Check for enterprise indicators in configuration
            configuration = info.get("configuration", {})
            if configuration.get("license"):
                return "enterprise"

            # Check plugins for enterprise-only plugins
            plugins = info.get("plugins", {}).get("available_on_server", {})
            enterprise_plugins = {"openid-connect", "vault-auth", "mtls-auth", "oas-validation"}
            if any(plugin in plugins for plugin in enterprise_plugins):
                return "enterprise"

            return "community"
        except KongAPIError:
            return "unknown"

    def is_enterprise(self) -> bool:
        """Check if Kong Enterprise edition is detected.

        This performs a lightweight check by probing the /workspaces endpoint.

        Returns:
            True if Kong Enterprise is detected, False otherwise.
        """
        if self._features is not None:
            return self._features.is_enterprise

        # Quick check: probe workspaces endpoint
        return self._probe_endpoint("/workspaces")

    def get_available_features(self, force_refresh: bool = False) -> EnterpriseFeatures:
        """Get all available Enterprise features.

        This method probes all Enterprise endpoints to determine
        which features are available.

        Args:
            force_refresh: Force re-detection even if cached.

        Returns:
            EnterpriseFeatures dataclass with availability flags.
        """
        if self._features is not None and self._cached and not force_refresh:
            return self._features

        logger.debug("Detecting Kong Enterprise features")

        # Detect edition first
        edition = self._detect_edition()

        # Probe each enterprise endpoint
        features = EnterpriseFeatures(edition=edition)

        for feature_name, endpoint in self._ENTERPRISE_ENDPOINTS.items():
            available = self._probe_endpoint(endpoint)
            setattr(features, feature_name, available)
            features._checked_features.add(feature_name)
            logger.debug(
                "Enterprise feature check",
                feature=feature_name,
                available=available,
            )

        # Try to get license info if enterprise
        if features.is_enterprise:
            try:
                license_info = self._client.get("/license")
                if "license" in license_info:
                    features.license_expiration = license_info["license"].get("expiration")
            except KongAPIError:
                pass  # License endpoint may not be accessible

        self._features = features
        self._cached = True

        logger.info(
            "Kong Enterprise detection complete",
            edition=edition,
            is_enterprise=features.is_enterprise,
            workspaces=features.workspaces,
            rbac=features.rbac,
            vaults=features.vaults,
            developer_portal=features.developer_portal,
        )

        return features

    def require_enterprise(self, feature: str) -> None:
        """Require that a specific Enterprise feature is available.

        Args:
            feature: The feature name to require.

        Raises:
            KongEnterpriseRequiredError: If the feature is not available.
        """
        features = self.get_available_features()

        if not features.is_enterprise:
            raise KongEnterpriseRequiredError(feature=feature)

        # Check specific feature if it's a known one
        if feature in self._ENTERPRISE_ENDPOINTS and not getattr(features, feature, False):
            raise KongEnterpriseRequiredError(
                feature=feature,
                message=f"Kong Enterprise feature '{feature}' is not enabled",
            )

    def check_feature(self, feature: str) -> bool:
        """Check if a specific Enterprise feature is available.

        Args:
            feature: The feature name to check.

        Returns:
            True if the feature is available, False otherwise.
        """
        features = self.get_available_features()

        if not features.is_enterprise:
            return False

        return getattr(features, feature, False)

    def clear_cache(self) -> None:
        """Clear the cached feature detection results."""
        self._features = None
        self._cached = False
