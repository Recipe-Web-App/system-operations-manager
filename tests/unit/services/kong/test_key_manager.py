"""Unit tests for Kong Key managers."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from system_operations_manager.integrations.kong.models.base import KongEntityReference
from system_operations_manager.integrations.kong.models.key import Key, KeySet
from system_operations_manager.services.kong.key_manager import KeyManager, KeySetManager


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock Kong Admin client."""
    return MagicMock()


class TestKeySetManagerInit:
    """Tests for KeySetManager initialization."""

    @pytest.mark.unit
    def test_key_set_manager_initialization(self, mock_client: MagicMock) -> None:
        """Manager should initialize with client."""
        manager = KeySetManager(mock_client)

        assert manager._client is mock_client
        assert manager._endpoint == "key-sets"
        assert manager._entity_name == "key_set"
        assert manager._model_class is KeySet


class TestKeySetManagerCRUD:
    """Tests for KeySetManager CRUD operations."""

    @pytest.fixture
    def manager(self, mock_client: MagicMock) -> KeySetManager:
        """Create a KeySetManager with mocked client."""
        return KeySetManager(mock_client)

    @pytest.mark.unit
    def test_list_key_sets(self, manager: KeySetManager, mock_client: MagicMock) -> None:
        """list should return key sets."""
        mock_client.get.return_value = {
            "data": [
                {
                    "id": "keyset-1",
                    "name": "jwt-keys",
                    "tags": ["jwt"],
                },
                {
                    "id": "keyset-2",
                    "name": "encryption-keys",
                    "tags": ["encryption"],
                },
            ]
        }

        key_sets, _offset = manager.list()

        assert len(key_sets) == 2
        assert key_sets[0].name == "jwt-keys"
        assert key_sets[1].name == "encryption-keys"
        mock_client.get.assert_called_once()

    @pytest.mark.unit
    def test_list_key_sets_with_tags(self, manager: KeySetManager, mock_client: MagicMock) -> None:
        """list should filter by tags."""
        mock_client.get.return_value = {
            "data": [
                {
                    "id": "keyset-1",
                    "name": "jwt-keys",
                    "tags": ["jwt"],
                },
            ]
        }

        key_sets, _offset = manager.list(tags=["jwt"])

        assert len(key_sets) == 1
        call_args = mock_client.get.call_args
        assert "tags" in call_args[1]["params"]

    @pytest.mark.unit
    def test_get_key_set(self, manager: KeySetManager, mock_client: MagicMock) -> None:
        """get should return key set by name or ID."""
        mock_client.get.return_value = {
            "id": "keyset-1",
            "name": "jwt-keys",
            "tags": ["jwt"],
        }

        key_set = manager.get("jwt-keys")

        assert key_set.name == "jwt-keys"
        mock_client.get.assert_called_once_with("key-sets/jwt-keys")

    @pytest.mark.unit
    def test_create_key_set(self, manager: KeySetManager, mock_client: MagicMock) -> None:
        """create should create a new key set."""
        mock_client.post.return_value = {
            "id": "keyset-new",
            "name": "new-key-set",
            "tags": ["new"],
            "created_at": 1234567890,
        }

        key_set = KeySet(
            name="new-key-set",
            tags=["new"],
        )
        created = manager.create(key_set)

        assert created.name == "new-key-set"
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "key-sets"

    @pytest.mark.unit
    def test_update_key_set(self, manager: KeySetManager, mock_client: MagicMock) -> None:
        """update should update an existing key set."""
        mock_client.patch.return_value = {
            "id": "keyset-1",
            "name": "jwt-keys",
            "tags": ["jwt", "updated"],
        }

        key_set = KeySet(
            name="jwt-keys",
            tags=["jwt", "updated"],
        )
        updated = manager.update("keyset-1", key_set)

        assert updated.tags == ["jwt", "updated"]
        mock_client.patch.assert_called_once()

    @pytest.mark.unit
    def test_delete_key_set(self, manager: KeySetManager, mock_client: MagicMock) -> None:
        """delete should remove key set."""
        manager.delete("jwt-keys")

        mock_client.delete.assert_called_once_with("key-sets/jwt-keys")

    @pytest.mark.unit
    def test_exists_returns_true(self, manager: KeySetManager, mock_client: MagicMock) -> None:
        """exists should return True when key set exists."""
        mock_client.get.return_value = {
            "id": "keyset-1",
            "name": "jwt-keys",
        }

        result = manager.exists("jwt-keys")

        assert result is True

    @pytest.mark.unit
    def test_get_keys(self, manager: KeySetManager, mock_client: MagicMock) -> None:
        """get_keys should return keys for a key set."""
        mock_client.get.return_value = {
            "data": [
                {
                    "id": "key-1",
                    "kid": "key-id-1",
                    "name": "signing-key",
                    "set": {"id": "keyset-1"},
                },
                {
                    "id": "key-2",
                    "kid": "key-id-2",
                    "name": "verification-key",
                    "set": {"id": "keyset-1"},
                },
            ]
        }

        keys = manager.get_keys("keyset-1")

        assert len(keys) == 2
        assert keys[0].kid == "key-id-1"
        assert keys[1].kid == "key-id-2"
        mock_client.get.assert_called_once_with("key-sets/keyset-1/keys")


class TestKeyManagerInit:
    """Tests for KeyManager initialization."""

    @pytest.mark.unit
    def test_key_manager_initialization(self, mock_client: MagicMock) -> None:
        """Manager should initialize with client."""
        manager = KeyManager(mock_client)

        assert manager._client is mock_client
        assert manager._endpoint == "keys"
        assert manager._entity_name == "key"
        assert manager._model_class is Key


class TestKeyManagerCRUD:
    """Tests for KeyManager CRUD operations."""

    @pytest.fixture
    def manager(self, mock_client: MagicMock) -> KeyManager:
        """Create a KeyManager with mocked client."""
        return KeyManager(mock_client)

    @pytest.mark.unit
    def test_list_keys(self, manager: KeyManager, mock_client: MagicMock) -> None:
        """list should return keys."""
        mock_client.get.return_value = {
            "data": [
                {
                    "id": "key-1",
                    "kid": "key-id-1",
                    "name": "signing-key",
                    "set": {"id": "keyset-1"},
                    "tags": ["jwt"],
                },
                {
                    "id": "key-2",
                    "kid": "key-id-2",
                    "name": "encryption-key",
                    "set": {"id": "keyset-2"},
                    "tags": ["encryption"],
                },
            ]
        }

        keys, _offset = manager.list()

        assert len(keys) == 2
        assert keys[0].kid == "key-id-1"
        assert keys[1].kid == "key-id-2"
        mock_client.get.assert_called_once()

    @pytest.mark.unit
    def test_get_key(self, manager: KeyManager, mock_client: MagicMock) -> None:
        """get should return key by ID."""
        mock_client.get.return_value = {
            "id": "key-1",
            "kid": "key-id-1",
            "name": "signing-key",
            "set": {"id": "keyset-1"},
            "tags": ["jwt"],
        }

        key = manager.get("key-1")

        assert key.kid == "key-id-1"
        assert key.name == "signing-key"
        mock_client.get.assert_called_once_with("keys/key-1")

    @pytest.mark.unit
    def test_create_key(self, manager: KeyManager, mock_client: MagicMock) -> None:
        """create should create a new key."""
        mock_client.post.return_value = {
            "id": "key-new",
            "kid": "new-key-id",
            "name": "new-signing-key",
            "set": {"id": "keyset-1"},
            "tags": ["new"],
            "created_at": 1234567890,
        }

        key = Key(
            kid="new-key-id",
            name="new-signing-key",
            set=KongEntityReference(id="keyset-1"),
            tags=["new"],
        )
        created = manager.create(key)

        assert created.kid == "new-key-id"
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "keys"

    @pytest.mark.unit
    def test_create_key_with_jwk(self, manager: KeyManager, mock_client: MagicMock) -> None:
        """create should handle JWK format."""
        jwk_data = '{"kty":"RSA","n":"...","e":"AQAB"}'
        mock_client.post.return_value = {
            "id": "key-new",
            "kid": "jwk-key-id",
            "name": "jwk-key",
            "jwk": jwk_data,
            "created_at": 1234567890,
        }

        key = Key(
            kid="jwk-key-id",
            name="jwk-key",
            jwk=jwk_data,
        )
        created = manager.create(key)

        assert created.jwk == jwk_data
        mock_client.post.assert_called_once()

    @pytest.mark.unit
    def test_create_key_with_pem(self, manager: KeyManager, mock_client: MagicMock) -> None:
        """create should handle PEM format."""
        pem_data = {
            "public_key": "-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----",
            "private_key": "-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----",
        }
        mock_client.post.return_value = {
            "id": "key-new",
            "kid": "pem-key-id",
            "name": "pem-key",
            "pem": pem_data,
            "created_at": 1234567890,
        }

        key = Key(
            kid="pem-key-id",
            name="pem-key",
            pem=pem_data,
        )
        created = manager.create(key)

        assert created.pem == pem_data
        mock_client.post.assert_called_once()

    @pytest.mark.unit
    def test_update_key(self, manager: KeyManager, mock_client: MagicMock) -> None:
        """update should update an existing key."""
        mock_client.patch.return_value = {
            "id": "key-1",
            "kid": "key-id-1",
            "name": "updated-signing-key",
            "tags": ["updated"],
        }

        key = Key(
            kid="key-id-1",
            name="updated-signing-key",
            tags=["updated"],
        )
        updated = manager.update("key-1", key)

        assert updated.name == "updated-signing-key"
        mock_client.patch.assert_called_once()

    @pytest.mark.unit
    def test_delete_key(self, manager: KeyManager, mock_client: MagicMock) -> None:
        """delete should remove key."""
        manager.delete("key-1")

        mock_client.delete.assert_called_once_with("keys/key-1")

    @pytest.mark.unit
    def test_exists_returns_true(self, manager: KeyManager, mock_client: MagicMock) -> None:
        """exists should return True when key exists."""
        mock_client.get.return_value = {
            "id": "key-1",
            "kid": "key-id-1",
        }

        result = manager.exists("key-1")

        assert result is True


class TestKeyIdentifier:
    """Tests for Key identifier property."""

    @pytest.mark.unit
    def test_key_identifier_with_name(self) -> None:
        """Key identifier should prefer name."""
        key = Key(kid="key-id-1", name="my-key")
        assert key.identifier == "my-key"

    @pytest.mark.unit
    def test_key_identifier_without_name(self) -> None:
        """Key identifier should fall back to kid."""
        key = Key(kid="key-id-1")
        assert key.identifier == "key-id-1"


class TestKeySetIdentifier:
    """Tests for KeySet identifier property."""

    @pytest.mark.unit
    def test_key_set_identifier(self) -> None:
        """KeySet identifier should return name."""
        key_set = KeySet(name="jwt-keys")
        assert key_set.identifier == "jwt-keys"
