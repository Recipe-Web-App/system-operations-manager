"""Key managers for Kong cryptographic key entities.

This module provides managers for Kong key-related entities:
- KeySetManager: Collections of cryptographic keys
- KeyManager: Individual cryptographic keys for JWT, encryption, etc.
"""

from __future__ import annotations

from system_operations_manager.integrations.kong.models.key import (
    Key,
    KeySet,
)
from system_operations_manager.services.kong.base import BaseEntityManager


class KeySetManager(BaseEntityManager[KeySet]):
    """Manager for Kong KeySet entities.

    Key sets group related keys together, typically used for key rotation
    scenarios where multiple keys may be valid at the same time.

    Example:
        >>> manager = KeySetManager(client)
        >>> key_set = KeySet(name="jwt-signing-keys")
        >>> created = manager.create(key_set)
        >>> keys = manager.get_keys(created.id)
    """

    _endpoint = "key-sets"
    _entity_name = "key_set"
    _model_class = KeySet

    def get_keys(self, key_set_id_or_name: str) -> list[Key]:
        """Get all keys in a key set.

        Args:
            key_set_id_or_name: KeySet ID or name.

        Returns:
            List of Key entities in the key set.
        """
        self._log.debug("getting_key_set_keys", key_set=key_set_id_or_name)
        response = self._client.get(f"key-sets/{key_set_id_or_name}/keys")
        keys = [Key.model_validate(k) for k in response.get("data", [])]
        self._log.debug("got_key_set_keys", key_set=key_set_id_or_name, count=len(keys))
        return keys


class KeyManager(BaseEntityManager[Key]):
    """Manager for Kong Key entities.

    Keys are used for various cryptographic operations such as JWT
    signature verification, encryption, and decryption.

    Example:
        >>> manager = KeyManager(client)
        >>> key = Key(
        ...     kid="my-key-id",
        ...     set=KongEntityReference.from_name("jwt-signing-keys"),
        ...     jwk='{"kty":"RSA","n":"...","e":"AQAB"}',
        ... )
        >>> created = manager.create(key)
    """

    _endpoint = "keys"
    _entity_name = "key"
    _model_class = Key

    def list_by_key_set(self, key_set_id_or_name: str) -> list[Key]:
        """List all keys in a specific key set.

        Args:
            key_set_id_or_name: KeySet ID or name.

        Returns:
            List of Key entities in the key set.
        """
        self._log.debug("listing_keys_by_key_set", key_set=key_set_id_or_name)
        response = self._client.get(f"key-sets/{key_set_id_or_name}/keys")
        keys = [Key.model_validate(k) for k in response.get("data", [])]
        self._log.debug("listed_keys_by_key_set", key_set=key_set_id_or_name, count=len(keys))
        return keys

    def get_by_kid(self, kid: str) -> Key | None:
        """Get a key by its Key ID (kid).

        Args:
            kid: Key ID (JWK 'kid' field).

        Returns:
            The key if found, None otherwise.
        """
        self._log.debug("getting_key_by_kid", kid=kid)
        keys, _ = self.list()
        for key in keys:
            if key.kid == kid:
                return key
        return None
