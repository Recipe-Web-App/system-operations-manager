"""Unit tests for Kong entity models."""

from __future__ import annotations

import pytest

from system_operations_manager.integrations.kong.models.base import (
    KongEntityBase,
    KongEntityReference,
    PaginatedResponse,
)
from system_operations_manager.integrations.kong.models.consumer import (
    ACLGroup,
    BasicAuthCredential,
    Consumer,
    KeyAuthCredential,
)
from system_operations_manager.integrations.kong.models.plugin import (
    AvailablePlugin,
    KongPluginEntity,
    PluginSchema,
)
from system_operations_manager.integrations.kong.models.route import Route
from system_operations_manager.integrations.kong.models.service import Service
from system_operations_manager.integrations.kong.models.upstream import (
    Target,
    Upstream,
    UpstreamHealth,
)


class TestKongEntityBase:
    """Tests for KongEntityBase model."""

    @pytest.mark.unit
    def test_to_create_payload_excludes_server_fields(self) -> None:
        """Server-assigned fields should be excluded from create payload."""

        class TestEntity(KongEntityBase):
            name: str = "test"

        entity = TestEntity(
            id="test-id",
            name="test-name",
            created_at=1234567890,
            updated_at=1234567890,
        )
        payload = entity.to_create_payload()

        assert "id" not in payload
        assert "created_at" not in payload
        assert "updated_at" not in payload
        assert payload["name"] == "test-name"

    @pytest.mark.unit
    def test_to_update_payload_excludes_none_values(self) -> None:
        """None values should be excluded from update payload."""

        class TestEntity(KongEntityBase):
            name: str | None = None
            value: str | None = None

        entity = TestEntity(name="test", value=None)
        payload = entity.to_update_payload()

        assert payload["name"] == "test"
        assert "value" not in payload


class TestKongEntityReference:
    """Tests for KongEntityReference model."""

    @pytest.mark.unit
    def test_from_id_or_name_with_uuid(self) -> None:
        """UUID-like strings should create id-based reference."""
        ref = KongEntityReference.from_id_or_name("550e8400-e29b-41d4-a716-446655440000")
        assert ref.id == "550e8400-e29b-41d4-a716-446655440000"
        assert ref.name is None

    @pytest.mark.unit
    def test_from_id_or_name_with_name(self) -> None:
        """Non-UUID strings should create name-based reference."""
        ref = KongEntityReference.from_id_or_name("my-service")
        assert ref.name == "my-service"
        assert ref.id is None

    @pytest.mark.unit
    def test_from_id_or_name_with_short_hex(self) -> None:
        """Short hex strings without dashes should be treated as names."""
        ref = KongEntityReference.from_id_or_name("abc123")
        assert ref.name == "abc123"
        assert ref.id is None


class TestPaginatedResponse:
    """Tests for PaginatedResponse model."""

    @pytest.mark.unit
    def test_pagination_with_offset(self) -> None:
        """PaginatedResponse should handle offset for pagination."""
        response = PaginatedResponse(
            data=[{"id": "1"}, {"id": "2"}],
            offset="next-page-token",
        )
        assert len(response.data) == 2
        assert response.offset == "next-page-token"

    @pytest.mark.unit
    def test_pagination_without_offset(self) -> None:
        """PaginatedResponse should handle missing offset."""
        response = PaginatedResponse(data=[{"id": "1"}])
        assert response.offset is None


class TestServiceModel:
    """Tests for Service model."""

    @pytest.mark.unit
    def test_service_with_defaults(self) -> None:
        """Service should have sensible defaults."""
        service = Service(host="api.example.com")

        assert service.host == "api.example.com"
        assert service.port == 80
        assert service.protocol == "http"
        assert service.retries == 5
        assert service.connect_timeout == 60000
        assert service.enabled is True

    @pytest.mark.unit
    def test_service_with_url(self) -> None:
        """Service should accept URL shorthand."""
        service = Service(url="https://api.example.com:8443/v1")

        assert service.url == "https://api.example.com:8443/v1"

    @pytest.mark.unit
    def test_service_path_validation(self) -> None:
        """Path should be prefixed with / if missing."""
        service = Service(host="api.example.com", path="api/v1")

        assert service.path == "/api/v1"

    @pytest.mark.unit
    def test_service_protocol_lowercase(self) -> None:
        """Protocol should be lowercased."""
        # Use a variable to test the before validator that lowercases
        protocol_input: str = "HTTPS"
        service = Service(host="api.example.com", protocol=protocol_input)  # type: ignore[arg-type]

        assert service.protocol == "https"


class TestRouteModel:
    """Tests for Route model."""

    @pytest.mark.unit
    def test_route_with_defaults(self) -> None:
        """Route should have sensible defaults."""
        route = Route(
            paths=["/api"],
            service=KongEntityReference(id="service-id"),
        )

        assert route.paths == ["/api"]
        assert route.protocols == ["http", "https"]
        assert route.strip_path is True
        assert route.preserve_host is False

    @pytest.mark.unit
    def test_route_methods_uppercase(self) -> None:
        """HTTP methods should be uppercased."""
        route = Route(methods=["get", "post"])

        assert route.methods == ["GET", "POST"]

    @pytest.mark.unit
    def test_route_paths_validation(self) -> None:
        """Paths should be prefixed with / if missing."""
        route = Route(paths=["api", "/v1", "~^/regex"])

        assert route.paths == ["/api", "/v1", "~^/regex"]


class TestConsumerModel:
    """Tests for Consumer model."""

    @pytest.mark.unit
    def test_consumer_with_username(self) -> None:
        """Consumer can be created with username."""
        consumer = Consumer(username="test-user")

        assert consumer.username == "test-user"
        assert consumer.custom_id is None

    @pytest.mark.unit
    def test_consumer_with_custom_id(self) -> None:
        """Consumer can be created with custom_id."""
        consumer = Consumer(custom_id="external-123")

        assert consumer.custom_id == "external-123"


class TestCredentialModels:
    """Tests for credential models."""

    @pytest.mark.unit
    def test_key_auth_credential(self) -> None:
        """KeyAuthCredential should have key field."""
        cred = KeyAuthCredential(
            id="cred-id",
            key="my-api-key",
            consumer={"id": "consumer-id"},
        )

        assert cred.key == "my-api-key"

    @pytest.mark.unit
    def test_basic_auth_credential(self) -> None:
        """BasicAuthCredential should have username/password."""
        cred = BasicAuthCredential(
            id="cred-id",
            username="user",
            password="pass",
            consumer={"id": "consumer-id"},
        )

        assert cred.username == "user"
        assert cred.password == "pass"

    @pytest.mark.unit
    def test_acl_group(self) -> None:
        """ACLGroup should have group field."""
        acl = ACLGroup(
            id="acl-id",
            group="admin",
            consumer={"id": "consumer-id"},
        )

        assert acl.group == "admin"


class TestUpstreamModel:
    """Tests for Upstream model."""

    @pytest.mark.unit
    def test_upstream_with_defaults(self) -> None:
        """Upstream should have sensible defaults."""
        upstream = Upstream(name="my-upstream")

        assert upstream.name == "my-upstream"
        assert upstream.algorithm == "round-robin"
        assert upstream.slots == 10000
        assert upstream.hash_on == "none"

    @pytest.mark.unit
    def test_upstream_with_consistent_hashing(self) -> None:
        """Upstream can use consistent-hashing algorithm."""
        upstream = Upstream(
            name="my-upstream",
            algorithm="consistent-hashing",
            hash_on="ip",
        )

        assert upstream.algorithm == "consistent-hashing"
        assert upstream.hash_on == "ip"


class TestTargetModel:
    """Tests for Target model."""

    @pytest.mark.unit
    def test_target_with_defaults(self) -> None:
        """Target should have default weight."""
        target = Target(target="192.168.1.1:8080")

        assert target.target == "192.168.1.1:8080"
        assert target.weight == 100

    @pytest.mark.unit
    def test_target_with_zero_weight(self) -> None:
        """Target with zero weight is disabled."""
        target = Target(target="192.168.1.1:8080", weight=0)

        assert target.weight == 0


class TestUpstreamHealthModel:
    """Tests for UpstreamHealth model."""

    @pytest.mark.unit
    def test_upstream_health(self) -> None:
        """UpstreamHealth should parse health status."""
        health = UpstreamHealth(
            id="upstream-id",
            health="HEALTHY",
            data=[{"target": "server1:8080", "health": "HEALTHY"}],
        )

        assert health.health == "HEALTHY"


class TestPluginModels:
    """Tests for plugin-related models."""

    @pytest.mark.unit
    def test_kong_plugin_entity(self) -> None:
        """KongPluginEntity should have name and config."""
        plugin = KongPluginEntity(
            id="plugin-id",
            name="rate-limiting",
            config={"minute": 100},
            enabled=True,
        )

        assert plugin.name == "rate-limiting"
        assert plugin.config == {"minute": 100}
        assert plugin.enabled is True

    @pytest.mark.unit
    def test_kong_plugin_with_scope(self) -> None:
        """KongPluginEntity can be scoped to service/route/consumer."""
        plugin = KongPluginEntity(
            id="plugin-id",
            name="key-auth",
            service=KongEntityReference(id="service-id"),
            enabled=True,
        )

        assert plugin.service is not None
        assert plugin.service.id == "service-id"
        assert plugin.route is None
        assert plugin.consumer is None

    @pytest.mark.unit
    def test_available_plugin(self) -> None:
        """AvailablePlugin should have name and optional metadata."""
        plugin = AvailablePlugin(
            name="rate-limiting",
            version="3.0.0",
            priority=901,
        )

        assert plugin.name == "rate-limiting"
        assert plugin.version == "3.0.0"
        assert plugin.priority == 901

    @pytest.mark.unit
    def test_plugin_schema(self) -> None:
        """PluginSchema should have name and fields."""
        schema = PluginSchema(
            name="rate-limiting",
            fields=[{"config": {"type": "record"}}],
        )

        assert schema.name == "rate-limiting"
        assert schema.fields is not None
        assert len(schema.fields) == 1
