"""Base entity manager for Kong services.

This module provides an abstract base class implementing the Repository pattern
for Kong entities. All entity-specific managers inherit from BaseEntityManager
and can extend it with entity-specific operations.
"""

from __future__ import annotations

import builtins
from abc import ABC
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from system_operations_manager.integrations.kong.client import KongAdminClient

from system_operations_manager.integrations.kong.exceptions import KongNotFoundError
from system_operations_manager.integrations.kong.models.base import KongEntityBase

logger = structlog.get_logger()


class BaseEntityManager[T: KongEntityBase](ABC):
    """Abstract base class for Kong entity managers.

    Implements the Repository pattern for Kong entities, providing standard
    CRUD operations that work with any Kong entity type. Subclasses must
    define the entity-specific endpoint, name, and model class.

    Type Parameters:
        T: The Pydantic model class for this entity type.

    Class Attributes:
        _endpoint: API endpoint path (e.g., "services", "routes").
        _entity_name: Human-readable entity name for logging.
        _model_class: Pydantic model class for deserializing responses.

    Example:
        >>> class ServiceManager(BaseEntityManager[Service]):
        ...     _endpoint = "services"
        ...     _entity_name = "service"
        ...     _model_class = Service
    """

    _endpoint: str = ""
    _entity_name: str = ""
    _model_class: type[T]

    def __init__(self, client: KongAdminClient) -> None:
        """Initialize the entity manager.

        Args:
            client: Kong Admin API client instance.
        """
        self._client = client
        self._log = logger.bind(entity=self._entity_name)

    @property
    def endpoint(self) -> str:
        """Return the API endpoint for this entity type."""
        return self._endpoint

    def list(
        self,
        *,
        tags: list[str] | None = None,
        limit: int | None = None,
        offset: str | None = None,
        **filters: Any,
    ) -> tuple[list[T], str | None]:
        """List all entities with optional filtering.

        Args:
            tags: Filter by tags (AND logic - entities must have all tags).
            limit: Maximum number of entities to return (Kong default: 100).
            offset: Pagination offset token from previous response.
            **filters: Additional entity-specific query parameters.

        Returns:
            Tuple of (list of entity models, next offset for pagination).
            The offset is None if there are no more results.

        Example:
            >>> services, next_offset = manager.list(tags=["production"], limit=10)
            >>> while next_offset:
            ...     more_services, next_offset = manager.list(offset=next_offset)
            ...     services.extend(more_services)
        """
        params: dict[str, Any] = {}
        if tags:
            params["tags"] = ",".join(tags)
        if limit:
            params["size"] = limit
        if offset:
            params["offset"] = offset
        params.update(filters)

        self._log.debug("listing_entities", **params)
        response = self._client.get(self._endpoint, params=params)

        entities = [self._model_class.model_validate(item) for item in response.get("data", [])]
        next_offset = response.get("offset")

        self._log.debug("listed_entities", count=len(entities), has_more=bool(next_offset))
        return entities, next_offset

    def get(self, id_or_name: str) -> T:
        """Get a single entity by ID or name.

        Args:
            id_or_name: Entity ID (UUID) or unique name.

        Returns:
            The entity model.

        Raises:
            KongNotFoundError: If entity doesn't exist.
        """
        self._log.debug("getting_entity", id_or_name=id_or_name)
        response = self._client.get(f"{self._endpoint}/{id_or_name}")
        entity = self._model_class.model_validate(response)
        self._log.debug("got_entity", id=entity.id)
        return entity

    def create(self, entity: T) -> T:
        """Create a new entity.

        Args:
            entity: Entity model with creation data. The id, created_at,
                and updated_at fields are ignored (assigned by Kong).

        Returns:
            The created entity with server-assigned fields populated.

        Raises:
            KongValidationError: If validation fails.
            KongDBLessWriteError: If Kong is in DB-less mode.
        """
        payload = entity.to_create_payload()
        self._log.info("creating_entity", **payload)
        response = self._client.post(self._endpoint, json=payload)
        created = self._model_class.model_validate(response)
        self._log.info("created_entity", id=created.id)
        return created

    def update(self, id_or_name: str, entity: T) -> T:
        """Update an existing entity (partial update).

        Uses PATCH semantics - only provided fields are updated.

        Args:
            id_or_name: Entity ID or name to update.
            entity: Entity model with fields to update. Only non-None
                fields will be sent to the API.

        Returns:
            The updated entity.

        Raises:
            KongNotFoundError: If entity doesn't exist.
            KongValidationError: If validation fails.
        """
        payload = entity.to_update_payload()
        self._log.info("updating_entity", id_or_name=id_or_name, **payload)
        response = self._client.patch(f"{self._endpoint}/{id_or_name}", json=payload)
        updated = self._model_class.model_validate(response)
        self._log.info("updated_entity", id=updated.id)
        return updated

    def upsert(self, id_or_name: str, entity: T) -> T:
        """Create or update an entity (upsert).

        Uses PUT semantics - creates if not exists, replaces if exists.

        Args:
            id_or_name: Entity ID or name for the upsert operation.
            entity: Entity model with complete data.

        Returns:
            The created or updated entity.
        """
        payload = entity.to_create_payload()
        self._log.info("upserting_entity", id_or_name=id_or_name, **payload)
        response = self._client.put(f"{self._endpoint}/{id_or_name}", json=payload)
        upserted = self._model_class.model_validate(response)
        self._log.info("upserted_entity", id=upserted.id)
        return upserted

    def delete(self, id_or_name: str) -> None:
        """Delete an entity.

        Args:
            id_or_name: Entity ID or name to delete.

        Raises:
            KongNotFoundError: If entity doesn't exist.
        """
        self._log.info("deleting_entity", id_or_name=id_or_name)
        self._client.delete(f"{self._endpoint}/{id_or_name}")
        self._log.info("deleted_entity", id_or_name=id_or_name)

    def exists(self, id_or_name: str) -> bool:
        """Check if an entity exists.

        Args:
            id_or_name: Entity ID or name to check.

        Returns:
            True if entity exists, False otherwise.
        """
        try:
            self.get(id_or_name)
            return True
        except KongNotFoundError:
            return False

    def count(self, *, tags: builtins.list[str] | None = None) -> int:
        """Count entities matching the filter criteria.

        Note: Kong doesn't provide a native count endpoint, so this
        fetches all entities. For large datasets, consider using
        list() with pagination instead.

        Args:
            tags: Filter by tags before counting.

        Returns:
            Total count of matching entities.
        """
        count = 0
        offset: str | None = None

        while True:
            entities, offset = self.list(tags=tags, offset=offset)
            count += len(entities)
            if not offset:
                break

        return count
