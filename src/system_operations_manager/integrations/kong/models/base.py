"""Base models for Kong entities.

This module provides common base classes and utilities for all Kong entity models.
All Kong entities share common fields (id, created_at, updated_at, tags) and
serialization patterns.
"""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field


class KongEntityBase(BaseModel):
    """Base class for all Kong entity models.

    Provides common fields and configuration for Kong entities.
    All Kong entities have id, created_at, updated_at, and tags fields.

    Attributes:
        id: Unique identifier (UUID string).
        created_at: Unix timestamp of creation.
        updated_at: Unix timestamp of last update.
        tags: Entity tags for filtering and organization.
    """

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    # Common Kong entity fields
    id: str | None = Field(default=None, description="Unique identifier")
    created_at: int | None = Field(default=None, description="Unix timestamp of creation")
    updated_at: int | None = Field(default=None, description="Unix timestamp of last update")
    tags: list[str] | None = Field(default=None, description="Entity tags for filtering")

    # Subclasses should define this for better error messages
    _entity_name: ClassVar[str] = "entity"

    def to_create_payload(self) -> dict[str, Any]:
        """Convert model to payload for create operations.

        Excludes id, created_at, updated_at, and None values.
        This ensures only user-provided fields are sent to the API.

        Returns:
            Dictionary suitable for POST request body.
        """
        exclude_fields = {"id", "created_at", "updated_at"}
        return {k: v for k, v in self.model_dump(exclude=exclude_fields).items() if v is not None}

    def to_update_payload(self) -> dict[str, Any]:
        """Convert model to payload for update operations.

        Excludes id, created_at, updated_at, and None values.
        This ensures only user-provided fields are sent to the API.

        Returns:
            Dictionary suitable for PATCH request body.
        """
        return self.to_create_payload()


class KongEntityReference(BaseModel):
    """Reference to another Kong entity (used for relationships).

    Kong uses this pattern to reference related entities, allowing
    specification by either ID or name.

    Attributes:
        id: Entity ID (UUID string).
        name: Entity name (alternative to ID).
    """

    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    name: str | None = None

    @classmethod
    def from_id(cls, entity_id: str) -> KongEntityReference:
        """Create a reference from an entity ID.

        Args:
            entity_id: The entity's UUID.

        Returns:
            KongEntityReference with id set.
        """
        return cls(id=entity_id)

    @classmethod
    def from_name(cls, name: str) -> KongEntityReference:
        """Create a reference from an entity name.

        Args:
            name: The entity's name.

        Returns:
            KongEntityReference with name set.
        """
        return cls(name=name)

    @classmethod
    def from_id_or_name(cls, id_or_name: str) -> KongEntityReference:
        """Create a reference from either an ID or name.

        Uses heuristic: if it looks like a UUID (contains hyphens and
        is 36 chars), treat as ID; otherwise treat as name.

        Args:
            id_or_name: Either an entity ID or name.

        Returns:
            KongEntityReference with appropriate field set.
        """
        # Simple heuristic: UUIDs are 36 chars with hyphens
        if len(id_or_name) == 36 and id_or_name.count("-") == 4:
            return cls(id=id_or_name)
        return cls(name=id_or_name)


class PaginatedResponse(BaseModel):
    """Paginated response from Kong Admin API.

    Kong uses cursor-based pagination with an offset token.

    Attributes:
        data: List of entity dictionaries.
        next: URL for next page (deprecated in newer Kong versions).
        offset: Offset token for next page.
    """

    model_config = ConfigDict(extra="allow")

    data: list[dict[str, Any]] = Field(default_factory=list)
    next: str | None = None
    offset: str | None = None

    @property
    def has_more(self) -> bool:
        """Check if there are more results available.

        Returns:
            True if pagination offset indicates more data.
        """
        return self.offset is not None or self.next is not None
