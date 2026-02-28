"""Unit tests for Kong plugin models."""

from __future__ import annotations

import pytest

from system_operations_manager.integrations.kong.models.base import KongEntityReference
from system_operations_manager.integrations.kong.models.plugin import (
    AvailablePlugin,
    KongPluginEntity,
    PluginSchema,
)


@pytest.mark.unit
class TestKongPluginEntity:
    """Tests for KongPluginEntity model."""

    def test_create_global_plugin(self) -> None:
        """Should create a global plugin with no scope."""
        plugin = KongPluginEntity(name="rate-limiting")

        assert plugin.name == "rate-limiting"
        assert plugin.service is None
        assert plugin.route is None
        assert plugin.consumer is None
        assert plugin.enabled is True
        assert plugin.config == {}

    def test_create_plugin_with_config(self) -> None:
        """Should create plugin with configuration."""
        plugin = KongPluginEntity(
            name="rate-limiting",
            config={"minute": 100, "hour": 1000},
            protocols=["http", "https"],
            enabled=True,
            tags=["production"],
        )

        assert plugin.config["minute"] == 100
        assert plugin.config["hour"] == 1000
        assert plugin.protocols == ["http", "https"]
        assert plugin.tags == ["production"]

    def test_create_service_scoped_plugin(self) -> None:
        """Should create plugin scoped to a service."""
        plugin = KongPluginEntity(
            name="key-auth",
            service=KongEntityReference.from_id("service-uuid-123"),
        )

        assert plugin.service is not None
        assert plugin.service.id == "service-uuid-123"

    def test_create_route_scoped_plugin(self) -> None:
        """Should create plugin scoped to a route."""
        plugin = KongPluginEntity(
            name="cors",
            route=KongEntityReference.from_name("my-route"),
        )

        assert plugin.route is not None
        assert plugin.route.name == "my-route"

    def test_default_protocols(self) -> None:
        """Should default to all four standard protocols."""
        plugin = KongPluginEntity(name="jwt")

        assert set(plugin.protocols) == {"grpc", "grpcs", "http", "https"}

    def test_to_create_payload_with_service_id_ref(self) -> None:
        """to_create_payload should simplify service reference to id-only dict (lines 76-77)."""
        plugin = KongPluginEntity(
            name="rate-limiting",
            service=KongEntityReference.from_id("service-uuid-456"),
            config={"minute": 50},
        )

        payload = plugin.to_create_payload()

        assert payload["service"] == {"id": "service-uuid-456"}

    def test_to_create_payload_with_route_name_ref(self) -> None:
        """to_create_payload should simplify route reference to name-only dict (lines 78-79)."""
        plugin = KongPluginEntity(
            name="cors",
            route=KongEntityReference.from_name("api-route"),
        )

        payload = plugin.to_create_payload()

        assert payload["route"] == {"name": "api-route"}

    def test_to_create_payload_with_consumer_id_ref(self) -> None:
        """to_create_payload should simplify consumer reference to id-only dict."""
        plugin = KongPluginEntity(
            name="acl",
            consumer=KongEntityReference.from_id("consumer-uuid-789"),
        )

        payload = plugin.to_create_payload()

        assert payload["consumer"] == {"id": "consumer-uuid-789"}

    def test_to_create_payload_with_consumer_name_ref(self) -> None:
        """to_create_payload should simplify consumer reference to name-only dict."""
        plugin = KongPluginEntity(
            name="acl",
            consumer=KongEntityReference.from_name("alice"),
        )

        payload = plugin.to_create_payload()

        assert payload["consumer"] == {"name": "alice"}

    def test_to_create_payload_excludes_id_and_timestamps(self) -> None:
        """to_create_payload should exclude id, created_at, updated_at."""
        plugin = KongPluginEntity(
            id="plugin-uuid-000",
            created_at=1704067200,
            updated_at=1704067200,
            name="jwt",
        )

        payload = plugin.to_create_payload()

        assert "id" not in payload
        assert "created_at" not in payload
        assert "updated_at" not in payload

    def test_to_create_payload_no_scope_refs(self) -> None:
        """to_create_payload for global plugin should not include scope fields."""
        plugin = KongPluginEntity(
            name="request-transformer", config={"add": {"headers": ["X-Custom: value"]}}
        )

        payload = plugin.to_create_payload()

        assert "service" not in payload
        assert "route" not in payload
        assert "consumer" not in payload
        assert payload["name"] == "request-transformer"

    def test_create_plugin_with_ordering(self) -> None:
        """Should create plugin with execution ordering (Kong 3.0+)."""
        plugin = KongPluginEntity(
            name="custom-plugin",
            ordering={"before": {"access": ["rate-limiting"]}},
        )

        assert plugin.ordering is not None
        assert "before" in plugin.ordering

    def test_create_plugin_disabled(self) -> None:
        """Should create a disabled plugin."""
        plugin = KongPluginEntity(name="rate-limiting", enabled=False)

        assert plugin.enabled is False

    def test_create_plugin_with_instance_name(self) -> None:
        """Should create plugin with instance name for same-type disambiguation."""
        plugin = KongPluginEntity(
            name="rate-limiting",
            instance_name="rate-limiting-strict",
        )

        assert plugin.instance_name == "rate-limiting-strict"


@pytest.mark.unit
class TestAvailablePlugin:
    """Tests for AvailablePlugin model."""

    def test_create_available_plugin(self) -> None:
        """Should create available plugin with all fields."""
        plugin = AvailablePlugin(
            name="rate-limiting",
            version="2.4.0",
            priority=901,
            phases=["access"],
        )

        assert plugin.name == "rate-limiting"
        assert plugin.version == "2.4.0"
        assert plugin.priority == 901
        assert plugin.phases == ["access"]

    def test_create_available_plugin_minimal(self) -> None:
        """Should create available plugin with name only."""
        plugin = AvailablePlugin(name="jwt")

        assert plugin.name == "jwt"
        assert plugin.version is None
        assert plugin.priority is None
        assert plugin.phases is None


@pytest.mark.unit
class TestPluginSchema:
    """Tests for PluginSchema model."""

    def test_create_plugin_schema(self) -> None:
        """Should create plugin schema with name and fields."""
        schema = PluginSchema(
            name="rate-limiting",
            fields=[
                {"minute": {"type": "integer", "default": 0}},
                {"hour": {"type": "integer", "default": 0}},
            ],
        )

        assert schema.name == "rate-limiting"
        assert schema.fields is not None

        assert len(schema.fields) == 2

    def test_create_empty_schema(self) -> None:
        """Should create plugin schema with all defaults."""
        schema = PluginSchema()

        assert schema.name is None
        assert schema.fields is None
