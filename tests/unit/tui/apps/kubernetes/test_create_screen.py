"""Unit tests for Kubernetes TUI resource create screen."""

from __future__ import annotations

from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest

from system_operations_manager.tui.apps.kubernetes.create_screen import (
    RESOURCE_FIELD_SPECS,
    ResourceCreateScreen,
    _parse_key_value_lines,
    _parse_port_lines,
)
from system_operations_manager.tui.apps.kubernetes.types import (
    CREATABLE_TYPES,
    ResourceType,
)


class TestParseKeyValueLines:
    @pytest.mark.unit
    def test_parse_simple(self) -> None:
        result = _parse_key_value_lines("key1=value1\nkey2=value2")
        assert result == {"key1": "value1", "key2": "value2"}

    @pytest.mark.unit
    def test_parse_empty(self) -> None:
        assert _parse_key_value_lines("") == {}

    @pytest.mark.unit
    def test_parse_skips_blank_lines(self) -> None:
        result = _parse_key_value_lines("key1=value1\n\nkey2=value2\n")
        assert result == {"key1": "value1", "key2": "value2"}

    @pytest.mark.unit
    def test_parse_skips_invalid_lines(self) -> None:
        result = _parse_key_value_lines("key1=value1\ninvalid_line\nkey2=value2")
        assert result == {"key1": "value1", "key2": "value2"}

    @pytest.mark.unit
    def test_parse_handles_equals_in_value(self) -> None:
        result = _parse_key_value_lines("key=val=ue")
        assert result == {"key": "val=ue"}


class TestParsePortLines:
    @pytest.mark.unit
    def test_parse_simple_port(self) -> None:
        result = _parse_port_lines("port=80")
        assert len(result) == 1
        assert result[0]["port"] == 80

    @pytest.mark.unit
    def test_parse_full_port(self) -> None:
        result = _parse_port_lines("port=80,target_port=8080,protocol=TCP,name=http")
        assert len(result) == 1
        assert result[0] == {"port": 80, "target_port": 8080, "protocol": "TCP", "name": "http"}

    @pytest.mark.unit
    def test_parse_multiple_ports(self) -> None:
        result = _parse_port_lines("port=80\nport=443")
        assert len(result) == 2

    @pytest.mark.unit
    def test_parse_empty(self) -> None:
        assert _parse_port_lines("") == []

    @pytest.mark.unit
    def test_parse_skips_lines_without_port(self) -> None:
        result = _parse_port_lines("target_port=8080")
        assert result == []


class TestResourceFieldSpecs:
    @pytest.mark.unit
    def test_all_creatable_types_have_specs(self) -> None:
        for rt in CREATABLE_TYPES:
            assert rt in RESOURCE_FIELD_SPECS, f"{rt} missing from RESOURCE_FIELD_SPECS"

    @pytest.mark.unit
    def test_each_type_has_name_field(self) -> None:
        for rt, specs in RESOURCE_FIELD_SPECS.items():
            names = [s.name for s in specs]
            assert "name" in names, f"{rt} missing 'name' field"

    @pytest.mark.unit
    def test_name_field_is_required(self) -> None:
        for rt, specs in RESOURCE_FIELD_SPECS.items():
            name_spec = next(s for s in specs if s.name == "name")
            assert name_spec.required, f"{rt} 'name' field should be required"


class TestResourceCreateScreen:
    @pytest.mark.unit
    def test_screen_stores_resource_type(self) -> None:
        mock_client = MagicMock()
        mock_client.default_namespace = "default"
        screen = ResourceCreateScreen(ResourceType.DEPLOYMENTS, mock_client)
        assert screen._resource_type == ResourceType.DEPLOYMENTS

    @pytest.mark.unit
    def test_resource_created_message(self) -> None:
        msg = ResourceCreateScreen.ResourceCreated(ResourceType.PODS, "test-pod")
        assert msg.resource_type == ResourceType.PODS
        assert msg.resource_name == "test-pod"


# ============================================================================
# Helper
# ============================================================================


def _make_create_screen(
    resource_type: ResourceType = ResourceType.DEPLOYMENTS,
) -> ResourceCreateScreen:
    """Create a ResourceCreateScreen bypassing __init__ for sync testing."""
    screen = ResourceCreateScreen.__new__(ResourceCreateScreen)
    screen._resource_type = resource_type
    object.__setattr__(screen, "_client", MagicMock())
    screen._namespace = "default"
    screen._field_specs = RESOURCE_FIELD_SPECS[resource_type]
    object.__setattr__(screen, "go_back", MagicMock())
    object.__setattr__(screen, "notify_user", MagicMock())
    object.__setattr__(screen, "post_message", MagicMock())
    object.__setattr__(screen, "query_one", MagicMock())
    return screen


# ============================================================================
# action_cancel Tests
# ============================================================================


@pytest.mark.unit
class TestActionCancel:
    """Tests for ResourceCreateScreen.action_cancel."""

    def test_action_cancel_goes_back(self) -> None:
        """action_cancel calls go_back."""
        screen = _make_create_screen()
        screen.action_cancel()
        cast(MagicMock, screen.go_back).assert_called_once()


# ============================================================================
# action_submit Tests
# ============================================================================


@pytest.mark.unit
class TestActionSubmit:
    """Tests for ResourceCreateScreen.action_submit."""

    def test_submit_returns_early_on_validation_failure(self) -> None:
        """action_submit returns early when _collect_values returns None."""
        screen = _make_create_screen()
        object.__setattr__(screen, "_collect_values", MagicMock(return_value=None))
        screen.action_submit()
        cast(MagicMock, screen.go_back).assert_not_called()

    def test_submit_success_posts_message_and_goes_back(self) -> None:
        """action_submit creates resource, posts message, and goes back."""
        screen = _make_create_screen()
        object.__setattr__(
            screen, "_collect_values", MagicMock(return_value={"name": "test", "image": "nginx"})
        )
        object.__setattr__(screen, "_create_resource", MagicMock(return_value="test"))
        screen.action_submit()
        cast(MagicMock, screen.post_message).assert_called_once()
        cast(MagicMock, screen.go_back).assert_called_once()
        cast(MagicMock, screen.notify_user).assert_called_once()
        assert "test" in cast(MagicMock, screen.notify_user).call_args[0][0]

    def test_submit_failure_shows_error(self) -> None:
        """action_submit shows error on exception."""
        screen = _make_create_screen()
        object.__setattr__(
            screen, "_collect_values", MagicMock(return_value={"name": "test", "image": "nginx"})
        )
        object.__setattr__(
            screen, "_create_resource", MagicMock(side_effect=RuntimeError("api error"))
        )
        screen.action_submit()
        cast(MagicMock, screen.notify_user).assert_called_once()
        assert cast(MagicMock, screen.notify_user).call_args[1]["severity"] == "error"


# ============================================================================
# on_button_pressed Tests
# ============================================================================


@pytest.mark.unit
class TestOnButtonPressed:
    """Tests for ResourceCreateScreen.on_button_pressed."""

    def test_create_button_calls_submit(self) -> None:
        """Pressing btn-create calls action_submit."""
        screen = _make_create_screen()
        object.__setattr__(screen, "action_submit", MagicMock())
        event = MagicMock()
        event.button.id = "btn-create"
        screen.on_button_pressed(event)
        cast(MagicMock, screen.action_submit).assert_called_once()

    def test_cancel_button_calls_cancel(self) -> None:
        """Pressing btn-cancel calls action_cancel."""
        screen = _make_create_screen()
        object.__setattr__(screen, "action_cancel", MagicMock())
        event = MagicMock()
        event.button.id = "btn-cancel"
        screen.on_button_pressed(event)
        cast(MagicMock, screen.action_cancel).assert_called_once()

    def test_unknown_button_does_nothing(self) -> None:
        """Pressing unknown button does nothing."""
        screen = _make_create_screen()
        object.__setattr__(screen, "action_submit", MagicMock())
        object.__setattr__(screen, "action_cancel", MagicMock())
        event = MagicMock()
        event.button.id = "btn-other"
        screen.on_button_pressed(event)
        cast(MagicMock, screen.action_submit).assert_not_called()
        cast(MagicMock, screen.action_cancel).assert_not_called()


# ============================================================================
# _create_resource Tests (all branches)
# ============================================================================


@pytest.mark.unit
class TestCreateResourceDeployments:
    """Tests for _create_resource with DEPLOYMENTS."""

    def test_create_deployment_basic(self) -> None:
        """Creates deployment with name + image."""
        screen = _make_create_screen(ResourceType.DEPLOYMENTS)
        values = {"name": "web", "image": "nginx", "namespace": "default", "labels": ""}
        with patch(
            "system_operations_manager.tui.apps.kubernetes.create_screen.WorkloadManager",
            create=True,
        ) as mock_cls:
            mock_cls.return_value = MagicMock()
            # patch the import inside the method
            with patch(
                "system_operations_manager.services.kubernetes.workload_manager.WorkloadManager",
                mock_cls,
            ):
                result = screen._create_resource(values)
        assert result == "web"

    def test_create_deployment_with_all_options(self) -> None:
        """Creates deployment with replicas, port, labels."""
        screen = _make_create_screen(ResourceType.DEPLOYMENTS)
        values = {
            "name": "web",
            "image": "nginx",
            "namespace": "default",
            "replicas": 3,
            "port": 80,
            "labels": "app=web\ntier=frontend",
        }
        with patch(
            "system_operations_manager.services.kubernetes.workload_manager.WorkloadManager",
        ) as mock_cls:
            mock_mgr = MagicMock()
            mock_cls.return_value = mock_mgr
            result = screen._create_resource(values)
        assert result == "web"
        mock_mgr.create_deployment.assert_called_once()


@pytest.mark.unit
class TestCreateResourceStatefulSets:
    """Tests for _create_resource with STATEFULSETS."""

    def test_create_statefulset(self) -> None:
        """Creates statefulset with required fields."""
        screen = _make_create_screen(ResourceType.STATEFULSETS)
        values = {
            "name": "redis",
            "image": "redis:7",
            "service_name": "redis-headless",
            "namespace": "default",
            "labels": "",
        }
        with patch(
            "system_operations_manager.services.kubernetes.workload_manager.WorkloadManager",
        ) as mock_cls:
            mock_cls.return_value = MagicMock()
            result = screen._create_resource(values)
        assert result == "redis"


@pytest.mark.unit
class TestCreateResourceDaemonSets:
    """Tests for _create_resource with DAEMONSETS."""

    def test_create_daemonset(self) -> None:
        """Creates daemonset with name + image."""
        screen = _make_create_screen(ResourceType.DAEMONSETS)
        values = {
            "name": "fluentd",
            "image": "fluent-bit:latest",
            "namespace": "logging",
            "labels": "",
        }
        with patch(
            "system_operations_manager.services.kubernetes.workload_manager.WorkloadManager",
        ) as mock_cls:
            mock_cls.return_value = MagicMock()
            result = screen._create_resource(values)
        assert result == "fluentd"


@pytest.mark.unit
class TestCreateResourceServices:
    """Tests for _create_resource with SERVICES."""

    def test_create_service(self) -> None:
        """Creates service with type, selector, ports."""
        screen = _make_create_screen(ResourceType.SERVICES)
        values = {
            "name": "web-svc",
            "type": "ClusterIP",
            "selector": "app=web",
            "ports": "port=80,target_port=8080",
            "namespace": "default",
            "labels": "app=web",
        }
        with patch(
            "system_operations_manager.services.kubernetes.networking_manager.NetworkingManager",
        ) as mock_cls:
            mock_cls.return_value = MagicMock()
            result = screen._create_resource(values)
        assert result == "web-svc"


@pytest.mark.unit
class TestCreateResourceIngresses:
    """Tests for _create_resource with INGRESSES."""

    def test_create_ingress(self) -> None:
        """Creates ingress with class, rules, tls."""
        screen = _make_create_screen(ResourceType.INGRESSES)
        values = {
            "name": "web-ingress",
            "class_name": "nginx",
            "rules": "- host: example.com\n  paths:\n    - path: /\n      path_type: Prefix\n      service_name: web-svc\n      service_port: 80",
            "tls": "- hosts:\n    - example.com\n  secret_name: tls-secret",
            "namespace": "default",
            "labels": "",
        }
        with patch(
            "system_operations_manager.services.kubernetes.networking_manager.NetworkingManager",
        ) as mock_cls:
            mock_cls.return_value = MagicMock()
            result = screen._create_resource(values)
        assert result == "web-ingress"


@pytest.mark.unit
class TestCreateResourceNetworkPolicies:
    """Tests for _create_resource with NETWORK_POLICIES."""

    def test_create_network_policy(self) -> None:
        """Creates network policy with pod selector, policy types."""
        screen = _make_create_screen(ResourceType.NETWORK_POLICIES)
        values = {
            "name": "deny-all",
            "pod_selector": "app=web",
            "policy_types": "Ingress,Egress",
            "namespace": "default",
            "labels": "",
        }
        with patch(
            "system_operations_manager.services.kubernetes.networking_manager.NetworkingManager",
        ) as mock_cls:
            mock_cls.return_value = MagicMock()
            result = screen._create_resource(values)
        assert result == "deny-all"


@pytest.mark.unit
class TestCreateResourceConfigMaps:
    """Tests for _create_resource with CONFIGMAPS."""

    def test_create_configmap(self) -> None:
        """Creates configmap with data."""
        screen = _make_create_screen(ResourceType.CONFIGMAPS)
        values = {
            "name": "app-config",
            "data": "key1=val1\nkey2=val2",
            "namespace": "default",
            "labels": "",
        }
        with patch(
            "system_operations_manager.services.kubernetes.configuration_manager.ConfigurationManager",
        ) as mock_cls:
            mock_cls.return_value = MagicMock()
            result = screen._create_resource(values)
        assert result == "app-config"


@pytest.mark.unit
class TestCreateResourceSecrets:
    """Tests for _create_resource with SECRETS."""

    def test_create_secret(self) -> None:
        """Creates secret with type and data."""
        screen = _make_create_screen(ResourceType.SECRETS)
        values = {
            "name": "db-creds",
            "secret_type": "Opaque",
            "data": "user=admin\npassword=secret123",
            "namespace": "default",
            "labels": "",
        }
        with patch(
            "system_operations_manager.services.kubernetes.configuration_manager.ConfigurationManager",
        ) as mock_cls:
            mock_cls.return_value = MagicMock()
            result = screen._create_resource(values)
        assert result == "db-creds"


@pytest.mark.unit
class TestCreateResourceNamespaces:
    """Tests for _create_resource with NAMESPACES."""

    def test_create_namespace(self) -> None:
        """Creates namespace."""
        screen = _make_create_screen(ResourceType.NAMESPACES)
        values = {"name": "my-ns", "labels": "team=backend"}
        with patch(
            "system_operations_manager.services.kubernetes.namespace_manager.NamespaceClusterManager",
        ) as mock_cls:
            mock_cls.return_value = MagicMock()
            result = screen._create_resource(values)
        assert result == "my-ns"


@pytest.mark.unit
class TestCreateResourceUnsupported:
    """Tests for _create_resource with unsupported types."""

    def test_unsupported_type_raises(self) -> None:
        """Unsupported resource type raises ValueError."""
        screen = _make_create_screen(ResourceType.DEPLOYMENTS)
        # Force to an unsupported type
        screen._resource_type = ResourceType.EVENTS
        values = {"name": "test"}
        with pytest.raises(ValueError, match="Create not supported"):
            screen._create_resource(values)


# ============================================================================
# _parse_port_lines edge case Tests
# ============================================================================


@pytest.mark.unit
class TestParsePortLinesEdgeCases:
    """Edge cases for _parse_port_lines not covered by TestParsePortLines."""

    def test_target_port_non_numeric_falls_back_to_string(self) -> None:
        """target_port that cannot be cast to int is stored as a string."""
        result = _parse_port_lines("port=80,target_port=http")
        assert len(result) == 1
        assert result[0]["target_port"] == "http"

    def test_protocol_field_is_parsed(self) -> None:
        """protocol field is included in the returned dict."""
        result = _parse_port_lines("port=80,protocol=UDP")
        assert len(result) == 1
        assert result[0]["protocol"] == "UDP"

    def test_name_field_is_parsed(self) -> None:
        """name field is included in the returned dict."""
        result = _parse_port_lines("port=53,name=dns")
        assert len(result) == 1
        assert result[0]["name"] == "dns"

    def test_protocol_and_name_together(self) -> None:
        """protocol and name fields are both parsed when present."""
        result = _parse_port_lines("port=53,protocol=UDP,name=dns")
        assert len(result) == 1
        assert result[0]["protocol"] == "UDP"
        assert result[0]["name"] == "dns"

    def test_blank_lines_between_port_entries_are_skipped(self) -> None:
        """Blank lines embedded inside multi-line input are skipped gracefully."""
        result = _parse_port_lines("port=80\n\nport=443")
        assert len(result) == 2
        assert result[0]["port"] == 80
        assert result[1]["port"] == 443


# ============================================================================
# _collect_values Tests
# ============================================================================


def _make_input_mock(value: str) -> MagicMock:
    """Return a mock that behaves like a Textual Input widget."""
    m = MagicMock()
    m.value = value
    return m


def _make_textarea_mock(text: str) -> MagicMock:
    """Return a mock that behaves like a Textual TextArea widget."""
    m = MagicMock()
    m.text = text
    return m


def _make_select_mock(value: object, blank: object = None) -> MagicMock:
    """Return a mock that behaves like a Textual Select widget."""
    m = MagicMock()
    m.value = value
    return m


@pytest.mark.unit
class TestCollectValuesDeployment:
    """_collect_values for DEPLOYMENTS (namespaced, int field, textarea)."""

    def _build_query(
        self,
        ns: str = "default",
        name: str = "web-app",
        image: str = "nginx:latest",
        replicas: str = "3",
        port: str = "80",
        labels: str = "",
    ) -> Any:
        ns_input = _make_input_mock(ns)
        name_input = _make_input_mock(name)
        image_input = _make_input_mock(image)
        replicas_input = _make_input_mock(replicas)
        port_input = _make_input_mock(port)
        labels_ta = _make_textarea_mock(labels)

        def mock_query(selector: str, *args: Any, **kwargs: Any) -> MagicMock:
            mapping = {
                "#field-namespace": ns_input,
                "#field-name": name_input,
                "#field-image": image_input,
                "#field-replicas": replicas_input,
                "#field-port": port_input,
                "#field-labels": labels_ta,
            }
            return mapping.get(selector, MagicMock(value="", text=""))

        return mock_query

    def test_collect_values_success(self) -> None:
        """All valid values are collected and returned."""
        screen = _make_create_screen(ResourceType.DEPLOYMENTS)
        object.__setattr__(screen, "query_one", MagicMock(side_effect=self._build_query()))
        result = screen._collect_values()
        assert result is not None
        assert result["namespace"] == "default"
        assert result["name"] == "web-app"
        assert result["image"] == "nginx:latest"
        assert result["replicas"] == 3
        assert result["port"] == 80

    def test_collect_values_uses_screen_namespace_when_field_empty(self) -> None:
        """When namespace input is empty, falls back to screen._namespace."""
        screen = _make_create_screen(ResourceType.DEPLOYMENTS)
        screen._namespace = "fallback-ns"
        object.__setattr__(screen, "query_one", MagicMock(side_effect=self._build_query(ns="")))
        result = screen._collect_values()
        assert result is not None
        assert result["namespace"] == "fallback-ns"

    def test_collect_values_required_field_empty_returns_none(self) -> None:
        """Returns None and notifies when a required field is empty."""
        screen = _make_create_screen(ResourceType.DEPLOYMENTS)
        # name is required; pass empty string for it
        object.__setattr__(screen, "query_one", MagicMock(side_effect=self._build_query(name="")))
        result = screen._collect_values()
        assert result is None
        cast(MagicMock, screen.notify_user).assert_called_once()
        call_args = cast(MagicMock, screen.notify_user).call_args
        assert call_args[1].get("severity") == "error" or "required" in call_args[0][0].lower()

    def test_collect_values_int_field_invalid_returns_none(self) -> None:
        """Returns None and notifies when an int field has a non-numeric value."""
        screen = _make_create_screen(ResourceType.DEPLOYMENTS)
        object.__setattr__(
            screen, "query_one", MagicMock(side_effect=self._build_query(replicas="abc"))
        )
        result = screen._collect_values()
        assert result is None
        cast(MagicMock, screen.notify_user).assert_called_once()
        assert cast(MagicMock, screen.notify_user).call_args[1].get("severity") == "error"

    def test_collect_values_empty_int_field_stored_as_string(self) -> None:
        """An optional int field left blank is stored as an empty string (not converted)."""
        screen = _make_create_screen(ResourceType.DEPLOYMENTS)
        object.__setattr__(
            screen, "query_one", MagicMock(side_effect=self._build_query(replicas="", port=""))
        )
        result = screen._collect_values()
        assert result is not None
        # Empty int fields are passed through as empty strings (no ValueError)
        assert result["replicas"] == ""
        assert result["port"] == ""


@pytest.mark.unit
class TestCollectValuesClusterScoped:
    """_collect_values skips namespace for cluster-scoped resources."""

    def test_collect_values_namespace_skipped_for_namespace_resource(self) -> None:
        """No namespace key in result for NAMESPACES (cluster-scoped)."""
        screen = _make_create_screen(ResourceType.NAMESPACES)

        name_input = _make_input_mock("my-ns")
        labels_ta = _make_textarea_mock("")

        def mock_query(selector: str, *args: Any, **kwargs: Any) -> MagicMock:
            if selector == "#field-name":
                return name_input
            if selector == "#field-labels":
                return labels_ta
            return MagicMock(value="", text="")

        object.__setattr__(screen, "query_one", MagicMock(side_effect=mock_query))
        result = screen._collect_values()
        assert result is not None
        assert "namespace" not in result
        assert result["name"] == "my-ns"


@pytest.mark.unit
class TestCollectValuesSelectField:
    """_collect_values handles select-type fields (e.g. SECRETS secret_type)."""

    def test_collect_values_select_with_value(self) -> None:
        """Select field value is collected as a string."""

        screen = _make_create_screen(ResourceType.SECRETS)

        ns_input = _make_input_mock("default")
        name_input = _make_input_mock("my-secret")
        # secret_type is a select field
        select_mock = _make_select_mock("kubernetes.io/tls")
        data_ta = _make_textarea_mock("cert=abc")
        labels_ta = _make_textarea_mock("")

        def mock_query(selector: str, *args: Any, **kwargs: Any) -> MagicMock:
            mapping = {
                "#field-namespace": ns_input,
                "#field-name": name_input,
                "#field-secret_type": select_mock,
                "#field-data": data_ta,
                "#field-labels": labels_ta,
            }
            return mapping.get(selector, MagicMock(value="", text=""))

        object.__setattr__(screen, "query_one", MagicMock(side_effect=mock_query))

        # Patch Select.BLANK so our mock value != BLANK
        with patch(
            "system_operations_manager.tui.apps.kubernetes.create_screen.Select"
        ) as mock_select_cls:
            mock_select_cls.BLANK = object()  # unique sentinel
            select_mock.value = "kubernetes.io/tls"
            result = screen._collect_values()

        assert result is not None
        assert result["secret_type"] == "kubernetes.io/tls"

    def test_collect_values_select_blank_uses_default(self) -> None:
        """Select field at BLANK falls back to spec.default."""
        from system_operations_manager.tui.apps.kubernetes.create_screen import RESOURCE_FIELD_SPECS

        screen = _make_create_screen(ResourceType.SECRETS)

        ns_input = _make_input_mock("default")
        name_input = _make_input_mock("my-secret")
        data_ta = _make_textarea_mock("key=val")
        labels_ta = _make_textarea_mock("")

        # We patch Select.BLANK and make select return that sentinel
        sentinel = object()

        select_mock = MagicMock()
        select_mock.value = sentinel  # equals BLANK

        def mock_query(selector: str, *args: Any, **kwargs: Any) -> MagicMock:
            mapping = {
                "#field-namespace": ns_input,
                "#field-name": name_input,
                "#field-secret_type": select_mock,
                "#field-data": data_ta,
                "#field-labels": labels_ta,
            }
            return mapping.get(selector, MagicMock(value="", text=""))

        object.__setattr__(screen, "query_one", MagicMock(side_effect=mock_query))

        with patch(
            "system_operations_manager.tui.apps.kubernetes.create_screen.Select"
        ) as mock_select_cls:
            mock_select_cls.BLANK = sentinel
            result = screen._collect_values()

        assert result is not None
        # default for secret_type is "Opaque"
        secret_spec = next(
            s for s in RESOURCE_FIELD_SPECS[ResourceType.SECRETS] if s.name == "secret_type"
        )
        assert result["secret_type"] == secret_spec.default


@pytest.mark.unit
class TestCollectValuesTextareaField:
    """_collect_values handles textarea-type fields correctly."""

    def test_collect_values_textarea_text_is_stripped(self) -> None:
        """TextArea .text is stripped when collected."""
        screen = _make_create_screen(ResourceType.CONFIGMAPS)

        ns_input = _make_input_mock("default")
        name_input = _make_input_mock("app-config")
        data_ta = _make_textarea_mock("  key1=val1\n  key2=val2  ")
        labels_ta = _make_textarea_mock("  ")

        def mock_query(selector: str, *args: Any, **kwargs: Any) -> MagicMock:
            mapping = {
                "#field-namespace": ns_input,
                "#field-name": name_input,
                "#field-data": data_ta,
                "#field-labels": labels_ta,
            }
            return mapping.get(selector, MagicMock(value="", text=""))

        object.__setattr__(screen, "query_one", MagicMock(side_effect=mock_query))
        result = screen._collect_values()
        assert result is not None
        assert result["data"] == "key1=val1\n  key2=val2"
        assert result["labels"] == ""


# ============================================================================
# _create_resource optional field branch Tests
# ============================================================================


@pytest.mark.unit
class TestCreateResourceStatefulSetsOptionalFields:
    """Tests that optional fields are forwarded when present for STATEFULSETS."""

    def test_create_statefulset_with_replicas_port_and_labels(self) -> None:
        """StatefulSet optional replicas, port, and labels are passed to manager."""
        screen = _make_create_screen(ResourceType.STATEFULSETS)
        values = {
            "name": "redis",
            "image": "redis:7",
            "service_name": "redis-headless",
            "namespace": "default",
            "replicas": 3,
            "port": 6379,
            "labels": "app=redis",
        }
        with patch(
            "system_operations_manager.services.kubernetes.workload_manager.WorkloadManager",
        ) as mock_cls:
            mock_mgr = MagicMock()
            mock_cls.return_value = mock_mgr
            result = screen._create_resource(values)

        assert result == "redis"
        mock_mgr.create_stateful_set.assert_called_once()
        call_kwargs = mock_mgr.create_stateful_set.call_args[1]
        assert call_kwargs.get("replicas") == 3
        assert call_kwargs.get("port") == 6379
        assert call_kwargs.get("labels") == {"app": "redis"}

    def test_create_statefulset_with_only_replicas(self) -> None:
        """StatefulSet with just replicas set passes it through."""
        screen = _make_create_screen(ResourceType.STATEFULSETS)
        values = {
            "name": "redis",
            "image": "redis:7",
            "service_name": "redis-headless",
            "namespace": "default",
            "replicas": 2,
            "port": "",
            "labels": "",
        }
        with patch(
            "system_operations_manager.services.kubernetes.workload_manager.WorkloadManager",
        ) as mock_cls:
            mock_mgr = MagicMock()
            mock_cls.return_value = mock_mgr
            result = screen._create_resource(values)

        assert result == "redis"
        call_kwargs = mock_mgr.create_stateful_set.call_args[1]
        assert call_kwargs.get("replicas") == 2
        assert "port" not in call_kwargs
        assert "labels" not in call_kwargs

    def test_create_statefulset_with_only_port(self) -> None:
        """StatefulSet with just port set passes it through."""
        screen = _make_create_screen(ResourceType.STATEFULSETS)
        values = {
            "name": "redis",
            "image": "redis:7",
            "service_name": "redis-headless",
            "namespace": "default",
            "replicas": "",
            "port": 6379,
            "labels": "",
        }
        with patch(
            "system_operations_manager.services.kubernetes.workload_manager.WorkloadManager",
        ) as mock_cls:
            mock_mgr = MagicMock()
            mock_cls.return_value = mock_mgr
            screen._create_resource(values)

        call_kwargs = mock_mgr.create_stateful_set.call_args[1]
        assert call_kwargs.get("port") == 6379
        assert "replicas" not in call_kwargs

    def test_create_statefulset_with_only_labels(self) -> None:
        """StatefulSet with just labels set passes them through."""
        screen = _make_create_screen(ResourceType.STATEFULSETS)
        values = {
            "name": "redis",
            "image": "redis:7",
            "service_name": "redis-headless",
            "namespace": "default",
            "replicas": "",
            "port": "",
            "labels": "env=prod",
        }
        with patch(
            "system_operations_manager.services.kubernetes.workload_manager.WorkloadManager",
        ) as mock_cls:
            mock_mgr = MagicMock()
            mock_cls.return_value = mock_mgr
            screen._create_resource(values)

        call_kwargs = mock_mgr.create_stateful_set.call_args[1]
        assert call_kwargs.get("labels") == {"env": "prod"}


@pytest.mark.unit
class TestCreateResourceDaemonSetsOptionalFields:
    """Tests that optional fields are forwarded when present for DAEMONSETS."""

    def test_create_daemonset_with_port_and_labels(self) -> None:
        """DaemonSet optional port and labels are passed to manager."""
        screen = _make_create_screen(ResourceType.DAEMONSETS)
        values = {
            "name": "fluentd",
            "image": "fluent-bit:latest",
            "namespace": "logging",
            "port": 2020,
            "labels": "tier=logging",
        }
        with patch(
            "system_operations_manager.services.kubernetes.workload_manager.WorkloadManager",
        ) as mock_cls:
            mock_mgr = MagicMock()
            mock_cls.return_value = mock_mgr
            result = screen._create_resource(values)

        assert result == "fluentd"
        mock_mgr.create_daemon_set.assert_called_once()
        call_kwargs = mock_mgr.create_daemon_set.call_args[1]
        assert call_kwargs.get("port") == 2020
        assert call_kwargs.get("labels") == {"tier": "logging"}

    def test_create_daemonset_with_only_port(self) -> None:
        """DaemonSet with just port set; no labels kwarg is passed."""
        screen = _make_create_screen(ResourceType.DAEMONSETS)
        values = {
            "name": "fluentd",
            "image": "fluent-bit:latest",
            "namespace": "logging",
            "port": 2020,
            "labels": "",
        }
        with patch(
            "system_operations_manager.services.kubernetes.workload_manager.WorkloadManager",
        ) as mock_cls:
            mock_mgr = MagicMock()
            mock_cls.return_value = mock_mgr
            screen._create_resource(values)

        call_kwargs = mock_mgr.create_daemon_set.call_args[1]
        assert call_kwargs.get("port") == 2020
        assert "labels" not in call_kwargs

    def test_create_daemonset_with_only_labels(self) -> None:
        """DaemonSet with just labels set; no port kwarg is passed."""
        screen = _make_create_screen(ResourceType.DAEMONSETS)
        values = {
            "name": "fluentd",
            "image": "fluent-bit:latest",
            "namespace": "logging",
            "port": "",
            "labels": "env=prod",
        }
        with patch(
            "system_operations_manager.services.kubernetes.workload_manager.WorkloadManager",
        ) as mock_cls:
            mock_mgr = MagicMock()
            mock_cls.return_value = mock_mgr
            screen._create_resource(values)

        call_kwargs = mock_mgr.create_daemon_set.call_args[1]
        assert call_kwargs.get("labels") == {"env": "prod"}
        assert "port" not in call_kwargs


@pytest.mark.unit
class TestCreateResourceIngressesOptionalFields:
    """Tests that optional labels branch is exercised for INGRESSES."""

    def test_create_ingress_with_labels(self) -> None:
        """Ingress labels are passed to manager when non-empty."""
        screen = _make_create_screen(ResourceType.INGRESSES)
        values = {
            "name": "web-ingress",
            "class_name": "nginx",
            "rules": (
                "- host: example.com\n"
                "  paths:\n"
                "    - path: /\n"
                "      path_type: Prefix\n"
                "      service_name: web-svc\n"
                "      service_port: 80"
            ),
            "tls": "",
            "namespace": "default",
            "labels": "app=web",
        }
        with patch(
            "system_operations_manager.services.kubernetes.networking_manager.NetworkingManager",
        ) as mock_cls:
            mock_mgr = MagicMock()
            mock_cls.return_value = mock_mgr
            result = screen._create_resource(values)

        assert result == "web-ingress"
        call_kwargs = mock_mgr.create_ingress.call_args[1]
        assert call_kwargs.get("labels") == {"app": "web"}

    def test_create_ingress_with_tls(self) -> None:
        """Ingress tls YAML list is parsed and passed to manager."""
        screen = _make_create_screen(ResourceType.INGRESSES)
        values = {
            "name": "tls-ingress",
            "class_name": "nginx",
            "rules": "",
            "tls": "- hosts:\n    - example.com\n  secret_name: tls-secret",
            "namespace": "default",
            "labels": "",
        }
        with patch(
            "system_operations_manager.services.kubernetes.networking_manager.NetworkingManager",
        ) as mock_cls:
            mock_mgr = MagicMock()
            mock_cls.return_value = mock_mgr
            result = screen._create_resource(values)

        assert result == "tls-ingress"
        call_kwargs = mock_mgr.create_ingress.call_args[1]
        assert "tls" in call_kwargs
        assert isinstance(call_kwargs["tls"], list)


@pytest.mark.unit
class TestCreateResourceNetworkPoliciesOptionalFields:
    """Tests that optional labels branch is exercised for NETWORK_POLICIES."""

    def test_create_network_policy_with_labels(self) -> None:
        """NetworkPolicy labels are passed to manager when non-empty."""
        screen = _make_create_screen(ResourceType.NETWORK_POLICIES)
        values = {
            "name": "deny-all",
            "pod_selector": "app=web",
            "policy_types": "Ingress,Egress",
            "namespace": "default",
            "labels": "env=prod",
        }
        with patch(
            "system_operations_manager.services.kubernetes.networking_manager.NetworkingManager",
        ) as mock_cls:
            mock_mgr = MagicMock()
            mock_cls.return_value = mock_mgr
            result = screen._create_resource(values)

        assert result == "deny-all"
        call_kwargs = mock_mgr.create_network_policy.call_args[1]
        assert call_kwargs.get("labels") == {"env": "prod"}

    def test_create_network_policy_without_labels(self) -> None:
        """NetworkPolicy with empty labels does not pass labels kwarg."""
        screen = _make_create_screen(ResourceType.NETWORK_POLICIES)
        values = {
            "name": "deny-all",
            "pod_selector": "",
            "policy_types": "",
            "namespace": "default",
            "labels": "",
        }
        with patch(
            "system_operations_manager.services.kubernetes.networking_manager.NetworkingManager",
        ) as mock_cls:
            mock_mgr = MagicMock()
            mock_cls.return_value = mock_mgr
            result = screen._create_resource(values)

        assert result == "deny-all"
        call_kwargs = mock_mgr.create_network_policy.call_args[1]
        assert "labels" not in call_kwargs
