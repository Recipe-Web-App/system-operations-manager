"""Key and KeySet models for Kong entities.

This module provides models for cryptographic keys and key sets used
for JWT verification, encryption, and other cryptographic operations in Kong.
"""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import Field

from system_operations_manager.integrations.kong.models.base import (
    KongEntityBase,
    KongEntityReference,
)


class KeySet(KongEntityBase):
    """Collection of cryptographic keys.

    Key sets group related keys together, typically used for key rotation
    scenarios where multiple keys may be valid at the same time.

    Attributes:
        name: Unique name for the key set.

    Example:
        >>> key_set = KeySet(
        ...     name="jwt-signing-keys",
        ...     tags=["jwt", "production"]
        ... )
    """

    _entity_name: ClassVar[str] = "key_set"

    name: str = Field(..., description="Unique name for the key set")

    @property
    def identifier(self) -> str:
        """Human-readable identifier for this key set."""
        return self.name


class Key(KongEntityBase):
    """Cryptographic key for JWT, encryption, etc.

    Keys are used for various cryptographic operations such as JWT
    signature verification, encryption, and decryption.

    Attributes:
        set: Reference to the key set this key belongs to.
        name: Optional name for the key.
        kid: Key ID (JWK 'kid' field), must be unique.
        jwk: JWK (JSON Web Key) representation of the key.
        pem: PEM-encoded key data with 'public_key' and optionally 'private_key'.

    Example:
        >>> key = Key(
        ...     kid="my-key-id",
        ...     set=KongEntityReference.from_name("jwt-signing-keys"),
        ...     jwk='{"kty":"RSA","n":"...","e":"AQAB"}',
        ... )
    """

    _entity_name: ClassVar[str] = "key"

    set: KongEntityReference | None = Field(
        default=None,
        description="Reference to the key set this key belongs to",
    )
    name: str | None = Field(
        default=None,
        description="Optional name for the key",
    )
    kid: str = Field(..., description="Key ID (JWK 'kid' field)")
    jwk: str | None = Field(
        default=None,
        description="JWK (JSON Web Key) representation",
    )
    pem: dict[str, str] | None = Field(
        default=None,
        description="PEM-encoded key data with 'public_key' and optionally 'private_key'",
    )

    @property
    def identifier(self) -> str:
        """Human-readable identifier for this key."""
        if self.name:
            return self.name
        return self.kid

    def to_create_payload(self) -> dict[str, Any]:
        """Convert model to payload for create operations.

        Handles the 'set' field reference conversion.
        """
        exclude_fields = {"id", "created_at", "updated_at"}
        payload = {
            k: v for k, v in self.model_dump(exclude=exclude_fields).items() if v is not None
        }
        # Ensure set reference is properly formatted
        if self.set and isinstance(payload.get("set"), dict):
            # Keep as-is, it's already a dict from model_dump
            pass
        return payload
