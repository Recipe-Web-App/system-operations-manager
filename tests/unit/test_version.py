"""Tests for version module."""

from __future__ import annotations

import pytest

from system_operations_manager import __version__
from system_operations_manager.__version__ import __version__ as version_string


class TestVersion:
    """Test version information."""

    @pytest.mark.unit
    def test_version_exists(self) -> None:
        """Test that version is defined."""
        assert __version__ is not None

    @pytest.mark.unit
    def test_version_format(self) -> None:
        """Test version follows semantic versioning."""
        parts = __version__.split(".")
        assert len(parts) >= 2, "Version should have at least major.minor"
        assert all(part.isdigit() for part in parts[:2]), "Major and minor should be numeric"

    @pytest.mark.unit
    def test_version_importable(self) -> None:
        """Test version can be imported from multiple locations."""
        assert __version__ == version_string
