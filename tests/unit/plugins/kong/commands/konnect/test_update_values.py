"""Tests for konnect setup --update-values functionality."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml


@pytest.mark.unit
class TestUpdateValuesFile:
    """Tests for _update_values_file helper function."""

    def test_updates_existing_file_with_endpoints(self, tmp_path: Path) -> None:
        """Test that existing values file is updated with Konnect endpoints."""
        from system_operations_manager.plugins.kong.commands.konnect import (
            _update_values_file,
        )

        # Create existing values file
        values_file = tmp_path / "values.yaml"
        existing_values = {
            "gateway": {
                "image": "kong:3.4",
                "env": {
                    "log_level": "info",
                },
            },
        }
        values_file.write_text(yaml.dump(existing_values))

        # Update with Konnect endpoints
        _update_values_file(
            values_path=str(values_file),
            telemetry_endpoint="telemetry.konghq.com:443",
            control_plane_endpoint="cp.konghq.com:443",
        )

        # Verify
        result = yaml.safe_load(values_file.read_text())
        assert result["gateway"]["image"] == "kong:3.4"  # Preserved
        assert result["gateway"]["env"]["log_level"] == "info"  # Preserved
        assert result["gateway"]["env"]["cluster_telemetry_endpoint"] == "telemetry.konghq.com:443"
        assert result["gateway"]["env"]["cluster_telemetry_server_name"] == "telemetry.konghq.com"
        assert result["gateway"]["env"]["cluster_control_plane"] == "cp.konghq.com:443"
        assert result["gateway"]["env"]["cluster_server_name"] == "cp.konghq.com"

    def test_creates_nested_structure_if_missing(self, tmp_path: Path) -> None:
        """Test that missing gateway.env structure is created."""
        from system_operations_manager.plugins.kong.commands.konnect import (
            _update_values_file,
        )

        # Create minimal values file
        values_file = tmp_path / "values.yaml"
        values_file.write_text(yaml.dump({"replicaCount": 2}))

        _update_values_file(
            values_path=str(values_file),
            telemetry_endpoint="telemetry.konghq.com:443",
            control_plane_endpoint="cp.konghq.com:443",
        )

        result = yaml.safe_load(values_file.read_text())
        assert result["replicaCount"] == 2  # Preserved
        assert "gateway" in result
        assert "env" in result["gateway"]
        assert result["gateway"]["env"]["cluster_telemetry_endpoint"] == "telemetry.konghq.com:443"

    def test_handles_nonexistent_file(self, tmp_path: Path) -> None:
        """Test creating a new values file if it doesn't exist."""
        from system_operations_manager.plugins.kong.commands.konnect import (
            _update_values_file,
        )

        values_file = tmp_path / "new-values.yaml"
        assert not values_file.exists()

        _update_values_file(
            values_path=str(values_file),
            telemetry_endpoint="telemetry.konghq.com:443",
            control_plane_endpoint="cp.konghq.com:443",
        )

        assert values_file.exists()
        result = yaml.safe_load(values_file.read_text())
        assert result["gateway"]["env"]["cluster_telemetry_endpoint"] == "telemetry.konghq.com:443"

    def test_extracts_hostname_from_endpoint_with_port(self, tmp_path: Path) -> None:
        """Test that hostname is correctly extracted when port is present."""
        from system_operations_manager.plugins.kong.commands.konnect import (
            _update_values_file,
        )

        values_file = tmp_path / "values.yaml"
        values_file.write_text("{}")

        _update_values_file(
            values_path=str(values_file),
            telemetry_endpoint="us-west-2.telemetry.konghq.com:443",
            control_plane_endpoint="us-west-2.cp.konghq.com:443",
        )

        result = yaml.safe_load(values_file.read_text())
        assert (
            result["gateway"]["env"]["cluster_telemetry_server_name"]
            == "us-west-2.telemetry.konghq.com"
        )
        assert result["gateway"]["env"]["cluster_server_name"] == "us-west-2.cp.konghq.com"

    def test_handles_endpoint_without_port(self, tmp_path: Path) -> None:
        """Test that hostname handling works without port in endpoint."""
        from system_operations_manager.plugins.kong.commands.konnect import (
            _update_values_file,
        )

        values_file = tmp_path / "values.yaml"
        values_file.write_text("{}")

        _update_values_file(
            values_path=str(values_file),
            telemetry_endpoint="telemetry.konghq.com",
            control_plane_endpoint="cp.konghq.com",
        )

        result = yaml.safe_load(values_file.read_text())
        assert result["gateway"]["env"]["cluster_telemetry_endpoint"] == "telemetry.konghq.com"
        assert result["gateway"]["env"]["cluster_telemetry_server_name"] == "telemetry.konghq.com"
        assert result["gateway"]["env"]["cluster_control_plane"] == "cp.konghq.com"
        assert result["gateway"]["env"]["cluster_server_name"] == "cp.konghq.com"

    def test_preserves_other_env_values(self, tmp_path: Path) -> None:
        """Test that existing env values are preserved."""
        from system_operations_manager.plugins.kong.commands.konnect import (
            _update_values_file,
        )

        values_file = tmp_path / "values.yaml"
        existing = {
            "gateway": {
                "env": {
                    "log_level": "debug",
                    "database": "off",
                    "proxy_access_log": "/dev/stdout",
                },
            },
        }
        values_file.write_text(yaml.dump(existing))

        _update_values_file(
            values_path=str(values_file),
            telemetry_endpoint="telemetry.konghq.com:443",
            control_plane_endpoint="cp.konghq.com:443",
        )

        result = yaml.safe_load(values_file.read_text())
        assert result["gateway"]["env"]["log_level"] == "debug"
        assert result["gateway"]["env"]["database"] == "off"
        assert result["gateway"]["env"]["proxy_access_log"] == "/dev/stdout"
        assert result["gateway"]["env"]["cluster_telemetry_endpoint"] == "telemetry.konghq.com:443"

    def test_overwrites_existing_konnect_endpoints(self, tmp_path: Path) -> None:
        """Test that existing Konnect endpoints are overwritten."""
        from system_operations_manager.plugins.kong.commands.konnect import (
            _update_values_file,
        )

        values_file = tmp_path / "values.yaml"
        existing = {
            "gateway": {
                "env": {
                    "cluster_telemetry_endpoint": "old.konghq.com:443",
                    "cluster_control_plane": "old-cp.konghq.com:443",
                },
            },
        }
        values_file.write_text(yaml.dump(existing))

        _update_values_file(
            values_path=str(values_file),
            telemetry_endpoint="new.konghq.com:443",
            control_plane_endpoint="new-cp.konghq.com:443",
        )

        result = yaml.safe_load(values_file.read_text())
        assert result["gateway"]["env"]["cluster_telemetry_endpoint"] == "new.konghq.com:443"
        assert result["gateway"]["env"]["cluster_control_plane"] == "new-cp.konghq.com:443"

    def test_handles_empty_yaml_file(self, tmp_path: Path) -> None:
        """Test handling an empty YAML file."""
        from system_operations_manager.plugins.kong.commands.konnect import (
            _update_values_file,
        )

        values_file = tmp_path / "values.yaml"
        values_file.write_text("")  # Empty file

        _update_values_file(
            values_path=str(values_file),
            telemetry_endpoint="telemetry.konghq.com:443",
            control_plane_endpoint="cp.konghq.com:443",
        )

        result = yaml.safe_load(values_file.read_text())
        assert result["gateway"]["env"]["cluster_telemetry_endpoint"] == "telemetry.konghq.com:443"

    def test_handles_null_yaml_content(self, tmp_path: Path) -> None:
        """Test handling YAML file with null content."""
        from system_operations_manager.plugins.kong.commands.konnect import (
            _update_values_file,
        )

        values_file = tmp_path / "values.yaml"
        values_file.write_text("null\n")

        _update_values_file(
            values_path=str(values_file),
            telemetry_endpoint="telemetry.konghq.com:443",
            control_plane_endpoint="cp.konghq.com:443",
        )

        result = yaml.safe_load(values_file.read_text())
        assert result["gateway"]["env"]["cluster_telemetry_endpoint"] == "telemetry.konghq.com:443"
