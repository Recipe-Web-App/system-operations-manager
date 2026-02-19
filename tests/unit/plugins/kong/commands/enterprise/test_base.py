"""Unit tests for Kong Enterprise base utilities."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import typer

from system_operations_manager.integrations.kong.exceptions import (
    KongEnterpriseRequiredError,
)
from system_operations_manager.plugins.kong.commands.enterprise.base import (
    enterprise_status_message,
    format_enterprise_feature,
    handle_enterprise_error,
    require_enterprise,
)


class TestHandleEnterpriseError:
    """Tests for handle_enterprise_error()."""

    @pytest.mark.unit
    def test_raises_typer_exit_with_code_1(self) -> None:
        """handle_enterprise_error should always exit with code 1."""
        error = KongEnterpriseRequiredError(feature="workspaces")

        with pytest.raises(typer.Exit) as exc_info:
            handle_enterprise_error(error)

        assert exc_info.value.exit_code == 1

    @pytest.mark.unit
    def test_prints_error_header(self) -> None:
        """handle_enterprise_error should print the error header to console."""
        error = KongEnterpriseRequiredError(feature="rbac")

        with (
            patch(
                "system_operations_manager.plugins.kong.commands.enterprise.base.console"
            ) as mock_console,
            pytest.raises(typer.Exit),
        ):
            handle_enterprise_error(error)

        printed_calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("Kong Enterprise Required" in call for call in printed_calls)

    @pytest.mark.unit
    def test_prints_error_message(self) -> None:
        """handle_enterprise_error should print the error message from the exception."""
        error = KongEnterpriseRequiredError(feature="dev-portal")

        with (
            patch(
                "system_operations_manager.plugins.kong.commands.enterprise.base.console"
            ) as mock_console,
            pytest.raises(typer.Exit),
        ):
            handle_enterprise_error(error)

        printed_args = [
            call.args[0] if call.args else "" for call in mock_console.print.call_args_list
        ]
        assert any(error.message in arg for arg in printed_args)

    @pytest.mark.unit
    def test_prints_enterprise_edition_hint(self) -> None:
        """handle_enterprise_error should print a hint about Enterprise edition."""
        error = KongEnterpriseRequiredError(feature="vaults")

        with (
            patch(
                "system_operations_manager.plugins.kong.commands.enterprise.base.console"
            ) as mock_console,
            pytest.raises(typer.Exit),
        ):
            handle_enterprise_error(error)

        printed_calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("Enterprise edition" in call for call in printed_calls)

    @pytest.mark.unit
    def test_prints_konghq_url(self) -> None:
        """handle_enterprise_error should print the KongHQ product URL."""
        error = KongEnterpriseRequiredError(feature="vaults")

        with (
            patch(
                "system_operations_manager.plugins.kong.commands.enterprise.base.console"
            ) as mock_console,
            pytest.raises(typer.Exit),
        ):
            handle_enterprise_error(error)

        printed_calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("konghq.com" in call for call in printed_calls)

    @pytest.mark.unit
    def test_uses_default_error_message_when_none_provided(self) -> None:
        """handle_enterprise_error should use auto-generated message when no custom message given."""
        error = KongEnterpriseRequiredError(feature="workspaces")

        with (
            patch(
                "system_operations_manager.plugins.kong.commands.enterprise.base.console"
            ) as mock_console,
            pytest.raises(typer.Exit),
        ):
            handle_enterprise_error(error)

        printed_args = [
            call.args[0] if call.args else "" for call in mock_console.print.call_args_list
        ]
        assert any("workspaces" in arg for arg in printed_args)

    @pytest.mark.unit
    def test_uses_custom_error_message_when_provided(self) -> None:
        """handle_enterprise_error should use custom message if one was set on the exception."""
        custom_msg = "Custom enterprise error message"
        error = KongEnterpriseRequiredError(feature="rbac", message=custom_msg)

        with (
            patch(
                "system_operations_manager.plugins.kong.commands.enterprise.base.console"
            ) as mock_console,
            pytest.raises(typer.Exit),
        ):
            handle_enterprise_error(error)

        printed_args = [
            call.args[0] if call.args else "" for call in mock_console.print.call_args_list
        ]
        assert any(custom_msg in arg for arg in printed_args)

    @pytest.mark.unit
    def test_console_print_called_multiple_times(self) -> None:
        """handle_enterprise_error should call console.print at least 4 times."""
        error = KongEnterpriseRequiredError(feature="rbac")

        with (
            patch(
                "system_operations_manager.plugins.kong.commands.enterprise.base.console"
            ) as mock_console,
            pytest.raises(typer.Exit),
        ):
            handle_enterprise_error(error)

        # The function calls print 4 times: header, message, blank line, edition hint, url
        assert mock_console.print.call_count >= 4


class TestRequireEnterprise:
    """Tests for require_enterprise() decorator."""

    @pytest.mark.unit
    def test_calls_wrapped_function_when_enterprise_available(self) -> None:
        """require_enterprise should call the wrapped function when checker succeeds."""
        mock_checker = MagicMock()
        mock_checker.require_enterprise.return_value = None

        def get_checker() -> MagicMock:
            return mock_checker

        mock_func = MagicMock(return_value="success")
        decorated = require_enterprise("workspaces", get_checker)(mock_func)

        result = decorated()

        mock_func.assert_called_once()
        assert result == "success"

    @pytest.mark.unit
    def test_calls_checker_require_enterprise_with_feature_name(self) -> None:
        """require_enterprise should call checker.require_enterprise with the feature name."""
        mock_checker = MagicMock()
        mock_checker.require_enterprise.return_value = None

        def get_checker() -> MagicMock:
            return mock_checker

        mock_func = MagicMock(return_value=None)
        decorated = require_enterprise("rbac", get_checker)(mock_func)
        decorated()

        mock_checker.require_enterprise.assert_called_once_with("rbac")

    @pytest.mark.unit
    def test_calls_get_checker_factory(self) -> None:
        """require_enterprise should invoke the get_checker factory on each call."""
        mock_checker = MagicMock()
        mock_checker.require_enterprise.return_value = None
        factory = MagicMock(return_value=mock_checker)

        mock_func = MagicMock(return_value=None)
        decorated = require_enterprise("vaults", factory)(mock_func)
        decorated()

        factory.assert_called_once()

    @pytest.mark.unit
    def test_exits_with_code_1_when_enterprise_not_available(self) -> None:
        """require_enterprise should exit with code 1 when KongEnterpriseRequiredError is raised."""
        mock_checker = MagicMock()
        mock_checker.require_enterprise.side_effect = KongEnterpriseRequiredError(
            feature="workspaces"
        )

        def get_checker() -> MagicMock:
            return mock_checker

        mock_func = MagicMock(return_value=None)
        decorated = require_enterprise("workspaces", get_checker)(mock_func)

        with (
            patch("system_operations_manager.plugins.kong.commands.enterprise.base.console"),
            pytest.raises(typer.Exit) as exc_info,
        ):
            decorated()

        assert exc_info.value.exit_code == 1

    @pytest.mark.unit
    def test_does_not_call_wrapped_function_when_enterprise_not_available(self) -> None:
        """require_enterprise should not call the wrapped function when the check fails."""
        mock_checker = MagicMock()
        mock_checker.require_enterprise.side_effect = KongEnterpriseRequiredError(
            feature="dev-portal"
        )

        def get_checker() -> MagicMock:
            return mock_checker

        mock_func = MagicMock(return_value=None)
        decorated = require_enterprise("dev-portal", get_checker)(mock_func)

        with (
            patch("system_operations_manager.plugins.kong.commands.enterprise.base.console"),
            pytest.raises(typer.Exit),
        ):
            decorated()

        mock_func.assert_not_called()

    @pytest.mark.unit
    def test_preserves_wrapped_function_name(self) -> None:
        """require_enterprise should preserve the wrapped function's __name__ via @wraps."""
        mock_checker = MagicMock()

        def get_checker() -> MagicMock:
            return mock_checker

        def my_command() -> None:
            """My command docstring."""

        decorated = require_enterprise("rbac", get_checker)(my_command)

        assert decorated.__name__ == "my_command"

    @pytest.mark.unit
    def test_preserves_wrapped_function_docstring(self) -> None:
        """require_enterprise should preserve the wrapped function's __doc__ via @wraps."""
        mock_checker = MagicMock()

        def get_checker() -> MagicMock:
            return mock_checker

        def my_command() -> None:
            """My command docstring."""

        decorated = require_enterprise("rbac", get_checker)(my_command)

        assert decorated.__doc__ == "My command docstring."

    @pytest.mark.unit
    def test_passes_positional_args_to_wrapped_function(self) -> None:
        """require_enterprise should forward positional arguments to the wrapped function."""
        mock_checker = MagicMock()
        mock_checker.require_enterprise.return_value = None

        def get_checker() -> MagicMock:
            return mock_checker

        mock_func = MagicMock(return_value=None)
        decorated = require_enterprise("workspaces", get_checker)(mock_func)
        decorated("arg1", "arg2")

        mock_func.assert_called_once_with("arg1", "arg2")

    @pytest.mark.unit
    def test_passes_keyword_args_to_wrapped_function(self) -> None:
        """require_enterprise should forward keyword arguments to the wrapped function."""
        mock_checker = MagicMock()
        mock_checker.require_enterprise.return_value = None

        def get_checker() -> MagicMock:
            return mock_checker

        mock_func = MagicMock(return_value=None)
        decorated = require_enterprise("rbac", get_checker)(mock_func)
        decorated(name="test", value=42)

        mock_func.assert_called_once_with(name="test", value=42)

    @pytest.mark.unit
    def test_returns_value_from_wrapped_function(self) -> None:
        """require_enterprise should return whatever the wrapped function returns."""
        mock_checker = MagicMock()
        mock_checker.require_enterprise.return_value = None

        def get_checker() -> MagicMock:
            return mock_checker

        expected = {"key": "value", "count": 99}
        mock_func = MagicMock(return_value=expected)
        decorated = require_enterprise("vaults", get_checker)(mock_func)

        result = decorated()

        assert result is expected

    @pytest.mark.unit
    def test_can_decorate_multiple_functions_independently(self) -> None:
        """require_enterprise should produce independent decorators for different functions."""
        mock_checker = MagicMock()
        mock_checker.require_enterprise.return_value = None

        def get_checker() -> MagicMock:
            return mock_checker

        func_a = MagicMock(return_value="a")
        func_b = MagicMock(return_value="b")

        decorated_a = require_enterprise("workspaces", get_checker)(func_a)
        decorated_b = require_enterprise("rbac", get_checker)(func_b)

        assert decorated_a() == "a"
        assert decorated_b() == "b"

        func_a.assert_called_once()
        func_b.assert_called_once()

    @pytest.mark.unit
    def test_calls_handle_enterprise_error_on_exception(self) -> None:
        """require_enterprise should call handle_enterprise_error when the check raises."""
        error = KongEnterpriseRequiredError(feature="workspaces")
        mock_checker = MagicMock()
        mock_checker.require_enterprise.side_effect = error

        def get_checker() -> MagicMock:
            return mock_checker

        mock_func = MagicMock(return_value=None)
        decorated = require_enterprise("workspaces", get_checker)(mock_func)

        with patch(
            "system_operations_manager.plugins.kong.commands.enterprise.base.handle_enterprise_error"
        ) as mock_handler:
            mock_handler.side_effect = typer.Exit(1)

            with pytest.raises(typer.Exit):
                decorated()

        mock_handler.assert_called_once_with(error)


class TestEnterpriseStatusMessage:
    """Tests for enterprise_status_message()."""

    @pytest.mark.unit
    def test_returns_green_enterprise_when_true(self) -> None:
        """enterprise_status_message should return a green Enterprise label for True."""
        result = enterprise_status_message(True)

        assert result == "[green]Enterprise[/green]"

    @pytest.mark.unit
    def test_returns_yellow_community_when_false(self) -> None:
        """enterprise_status_message should return a yellow Community label for False."""
        result = enterprise_status_message(False)

        assert result == "[yellow]Community (OSS)[/yellow]"

    @pytest.mark.unit
    def test_result_contains_enterprise_text_when_true(self) -> None:
        """enterprise_status_message should include 'Enterprise' text for True."""
        result = enterprise_status_message(True)

        assert "Enterprise" in result

    @pytest.mark.unit
    def test_result_contains_community_text_when_false(self) -> None:
        """enterprise_status_message should include 'Community' text for False."""
        result = enterprise_status_message(False)

        assert "Community" in result

    @pytest.mark.unit
    def test_result_contains_oss_text_when_false(self) -> None:
        """enterprise_status_message should include 'OSS' text for False."""
        result = enterprise_status_message(False)

        assert "OSS" in result

    @pytest.mark.unit
    def test_returns_string(self) -> None:
        """enterprise_status_message should always return a str."""
        assert isinstance(enterprise_status_message(True), str)
        assert isinstance(enterprise_status_message(False), str)

    @pytest.mark.unit
    def test_true_and_false_return_different_strings(self) -> None:
        """enterprise_status_message should return distinct strings for True and False."""
        assert enterprise_status_message(True) != enterprise_status_message(False)


class TestFormatEnterpriseFeature:
    """Tests for format_enterprise_feature()."""

    @pytest.mark.unit
    def test_returns_green_available_when_true(self) -> None:
        """format_enterprise_feature should return a green Available label for True."""
        result = format_enterprise_feature(True)

        assert result == "[green]Available[/green]"

    @pytest.mark.unit
    def test_returns_dim_not_available_when_false(self) -> None:
        """format_enterprise_feature should return a dim Not available label for False."""
        result = format_enterprise_feature(False)

        assert result == "[dim]Not available[/dim]"

    @pytest.mark.unit
    def test_result_contains_available_text_when_true(self) -> None:
        """format_enterprise_feature should include 'Available' text for True."""
        result = format_enterprise_feature(True)

        assert "Available" in result

    @pytest.mark.unit
    def test_result_contains_not_available_text_when_false(self) -> None:
        """format_enterprise_feature should include 'Not available' text for False."""
        result = format_enterprise_feature(False)

        assert "Not available" in result

    @pytest.mark.unit
    def test_returns_string(self) -> None:
        """format_enterprise_feature should always return a str."""
        assert isinstance(format_enterprise_feature(True), str)
        assert isinstance(format_enterprise_feature(False), str)

    @pytest.mark.unit
    def test_true_and_false_return_different_strings(self) -> None:
        """format_enterprise_feature should return distinct strings for True and False."""
        assert format_enterprise_feature(True) != format_enterprise_feature(False)

    @pytest.mark.unit
    def test_available_uses_green_markup(self) -> None:
        """format_enterprise_feature should use Rich green markup when available."""
        result = format_enterprise_feature(True)

        assert result.startswith("[green]")
        assert result.endswith("[/green]")

    @pytest.mark.unit
    def test_not_available_uses_dim_markup(self) -> None:
        """format_enterprise_feature should use Rich dim markup when not available."""
        result = format_enterprise_feature(False)

        assert result.startswith("[dim]")
        assert result.endswith("[/dim]")
