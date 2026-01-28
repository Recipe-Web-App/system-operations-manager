"""Integration tests for ConsumerManager."""

from __future__ import annotations

import pytest

from system_operations_manager.integrations.kong.exceptions import KongNotFoundError
from system_operations_manager.services.kong.consumer_manager import ConsumerManager


@pytest.mark.integration
@pytest.mark.kong
class TestConsumerManagerList:
    """Test consumer listing operations."""

    def test_list_all_consumers(
        self,
        consumer_manager: ConsumerManager,
    ) -> None:
        """list should return consumers from declarative config."""
        consumers, _ = consumer_manager.list()

        assert len(consumers) >= 1
        usernames = [c.username for c in consumers]
        assert "test-user" in usernames

    def test_list_with_pagination(
        self,
        consumer_manager: ConsumerManager,
    ) -> None:
        """list should support pagination."""
        consumers, _ = consumer_manager.list(limit=1)

        assert len(consumers) <= 1

    def test_list_returns_expected_consumers(
        self,
        consumer_manager: ConsumerManager,
    ) -> None:
        """list should return both configured consumers."""
        consumers, _ = consumer_manager.list()

        usernames = [c.username for c in consumers]
        assert "test-user" in usernames
        assert "api-consumer" in usernames


@pytest.mark.integration
@pytest.mark.kong
class TestConsumerManagerGet:
    """Test consumer retrieval operations."""

    def test_get_consumer_by_username(
        self,
        consumer_manager: ConsumerManager,
    ) -> None:
        """get should retrieve consumer by username."""
        consumer = consumer_manager.get("test-user")

        assert consumer.username == "test-user"
        assert consumer.custom_id == "test-custom-id"

    def test_get_api_consumer(
        self,
        consumer_manager: ConsumerManager,
    ) -> None:
        """get should retrieve api-consumer."""
        consumer = consumer_manager.get("api-consumer")

        assert consumer.username == "api-consumer"

    def test_get_nonexistent_consumer_raises(
        self,
        consumer_manager: ConsumerManager,
    ) -> None:
        """get should raise KongNotFoundError for missing consumer."""
        with pytest.raises(KongNotFoundError):
            consumer_manager.get("nonexistent-consumer")

    def test_exists_returns_true_for_existing(
        self,
        consumer_manager: ConsumerManager,
    ) -> None:
        """exists should return True for existing consumer."""
        assert consumer_manager.exists("test-user") is True

    def test_exists_returns_false_for_missing(
        self,
        consumer_manager: ConsumerManager,
    ) -> None:
        """exists should return False for missing consumer."""
        assert consumer_manager.exists("nonexistent") is False


@pytest.mark.integration
@pytest.mark.kong
class TestConsumerCredentials:
    """Test consumer credential operations."""

    def test_list_keyauth_credentials(
        self,
        consumer_manager: ConsumerManager,
    ) -> None:
        """list_credentials should return key-auth credentials."""
        creds = consumer_manager.list_credentials("api-consumer", "key-auth")

        assert len(creds) >= 1
        # Check that the test API key exists
        keys = [getattr(c, "key", None) for c in creds]
        assert "test-api-key" in keys

    def test_list_credentials_empty_for_consumer_without_creds(
        self,
        consumer_manager: ConsumerManager,
    ) -> None:
        """list_credentials should return empty for consumer without credentials."""
        creds = consumer_manager.list_credentials("test-user", "key-auth")

        # test-user has no key-auth credentials
        assert isinstance(creds, list)
        assert len(creds) == 0


@pytest.mark.integration
@pytest.mark.kong
class TestConsumerACLGroups:
    """Test consumer ACL group operations."""

    def test_list_acl_groups_empty(
        self,
        consumer_manager: ConsumerManager,
    ) -> None:
        """list_acl_groups should return empty for consumer without ACLs."""
        acls = consumer_manager.list_acl_groups("test-user")

        # test-user has no ACL groups in declarative config
        assert isinstance(acls, list)


@pytest.mark.integration
@pytest.mark.kong
class TestConsumerPlugins:
    """Test consumer plugin operations."""

    def test_get_plugins_for_consumer(
        self,
        consumer_manager: ConsumerManager,
    ) -> None:
        """get_plugins should return plugins for consumer."""
        plugins = consumer_manager.get_plugins("test-user")

        # May be empty if no plugins configured on consumer
        assert isinstance(plugins, list)

    def test_count_consumers(
        self,
        consumer_manager: ConsumerManager,
    ) -> None:
        """count should return total number of consumers."""
        count = consumer_manager.count()

        assert count >= 2  # test-user and api-consumer
