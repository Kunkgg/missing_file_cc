"""
Tests for simplified LocalProjectAdapter.

Tests the new two-file approach with separate build_info and file_list files.
"""

import pytest
from pathlib import Path

from missing_file_check.config.models import ProjectConfig, ProjectType
from missing_file_check.adapters.local_adapter import LocalProjectAdapter
from missing_file_check.adapters.base import AdapterError


class TestSimplifiedLocalAdapter:
    """Test simplified local adapter with separate files."""

    def test_load_with_csv_file_list(self):
        """Test loading with CSV file list."""
        config = ProjectConfig(
            project_id="test-target",
            project_name="Test Target",
            project_type=ProjectType.LOCAL,
            connection={
                "build_info_file": "test_data/target_build_info.json",
                "file_list_file": "test_data/target_files.csv",
            },
        )

        adapter = LocalProjectAdapter(config)
        result = adapter.fetch_files()

        assert result.project_id == "target-project"  # From build_info file
        assert result.build_info.build_no == "BUILD-TARGET-001"
        assert result.build_info.commit_id == "abc123def456"
        assert len(result.files) == 5

        # Check CSV parsing
        paths = [f.path for f in result.files]
        assert "/project/src/main.py" in paths

        # Check status parsing
        failed_files = [f for f in result.files if f.status == "failed"]
        assert len(failed_files) == 1
        assert failed_files[0].path == "/project/tests/test_main.py"

    def test_load_with_json_file_list(self):
        """Test loading with JSON file list."""
        config = ProjectConfig(
            project_id="test-baseline",
            project_name="Test Baseline",
            project_type=ProjectType.LOCAL,
            connection={
                "build_info_file": "test_data/baseline_build_info.json",
                "file_list_file": "test_data/baseline_files.json",
            },
        )

        adapter = LocalProjectAdapter(config)
        result = adapter.fetch_files()

        assert result.project_id == "baseline-project"
        assert result.build_info.build_no == "BUILD-BASELINE-001"
        assert len(result.files) == 10

        # Check JSON parsing
        paths = [f.path for f in result.files]
        assert "/baseline/src/database.py" in paths
        assert "/baseline/docs/API.md" in paths

    def test_commit_id_filter(self):
        """Test commit_id filter validation."""
        config = ProjectConfig(
            project_id="test",
            project_name="Test",
            project_type=ProjectType.LOCAL,
            connection={
                "build_info_file": "test_data/target_build_info.json",
                "file_list_file": "test_data/target_files.csv",
            },
        )

        adapter = LocalProjectAdapter(config)

        # Should succeed with matching commit_id
        result = adapter.fetch_files(commit_id="abc123def456")
        assert result.build_info.commit_id == "abc123def456"

        # Should fail with non-matching commit_id
        with pytest.raises(AdapterError, match="does not match"):
            adapter.fetch_files(commit_id="wrong_commit_id")

    def test_version_filter(self):
        """Test b_version filter validation."""
        config = ProjectConfig(
            project_id="test",
            project_name="Test",
            project_type=ProjectType.LOCAL,
            connection={
                "build_info_file": "test_data/baseline_build_info.json",
                "file_list_file": "test_data/baseline_files.json",
            },
        )

        adapter = LocalProjectAdapter(config)

        # Should succeed with matching version
        result = adapter.fetch_files(b_version="1.0.0")
        assert result.build_info.b_version == "1.0.0"

        # Should fail with non-matching version
        with pytest.raises(AdapterError, match="does not match"):
            adapter.fetch_files(b_version="2.0.0")

    def test_build_info_file_not_found(self):
        """Test error when build_info file doesn't exist."""
        config = ProjectConfig(
            project_id="test",
            project_name="Test",
            project_type=ProjectType.LOCAL,
            connection={
                "build_info_file": "test_data/nonexistent_build.json",
                "file_list_file": "test_data/target_files.csv",
            },
        )

        adapter = LocalProjectAdapter(config)

        with pytest.raises(AdapterError, match="not found"):
            adapter.fetch_files()

    def test_file_list_file_not_found(self):
        """Test error when file_list file doesn't exist."""
        config = ProjectConfig(
            project_id="test",
            project_name="Test",
            project_type=ProjectType.LOCAL,
            connection={
                "build_info_file": "test_data/target_build_info.json",
                "file_list_file": "test_data/nonexistent_files.csv",
            },
        )

        adapter = LocalProjectAdapter(config)

        with pytest.raises(AdapterError, match="not found"):
            adapter.fetch_files()

    def test_unsupported_file_format(self, tmp_path):
        """Test error with unsupported file format."""
        # Create dummy files
        build_info = tmp_path / "build.json"
        build_info.write_text('{"project_id": "test", "build_info": {}}')

        file_list = tmp_path / "files.txt"  # Unsupported format
        file_list.write_text("/file1.py\n/file2.py")

        config = ProjectConfig(
            project_id="test",
            project_name="Test",
            project_type=ProjectType.LOCAL,
            connection={
                "build_info_file": str(build_info),
                "file_list_file": str(file_list),
            },
        )

        adapter = LocalProjectAdapter(config)

        with pytest.raises(AdapterError, match="Unsupported file format"):
            adapter.fetch_files()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
