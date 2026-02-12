"""Unit tests for Kubernetes base models and utilities."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from system_operations_manager.integrations.kubernetes.models.base import (
    K8sEntityBase,
    OwnerReference,
    _get_annotations,
    _get_labels,
    _get_timestamp,
    _safe_get,
)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestSafeGet:
    """Test _safe_get utility function."""

    def test_safe_get_single_attr(self) -> None:
        """Test getting single attribute."""
        obj = MagicMock()
        obj.name = "test"
        result = _safe_get(obj, "name")
        assert result == "test"

    def test_safe_get_nested_attrs(self) -> None:
        """Test getting nested attributes."""
        obj = MagicMock()
        obj.metadata.name = "test-pod"
        result = _safe_get(obj, "metadata", "name")
        assert result == "test-pod"

    def test_safe_get_deeply_nested(self) -> None:
        """Test getting deeply nested attributes."""
        obj = MagicMock()
        obj.spec.template.metadata.labels = {"app": "test"}
        result = _safe_get(obj, "spec", "template", "metadata", "labels")
        assert result == {"app": "test"}

    def test_safe_get_missing_attr(self) -> None:
        """Test getting missing attribute returns default."""
        obj = SimpleNamespace(name="test")
        result = _safe_get(obj, "missing", default="default-value")
        assert result == "default-value"

    def test_safe_get_none_object(self) -> None:
        """Test getting from None object returns default."""
        result = _safe_get(None, "name", default="default")
        assert result == "default"

    def test_safe_get_none_intermediate(self) -> None:
        """Test getting when intermediate value is None."""
        obj = MagicMock()
        obj.metadata = None
        result = _safe_get(obj, "metadata", "name", default="unknown")
        assert result == "unknown"

    def test_safe_get_default_none(self) -> None:
        """Test default is None when not specified."""
        obj = SimpleNamespace()
        result = _safe_get(obj, "missing")
        assert result is None


@pytest.mark.unit
@pytest.mark.kubernetes
class TestGetTimestamp:
    """Test _get_timestamp utility function."""

    def test_get_timestamp_none(self) -> None:
        """Test getting timestamp from None."""
        result = _get_timestamp(None)
        assert result is None

    def test_get_timestamp_string(self) -> None:
        """Test getting timestamp from string."""
        timestamp = "2024-01-01T00:00:00Z"
        result = _get_timestamp(timestamp)
        assert result == timestamp

    def test_get_timestamp_datetime(self) -> None:
        """Test getting timestamp from datetime object."""
        dt = datetime(2024, 1, 1, 12, 30, 45, tzinfo=UTC)
        result = _get_timestamp(dt)
        assert result == "2024-01-01T12:30:45+00:00"

    def test_get_timestamp_other_type(self) -> None:
        """Test getting timestamp from other type converts to string."""
        result = _get_timestamp(12345)
        assert result == "12345"


@pytest.mark.unit
@pytest.mark.kubernetes
class TestGetLabels:
    """Test _get_labels utility function."""

    def test_get_labels_with_labels(self) -> None:
        """Test getting labels when present."""
        obj = MagicMock()
        obj.metadata.labels = {"app": "test", "env": "prod"}
        result = _get_labels(obj)
        assert result == {"app": "test", "env": "prod"}

    def test_get_labels_empty_dict(self) -> None:
        """Test getting empty labels returns None."""
        obj = MagicMock()
        obj.metadata.labels = {}
        result = _get_labels(obj)
        assert result is None

    def test_get_labels_none(self) -> None:
        """Test getting None labels returns None."""
        obj = MagicMock()
        obj.metadata.labels = None
        result = _get_labels(obj)
        assert result is None

    def test_get_labels_no_metadata(self) -> None:
        """Test getting labels when metadata is missing."""
        obj = MagicMock()
        obj.metadata = None
        result = _get_labels(obj)
        assert result is None


@pytest.mark.unit
@pytest.mark.kubernetes
class TestGetAnnotations:
    """Test _get_annotations utility function."""

    def test_get_annotations_with_annotations(self) -> None:
        """Test getting annotations when present."""
        obj = MagicMock()
        obj.metadata.annotations = {"key": "value", "note": "test"}
        result = _get_annotations(obj)
        assert result == {"key": "value", "note": "test"}

    def test_get_annotations_empty_dict(self) -> None:
        """Test getting empty annotations returns None."""
        obj = MagicMock()
        obj.metadata.annotations = {}
        result = _get_annotations(obj)
        assert result is None

    def test_get_annotations_none(self) -> None:
        """Test getting None annotations returns None."""
        obj = MagicMock()
        obj.metadata.annotations = None
        result = _get_annotations(obj)
        assert result is None

    def test_get_annotations_no_metadata(self) -> None:
        """Test getting annotations when metadata is missing."""
        obj = MagicMock()
        obj.metadata = None
        result = _get_annotations(obj)
        assert result is None


@pytest.mark.unit
@pytest.mark.kubernetes
class TestK8sEntityBase:
    """Test K8sEntityBase model."""

    def test_init_minimal(self) -> None:
        """Test initialization with minimal fields."""
        entity = K8sEntityBase(name="test")
        assert entity.name == "test"
        assert entity.namespace is None
        assert entity.uid is None
        assert entity.creation_timestamp is None
        assert entity.labels is None
        assert entity.annotations is None

    def test_init_complete(self) -> None:
        """Test initialization with all fields."""
        entity = K8sEntityBase(
            name="test-pod",
            namespace="default",
            uid="uid-123",
            creation_timestamp="2024-01-01T00:00:00Z",
            labels={"app": "test"},
            annotations={"note": "example"},
        )
        assert entity.name == "test-pod"
        assert entity.namespace == "default"
        assert entity.uid == "uid-123"
        assert entity.creation_timestamp == "2024-01-01T00:00:00Z"
        assert entity.labels == {"app": "test"}
        assert entity.annotations == {"note": "example"}

    def test_age_property_unknown_no_timestamp(self) -> None:
        """Test age property returns Unknown when no timestamp."""
        entity = K8sEntityBase(name="test")
        assert entity.age == "Unknown"

    def test_age_property_days(self) -> None:
        """Test age property returns days."""
        created = datetime.now(UTC) - timedelta(days=5, hours=2)
        entity = K8sEntityBase(
            name="test",
            creation_timestamp=created.isoformat(),
        )
        assert entity.age == "5d"

    def test_age_property_hours(self) -> None:
        """Test age property returns hours."""
        created = datetime.now(UTC) - timedelta(hours=3, minutes=30)
        entity = K8sEntityBase(
            name="test",
            creation_timestamp=created.isoformat(),
        )
        assert entity.age == "3h"

    def test_age_property_minutes(self) -> None:
        """Test age property returns minutes."""
        created = datetime.now(UTC) - timedelta(minutes=45)
        entity = K8sEntityBase(
            name="test",
            creation_timestamp=created.isoformat(),
        )
        assert entity.age == "45m"

    def test_age_property_recent(self) -> None:
        """Test age property for very recent entity."""
        created = datetime.now(UTC) - timedelta(seconds=30)
        entity = K8sEntityBase(
            name="test",
            creation_timestamp=created.isoformat(),
        )
        assert entity.age == "0m"

    def test_age_property_invalid_timestamp(self) -> None:
        """Test age property with invalid timestamp."""
        entity = K8sEntityBase(
            name="test",
            creation_timestamp="invalid-timestamp",
        )
        assert entity.age == "Unknown"

    def test_model_config_extra_ignore(self) -> None:
        """Test that extra fields are ignored."""
        entity = K8sEntityBase(name="test", unknown_field="ignored")
        assert entity.name == "test"
        assert not hasattr(entity, "unknown_field")

    def test_str_strip_whitespace(self) -> None:
        """Test that string fields are stripped."""
        entity = K8sEntityBase(name="  test  ")
        assert entity.name == "test"

    def test_entity_name_class_var(self) -> None:
        """Test _entity_name class variable."""
        assert K8sEntityBase._entity_name == "entity"


@pytest.mark.unit
@pytest.mark.kubernetes
class TestOwnerReference:
    """Test OwnerReference model."""

    def test_init_default(self) -> None:
        """Test initialization with defaults."""
        ref = OwnerReference()
        assert ref.api_version is None
        assert ref.kind is None
        assert ref.name is None
        assert ref.uid is None

    def test_init_with_values(self) -> None:
        """Test initialization with values."""
        ref = OwnerReference(
            api_version="apps/v1",
            kind="Deployment",
            name="nginx",
            uid="uid-456",
        )
        assert ref.api_version == "apps/v1"
        assert ref.kind == "Deployment"
        assert ref.name == "nginx"
        assert ref.uid == "uid-456"

    def test_from_k8s_object_complete(self) -> None:
        """Test from_k8s_object with complete object."""
        obj = MagicMock()
        obj.api_version = "apps/v1"
        obj.kind = "ReplicaSet"
        obj.name = "nginx-abc123"
        obj.uid = "uid-789"

        ref = OwnerReference.from_k8s_object(obj)

        assert ref.api_version == "apps/v1"
        assert ref.kind == "ReplicaSet"
        assert ref.name == "nginx-abc123"
        assert ref.uid == "uid-789"

    def test_from_k8s_object_partial(self) -> None:
        """Test from_k8s_object with partial object."""
        obj = MagicMock()
        obj.kind = "Deployment"
        obj.name = "app"
        del obj.api_version
        del obj.uid

        ref = OwnerReference.from_k8s_object(obj)

        assert ref.api_version is None
        assert ref.kind == "Deployment"
        assert ref.name == "app"
        assert ref.uid is None

    def test_from_k8s_object_none(self) -> None:
        """Test from_k8s_object with None."""
        ref = OwnerReference.from_k8s_object(None)

        assert ref.api_version is None
        assert ref.kind is None
        assert ref.name is None
        assert ref.uid is None

    def test_model_config_extra_ignore(self) -> None:
        """Test that extra fields are ignored."""
        ref = OwnerReference(kind="Pod", unknown="ignored")
        assert ref.kind == "Pod"
        assert not hasattr(ref, "unknown")
