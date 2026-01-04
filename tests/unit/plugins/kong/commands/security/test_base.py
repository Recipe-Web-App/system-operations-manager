"""Unit tests for security command base utilities."""

from __future__ import annotations

from pathlib import Path

import pytest
import typer

from system_operations_manager.plugins.kong.commands.security.base import (
    ACL_COLUMNS,
    JWT_COLUMNS,
    KEY_AUTH_COLUMNS,
    MTLS_COLUMNS,
    OAUTH2_COLUMNS,
    build_plugin_config,
    read_file_or_value,
)


class TestReadFileOrValue:
    """Tests for read_file_or_value utility function."""

    @pytest.mark.unit
    def test_inline_value_returned_as_is(self) -> None:
        """Values without @ prefix should be returned unchanged."""
        result = read_file_or_value("my-secret-key")
        assert result == "my-secret-key"

    @pytest.mark.unit
    def test_inline_value_with_special_chars(self) -> None:
        """Values with special characters should be preserved."""
        value = "key=value&foo=bar"
        result = read_file_or_value(value)
        assert result == value

    @pytest.mark.unit
    def test_reads_file_content(self, tmp_path: Path) -> None:
        """Values with @ prefix should read from file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("file-content-here")

        result = read_file_or_value(f"@{test_file}")
        assert result == "file-content-here"

    @pytest.mark.unit
    def test_strips_whitespace_from_file(self, tmp_path: Path) -> None:
        """File content should have trailing whitespace stripped."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content-with-whitespace\n\n  ")

        result = read_file_or_value(f"@{test_file}")
        assert result == "content-with-whitespace"

    @pytest.mark.unit
    def test_preserves_internal_whitespace(self, tmp_path: Path) -> None:
        """Internal whitespace in file content should be preserved."""
        test_file = tmp_path / "test.txt"
        content = "line one\nline two\nline three"
        test_file.write_text(content + "\n")

        result = read_file_or_value(f"@{test_file}")
        assert result == content

    @pytest.mark.unit
    def test_file_not_found_raises_bad_parameter(self) -> None:
        """Missing file should raise typer.BadParameter."""
        with pytest.raises(typer.BadParameter) as exc_info:
            read_file_or_value("@/nonexistent/path/to/file.txt")

        assert "File not found" in str(exc_info.value)

    @pytest.mark.unit
    def test_reads_pem_certificate(self, tmp_path: Path) -> None:
        """PEM-formatted certificates should be read correctly."""
        cert_file = tmp_path / "cert.pem"
        cert_content = "-----BEGIN CERTIFICATE-----\nMIIBkTCC...\n-----END CERTIFICATE-----"
        cert_file.write_text(cert_content)

        result = read_file_or_value(f"@{cert_file}")
        assert result == cert_content


class TestBuildPluginConfig:
    """Tests for build_plugin_config utility function."""

    @pytest.mark.unit
    def test_filters_out_none_values(self) -> None:
        """None values should be excluded from the result."""
        result = build_plugin_config(
            key1="value1",
            key2=None,
            key3="value3",
        )

        assert result == {"key1": "value1", "key3": "value3"}
        assert "key2" not in result

    @pytest.mark.unit
    def test_returns_empty_dict_for_all_none(self) -> None:
        """All None values should return empty dict."""
        result = build_plugin_config(a=None, b=None, c=None)
        assert result == {}

    @pytest.mark.unit
    def test_returns_all_non_none_values(self) -> None:
        """All non-None values should be included."""
        result = build_plugin_config(
            string="value",
            number=42,
            boolean=True,
            list_val=["a", "b"],
        )

        assert result == {
            "string": "value",
            "number": 42,
            "boolean": True,
            "list_val": ["a", "b"],
        }

    @pytest.mark.unit
    def test_preserves_false_and_zero_values(self) -> None:
        """False and 0 are valid values and should be preserved."""
        result = build_plugin_config(
            enabled=False,
            count=0,
            empty_string="",
        )

        assert result == {
            "enabled": False,
            "count": 0,
            "empty_string": "",
        }

    @pytest.mark.unit
    def test_empty_call_returns_empty_dict(self) -> None:
        """Calling with no arguments should return empty dict."""
        result = build_plugin_config()
        assert result == {}


class TestColumnDefinitions:
    """Tests to verify column definitions are properly defined."""

    @pytest.mark.unit
    def test_key_auth_columns_defined(self) -> None:
        """KEY_AUTH_COLUMNS should be a non-empty list of tuples."""
        assert isinstance(KEY_AUTH_COLUMNS, list)
        assert len(KEY_AUTH_COLUMNS) > 0
        assert all(isinstance(col, tuple) and len(col) == 2 for col in KEY_AUTH_COLUMNS)

    @pytest.mark.unit
    def test_jwt_columns_defined(self) -> None:
        """JWT_COLUMNS should be a non-empty list of tuples."""
        assert isinstance(JWT_COLUMNS, list)
        assert len(JWT_COLUMNS) > 0
        assert all(isinstance(col, tuple) and len(col) == 2 for col in JWT_COLUMNS)

    @pytest.mark.unit
    def test_oauth2_columns_defined(self) -> None:
        """OAUTH2_COLUMNS should be a non-empty list of tuples."""
        assert isinstance(OAUTH2_COLUMNS, list)
        assert len(OAUTH2_COLUMNS) > 0
        assert all(isinstance(col, tuple) and len(col) == 2 for col in OAUTH2_COLUMNS)

    @pytest.mark.unit
    def test_acl_columns_defined(self) -> None:
        """ACL_COLUMNS should be a non-empty list of tuples."""
        assert isinstance(ACL_COLUMNS, list)
        assert len(ACL_COLUMNS) > 0
        assert all(isinstance(col, tuple) and len(col) == 2 for col in ACL_COLUMNS)

    @pytest.mark.unit
    def test_mtls_columns_defined(self) -> None:
        """MTLS_COLUMNS should be a non-empty list of tuples."""
        assert isinstance(MTLS_COLUMNS, list)
        assert len(MTLS_COLUMNS) > 0
        assert all(isinstance(col, tuple) and len(col) == 2 for col in MTLS_COLUMNS)

    @pytest.mark.unit
    def test_columns_have_id_field(self) -> None:
        """All column definitions should include an 'id' field."""
        for columns, name in [
            (KEY_AUTH_COLUMNS, "KEY_AUTH"),
            (JWT_COLUMNS, "JWT"),
            (OAUTH2_COLUMNS, "OAUTH2"),
            (ACL_COLUMNS, "ACL"),
            (MTLS_COLUMNS, "MTLS"),
        ]:
            field_names = [col[0] for col in columns]
            assert "id" in field_names, f"{name}_COLUMNS missing 'id' field"
