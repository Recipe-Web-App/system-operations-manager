"""Consumer manager for Kong Consumers.

This module provides the ConsumerManager class for managing Kong Consumer
entities and their associated credentials through the Admin API.
"""

from __future__ import annotations

from typing import Any

from system_operations_manager.integrations.kong.models.consumer import (
    ACLGroup,
    Consumer,
    Credential,
    get_credential_model,
)
from system_operations_manager.services.kong.base import BaseEntityManager


class ConsumerManager(BaseEntityManager[Consumer]):
    """Manager for Kong Consumer entities.

    Extends BaseEntityManager with consumer-specific operations
    including credential and ACL management.

    Example:
        >>> manager = ConsumerManager(client)
        >>> consumer = Consumer(username="my-user")
        >>> created = manager.create(consumer)
        >>> manager.add_credential(created.id, "key-auth", {"key": "my-api-key"})
    """

    _endpoint = "consumers"
    _entity_name = "consumer"
    _model_class = Consumer

    # Credential type to API endpoint mapping
    CREDENTIAL_ENDPOINTS: dict[str, str] = {
        "key-auth": "key-auth",
        "basic-auth": "basic-auth",
        "hmac-auth": "hmac-auth",
        "jwt": "jwt",
        "oauth2": "oauth2",
        "acls": "acls",
    }

    def list_credentials(
        self,
        consumer_id_or_name: str,
        credential_type: str,
    ) -> list[Credential]:
        """List credentials of a specific type for a consumer.

        Args:
            consumer_id_or_name: Consumer ID or username.
            credential_type: Type of credential (key-auth, jwt, etc.).

        Returns:
            List of credential objects.

        Raises:
            ValueError: If credential type is unknown.
        """
        endpoint = self._get_credential_endpoint(credential_type)
        self._log.debug(
            "listing_credentials",
            consumer=consumer_id_or_name,
            type=credential_type,
        )

        response = self._client.get(f"consumers/{consumer_id_or_name}/{endpoint}")
        model_class = get_credential_model(credential_type)
        credentials = [model_class.model_validate(c) for c in response.get("data", [])]

        self._log.debug(
            "listed_credentials",
            consumer=consumer_id_or_name,
            type=credential_type,
            count=len(credentials),
        )
        return credentials

    def add_credential(
        self,
        consumer_id_or_name: str,
        credential_type: str,
        data: dict[str, Any],
    ) -> Credential:
        """Add a credential to a consumer.

        Args:
            consumer_id_or_name: Consumer ID or username.
            credential_type: Type of credential (key-auth, jwt, etc.).
            data: Credential configuration data.

        Returns:
            Created credential object.

        Raises:
            ValueError: If credential type is unknown.
        """
        endpoint = self._get_credential_endpoint(credential_type)
        self._log.info(
            "adding_credential",
            consumer=consumer_id_or_name,
            type=credential_type,
        )

        response = self._client.post(
            f"consumers/{consumer_id_or_name}/{endpoint}",
            json=data,
        )
        model_class = get_credential_model(credential_type)
        credential = model_class.model_validate(response)

        self._log.info(
            "added_credential",
            consumer=consumer_id_or_name,
            type=credential_type,
            id=credential.id,
        )
        return credential

    def get_credential(
        self,
        consumer_id_or_name: str,
        credential_type: str,
        credential_id: str,
    ) -> Credential:
        """Get a specific credential.

        Args:
            consumer_id_or_name: Consumer ID or username.
            credential_type: Type of credential.
            credential_id: Credential ID.

        Returns:
            The credential object.
        """
        endpoint = self._get_credential_endpoint(credential_type)
        self._log.debug(
            "getting_credential",
            consumer=consumer_id_or_name,
            type=credential_type,
            id=credential_id,
        )

        response = self._client.get(f"consumers/{consumer_id_or_name}/{endpoint}/{credential_id}")
        model_class = get_credential_model(credential_type)
        return model_class.model_validate(response)

    def delete_credential(
        self,
        consumer_id_or_name: str,
        credential_type: str,
        credential_id: str,
    ) -> None:
        """Delete a credential from a consumer.

        Args:
            consumer_id_or_name: Consumer ID or username.
            credential_type: Type of credential.
            credential_id: Credential ID.
        """
        endpoint = self._get_credential_endpoint(credential_type)
        self._log.info(
            "deleting_credential",
            consumer=consumer_id_or_name,
            type=credential_type,
            id=credential_id,
        )

        self._client.delete(f"consumers/{consumer_id_or_name}/{endpoint}/{credential_id}")

        self._log.info(
            "deleted_credential",
            consumer=consumer_id_or_name,
            type=credential_type,
            id=credential_id,
        )

    def list_acl_groups(self, consumer_id_or_name: str) -> list[ACLGroup]:
        """List ACL groups for a consumer.

        Args:
            consumer_id_or_name: Consumer ID or username.

        Returns:
            List of ACL group memberships.
        """
        self._log.debug("listing_acl_groups", consumer=consumer_id_or_name)
        response = self._client.get(f"consumers/{consumer_id_or_name}/acls")
        groups = [ACLGroup.model_validate(g) for g in response.get("data", [])]
        self._log.debug(
            "listed_acl_groups",
            consumer=consumer_id_or_name,
            count=len(groups),
        )
        return groups

    def add_to_acl_group(
        self,
        consumer_id_or_name: str,
        group: str,
        tags: list[str] | None = None,
    ) -> ACLGroup:
        """Add consumer to an ACL group.

        Args:
            consumer_id_or_name: Consumer ID or username.
            group: ACL group name.
            tags: Optional tags.

        Returns:
            Created ACL group membership.
        """
        self._log.info(
            "adding_to_acl_group",
            consumer=consumer_id_or_name,
            group=group,
        )

        data: dict[str, Any] = {"group": group}
        if tags:
            data["tags"] = tags

        response = self._client.post(
            f"consumers/{consumer_id_or_name}/acls",
            json=data,
        )
        acl = ACLGroup.model_validate(response)

        self._log.info(
            "added_to_acl_group",
            consumer=consumer_id_or_name,
            group=group,
            id=acl.id,
        )
        return acl

    def remove_from_acl_group(
        self,
        consumer_id_or_name: str,
        acl_id: str,
    ) -> None:
        """Remove consumer from an ACL group.

        Args:
            consumer_id_or_name: Consumer ID or username.
            acl_id: ACL entry ID.
        """
        self._log.info(
            "removing_from_acl_group",
            consumer=consumer_id_or_name,
            acl_id=acl_id,
        )
        self._client.delete(f"consumers/{consumer_id_or_name}/acls/{acl_id}")
        self._log.info(
            "removed_from_acl_group",
            consumer=consumer_id_or_name,
            acl_id=acl_id,
        )

    def get_plugins(self, consumer_id_or_name: str) -> list[dict[str, Any]]:
        """Get all plugins associated with a consumer.

        Args:
            consumer_id_or_name: Consumer ID or username.

        Returns:
            List of plugin configuration dictionaries.
        """
        self._log.debug("getting_consumer_plugins", consumer=consumer_id_or_name)
        response = self._client.get(f"consumers/{consumer_id_or_name}/plugins")
        plugins: list[dict[str, Any]] = response.get("data", [])
        self._log.debug(
            "got_consumer_plugins",
            consumer=consumer_id_or_name,
            count=len(plugins),
        )
        return plugins

    def _get_credential_endpoint(self, credential_type: str) -> str:
        """Get the API endpoint for a credential type.

        Args:
            credential_type: Type of credential.

        Returns:
            API endpoint path.

        Raises:
            ValueError: If credential type is unknown.
        """
        endpoint = self.CREDENTIAL_ENDPOINTS.get(credential_type)
        if endpoint is None:
            valid_types = ", ".join(self.CREDENTIAL_ENDPOINTS.keys())
            raise ValueError(
                f"Unknown credential type: {credential_type}. Valid types: {valid_types}"
            )
        return endpoint
