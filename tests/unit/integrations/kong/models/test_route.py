"""Unit tests for Kong route models."""

from __future__ import annotations

import pytest

from system_operations_manager.integrations.kong.models.base import KongEntityReference
from system_operations_manager.integrations.kong.models.route import (
    Route,
    RouteSummary,
)


@pytest.mark.unit
class TestRoute:
    """Tests for Route model."""

    def test_create_minimal_route(self) -> None:
        """Should create route with default values."""
        route = Route()

        assert route.name is None
        assert route.protocols == ["http", "https"]
        assert route.methods is None
        assert route.hosts is None
        assert route.paths is None
        assert route.strip_path is True
        assert route.preserve_host is False
        assert route.regex_priority == 0
        assert route.https_redirect_status_code == 426

    def test_create_route_with_paths(self) -> None:
        """Should create route matching on paths."""
        route = Route(
            name="api-route",
            paths=["/api/v1", "/api/v2"],
            methods=["GET", "POST"],
        )

        assert route.name == "api-route"
        assert route.paths == ["/api/v1", "/api/v2"]
        assert route.methods == ["GET", "POST"]

    def test_create_route_with_hosts(self) -> None:
        """Should create route matching on hosts."""
        route = Route(
            name="host-route",
            hosts=["api.example.com", "www.example.com"],
            protocols=["http", "https"],
        )

        assert route.hosts == ["api.example.com", "www.example.com"]

    def test_create_route_with_service_reference(self) -> None:
        """Should create route associated with a service."""
        route = Route(
            name="svc-route",
            paths=["/api"],
            service=KongEntityReference.from_id("service-uuid-123"),
        )

        assert route.service is not None
        assert route.service.id == "service-uuid-123"

    def test_uppercase_methods_validator(self) -> None:
        """uppercase_methods should convert methods to uppercase."""
        route = Route(methods=["get", "post", "delete"])

        assert route.methods == ["GET", "POST", "DELETE"]

    def test_uppercase_methods_validator_already_uppercase(self) -> None:
        """uppercase_methods should keep already-uppercase methods unchanged."""
        route = Route(methods=["GET", "PUT"])

        assert route.methods == ["GET", "PUT"]

    def test_uppercase_methods_validator_none_returns_none(self) -> None:
        """uppercase_methods should return None unchanged (line 91)."""
        route = Route(methods=None)

        assert route.methods is None

    def test_validate_paths_prepends_slash(self) -> None:
        """validate_paths should prepend '/' to paths that lack one."""
        route = Route(paths=["api/v1", "health"])

        assert route.paths == ["/api/v1", "/health"]

    def test_validate_paths_keeps_existing_slash(self) -> None:
        """validate_paths should leave paths that already start with '/' alone."""
        route = Route(paths=["/api/v1", "/health"])

        assert route.paths == ["/api/v1", "/health"]

    def test_validate_paths_keeps_tilde_prefix(self) -> None:
        """validate_paths should leave paths starting with '~' (regex) alone."""
        route = Route(paths=["~/api/v[0-9]+"])

        assert route.paths == ["~/api/v[0-9]+"]

    def test_validate_paths_none_returns_none(self) -> None:
        """validate_paths should return None unchanged (line 99)."""
        route = Route(paths=None)

        assert route.paths is None

    def test_to_create_payload_with_service_id_ref(self) -> None:
        """to_create_payload should simplify service reference to id-only dict (lines 120-121)."""
        route = Route(
            name="api-route",
            paths=["/api"],
            service=KongEntityReference.from_id("service-uuid-456"),
        )

        payload = route.to_create_payload()

        assert payload["service"] == {"id": "service-uuid-456"}

    def test_to_create_payload_with_service_name_ref(self) -> None:
        """to_create_payload should simplify service reference to name-only dict (lines 122-123)."""
        route = Route(
            name="api-route",
            paths=["/api"],
            service=KongEntityReference.from_name("my-service"),
        )

        payload = route.to_create_payload()

        assert payload["service"] == {"name": "my-service"}

    def test_to_create_payload_without_service(self) -> None:
        """to_create_payload without service should not include service key."""
        route = Route(name="standalone-route", paths=["/api"])

        payload = route.to_create_payload()

        assert "service" not in payload

    def test_to_create_payload_excludes_id_and_timestamps(self) -> None:
        """to_create_payload should exclude id, created_at, updated_at."""
        route = Route(
            id="route-uuid-789",
            created_at=1704067200,
            updated_at=1704067200,
            paths=["/api"],
        )

        payload = route.to_create_payload()

        assert "id" not in payload
        assert "created_at" not in payload
        assert "updated_at" not in payload

    def test_route_with_all_matching_criteria(self) -> None:
        """Should create route with multiple matching criteria."""
        route = Route(
            name="full-route",
            methods=["GET"],
            hosts=["api.example.com"],
            paths=["/v1"],
            headers={"X-Version": ["v1"]},
            protocols=["https"],
            snis=["api.example.com"],
        )

        assert route.methods == ["GET"]
        assert route.hosts == ["api.example.com"]
        assert route.paths == ["/v1"]
        assert route.headers == {"X-Version": ["v1"]}
        assert route.snis == ["api.example.com"]

    def test_route_with_stream_criteria(self) -> None:
        """Should create route with stream sources and destinations."""
        route = Route(
            protocols=["tcp"],
            sources=[{"ip": "192.168.1.0/24"}],
            destinations=[{"ip": "10.0.0.1", "port": 8080}],
        )

        assert route.sources == [{"ip": "192.168.1.0/24"}]
        assert route.destinations == [{"ip": "10.0.0.1", "port": 8080}]

    def test_route_path_handling_default(self) -> None:
        """path_handling should default to v0."""
        route = Route(paths=["/api"])

        assert route.path_handling == "v0"

    def test_route_path_handling_v1(self) -> None:
        """Should accept v1 path handling."""
        route = Route(paths=["/api"], path_handling="v1")

        assert route.path_handling == "v1"

    def test_route_buffering_defaults(self) -> None:
        """request_buffering and response_buffering should default to True."""
        route = Route()

        assert route.request_buffering is True
        assert route.response_buffering is True

    def test_to_create_payload_includes_protocols(self) -> None:
        """to_create_payload should include protocols field."""
        route = Route(paths=["/grpc"], protocols=["grpc", "grpcs"])

        payload = route.to_create_payload()

        assert payload["protocols"] == ["grpc", "grpcs"]


@pytest.mark.unit
class TestRouteSummary:
    """Tests for RouteSummary model."""

    def test_create_empty_summary(self) -> None:
        """Should create route summary with all defaults."""
        summary = RouteSummary()

        assert summary.name is None
        assert summary.paths is None
        assert summary.methods is None
        assert summary.hosts is None
        assert summary.service is None

    def test_create_summary_with_fields(self) -> None:
        """Should create route summary with name, paths, and methods."""
        summary = RouteSummary(
            id="route-uuid-001",
            name="api-route",
            paths=["/api"],
            methods=["GET", "POST"],
            service=KongEntityReference.from_id("svc-uuid-001"),
        )

        assert summary.name == "api-route"
        assert summary.paths == ["/api"]
        assert summary.methods == ["GET", "POST"]
        assert summary.service is not None

        assert summary.service.id == "svc-uuid-001"
