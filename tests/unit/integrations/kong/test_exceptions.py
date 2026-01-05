"""Unit tests for Kong custom exceptions."""

from __future__ import annotations

import pytest

from system_operations_manager.integrations.kong.exceptions import (
    KongAPIError,
    KongAuthError,
    KongConnectionError,
    KongDBLessWriteError,
    KongEnterpriseRequiredError,
    KongNotFoundError,
    KongValidationError,
)


class TestKongAPIError:
    """Tests for KongAPIError base exception."""

    @pytest.mark.unit
    def test_api_error_message_only(self) -> None:
        """Error should store message."""
        error = KongAPIError("Something went wrong")

        assert error.message == "Something went wrong"
        assert error.status_code is None
        assert error.response_body is None
        assert error.endpoint is None

    @pytest.mark.unit
    def test_api_error_with_status_code(self) -> None:
        """Error should store status code."""
        error = KongAPIError("Server error", status_code=500)

        assert error.message == "Server error"
        assert error.status_code == 500

    @pytest.mark.unit
    def test_api_error_with_response_body(self) -> None:
        """Error should store response body."""
        body = {"error": "details", "code": 123}
        error = KongAPIError("Error", response_body=body)

        assert error.response_body == body

    @pytest.mark.unit
    def test_api_error_with_endpoint(self) -> None:
        """Error should store endpoint."""
        error = KongAPIError("Error", endpoint="/services")

        assert error.endpoint == "/services"

    @pytest.mark.unit
    def test_api_error_str_message_only(self) -> None:
        """String representation should include message."""
        error = KongAPIError("Something went wrong")

        assert str(error) == "Something went wrong"

    @pytest.mark.unit
    def test_api_error_str_with_status_code(self) -> None:
        """String representation should include status code."""
        error = KongAPIError("Server error", status_code=500)

        assert "Server error" in str(error)
        assert "(status: 500)" in str(error)

    @pytest.mark.unit
    def test_api_error_str_with_endpoint(self) -> None:
        """String representation should include endpoint."""
        error = KongAPIError("Error", endpoint="/services")

        assert "Error" in str(error)
        assert "[endpoint: /services]" in str(error)

    @pytest.mark.unit
    def test_api_error_str_with_all_fields(self) -> None:
        """String representation should include all fields."""
        error = KongAPIError(
            "Failed request",
            status_code=400,
            endpoint="/routes",
        )

        result = str(error)
        assert "Failed request" in result
        assert "(status: 400)" in result
        assert "[endpoint: /routes]" in result

    @pytest.mark.unit
    def test_api_error_is_exception(self) -> None:
        """KongAPIError should be an Exception."""
        error = KongAPIError("Error")

        assert isinstance(error, Exception)

    @pytest.mark.unit
    def test_api_error_can_be_raised(self) -> None:
        """KongAPIError should be raisable."""
        with pytest.raises(KongAPIError) as exc_info:
            raise KongAPIError("Test error", status_code=500)

        assert exc_info.value.message == "Test error"
        assert exc_info.value.status_code == 500


class TestKongConnectionError:
    """Tests for KongConnectionError exception."""

    @pytest.mark.unit
    def test_connection_error_default_message(self) -> None:
        """Connection error should have default message."""
        error = KongConnectionError()

        assert error.message == "Failed to connect to Kong Admin API"

    @pytest.mark.unit
    def test_connection_error_custom_message(self) -> None:
        """Connection error should accept custom message."""
        error = KongConnectionError("Connection refused")

        assert error.message == "Connection refused"

    @pytest.mark.unit
    def test_connection_error_with_endpoint(self) -> None:
        """Connection error should store endpoint."""
        error = KongConnectionError("Timeout", endpoint="/status")

        assert error.endpoint == "/status"

    @pytest.mark.unit
    def test_connection_error_with_original_error(self) -> None:
        """Connection error should store original exception."""
        original = ConnectionRefusedError("Connection refused")
        error = KongConnectionError("Failed", original_error=original)

        assert error.original_error is original

    @pytest.mark.unit
    def test_connection_error_inherits_from_api_error(self) -> None:
        """KongConnectionError should inherit from KongAPIError."""
        assert issubclass(KongConnectionError, KongAPIError)

    @pytest.mark.unit
    def test_connection_error_no_status_code(self) -> None:
        """Connection error should not have status code by default."""
        error = KongConnectionError()

        assert error.status_code is None


class TestKongAuthError:
    """Tests for KongAuthError exception."""

    @pytest.mark.unit
    def test_auth_error_default_message(self) -> None:
        """Auth error should have default message."""
        error = KongAuthError()

        assert error.message == "Authentication to Kong Admin API failed"

    @pytest.mark.unit
    def test_auth_error_default_status_code(self) -> None:
        """Auth error should default to 401 status code."""
        error = KongAuthError()

        assert error.status_code == 401

    @pytest.mark.unit
    def test_auth_error_custom_status_code(self) -> None:
        """Auth error should accept custom status code (e.g., 403)."""
        error = KongAuthError(status_code=403)

        assert error.status_code == 403

    @pytest.mark.unit
    def test_auth_error_custom_message(self) -> None:
        """Auth error should accept custom message."""
        error = KongAuthError("Invalid API key")

        assert error.message == "Invalid API key"

    @pytest.mark.unit
    def test_auth_error_with_response_body(self) -> None:
        """Auth error should store response body."""
        body = {"message": "Unauthorized"}
        error = KongAuthError(response_body=body)

        assert error.response_body == body

    @pytest.mark.unit
    def test_auth_error_with_endpoint(self) -> None:
        """Auth error should store endpoint."""
        error = KongAuthError(endpoint="/services")

        assert error.endpoint == "/services"

    @pytest.mark.unit
    def test_auth_error_inherits_from_api_error(self) -> None:
        """KongAuthError should inherit from KongAPIError."""
        assert issubclass(KongAuthError, KongAPIError)


class TestKongNotFoundError:
    """Tests for KongNotFoundError exception."""

    @pytest.mark.unit
    def test_not_found_error_default_message(self) -> None:
        """Not found error should have default message."""
        error = KongNotFoundError()

        assert error.message == "Kong resource not found"

    @pytest.mark.unit
    def test_not_found_error_with_resource_type_and_id(self) -> None:
        """Not found error should format message with resource info."""
        error = KongNotFoundError(resource_type="service", resource_id="my-service")

        assert error.message == "service 'my-service' not found"
        assert error.resource_type == "service"
        assert error.resource_id == "my-service"

    @pytest.mark.unit
    def test_not_found_error_status_code_is_404(self) -> None:
        """Not found error should always have 404 status code."""
        error = KongNotFoundError()

        assert error.status_code == 404

    @pytest.mark.unit
    def test_not_found_error_with_response_body(self) -> None:
        """Not found error should store response body."""
        body = {"message": "Not found"}
        error = KongNotFoundError(response_body=body)

        assert error.response_body == body

    @pytest.mark.unit
    def test_not_found_error_with_endpoint(self) -> None:
        """Not found error should store endpoint."""
        error = KongNotFoundError(endpoint="/services/missing")

        assert error.endpoint == "/services/missing"

    @pytest.mark.unit
    def test_not_found_error_inherits_from_api_error(self) -> None:
        """KongNotFoundError should inherit from KongAPIError."""
        assert issubclass(KongNotFoundError, KongAPIError)

    @pytest.mark.unit
    def test_not_found_error_custom_message_without_resource(self) -> None:
        """Not found error should use custom message when no resource info."""
        error = KongNotFoundError(message="Custom not found message")

        assert error.message == "Custom not found message"


class TestKongValidationError:
    """Tests for KongValidationError exception."""

    @pytest.mark.unit
    def test_validation_error_default_message(self) -> None:
        """Validation error should have default message."""
        error = KongValidationError()

        assert error.message == "Invalid request data"

    @pytest.mark.unit
    def test_validation_error_custom_message(self) -> None:
        """Validation error should accept custom message."""
        error = KongValidationError("Schema validation failed")

        assert error.message == "Schema validation failed"

    @pytest.mark.unit
    def test_validation_error_with_validation_errors(self) -> None:
        """Validation error should store field validation errors."""
        errors = {"name": "is required", "host": "must be a string"}
        error = KongValidationError(validation_errors=errors)

        assert error.validation_errors == errors

    @pytest.mark.unit
    def test_validation_error_empty_validation_errors_default(self) -> None:
        """Validation error should default to empty dict for validation_errors."""
        error = KongValidationError()

        assert error.validation_errors == {}

    @pytest.mark.unit
    def test_validation_error_status_code_is_400(self) -> None:
        """Validation error should always have 400 status code."""
        error = KongValidationError()

        assert error.status_code == 400

    @pytest.mark.unit
    def test_validation_error_with_response_body(self) -> None:
        """Validation error should store response body."""
        body = {"message": "schema violation", "fields": {}}
        error = KongValidationError(response_body=body)

        assert error.response_body == body

    @pytest.mark.unit
    def test_validation_error_with_endpoint(self) -> None:
        """Validation error should store endpoint."""
        error = KongValidationError(endpoint="/services")

        assert error.endpoint == "/services"

    @pytest.mark.unit
    def test_validation_error_inherits_from_api_error(self) -> None:
        """KongValidationError should inherit from KongAPIError."""
        assert issubclass(KongValidationError, KongAPIError)


class TestKongDBLessWriteError:
    """Tests for KongDBLessWriteError exception."""

    @pytest.mark.unit
    def test_dbless_error_default_message(self) -> None:
        """DB-less error should have default message."""
        error = KongDBLessWriteError()

        assert error.message == "Write operations are not allowed in DB-less mode"

    @pytest.mark.unit
    def test_dbless_error_custom_message(self) -> None:
        """DB-less error should accept custom message."""
        error = KongDBLessWriteError("Cannot create service in DB-less mode")

        assert error.message == "Cannot create service in DB-less mode"

    @pytest.mark.unit
    def test_dbless_error_with_endpoint(self) -> None:
        """DB-less error should store endpoint."""
        error = KongDBLessWriteError(endpoint="/services")

        assert error.endpoint == "/services"

    @pytest.mark.unit
    def test_dbless_error_status_code_is_405(self) -> None:
        """DB-less error should always have 405 status code."""
        error = KongDBLessWriteError()

        assert error.status_code == 405

    @pytest.mark.unit
    def test_dbless_error_inherits_from_api_error(self) -> None:
        """KongDBLessWriteError should inherit from KongAPIError."""
        assert issubclass(KongDBLessWriteError, KongAPIError)


class TestKongEnterpriseRequiredError:
    """Tests for KongEnterpriseRequiredError exception."""

    @pytest.mark.unit
    def test_enterprise_error_with_feature(self) -> None:
        """Enterprise error should format message with feature name."""
        error = KongEnterpriseRequiredError(feature="workspaces")

        assert error.feature == "workspaces"
        assert "workspaces" in error.message
        assert "Kong Enterprise is required" in error.message

    @pytest.mark.unit
    def test_enterprise_error_custom_message(self) -> None:
        """Enterprise error should accept custom message."""
        error = KongEnterpriseRequiredError(
            feature="rbac",
            message="RBAC requires Kong Enterprise license",
        )

        assert error.message == "RBAC requires Kong Enterprise license"
        assert error.feature == "rbac"

    @pytest.mark.unit
    def test_enterprise_error_feature_attribute(self) -> None:
        """Enterprise error should store feature attribute."""
        error = KongEnterpriseRequiredError(feature="vaults")

        assert error.feature == "vaults"

    @pytest.mark.unit
    def test_enterprise_error_no_status_code(self) -> None:
        """Enterprise error should not have status code."""
        error = KongEnterpriseRequiredError(feature="workspaces")

        assert error.status_code is None

    @pytest.mark.unit
    def test_enterprise_error_inherits_from_api_error(self) -> None:
        """KongEnterpriseRequiredError should inherit from KongAPIError."""
        assert issubclass(KongEnterpriseRequiredError, KongAPIError)

    @pytest.mark.unit
    def test_enterprise_error_can_be_raised(self) -> None:
        """KongEnterpriseRequiredError should be raisable."""
        with pytest.raises(KongEnterpriseRequiredError) as exc_info:
            raise KongEnterpriseRequiredError(feature="developer_portal")

        assert exc_info.value.feature == "developer_portal"
