"""Unit tests for Kong Enterprise feature detection."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from system_operations_manager.integrations.kong.enterprise import (
    EnterpriseFeatureChecker,
    EnterpriseFeatures,
)
from system_operations_manager.integrations.kong.exceptions import (
    KongAPIError,
    KongEnterpriseRequiredError,
    KongNotFoundError,
)


class TestEnterpriseFeatures:
    """Tests for EnterpriseFeatures dataclass."""

    @pytest.mark.unit
    def test_enterprise_features_defaults(self) -> None:
        """Features should default to disabled."""
        features = EnterpriseFeatures()

        assert features.workspaces is False
        assert features.rbac is False
        assert features.vaults is False
        assert features.developer_portal is False
        assert features.license_expiration is None
        assert features.edition == "community"

    @pytest.mark.unit
    def test_enterprise_features_is_enterprise_true(self) -> None:
        """is_enterprise should return True for enterprise edition."""
        features = EnterpriseFeatures(edition="enterprise")

        assert features.is_enterprise is True

    @pytest.mark.unit
    def test_enterprise_features_is_enterprise_edition_variant(self) -> None:
        """is_enterprise should return True for enterprise-edition."""
        features = EnterpriseFeatures(edition="enterprise-edition")

        assert features.is_enterprise is True

    @pytest.mark.unit
    def test_enterprise_features_is_enterprise_false(self) -> None:
        """is_enterprise should return False for community edition."""
        features = EnterpriseFeatures(edition="community")

        assert features.is_enterprise is False

    @pytest.mark.unit
    def test_enterprise_features_is_enterprise_case_insensitive(self) -> None:
        """is_enterprise should be case insensitive."""
        features = EnterpriseFeatures(edition="ENTERPRISE")

        assert features.is_enterprise is True

    @pytest.mark.unit
    def test_enterprise_features_with_all_enabled(self) -> None:
        """Features can be created with all features enabled."""
        features = EnterpriseFeatures(
            workspaces=True,
            rbac=True,
            vaults=True,
            developer_portal=True,
            edition="enterprise",
            license_expiration=1735689600,
        )

        assert features.workspaces is True
        assert features.rbac is True
        assert features.vaults is True
        assert features.developer_portal is True
        assert features.license_expiration == 1735689600

    @pytest.mark.unit
    def test_enterprise_features_post_init(self) -> None:
        """Post-init should initialize checked_features set."""
        features = EnterpriseFeatures()

        assert isinstance(features._checked_features, set)


class TestEnterpriseFeatureChecker:
    """Tests for EnterpriseFeatureChecker class."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create a mock Kong Admin client."""
        return MagicMock()

    @pytest.fixture
    def checker(self, mock_client: MagicMock) -> EnterpriseFeatureChecker:
        """Create a checker with mocked client."""
        return EnterpriseFeatureChecker(mock_client)

    @pytest.mark.unit
    def test_checker_initialization(self, mock_client: MagicMock) -> None:
        """Checker should initialize with client."""
        checker = EnterpriseFeatureChecker(mock_client)

        assert checker._client is mock_client
        assert checker._features is None
        assert checker._cached is False


class TestEnterpriseFeatureCheckerProbe:
    """Tests for endpoint probing."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create a mock Kong Admin client."""
        return MagicMock()

    @pytest.fixture
    def checker(self, mock_client: MagicMock) -> EnterpriseFeatureChecker:
        """Create a checker with mocked client."""
        return EnterpriseFeatureChecker(mock_client)

    @pytest.mark.unit
    def test_probe_endpoint_success(
        self, checker: EnterpriseFeatureChecker, mock_client: MagicMock
    ) -> None:
        """Probe should return True on successful response."""
        mock_client.get.return_value = {"data": []}

        result = checker._probe_endpoint("/workspaces")

        assert result is True
        mock_client.get.assert_called_once_with("/workspaces")

    @pytest.mark.unit
    def test_probe_endpoint_not_found_returns_true(
        self, checker: EnterpriseFeatureChecker, mock_client: MagicMock
    ) -> None:
        """Probe should return True on 404 (empty collection)."""
        mock_client.get.side_effect = KongNotFoundError()

        result = checker._probe_endpoint("/workspaces")

        assert result is True

    @pytest.mark.unit
    def test_probe_endpoint_api_error_404_returns_false(
        self, checker: EnterpriseFeatureChecker, mock_client: MagicMock
    ) -> None:
        """Probe should return False on generic 404 API error."""
        mock_client.get.side_effect = KongAPIError("Not found", status_code=404)

        result = checker._probe_endpoint("/workspaces")

        assert result is False

    @pytest.mark.unit
    def test_probe_endpoint_other_error_returns_false(
        self, checker: EnterpriseFeatureChecker, mock_client: MagicMock
    ) -> None:
        """Probe should return False on other API errors."""
        mock_client.get.side_effect = KongAPIError("Error", status_code=500)

        result = checker._probe_endpoint("/workspaces")

        assert result is False


class TestEnterpriseFeatureCheckerDetectEdition:
    """Tests for edition detection."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create a mock Kong Admin client."""
        return MagicMock()

    @pytest.fixture
    def checker(self, mock_client: MagicMock) -> EnterpriseFeatureChecker:
        """Create a checker with mocked client."""
        return EnterpriseFeatureChecker(mock_client)

    @pytest.mark.unit
    def test_detect_edition_from_info(
        self, checker: EnterpriseFeatureChecker, mock_client: MagicMock
    ) -> None:
        """Should detect edition from info response."""
        mock_client.get_info.return_value = {"edition": "enterprise", "version": "3.0.0"}

        result = checker._detect_edition()

        assert result == "enterprise"

    @pytest.mark.unit
    def test_detect_edition_from_license(
        self, checker: EnterpriseFeatureChecker, mock_client: MagicMock
    ) -> None:
        """Should detect enterprise from license in configuration."""
        mock_client.get_info.return_value = {
            "configuration": {"license": {"key": "..."}},
            "plugins": {"available_on_server": {}},
        }

        result = checker._detect_edition()

        assert result == "enterprise"

    @pytest.mark.unit
    def test_detect_edition_from_plugins(
        self, checker: EnterpriseFeatureChecker, mock_client: MagicMock
    ) -> None:
        """Should detect enterprise from enterprise-only plugins."""
        mock_client.get_info.return_value = {
            "configuration": {},
            "plugins": {"available_on_server": {"openid-connect": True}},
        }

        result = checker._detect_edition()

        assert result == "enterprise"

    @pytest.mark.unit
    def test_detect_edition_community_fallback(
        self, checker: EnterpriseFeatureChecker, mock_client: MagicMock
    ) -> None:
        """Should default to community when no enterprise indicators."""
        mock_client.get_info.return_value = {
            "version": "3.0.0",
            "configuration": {},
            "plugins": {"available_on_server": {"rate-limiting": True}},
        }

        result = checker._detect_edition()

        assert result == "community"

    @pytest.mark.unit
    def test_detect_edition_api_error(
        self, checker: EnterpriseFeatureChecker, mock_client: MagicMock
    ) -> None:
        """Should return 'unknown' on API error."""
        mock_client.get_info.side_effect = KongAPIError("Error")

        result = checker._detect_edition()

        assert result == "unknown"


class TestEnterpriseFeatureCheckerIsEnterprise:
    """Tests for is_enterprise method."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create a mock Kong Admin client."""
        return MagicMock()

    @pytest.fixture
    def checker(self, mock_client: MagicMock) -> EnterpriseFeatureChecker:
        """Create a checker with mocked client."""
        return EnterpriseFeatureChecker(mock_client)

    @pytest.mark.unit
    def test_is_enterprise_with_cached_features(self, checker: EnterpriseFeatureChecker) -> None:
        """Should use cached features if available."""
        checker._features = EnterpriseFeatures(edition="enterprise")

        result = checker.is_enterprise()

        assert result is True

    @pytest.mark.unit
    def test_is_enterprise_probes_workspaces(
        self, checker: EnterpriseFeatureChecker, mock_client: MagicMock
    ) -> None:
        """Should probe workspaces endpoint when no cache."""
        mock_client.get.return_value = {"data": []}

        result = checker.is_enterprise()

        assert result is True
        mock_client.get.assert_called_with("/workspaces")

    @pytest.mark.unit
    def test_is_enterprise_false_when_probe_fails(
        self, checker: EnterpriseFeatureChecker, mock_client: MagicMock
    ) -> None:
        """Should return False when workspace probe fails."""
        mock_client.get.side_effect = KongAPIError("Not found", status_code=404)

        result = checker.is_enterprise()

        assert result is False


class TestEnterpriseFeatureCheckerGetAvailableFeatures:
    """Tests for get_available_features method."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create a mock Kong Admin client."""
        client = MagicMock()
        # Default responses for all probed endpoints
        client.get_info.return_value = {"edition": "enterprise"}
        client.get.return_value = {"data": []}
        return client

    @pytest.fixture
    def checker(self, mock_client: MagicMock) -> EnterpriseFeatureChecker:
        """Create a checker with mocked client."""
        return EnterpriseFeatureChecker(mock_client)

    @pytest.mark.unit
    def test_get_available_features_all_enabled(
        self, checker: EnterpriseFeatureChecker, mock_client: MagicMock
    ) -> None:
        """Should detect all features when all endpoints respond."""
        features = checker.get_available_features()

        assert features.edition == "enterprise"
        assert features.workspaces is True
        assert features.rbac is True
        assert features.vaults is True
        assert features.developer_portal is True

    @pytest.mark.unit
    def test_get_available_features_partial(
        self, checker: EnterpriseFeatureChecker, mock_client: MagicMock
    ) -> None:
        """Should handle partial feature availability."""

        def side_effect(endpoint: str) -> dict[str, Any]:
            if endpoint == "/vaults":
                raise KongAPIError("Not found", status_code=404)
            if endpoint == "/license":
                raise KongAPIError("Not found", status_code=404)
            return {"data": []}

        mock_client.get.side_effect = side_effect

        features = checker.get_available_features()

        assert features.workspaces is True
        assert features.vaults is False

    @pytest.mark.unit
    def test_get_available_features_cached(
        self, checker: EnterpriseFeatureChecker, mock_client: MagicMock
    ) -> None:
        """Should return cached features on subsequent calls."""
        # First call
        features1 = checker.get_available_features()
        call_count = mock_client.get_info.call_count

        # Second call should use cache
        features2 = checker.get_available_features()

        assert features1 is features2
        assert mock_client.get_info.call_count == call_count

    @pytest.mark.unit
    def test_get_available_features_force_refresh(
        self, checker: EnterpriseFeatureChecker, mock_client: MagicMock
    ) -> None:
        """Should refresh when force_refresh=True."""
        # First call
        checker.get_available_features()
        call_count = mock_client.get_info.call_count

        # Force refresh
        checker.get_available_features(force_refresh=True)

        assert mock_client.get_info.call_count > call_count

    @pytest.mark.unit
    def test_get_available_features_with_license(
        self, checker: EnterpriseFeatureChecker, mock_client: MagicMock
    ) -> None:
        """Should extract license expiration when available."""

        def side_effect(endpoint: str) -> dict[str, Any]:
            if endpoint == "/license":
                return {"license": {"expiration": 1735689600}}
            return {"data": []}

        mock_client.get.side_effect = side_effect

        features = checker.get_available_features()

        assert features.license_expiration == 1735689600


class TestEnterpriseFeatureCheckerRequireEnterprise:
    """Tests for require_enterprise method."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create a mock Kong Admin client."""
        client = MagicMock()
        client.get_info.return_value = {"edition": "enterprise"}
        client.get.return_value = {"data": []}
        return client

    @pytest.fixture
    def checker(self, mock_client: MagicMock) -> EnterpriseFeatureChecker:
        """Create a checker with mocked client."""
        return EnterpriseFeatureChecker(mock_client)

    @pytest.mark.unit
    def test_require_enterprise_success(self, checker: EnterpriseFeatureChecker) -> None:
        """Should not raise when feature is available."""
        # Should not raise
        checker.require_enterprise("workspaces")

    @pytest.mark.unit
    def test_require_enterprise_raises_for_oss(
        self, checker: EnterpriseFeatureChecker, mock_client: MagicMock
    ) -> None:
        """Should raise when not enterprise edition."""
        mock_client.get_info.return_value = {"edition": "community"}
        mock_client.get.side_effect = KongAPIError("Not found", status_code=404)

        with pytest.raises(KongEnterpriseRequiredError) as exc_info:
            checker.require_enterprise("workspaces")

        assert exc_info.value.feature == "workspaces"

    @pytest.mark.unit
    def test_require_enterprise_raises_for_disabled_feature(
        self, checker: EnterpriseFeatureChecker, mock_client: MagicMock
    ) -> None:
        """Should raise when specific feature is disabled."""

        def side_effect(endpoint: str) -> dict[str, Any]:
            if endpoint == "/vaults":
                raise KongAPIError("Not found", status_code=404)
            if endpoint == "/license":
                raise KongAPIError("Not found", status_code=404)
            return {"data": []}

        mock_client.get.side_effect = side_effect

        with pytest.raises(KongEnterpriseRequiredError) as exc_info:
            checker.require_enterprise("vaults")

        assert "vaults" in exc_info.value.message


class TestEnterpriseFeatureCheckerCheckFeature:
    """Tests for check_feature method."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create a mock Kong Admin client."""
        client = MagicMock()
        client.get_info.return_value = {"edition": "enterprise"}
        client.get.return_value = {"data": []}
        return client

    @pytest.fixture
    def checker(self, mock_client: MagicMock) -> EnterpriseFeatureChecker:
        """Create a checker with mocked client."""
        return EnterpriseFeatureChecker(mock_client)

    @pytest.mark.unit
    def test_check_feature_true(self, checker: EnterpriseFeatureChecker) -> None:
        """Should return True when feature is available."""
        result = checker.check_feature("workspaces")

        assert result is True

    @pytest.mark.unit
    def test_check_feature_false(
        self, checker: EnterpriseFeatureChecker, mock_client: MagicMock
    ) -> None:
        """Should return False when feature is not available."""

        def side_effect(endpoint: str) -> dict[str, Any]:
            if endpoint == "/vaults":
                raise KongAPIError("Not found", status_code=404)
            if endpoint == "/license":
                raise KongAPIError("Not found", status_code=404)
            return {"data": []}

        mock_client.get.side_effect = side_effect

        result = checker.check_feature("vaults")

        assert result is False

    @pytest.mark.unit
    def test_check_feature_non_enterprise(
        self, checker: EnterpriseFeatureChecker, mock_client: MagicMock
    ) -> None:
        """Should return False when not enterprise edition."""
        mock_client.get_info.return_value = {"edition": "community"}
        mock_client.get.side_effect = KongAPIError("Not found", status_code=404)

        result = checker.check_feature("workspaces")

        assert result is False


class TestEnterpriseFeatureCheckerClearCache:
    """Tests for clear_cache method."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create a mock Kong Admin client."""
        client = MagicMock()
        client.get_info.return_value = {"edition": "enterprise"}
        client.get.return_value = {"data": []}
        return client

    @pytest.fixture
    def checker(self, mock_client: MagicMock) -> EnterpriseFeatureChecker:
        """Create a checker with mocked client."""
        return EnterpriseFeatureChecker(mock_client)

    @pytest.mark.unit
    def test_clear_cache(self, checker: EnterpriseFeatureChecker) -> None:
        """Should clear cached features."""
        # Populate cache
        checker.get_available_features()
        assert checker._features is not None
        assert checker._cached is True

        # Clear cache
        checker.clear_cache()

        assert checker._features is None
        assert checker._cached is False
