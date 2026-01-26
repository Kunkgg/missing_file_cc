"""
Local file adapter for reading project scan data from local files.

Supports reading scan results stored as JSON files on the local filesystem.
"""

import json
import os
from datetime import datetime
from glob import glob
from typing import List, Optional

from missing_file_check.adapters.base import (
    ProjectAdapter,
    BuildInfo,
    FileEntry,
    ProjectScanResult,
    AdapterError,
)
from missing_file_check.config.models import ProjectType


class LocalProjectAdapter(ProjectAdapter):
    """
    Adapter for local file-based project data sources.

    Reads scan results from JSON files in the local filesystem.
    Supports file pattern matching to find the latest scan result.
    """

    def __init__(self, project_config):
        """
        Initialize local file adapter.

        Args:
            project_config: ProjectConfig with local connection details
        """
        super().__init__(project_config)

        # Extract connection details
        conn = project_config.connection
        self.base_path = conn["base_path"]
        self.file_pattern = conn.get("file_pattern", "*.json")

    def fetch_files(
        self, commit_id: Optional[str] = None, b_version: Optional[str] = None
    ) -> ProjectScanResult:
        """
        Fetch file list from local JSON file.

        Args:
            commit_id: Optional commit ID filter
            b_version: Optional version filter

        Returns:
            ProjectScanResult with build info and file list

        Raises:
            AdapterError: If file not found or parsing fails
        """
        try:
            # Find matching files
            scan_file = self._find_scan_file(commit_id, b_version)

            # Parse scan result
            with open(scan_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Parse build info
            build_data = data.get("build_info", {})
            build_info = BuildInfo(
                build_no=build_data.get("build_no", "unknown"),
                build_status=build_data.get("build_status", "success"),
                branch=build_data.get("branch", "main"),
                commit_id=build_data.get("commit_id", ""),
                b_version=build_data.get("b_version", ""),
                build_url=build_data.get("build_url", ""),
                start_time=self._parse_datetime(
                    build_data.get("start_time", datetime.now().isoformat())
                ),
                end_time=self._parse_datetime(
                    build_data.get("end_time", datetime.now().isoformat())
                ),
            )

            # Apply filters if specified
            if commit_id and build_info.commit_id != commit_id:
                raise AdapterError(
                    f"No scan file found with commit_id={commit_id} for project "
                    f"{self.project_config.project_id}"
                )
            if b_version and build_info.b_version != b_version:
                raise AdapterError(
                    f"No scan file found with b_version={b_version} for project "
                    f"{self.project_config.project_id}"
                )

            # Parse file list
            files_data = data.get("files", [])
            files = [
                FileEntry(
                    path=file_data["path"] if isinstance(file_data, dict) else file_data,
                    status=file_data.get("status", "success")
                    if isinstance(file_data, dict)
                    else "success",
                )
                for file_data in files_data
            ]

            return ProjectScanResult(
                project_id=self.project_config.project_id,
                build_info=build_info,
                files=files,
            )

        except FileNotFoundError as e:
            raise AdapterError(
                f"Scan file not found for project {self.project_config.project_id}: {e}"
            )
        except json.JSONDecodeError as e:
            raise AdapterError(
                f"Invalid JSON in scan file for project {self.project_config.project_id}: {e}"
            )
        except KeyError as e:
            raise AdapterError(
                f"Missing required field in scan file for project "
                f"{self.project_config.project_id}: {e}"
            )
        except Exception as e:
            raise AdapterError(
                f"Unexpected error reading scan file for project "
                f"{self.project_config.project_id}: {e}"
            )

    def _find_scan_file(
        self, commit_id: Optional[str], b_version: Optional[str]
    ) -> str:
        """
        Find the appropriate scan file.

        If filters are specified, looks for matching file.
        Otherwise, returns the most recent file.

        Args:
            commit_id: Optional commit ID filter
            b_version: Optional version filter

        Returns:
            Path to the scan file

        Raises:
            AdapterError: If no matching file found
        """
        # Build search pattern
        pattern = os.path.join(self.base_path, self.file_pattern)

        # Find matching files
        files = glob(pattern)

        if not files:
            raise AdapterError(
                f"No scan files found matching pattern: {pattern}"
            )

        # If no filters, return most recent file
        if not commit_id and not b_version:
            # Sort by modification time, newest first
            files.sort(key=os.path.getmtime, reverse=True)
            return files[0]

        # If filters specified, search for matching file
        for file_path in files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    build_info = data.get("build_info", {})

                    # Check filters
                    if commit_id and build_info.get("commit_id") == commit_id:
                        return file_path
                    if b_version and build_info.get("b_version") == b_version:
                        return file_path

            except (json.JSONDecodeError, KeyError):
                # Skip invalid files
                continue

        # No matching file found
        filters = []
        if commit_id:
            filters.append(f"commit_id={commit_id}")
        if b_version:
            filters.append(f"b_version={b_version}")
        raise AdapterError(
            f"No scan file found matching filters: {', '.join(filters)}"
        )

    def _parse_datetime(self, dt_str: str) -> datetime:
        """
        Parse datetime string from JSON file.

        Args:
            dt_str: Datetime string

        Returns:
            Parsed datetime object
        """
        # Try ISO format first
        for fmt in [
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
        ]:
            try:
                return datetime.strptime(dt_str, fmt)
            except ValueError:
                continue

        # Fallback to current time
        return datetime.now()


# Auto-register adapter with factory
def _register():
    """Register local adapter with factory on import."""
    from missing_file_check.adapters.factory import AdapterFactory

    AdapterFactory.register(ProjectType.LOCAL, LocalProjectAdapter)


_register()
