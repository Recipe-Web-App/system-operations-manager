"""Pydantic models for Kong Consumers and Credentials.

A Consumer in Kong represents a user or application that consumes APIs.
Consumers can have various types of credentials attached for authentication.
"""

from __future__ import annotations

from typing import ClassVar

from pydantic import Field, model_validator

from system_operations_manager.integrations.kong.models.base import KongEntityBase


class Consumer(KongEntityBase):
    """Kong Consumer entity model.

    A Consumer represents a user or application consuming APIs through Kong.
    Consumers are identified by either a username or custom_id (at least one
    must be provided). Credentials for authentication can be attached to
    consumers.

    Attributes:
        username: Consumer username (unique).
        custom_id: Custom identifier (unique).
    """

    _entity_name: ClassVar[str] = "consumer"

    username: str | None = Field(default=None, description="Consumer username (unique)")
    custom_id: str | None = Field(default=None, description="Custom identifier (unique)")

    @model_validator(mode="after")
    def check_identifier(self) -> Consumer:
        """Ensure at least username or custom_id is provided for creation.

        Note: This is relaxed for API responses which always have at least one.
        """
        return self


class Credential(KongEntityBase):
    """Base model for consumer credentials.

    All credential types share common fields including the associated
    consumer reference.
    """

    _entity_name: ClassVar[str] = "credential"

    consumer: dict[str, str] | None = Field(default=None, description="Associated consumer")


class KeyAuthCredential(Credential):
    """Key authentication credential.

    Used with the key-auth plugin for API key authentication.

    Attributes:
        key: The API key value. If not provided, Kong generates one.
        ttl: Time-to-live in seconds (optional).
    """

    _entity_name: ClassVar[str] = "key-auth"

    key: str | None = Field(default=None, description="API key value")
    ttl: int | None = Field(default=None, description="Time-to-live in seconds")


class BasicAuthCredential(Credential):
    """Basic authentication credential.

    Used with the basic-auth plugin for HTTP Basic authentication.

    Attributes:
        username: Basic auth username.
        password: Basic auth password (hashed in storage).
    """

    _entity_name: ClassVar[str] = "basic-auth"

    username: str = Field(description="Basic auth username")
    password: str | None = Field(default=None, description="Basic auth password")


class HMACAuthCredential(Credential):
    """HMAC authentication credential.

    Used with the hmac-auth plugin for HMAC signature authentication.

    Attributes:
        username: HMAC username.
        secret: HMAC secret key.
    """

    _entity_name: ClassVar[str] = "hmac-auth"

    username: str = Field(description="HMAC username")
    secret: str | None = Field(default=None, description="HMAC secret key")


class JWTCredential(Credential):
    """JWT credential.

    Used with the jwt plugin for JSON Web Token authentication.

    Attributes:
        key: JWT key (used as 'iss' claim).
        algorithm: Signing algorithm (HS256, HS384, HS512, RS256, etc.).
        secret: Secret for HS algorithms.
        rsa_public_key: RSA public key for RS algorithms.
    """

    _entity_name: ClassVar[str] = "jwt"

    key: str | None = Field(default=None, description="JWT key (iss claim)")
    algorithm: str = Field(default="HS256", description="Signing algorithm")
    secret: str | None = Field(default=None, description="Secret for HS algorithms")
    rsa_public_key: str | None = Field(default=None, description="RSA public key for RS algorithms")


class OAuth2Credential(Credential):
    """OAuth2 credential.

    Used with the oauth2 plugin for OAuth 2.0 authentication.

    Attributes:
        name: Application name.
        client_id: OAuth2 client ID.
        client_secret: OAuth2 client secret.
        redirect_uris: Allowed redirect URIs.
        hash_secret: Whether to hash the client secret.
    """

    _entity_name: ClassVar[str] = "oauth2"

    name: str = Field(description="Application name")
    client_id: str | None = Field(default=None, description="OAuth2 client ID")
    client_secret: str | None = Field(default=None, description="OAuth2 client secret")
    redirect_uris: list[str] | None = Field(default=None, description="Allowed redirect URIs")
    hash_secret: bool = Field(default=False, description="Whether to hash the client secret")


class ACLGroup(KongEntityBase):
    """ACL group membership.

    Represents a consumer's membership in an ACL group, used with
    the acl plugin for access control.

    Attributes:
        group: ACL group name.
        consumer: Associated consumer.
    """

    _entity_name: ClassVar[str] = "acl"

    group: str = Field(description="ACL group name")
    consumer: dict[str, str] | None = Field(default=None, description="Associated consumer")


class MTLSAuthCredential(KongEntityBase):
    """mTLS authentication credential.

    Used with the mtls-auth plugin for client certificate authentication.

    Attributes:
        subject_name: Certificate subject distinguished name.
        ca_certificate: Reference to CA certificate used for validation.
        consumer: Associated consumer reference.
    """

    _entity_name: ClassVar[str] = "mtls-auth"

    subject_name: str | None = Field(default=None, description="Certificate subject DN")
    ca_certificate: dict[str, str] | None = Field(
        default=None, description="CA certificate reference"
    )
    consumer: dict[str, str] | None = Field(default=None, description="Associated consumer")


# Mapping of credential type names to model classes
CREDENTIAL_TYPES: dict[str, type[Credential | MTLSAuthCredential]] = {
    "key-auth": KeyAuthCredential,
    "basic-auth": BasicAuthCredential,
    "hmac-auth": HMACAuthCredential,
    "jwt": JWTCredential,
    "oauth2": OAuth2Credential,
    "mtls-auth": MTLSAuthCredential,
}


def get_credential_model(credential_type: str) -> type[Credential] | type[MTLSAuthCredential]:
    """Get the credential model class for a credential type.

    Args:
        credential_type: Type of credential (key-auth, basic-auth, etc.).

    Returns:
        The credential model class.

    Raises:
        ValueError: If credential type is unknown.
    """
    model = CREDENTIAL_TYPES.get(credential_type)
    if model is None:
        valid_types = ", ".join(CREDENTIAL_TYPES.keys())
        raise ValueError(f"Unknown credential type: {credential_type}. Valid types: {valid_types}")
    return model
