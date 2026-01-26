"""
Integration tests for all adapters.

Tests API, FTP, and Local file adapters with mock data and servers.
"""

import json
import os
import pytest
from unittest.mock import Mock, patch, MagicMock

from missing_file_check.config.models import ProjectConfig, ProjectType
from missing_file_check.adapters.api_adapter import APIProjectAdapter
from missing_file_check.adapters.local_adapter import LocalProjectAdapter
from missing_file_check.adapters.ftp_adapter import FTPProjectAdapter
from missing_file_check.adapters.factory import AdapterFactory


class TestLocalAdapter:
    """Test local file adapter with actual test files."""

    def test_fetch_files_from_json(self):
        """Test fetching files from local JSON file."""
        config = ProjectConfig(
            project_id="local-target",
            project_name="Local Target Project",
            project_type=ProjectType.LOCAL,
            connection={
                "base_path": "test_data",
                "file_pattern": "target_scan_result.json",
            },
        )

        adapter = LocalProjectAdapter(config)
        result = adapter.fetch_files()

        assert result.project_id == "local-target"
        assert result.build_info.build_no == "BUILD-TARGET-001"
        assert result.build_info.commit_id == "abc123def456"
        assert result.build_info.b_version == "1.0.0"
        assert len(result.files) == 5

        # Check file paths
        paths = [f.path for f in result.files]
        assert "/project/src/main.py" in paths
        assert "/project/tests/test_main.py" in paths

        # Check file status
        failed_files = [f for f in result.files if f.status == "failed"]
        assert len(failed_files) == 1
        assert failed_files[0].path == "/project/tests/test_main.py"

    def test_fetch_with_commit_id_filter(self):
        """Test fetching with commit_id filter."""
        config = ProjectConfig(
            project_id="local-baseline",
            project_name="Local Baseline Project",
            project_type=ProjectType.LOCAL,
            connection={
                "base_path": "test_data",
                "file_pattern": "baseline_scan_result.json",
            },
        )

        adapter = LocalProjectAdapter(config)
        result = adapter.fetch_files(commit_id="abc123def456")

        assert result.build_info.commit_id == "abc123def456"
        assert len(result.files) == 10

    def test_fetch_with_version_filter(self):
        """Test fetching with b_version filter."""
        config = ProjectConfig(
            project_id="local-baseline",
            project_name="Local Baseline Project",
            project_type=ProjectType.LOCAL,
            connection={
                "base_path": "test_data",
                "file_pattern": "*.json",
            },
        )

        adapter = LocalProjectAdapter(config)
        result = adapter.fetch_files(b_version="1.0.0")

        assert result.build_info.b_version == "1.0.0"

    def test_file_not_found(self):
        """Test error handling when file doesn't exist."""
        config = ProjectConfig(
            project_id="local-missing",
            project_name="Missing Project",
            project_type=ProjectType.LOCAL,
            connection={
                "base_path": "test_data",
                "file_pattern": "nonexistent.json",
            },
        )

        adapter = LocalProjectAdapter(config)
        with pytest.raises(Exception):  # AdapterError
            adapter.fetch_files()


class TestAPIAdapter:
    """Test API adapter with mocked requests."""

    @patch("missing_file_check.adapters.api_adapter.requests.request")
    def test_fetch_files_from_api(self, mock_request):
        """Test fetching files from API with mocked responses."""
        # Mock build info response
        build_response = Mock()
        build_response.status_code = 200
        build_response.json.return_value = {
            "data": [
                {
                    "build_no": "BUILD-API-001",
                    "build_status": "success",
                    "branch": "main",
                    "commit_id": "xyz789",
                    "b_version": "2.0.0",
                    "build_url": "https://example.com/build/001",
                    "start_time": "2026-01-27T10:00:00Z",
                    "end_time": "2026-01-27T10:30:00Z",
                }
            ]
        }

        # Mock file list response
        files_response = Mock()
        files_response.status_code = 200
        files_response.json.return_value = {
            "data": [
                {"file_path": "/api/src/main.py", "status": "success"},
                {"file_path": "/api/src/utils.py", "status": "success"},
                {"file_path": "/api/src/config.py", "status": "failed"},
            ],
            "pagination": {"total_pages": 1},
        }

        # Configure mock to return different responses
        mock_request.side_effect = [build_response, files_response]

        # Create adapter
        config = ProjectConfig(
            project_id="api-target",
            project_name="API Target Project",
            project_type=ProjectType.TARGET_PROJECT_API,
            connection={
                "api_endpoint": "https://api.example.com",
                "token": "test-token",
                "project_key": "API-TARGET",
            },
        )

        adapter = APIProjectAdapter(config)
        result = adapter.fetch_files()

        assert result.project_id == "api-target"
        assert result.build_info.build_no == "BUILD-API-001"
        assert result.build_info.commit_id == "xyz789"
        assert len(result.files) == 3

        # Verify failed file
        failed_files = [f for f in result.files if f.status == "failed"]
        assert len(failed_files) == 1
        assert failed_files[0].path == "/api/src/config.py"

    @patch("missing_file_check.adapters.api_adapter.requests.request")
    def test_fetch_with_filters(self, mock_request):
        """Test API fetch with commit_id filter."""
        build_response = Mock()
        build_response.status_code = 200
        build_response.json.return_value = {
            "data": [
                {
                    "build_no": "BUILD-002",
                    "build_status": "success",
                    "branch": "feature",
                    "commit_id": "filtered123",
                    "b_version": "2.1.0",
                    "build_url": "https://example.com/build/002",
                    "start_time": "2026-01-27T11:00:00Z",
                    "end_time": "2026-01-27T11:30:00Z",
                }
            ]
        }

        files_response = Mock()
        files_response.status_code = 200
        files_response.json.return_value = {
            "data": [{"file_path": "/api/test.py", "status": "success"}],
            "pagination": {"total_pages": 1},
        }

        mock_request.side_effect = [build_response, files_response]

        config = ProjectConfig(
            project_id="api-filtered",
            project_name="Filtered API Project",
            project_type=ProjectType.BASELINE_PROJECT_API,
            connection={
                "api_endpoint": "https://api.example.com",
                "token": "test-token",
                "project_key": "API-BASE",
            },
        )

        adapter = APIProjectAdapter(config)
        result = adapter.fetch_files(commit_id="filtered123")

        assert result.build_info.commit_id == "filtered123"
        assert len(result.files) == 1

    @patch("missing_file_check.adapters.api_adapter.requests.request")
    def test_pagination_handling(self, mock_request):
        """Test API adapter handles pagination correctly."""
        build_response = Mock()
        build_response.status_code = 200
        build_response.json.return_value = {
            "data": [
                {
                    "build_no": "BUILD-003",
                    "build_status": "success",
                    "branch": "main",
                    "commit_id": "page123",
                    "b_version": "3.0.0",
                    "build_url": "https://example.com/build/003",
                    "start_time": "2026-01-27T12:00:00Z",
                    "end_time": "2026-01-27T12:30:00Z",
                }
            ]
        }

        # Mock paginated file responses
        page1_response = Mock()
        page1_response.status_code = 200
        page1_response.json.return_value = {
            "data": [
                {"file_path": "/api/file1.py", "status": "success"},
                {"file_path": "/api/file2.py", "status": "success"},
            ],
            "pagination": {"total_pages": 2},
        }

        page2_response = Mock()
        page2_response.status_code = 200
        page2_response.json.return_value = {
            "data": [
                {"file_path": "/api/file3.py", "status": "success"},
            ],
            "pagination": {"total_pages": 2},
        }

        mock_request.side_effect = [build_response, page1_response, page2_response]

        config = ProjectConfig(
            project_id="api-paginated",
            project_name="Paginated API Project",
            project_type=ProjectType.TARGET_PROJECT_API,
            connection={
                "api_endpoint": "https://api.example.com",
                "token": "test-token",
                "project_key": "API-PAGE",
            },
        )

        adapter = APIProjectAdapter(config)
        result = adapter.fetch_files()

        # Should have collected files from both pages
        assert len(result.files) == 3


class TestFTPAdapter:
    """Test FTP adapter with mocked FTP server."""

    @patch("missing_file_check.adapters.ftp_adapter.FTP")
    def test_fetch_files_from_ftp(self, mock_ftp_class):
        """Test fetching files from FTP server."""
        # Create mock FTP instance
        mock_ftp = MagicMock()
        mock_ftp_class.return_value = mock_ftp

        # Mock FTP operations
        mock_ftp.nlst.return_value = ["scan_result.json"]

        # Mock file download
        scan_data = {
            "build_info": {
                "build_no": "BUILD-FTP-001",
                "build_status": "success",
                "branch": "main",
                "commit_id": "ftp123",
                "b_version": "1.5.0",
                "build_url": "https://example.com/ftp/001",
                "start_time": "2026-01-27T08:00:00Z",
                "end_time": "2026-01-27T08:30:00Z",
            },
            "files": [
                {"path": "/ftp/src/main.py", "status": "success"},
                {"path": "/ftp/src/utils.py", "status": "success"},
            ],
        }

        def mock_retrbinary(cmd, callback):
            content = json.dumps(scan_data).encode("utf-8")
            callback(content)

        mock_ftp.retrbinary.side_effect = mock_retrbinary

        # Create adapter
        config = ProjectConfig(
            project_id="ftp-target",
            project_name="FTP Target Project",
            project_type=ProjectType.FTP,
            connection={
                "host": "ftp.example.com",
                "username": "user",
                "password": "pass",
                "base_path": "/scans",
            },
        )

        adapter = FTPProjectAdapter(config)
        result = adapter.fetch_files()

        assert result.project_id == "ftp-target"
        assert result.build_info.build_no == "BUILD-FTP-001"
        assert result.build_info.commit_id == "ftp123"
        assert len(result.files) == 2

        # Verify FTP operations were called
        mock_ftp.connect.assert_called_once()
        mock_ftp.login.assert_called_once_with("user", "pass")
        mock_ftp.cwd.assert_called_once_with("/scans")


class TestAdapterFactory:
    """Test adapter factory registration and creation."""

    def test_factory_creates_correct_adapters(self):
        """Test that factory creates the correct adapter type."""
        # Test LOCAL adapter
        local_config = ProjectConfig(
            project_id="test-local",
            project_name="Test Local",
            project_type=ProjectType.LOCAL,
            connection={"base_path": "/test"},
        )
        local_adapter = AdapterFactory.create(local_config)
        assert isinstance(local_adapter, LocalProjectAdapter)

        # Test API adapters
        api_config = ProjectConfig(
            project_id="test-api",
            project_name="Test API",
            project_type=ProjectType.TARGET_PROJECT_API,
            connection={
                "api_endpoint": "https://api.test.com",
                "token": "test",
                "project_key": "TEST",
            },
        )
        api_adapter = AdapterFactory.create(api_config)
        assert isinstance(api_adapter, APIProjectAdapter)

        # Test FTP adapter
        ftp_config = ProjectConfig(
            project_id="test-ftp",
            project_name="Test FTP",
            project_type=ProjectType.FTP,
            connection={
                "host": "ftp.test.com",
                "username": "user",
                "password": "pass",
                "base_path": "/",
            },
        )
        ftp_adapter = AdapterFactory.create(ftp_config)
        assert isinstance(ftp_adapter, FTPProjectAdapter)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
