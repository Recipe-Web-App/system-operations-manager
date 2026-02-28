"""Unit tests for Kong command base utilities."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import typer

from system_operations_manager.integrations.kong.exceptions import (
    KongAPIError,
    KongAuthError,
    KongConnectionError,
    KongDBLessWriteError,
    KongNotFoundError,
    KongValidationError,
)
from system_operations_manager.plugins.kong.commands.base import (
    _parse_config_value,
    _set_nested,
    confirm_action,
    confirm_delete,
    handle_kong_error,
    merge_config,
    parse_config_options,
)

# =============================================================================
# TestHandleKongError
# =============================================================================


class TestHandleKongErrorConnectionError:
    """Tests for handle_kong_error with KongConnectionError."""

    @pytest.mark.unit
    def test_connection_error_prints_message_and_exits(self) -> None:
        """handle_kong_error prints connection error message and exits with code 1."""
        mock_console: Any = MagicMock()
        error = KongConnectionError(message="Connection refused", endpoint="/services")

        with (
            patch("system_operations_manager.plugins.kong.commands.base.console", mock_console),
            pytest.raises(typer.Exit) as exc_info,
        ):
            handle_kong_error(error)

        assert exc_info.value.exit_code == 1
        mock_console.print.assert_any_call("[red]Error:[/red] Cannot connect to Kong Admin API")
        mock_console.print.assert_any_call(f"  {error.message}")

    @pytest.mark.unit
    def test_connection_error_with_original_error_prints_cause(self) -> None:
        """handle_kong_error prints the original cause when original_error is set."""
        mock_console: Any = MagicMock()
        original = ConnectionRefusedError("port closed")
        error = KongConnectionError(message="Connection refused", original_error=original)

        with (
            patch("system_operations_manager.plugins.kong.commands.base.console", mock_console),
            pytest.raises(typer.Exit),
        ):
            handle_kong_error(error)

        mock_console.print.assert_any_call(f"  Cause: {original}")

    @pytest.mark.unit
    def test_connection_error_without_original_error_skips_cause(self) -> None:
        """handle_kong_error does not print cause when original_error is None."""
        mock_console: Any = MagicMock()
        error = KongConnectionError(message="Timeout", original_error=None)

        with (
            patch("system_operations_manager.plugins.kong.commands.base.console", mock_console),
            pytest.raises(typer.Exit),
        ):
            handle_kong_error(error)

        printed_args = [call.args[0] for call in mock_console.print.call_args_list]
        assert not any("Cause:" in arg for arg in printed_args)

    @pytest.mark.unit
    def test_connection_error_prints_hint(self) -> None:
        """handle_kong_error prints the URL hint for connection errors."""
        mock_console: Any = MagicMock()
        error = KongConnectionError(message="Unreachable")

        with (
            patch("system_operations_manager.plugins.kong.commands.base.console", mock_console),
            pytest.raises(typer.Exit),
        ):
            handle_kong_error(error)

        mock_console.print.assert_any_call(
            "\n[dim]Hint: Check that Kong is running and the URL is correct.[/dim]"
        )


class TestHandleKongErrorAuthError:
    """Tests for handle_kong_error with KongAuthError."""

    @pytest.mark.unit
    def test_auth_error_prints_authentication_failed(self) -> None:
        """handle_kong_error prints authentication failed for KongAuthError."""
        mock_console: Any = MagicMock()
        error = KongAuthError(message="Invalid API key")

        with (
            patch("system_operations_manager.plugins.kong.commands.base.console", mock_console),
            pytest.raises(typer.Exit) as exc_info,
        ):
            handle_kong_error(error)

        assert exc_info.value.exit_code == 1
        mock_console.print.assert_any_call("[red]Error:[/red] Authentication failed")
        mock_console.print.assert_any_call(f"  {error.message}")

    @pytest.mark.unit
    def test_auth_error_prints_hint(self) -> None:
        """handle_kong_error prints the certificate hint for auth errors."""
        mock_console: Any = MagicMock()
        error = KongAuthError(message="Forbidden")

        with (
            patch("system_operations_manager.plugins.kong.commands.base.console", mock_console),
            pytest.raises(typer.Exit),
        ):
            handle_kong_error(error)

        mock_console.print.assert_any_call(
            "\n[dim]Hint: Check your API key or certificate configuration.[/dim]"
        )


class TestHandleKongErrorNotFoundError:
    """Tests for handle_kong_error with KongNotFoundError."""

    @pytest.mark.unit
    def test_not_found_error_with_resource_id_prints_detailed_message(self) -> None:
        """handle_kong_error prints resource type and id for KongNotFoundError with resource_id."""
        mock_console: Any = MagicMock()
        error = KongNotFoundError(resource_type="service", resource_id="svc-abc")

        with (
            patch("system_operations_manager.plugins.kong.commands.base.console", mock_console),
            pytest.raises(typer.Exit) as exc_info,
        ):
            handle_kong_error(error)

        assert exc_info.value.exit_code == 1
        mock_console.print.assert_any_call("[red]Error:[/red] service not found")
        mock_console.print.assert_any_call("  Could not find service 'svc-abc'")

    @pytest.mark.unit
    def test_not_found_error_without_resource_id_prints_generic_message(self) -> None:
        """handle_kong_error falls back to error.message when resource_id is absent."""
        mock_console: Any = MagicMock()
        error = KongNotFoundError(message="The resource was not found", resource_type="route")

        with (
            patch("system_operations_manager.plugins.kong.commands.base.console", mock_console),
            pytest.raises(typer.Exit) as exc_info,
        ):
            handle_kong_error(error)

        assert exc_info.value.exit_code == 1
        mock_console.print.assert_any_call("[red]Error:[/red] route not found")
        mock_console.print.assert_any_call(f"  {error.message}")


class TestHandleKongErrorValidationError:
    """Tests for handle_kong_error with KongValidationError."""

    @pytest.mark.unit
    def test_validation_error_prints_validation_failed(self) -> None:
        """handle_kong_error prints validation failed for KongValidationError."""
        mock_console: Any = MagicMock()
        error = KongValidationError(message="Schema violation")

        with (
            patch("system_operations_manager.plugins.kong.commands.base.console", mock_console),
            pytest.raises(typer.Exit) as exc_info,
        ):
            handle_kong_error(error)

        assert exc_info.value.exit_code == 1
        mock_console.print.assert_any_call("[red]Error:[/red] Validation failed")
        mock_console.print.assert_any_call(f"  {error.message}")

    @pytest.mark.unit
    def test_validation_error_with_field_errors_prints_each_field(self) -> None:
        """handle_kong_error prints individual field errors when validation_errors is set."""
        mock_console: Any = MagicMock()
        error = KongValidationError(
            message="Schema violation",
            validation_errors={"host": "required field", "port": "must be integer"},
        )

        with (
            patch("system_operations_manager.plugins.kong.commands.base.console", mock_console),
            pytest.raises(typer.Exit),
        ):
            handle_kong_error(error)

        mock_console.print.assert_any_call("\n  Field errors:")
        mock_console.print.assert_any_call("    - host: required field")
        mock_console.print.assert_any_call("    - port: must be integer")

    @pytest.mark.unit
    def test_validation_error_without_field_errors_skips_field_section(self) -> None:
        """handle_kong_error does not print field errors when validation_errors is empty."""
        mock_console: Any = MagicMock()
        error = KongValidationError(message="Schema violation", validation_errors={})

        with (
            patch("system_operations_manager.plugins.kong.commands.base.console", mock_console),
            pytest.raises(typer.Exit),
        ):
            handle_kong_error(error)

        printed_args = [call.args[0] for call in mock_console.print.call_args_list]
        assert not any("Field errors:" in arg for arg in printed_args)


class TestHandleKongErrorDBLessWriteError:
    """Tests for handle_kong_error with KongDBLessWriteError."""

    @pytest.mark.unit
    def test_dbless_write_error_prints_dbless_mode_message(self) -> None:
        """handle_kong_error prints DB-less mode message for KongDBLessWriteError."""
        mock_console: Any = MagicMock()
        error = KongDBLessWriteError()

        with (
            patch("system_operations_manager.plugins.kong.commands.base.console", mock_console),
            pytest.raises(typer.Exit) as exc_info,
        ):
            handle_kong_error(error)

        assert exc_info.value.exit_code == 1
        mock_console.print.assert_any_call("[red]Error:[/red] Kong is running in DB-less mode")
        mock_console.print.assert_any_call(
            "  Write operations are not available via the Admin API."
        )

    @pytest.mark.unit
    def test_dbless_write_error_prints_declarative_config_hint(self) -> None:
        """handle_kong_error prints the declarative config hint for DB-less errors."""
        mock_console: Any = MagicMock()
        error = KongDBLessWriteError()

        with (
            patch("system_operations_manager.plugins.kong.commands.base.console", mock_console),
            pytest.raises(typer.Exit),
        ):
            handle_kong_error(error)

        mock_console.print.assert_any_call(
            "\n[dim]Hint: Use declarative configuration instead:[/dim]"
        )
        mock_console.print.assert_any_call("  ops kong config apply <config-file>")


class TestHandleKongErrorGenericAPIError:
    """Tests for handle_kong_error with generic KongAPIError."""

    @pytest.mark.unit
    def test_generic_error_prints_message(self) -> None:
        """handle_kong_error prints the message for a generic KongAPIError."""
        mock_console: Any = MagicMock()
        error = KongAPIError(message="Something went wrong")

        with (
            patch("system_operations_manager.plugins.kong.commands.base.console", mock_console),
            pytest.raises(typer.Exit) as exc_info,
        ):
            handle_kong_error(error)

        assert exc_info.value.exit_code == 1
        mock_console.print.assert_any_call(f"[red]Error:[/red] {error.message}")

    @pytest.mark.unit
    def test_generic_error_with_status_code_prints_status(self) -> None:
        """handle_kong_error prints HTTP status code when set on a generic error."""
        mock_console: Any = MagicMock()
        error = KongAPIError(message="Server error", status_code=500)

        with (
            patch("system_operations_manager.plugins.kong.commands.base.console", mock_console),
            pytest.raises(typer.Exit),
        ):
            handle_kong_error(error)

        mock_console.print.assert_any_call(f"  HTTP Status: {error.status_code}")

    @pytest.mark.unit
    def test_generic_error_with_endpoint_prints_endpoint(self) -> None:
        """handle_kong_error prints endpoint when set on a generic error."""
        mock_console: Any = MagicMock()
        error = KongAPIError(message="Not found", status_code=404, endpoint="/services/abc")

        with (
            patch("system_operations_manager.plugins.kong.commands.base.console", mock_console),
            pytest.raises(typer.Exit),
        ):
            handle_kong_error(error)

        mock_console.print.assert_any_call(f"  Endpoint: {error.endpoint}")

    @pytest.mark.unit
    def test_generic_error_without_status_or_endpoint_skips_extras(self) -> None:
        """handle_kong_error does not print status/endpoint when neither is set."""
        mock_console: Any = MagicMock()
        error = KongAPIError(message="Unknown error")

        with (
            patch("system_operations_manager.plugins.kong.commands.base.console", mock_console),
            pytest.raises(typer.Exit),
        ):
            handle_kong_error(error)

        printed_args = [call.args[0] for call in mock_console.print.call_args_list]
        assert not any("HTTP Status:" in arg for arg in printed_args)
        assert not any("Endpoint:" in arg for arg in printed_args)


# =============================================================================
# TestConfirmDelete
# =============================================================================


class TestConfirmDelete:
    """Tests for confirm_delete function."""

    @pytest.mark.unit
    def test_confirm_delete_returns_true_when_confirmed(self) -> None:
        """confirm_delete returns True when typer.confirm returns True."""
        with patch(
            "system_operations_manager.plugins.kong.commands.base.typer.confirm",
            return_value=True,
        ) as mock_confirm:
            result = confirm_delete("service", "my-svc")

        assert result is True
        mock_confirm.assert_called_once_with(
            "Are you sure you want to delete service 'my-svc'?",
            default=False,
        )

    @pytest.mark.unit
    def test_confirm_delete_returns_false_when_declined(self) -> None:
        """confirm_delete returns False when typer.confirm returns False."""
        with patch(
            "system_operations_manager.plugins.kong.commands.base.typer.confirm",
            return_value=False,
        ):
            result = confirm_delete("route", "route-id-123")

        assert result is False


# =============================================================================
# TestConfirmAction
# =============================================================================


class TestConfirmAction:
    """Tests for confirm_action function."""

    @pytest.mark.unit
    def test_confirm_action_returns_true_when_confirmed(self) -> None:
        """confirm_action returns True when typer.confirm returns True."""
        with patch(
            "system_operations_manager.plugins.kong.commands.base.typer.confirm",
            return_value=True,
        ) as mock_confirm:
            result = confirm_action("Proceed?", default=False)

        assert result is True
        mock_confirm.assert_called_once_with("Proceed?", default=False)

    @pytest.mark.unit
    def test_confirm_action_passes_default_true(self) -> None:
        """confirm_action passes default=True to typer.confirm."""
        with patch(
            "system_operations_manager.plugins.kong.commands.base.typer.confirm",
            return_value=True,
        ) as mock_confirm:
            confirm_action("Continue?", default=True)

        mock_confirm.assert_called_once_with("Continue?", default=True)

    @pytest.mark.unit
    def test_confirm_action_returns_false_when_declined(self) -> None:
        """confirm_action returns False when typer.confirm returns False."""
        with patch(
            "system_operations_manager.plugins.kong.commands.base.typer.confirm",
            return_value=False,
        ):
            result = confirm_action("Delete everything?")

        assert result is False


# =============================================================================
# TestParseConfigOptions
# =============================================================================


class TestParseConfigOptions:
    """Tests for parse_config_options function."""

    @pytest.mark.unit
    def test_returns_empty_dict_for_none(self) -> None:
        """parse_config_options returns {} when given None."""
        result = parse_config_options(None)
        assert result == {}

    @pytest.mark.unit
    def test_returns_empty_dict_for_empty_list(self) -> None:
        """parse_config_options returns {} when given an empty list."""
        result = parse_config_options([])
        assert result == {}

    @pytest.mark.unit
    def test_parses_simple_key_value(self) -> None:
        """parse_config_options parses a simple 'key=value' pair."""
        result = parse_config_options(["minute=100"])
        assert result == {"minute": 100}

    @pytest.mark.unit
    def test_parses_multiple_key_values(self) -> None:
        """parse_config_options parses multiple 'key=value' pairs."""
        result = parse_config_options(["minute=100", "hour=5000"])
        assert result == {"minute": 100, "hour": 5000}

    @pytest.mark.unit
    def test_raises_bad_parameter_for_missing_equals(self) -> None:
        """parse_config_options raises BadParameter when '=' is absent."""
        with pytest.raises(typer.BadParameter, match="Invalid config format"):
            parse_config_options(["badvalue"])

    @pytest.mark.unit
    def test_raises_bad_parameter_for_empty_key(self) -> None:
        """parse_config_options raises BadParameter when key is empty."""
        with pytest.raises(typer.BadParameter, match="Empty key"):
            parse_config_options(["=value"])

    @pytest.mark.unit
    def test_parses_nested_key_with_dot_notation(self) -> None:
        """parse_config_options builds nested dict from dot-notation keys."""
        result = parse_config_options(["limits.minute=100"])
        assert result == {"limits": {"minute": 100}}

    @pytest.mark.unit
    def test_parses_deeply_nested_key(self) -> None:
        """parse_config_options handles deeply nested dot-notation keys."""
        result = parse_config_options(["a.b.c=42"])
        assert result == {"a": {"b": {"c": 42}}}

    @pytest.mark.unit
    def test_value_with_equals_sign_is_preserved(self) -> None:
        """parse_config_options preserves value containing '=' using partition."""
        result = parse_config_options(["key=a=b"])
        assert result == {"key": "a=b"}

    @pytest.mark.unit
    def test_whitespace_is_stripped_from_key_and_value(self) -> None:
        """parse_config_options strips leading/trailing whitespace from key and value."""
        result = parse_config_options([" key = value "])
        assert result == {"key": "value"}


# =============================================================================
# TestParseConfigValue
# =============================================================================


class TestParseConfigValue:
    """Tests for _parse_config_value helper function."""

    @pytest.mark.unit
    def test_true_string_returns_true(self) -> None:
        """_parse_config_value converts 'true' to Python True."""
        assert _parse_config_value("true") is True

    @pytest.mark.unit
    def test_yes_string_returns_true(self) -> None:
        """_parse_config_value converts 'yes' to Python True."""
        assert _parse_config_value("yes") is True

    @pytest.mark.unit
    def test_on_string_returns_true(self) -> None:
        """_parse_config_value converts 'on' to Python True."""
        assert _parse_config_value("on") is True

    @pytest.mark.unit
    def test_false_string_returns_false(self) -> None:
        """_parse_config_value converts 'false' to Python False."""
        assert _parse_config_value("false") is False

    @pytest.mark.unit
    def test_no_string_returns_false(self) -> None:
        """_parse_config_value converts 'no' to Python False."""
        assert _parse_config_value("no") is False

    @pytest.mark.unit
    def test_off_string_returns_false(self) -> None:
        """_parse_config_value converts 'off' to Python False."""
        assert _parse_config_value("off") is False

    @pytest.mark.unit
    def test_integer_string_returns_int(self) -> None:
        """_parse_config_value converts numeric string without dot to int."""
        assert _parse_config_value("42") == 42
        assert isinstance(_parse_config_value("42"), int)

    @pytest.mark.unit
    def test_float_string_returns_float(self) -> None:
        """_parse_config_value converts numeric string with dot to float."""
        assert _parse_config_value("3.14") == pytest.approx(3.14)
        assert isinstance(_parse_config_value("3.14"), float)

    @pytest.mark.unit
    def test_plain_string_is_returned_as_is(self) -> None:
        """_parse_config_value returns non-special strings unchanged."""
        assert _parse_config_value("my-value") == "my-value"

    @pytest.mark.unit
    def test_case_insensitive_boolean_true(self) -> None:
        """_parse_config_value handles mixed-case boolean truthy strings."""
        assert _parse_config_value("True") is True
        assert _parse_config_value("YES") is True


# =============================================================================
# TestSetNested
# =============================================================================


class TestSetNested:
    """Tests for _set_nested helper function."""

    @pytest.mark.unit
    def test_sets_single_level_key(self) -> None:
        """_set_nested sets a value at a single-key path."""
        d: dict[str, Any] = {}
        _set_nested(d, ["foo"], "bar")
        assert d == {"foo": "bar"}

    @pytest.mark.unit
    def test_sets_nested_two_level_key(self) -> None:
        """_set_nested creates intermediate dict and sets value at two-key path."""
        d: dict[str, Any] = {}
        _set_nested(d, ["outer", "inner"], 99)
        assert d == {"outer": {"inner": 99}}

    @pytest.mark.unit
    def test_sets_deeply_nested_key(self) -> None:
        """_set_nested creates nested dicts for paths with more than two keys."""
        d: dict[str, Any] = {}
        _set_nested(d, ["a", "b", "c"], "deep")
        assert d == {"a": {"b": {"c": "deep"}}}

    @pytest.mark.unit
    def test_existing_intermediate_dict_is_reused(self) -> None:
        """_set_nested reuses existing intermediate dicts rather than replacing them."""
        d: dict[str, Any] = {"outer": {"existing": 1}}
        _set_nested(d, ["outer", "new_key"], 2)
        assert d == {"outer": {"existing": 1, "new_key": 2}}


# =============================================================================
# TestMergeConfig
# =============================================================================


class TestMergeConfig:
    """Tests for merge_config function."""

    @pytest.mark.unit
    def test_merges_non_overlapping_keys(self) -> None:
        """merge_config combines keys from both dicts when no overlap exists."""
        base: dict[str, Any] = {"a": 1}
        override: dict[str, Any] = {"b": 2}
        result = merge_config(base, override)
        assert result == {"a": 1, "b": 2}

    @pytest.mark.unit
    def test_override_replaces_scalar_value(self) -> None:
        """merge_config replaces a scalar value in base with override value."""
        base: dict[str, Any] = {"a": 1, "b": 2}
        override: dict[str, Any] = {"b": 99}
        result = merge_config(base, override)
        assert result == {"a": 1, "b": 99}

    @pytest.mark.unit
    def test_deep_merges_nested_dicts(self) -> None:
        """merge_config recursively merges nested dict values."""
        base: dict[str, Any] = {"limits": {"minute": 100, "hour": 1000}}
        override: dict[str, Any] = {"limits": {"minute": 200}}
        result = merge_config(base, override)
        assert result == {"limits": {"minute": 200, "hour": 1000}}

    @pytest.mark.unit
    def test_does_not_mutate_base(self) -> None:
        """merge_config returns a new dict and does not mutate base."""
        base: dict[str, Any] = {"a": 1}
        override: dict[str, Any] = {"a": 2}
        result = merge_config(base, override)
        assert base == {"a": 1}
        assert result == {"a": 2}

    @pytest.mark.unit
    def test_override_replaces_dict_with_scalar(self) -> None:
        """merge_config replaces a dict value with a scalar when override is not a dict."""
        base: dict[str, Any] = {"config": {"key": "value"}}
        override: dict[str, Any] = {"config": "flat"}
        result = merge_config(base, override)
        assert result == {"config": "flat"}

    @pytest.mark.unit
    def test_empty_override_returns_copy_of_base(self) -> None:
        """merge_config with empty override returns a copy of base."""
        base: dict[str, Any] = {"a": 1, "b": {"c": 3}}
        result = merge_config(base, {})
        assert result == base

    @pytest.mark.unit
    def test_empty_base_returns_override_contents(self) -> None:
        """merge_config with empty base returns the override contents."""
        override: dict[str, Any] = {"x": 10}
        result = merge_config({}, override)
        assert result == {"x": 10}
