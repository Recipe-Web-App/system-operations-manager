"""Form-based resource creation screen for Kubernetes TUI.

Provides a dynamic form that adapts its fields based on the selected
resource type. Uses a field-spec registry to define what inputs each
resource type requires.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import structlog
from textual.app import ComposeResult
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.message import Message
from textual.widgets import Button, Input, Label, Select, TextArea

from system_operations_manager.tui.apps.kubernetes.types import (
    CLUSTER_SCOPED_TYPES,
    ResourceType,
)
from system_operations_manager.tui.base import BaseScreen

if TYPE_CHECKING:
    from system_operations_manager.integrations.kubernetes.client import KubernetesClient

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Field specification
# ---------------------------------------------------------------------------


@dataclass
class FieldSpec:
    """Describes a single form field for resource creation."""

    name: str
    label: str
    field_type: str = "text"  # text | int | select | textarea
    required: bool = False
    default: str = ""
    options: list[tuple[str, str]] | None = None  # (label, value) for selects
    placeholder: str = ""
    help_text: str = ""


# ---------------------------------------------------------------------------
# Per-resource-type field definitions
# ---------------------------------------------------------------------------

RESOURCE_FIELD_SPECS: dict[ResourceType, list[FieldSpec]] = {
    ResourceType.DEPLOYMENTS: [
        FieldSpec("name", "Name", required=True, placeholder="my-deployment"),
        FieldSpec("image", "Image", required=True, placeholder="nginx:latest"),
        FieldSpec("replicas", "Replicas", field_type="int", default="1"),
        FieldSpec("port", "Container Port", field_type="int", placeholder="80"),
        FieldSpec(
            "labels",
            "Labels",
            field_type="textarea",
            placeholder="key=value (one per line)",
            help_text="Labels as key=value pairs, one per line",
        ),
    ],
    ResourceType.STATEFULSETS: [
        FieldSpec("name", "Name", required=True, placeholder="my-statefulset"),
        FieldSpec("image", "Image", required=True, placeholder="postgres:16"),
        FieldSpec("replicas", "Replicas", field_type="int", default="1"),
        FieldSpec(
            "service_name",
            "Headless Service",
            required=True,
            placeholder="my-svc-headless",
        ),
        FieldSpec("port", "Container Port", field_type="int", placeholder="5432"),
        FieldSpec(
            "labels",
            "Labels",
            field_type="textarea",
            placeholder="key=value (one per line)",
        ),
    ],
    ResourceType.DAEMONSETS: [
        FieldSpec("name", "Name", required=True, placeholder="my-daemonset"),
        FieldSpec("image", "Image", required=True, placeholder="fluent-bit:latest"),
        FieldSpec("port", "Container Port", field_type="int", placeholder="2020"),
        FieldSpec(
            "labels",
            "Labels",
            field_type="textarea",
            placeholder="key=value (one per line)",
        ),
    ],
    ResourceType.SERVICES: [
        FieldSpec("name", "Name", required=True, placeholder="my-service"),
        FieldSpec(
            "type",
            "Type",
            field_type="select",
            default="ClusterIP",
            options=[
                ("ClusterIP", "ClusterIP"),
                ("NodePort", "NodePort"),
                ("LoadBalancer", "LoadBalancer"),
                ("ExternalName", "ExternalName"),
            ],
        ),
        FieldSpec(
            "selector",
            "Selector",
            field_type="textarea",
            placeholder="app=my-app (one per line)",
            help_text="Pod selector as key=value pairs",
        ),
        FieldSpec(
            "ports",
            "Ports",
            field_type="textarea",
            placeholder="port=80,target_port=8080 (one per line)",
            help_text="Port mappings: port=N,target_port=N,protocol=TCP",
        ),
        FieldSpec(
            "labels",
            "Labels",
            field_type="textarea",
            placeholder="key=value (one per line)",
        ),
    ],
    ResourceType.INGRESSES: [
        FieldSpec("name", "Name", required=True, placeholder="my-ingress"),
        FieldSpec("class_name", "Ingress Class", placeholder="nginx"),
        FieldSpec(
            "rules",
            "Rules (YAML)",
            field_type="textarea",
            placeholder=(
                "- host: example.com\n"
                "  paths:\n"
                "    - path: /\n"
                "      path_type: Prefix\n"
                "      service_name: my-svc\n"
                "      service_port: 80"
            ),
            help_text="Ingress rules in YAML list format",
        ),
        FieldSpec(
            "tls",
            "TLS (YAML)",
            field_type="textarea",
            placeholder=("- hosts:\n    - example.com\n  secret_name: tls-secret"),
            help_text="TLS config in YAML list format",
        ),
        FieldSpec(
            "labels",
            "Labels",
            field_type="textarea",
            placeholder="key=value (one per line)",
        ),
    ],
    ResourceType.NETWORK_POLICIES: [
        FieldSpec("name", "Name", required=True, placeholder="my-netpol"),
        FieldSpec(
            "pod_selector",
            "Pod Selector",
            field_type="textarea",
            placeholder="app=my-app (one per line)",
            help_text="Pod selector as key=value pairs",
        ),
        FieldSpec(
            "policy_types",
            "Policy Types",
            placeholder="Ingress,Egress",
            help_text="Comma-separated: Ingress, Egress",
        ),
        FieldSpec(
            "labels",
            "Labels",
            field_type="textarea",
            placeholder="key=value (one per line)",
        ),
    ],
    ResourceType.CONFIGMAPS: [
        FieldSpec("name", "Name", required=True, placeholder="my-configmap"),
        FieldSpec(
            "data",
            "Data",
            field_type="textarea",
            placeholder="key=value (one per line)",
            help_text="ConfigMap data as key=value pairs",
        ),
        FieldSpec(
            "labels",
            "Labels",
            field_type="textarea",
            placeholder="key=value (one per line)",
        ),
    ],
    ResourceType.SECRETS: [
        FieldSpec("name", "Name", required=True, placeholder="my-secret"),
        FieldSpec(
            "secret_type",
            "Secret Type",
            field_type="select",
            default="Opaque",
            options=[
                ("Opaque", "Opaque"),
                ("TLS", "kubernetes.io/tls"),
                ("Docker Registry", "kubernetes.io/dockerconfigjson"),
            ],
        ),
        FieldSpec(
            "data",
            "Data",
            field_type="textarea",
            placeholder="key=value (one per line)",
            help_text="Secret data as key=value pairs (values will be base64-encoded)",
        ),
        FieldSpec(
            "labels",
            "Labels",
            field_type="textarea",
            placeholder="key=value (one per line)",
        ),
    ],
    ResourceType.NAMESPACES: [
        FieldSpec("name", "Name", required=True, placeholder="my-namespace"),
        FieldSpec(
            "labels",
            "Labels",
            field_type="textarea",
            placeholder="key=value (one per line)",
        ),
    ],
}


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def _parse_key_value_lines(text: str) -> dict[str, str]:
    """Parse ``key=value`` lines into a dict, skipping blank lines."""
    result: dict[str, str] = {}
    for line in text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        result[key.strip()] = value.strip()
    return result


def _parse_port_lines(text: str) -> list[dict[str, Any]]:
    """Parse port definitions from ``key=value`` comma-separated lines.

    Each line describes one port mapping::

        port=80,target_port=8080,protocol=TCP,name=http
    """
    ports: list[dict[str, Any]] = []
    for line in text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        parts = _parse_key_value_lines(line.replace(",", "\n"))
        if "port" not in parts:
            continue
        port_def: dict[str, Any] = {"port": int(parts["port"])}
        if "target_port" in parts:
            try:
                port_def["target_port"] = int(parts["target_port"])
            except ValueError:
                port_def["target_port"] = parts["target_port"]
        if "protocol" in parts:
            port_def["protocol"] = parts["protocol"]
        if "name" in parts:
            port_def["name"] = parts["name"]
        ports.append(port_def)
    return ports


# ---------------------------------------------------------------------------
# Create screen
# ---------------------------------------------------------------------------


class ResourceCreateScreen(BaseScreen[None]):
    """Form-based screen for creating Kubernetes resources."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("ctrl+s", "submit", "Create"),
    ]

    class ResourceCreated(Message):
        """Emitted when a resource is successfully created."""

        def __init__(self, resource_type: ResourceType, name: str) -> None:
            self.resource_type = resource_type
            self.resource_name = name
            super().__init__()

    def __init__(
        self,
        resource_type: ResourceType,
        client: KubernetesClient,
        namespace: str | None = None,
    ) -> None:
        super().__init__()
        self._resource_type = resource_type
        self._client = client
        self._namespace = namespace
        self._field_specs = RESOURCE_FIELD_SPECS[resource_type]
        self._log = logger.bind(screen="create", resource_type=resource_type.value)

    def compose(self) -> ComposeResult:
        """Build the form dynamically from the field spec registry."""
        type_label = self._resource_type.value
        if type_label.endswith("s"):
            type_label = type_label[:-1]

        yield Label(f"Create {type_label}", id="create-header")

        with ScrollableContainer(id="create-form"):
            # Namespace field for namespaced resources
            if self._resource_type not in CLUSTER_SCOPED_TYPES:
                with Vertical(classes="form-field"):
                    yield Label("Namespace", classes="form-label")
                    yield Input(
                        value=self._namespace or "",
                        placeholder="default",
                        id="field-namespace",
                    )

            for spec in self._field_specs:
                with Vertical(classes="form-field"):
                    label_text = spec.label
                    if spec.required:
                        label_text += " *"
                    yield Label(label_text, classes="form-label")

                    if spec.field_type == "select" and spec.options:
                        yield Select(
                            [(label, value) for label, value in spec.options],
                            value=spec.default or Select.BLANK,
                            id=f"field-{spec.name}",
                        )
                    elif spec.field_type == "textarea":
                        yield TextArea(
                            spec.default,
                            id=f"field-{spec.name}",
                        )
                    elif spec.field_type == "int":
                        yield Input(
                            value=spec.default,
                            placeholder=spec.placeholder,
                            id=f"field-{spec.name}",
                            type="integer",
                        )
                    else:
                        yield Input(
                            value=spec.default,
                            placeholder=spec.placeholder,
                            id=f"field-{spec.name}",
                        )

                    if spec.help_text:
                        yield Label(spec.help_text, classes="form-help")

        with Horizontal(id="create-buttons"):
            yield Button("Create", variant="success", id="btn-create")
            yield Button("Cancel", variant="default", id="btn-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks."""
        if event.button.id == "btn-create":
            self.action_submit()
        elif event.button.id == "btn-cancel":
            self.action_cancel()

    def action_cancel(self) -> None:
        """Go back without creating."""
        self.go_back()

    def action_submit(self) -> None:
        """Validate fields and create the resource."""
        values = self._collect_values()
        if values is None:
            return

        try:
            name = self._create_resource(values)
            self.post_message(self.ResourceCreated(self._resource_type, name))
            self.notify_user(f"Created {self._resource_type.value[:-1]} '{name}'")
            self.go_back()
        except Exception as e:
            self.notify_user(f"Create failed: {e}", severity="error")

    def _collect_values(self) -> dict[str, Any] | None:
        """Collect and validate form field values.

        Returns:
            Dictionary of field values, or None if validation fails.
        """
        values: dict[str, Any] = {}

        # Namespace
        if self._resource_type not in CLUSTER_SCOPED_TYPES:
            ns_input = self.query_one("#field-namespace", Input)
            values["namespace"] = ns_input.value.strip() or self._namespace

        for spec in self._field_specs:
            widget_id = f"#field-{spec.name}"

            if spec.field_type == "select":
                widget = self.query_one(widget_id, Select)
                raw = str(widget.value) if widget.value != Select.BLANK else spec.default
            elif spec.field_type == "textarea":
                widget = self.query_one(widget_id, TextArea)
                raw = widget.text.strip()
            else:
                widget = self.query_one(widget_id, Input)
                raw = widget.value.strip()

            if spec.required and not raw:
                self.notify_user(f"{spec.label} is required", severity="error")
                return None

            if spec.field_type == "int" and raw:
                try:
                    values[spec.name] = int(raw)
                except ValueError:
                    self.notify_user(f"{spec.label} must be a number", severity="error")
                    return None
            else:
                values[spec.name] = raw

        return values

    def _create_resource(self, values: dict[str, Any]) -> str:
        """Dispatch to the correct service manager create method.

        Returns:
            The name of the created resource.
        """
        name = values["name"]
        namespace = values.get("namespace")
        labels = _parse_key_value_lines(values.get("labels", "")) or None

        rt = self._resource_type

        if rt == ResourceType.DEPLOYMENTS:
            from system_operations_manager.services.kubernetes.workload_manager import (
                WorkloadManager,
            )

            mgr = WorkloadManager(self._client)
            kwargs: dict[str, Any] = {"image": values["image"]}
            if values.get("replicas"):
                kwargs["replicas"] = values["replicas"]
            if values.get("port"):
                kwargs["port"] = values["port"]
            if labels:
                kwargs["labels"] = labels
            mgr.create_deployment(name, namespace, **kwargs)

        elif rt == ResourceType.STATEFULSETS:
            from system_operations_manager.services.kubernetes.workload_manager import (
                WorkloadManager,
            )

            mgr = WorkloadManager(self._client)
            kwargs = {
                "image": values["image"],
                "service_name": values["service_name"],
            }
            if values.get("replicas"):
                kwargs["replicas"] = values["replicas"]
            if values.get("port"):
                kwargs["port"] = values["port"]
            if labels:
                kwargs["labels"] = labels
            mgr.create_stateful_set(name, namespace, **kwargs)

        elif rt == ResourceType.DAEMONSETS:
            from system_operations_manager.services.kubernetes.workload_manager import (
                WorkloadManager,
            )

            mgr = WorkloadManager(self._client)
            kwargs = {"image": values["image"]}
            if values.get("port"):
                kwargs["port"] = values["port"]
            if labels:
                kwargs["labels"] = labels
            mgr.create_daemon_set(name, namespace, **kwargs)

        elif rt == ResourceType.SERVICES:
            from system_operations_manager.services.kubernetes.networking_manager import (
                NetworkingManager,
            )

            mgr = NetworkingManager(self._client)
            kwargs = {}
            if values.get("type"):
                kwargs["type"] = values["type"]
            selector = _parse_key_value_lines(values.get("selector", ""))
            if selector:
                kwargs["selector"] = selector
            ports = _parse_port_lines(values.get("ports", ""))
            if ports:
                kwargs["ports"] = ports
            if labels:
                kwargs["labels"] = labels
            mgr.create_service(name, namespace, **kwargs)

        elif rt == ResourceType.INGRESSES:
            from system_operations_manager.services.kubernetes.networking_manager import (
                NetworkingManager,
            )

            mgr = NetworkingManager(self._client)
            kwargs = {}
            if values.get("class_name"):
                kwargs["class_name"] = values["class_name"]
            if values.get("rules"):
                import yaml

                rules = yaml.safe_load(values["rules"])
                if isinstance(rules, list):
                    kwargs["rules"] = rules
            if values.get("tls"):
                import yaml

                tls = yaml.safe_load(values["tls"])
                if isinstance(tls, list):
                    kwargs["tls"] = tls
            if labels:
                kwargs["labels"] = labels
            mgr.create_ingress(name, namespace, **kwargs)

        elif rt == ResourceType.NETWORK_POLICIES:
            from system_operations_manager.services.kubernetes.networking_manager import (
                NetworkingManager,
            )

            mgr = NetworkingManager(self._client)
            kwargs = {}
            pod_selector = _parse_key_value_lines(values.get("pod_selector", ""))
            if pod_selector:
                kwargs["pod_selector"] = pod_selector
            if values.get("policy_types"):
                kwargs["policy_types"] = [
                    t.strip() for t in values["policy_types"].split(",") if t.strip()
                ]
            if labels:
                kwargs["labels"] = labels
            mgr.create_network_policy(name, namespace, **kwargs)

        elif rt == ResourceType.CONFIGMAPS:
            from system_operations_manager.services.kubernetes.configuration_manager import (
                ConfigurationManager,
            )

            mgr = ConfigurationManager(self._client)
            data = _parse_key_value_lines(values.get("data", "")) or None
            mgr.create_config_map(name, namespace, data=data, labels=labels)

        elif rt == ResourceType.SECRETS:
            from system_operations_manager.services.kubernetes.configuration_manager import (
                ConfigurationManager,
            )

            mgr = ConfigurationManager(self._client)
            data = _parse_key_value_lines(values.get("data", "")) or None
            secret_type = values.get("secret_type", "Opaque")
            mgr.create_secret(name, namespace, data=data, secret_type=secret_type, labels=labels)

        elif rt == ResourceType.NAMESPACES:
            from system_operations_manager.services.kubernetes.namespace_manager import (
                NamespaceClusterManager,
            )

            mgr = NamespaceClusterManager(self._client)
            mgr.create_namespace(name, labels=labels)

        else:
            msg = f"Create not supported for {rt.value}"
            raise ValueError(msg)

        return name
