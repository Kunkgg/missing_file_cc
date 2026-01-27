"""
Local file adapter for reading project scan data from local files.

Simplified design: Uses two separate files:
1. build_info_file: JSON file with project_id and build_info
2. file_list_file: CSV or JSON file with file list
"""

import csv
import json
from datetime import datetime
from pathlib import Path
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

    Configuration:
        connection = {
            "build_info_file": "/path/to/build_info.json",  # Contains project_id and build_info
            "file_list_file": "/path/to/files.csv"  # or files.json, contains file list
        }

    build_info.json format:
        {
          "project_id": "project-1",
          "build_info": {
            "build_no": "BUILD-001",
            "build_status": "success",
            "branch": "main",
            "commit_id": "abc123",
            "b_version": "1.0.0",
            "build_url": "https://...",
            "start_time": "2026-01-27T00:00:00Z",
            "end_time": "2026-01-27T00:30:00Z"
          }
        }

    files.csv format:
        file_path,status
        /project/src/main.py,success
        /project/src/test.py,failed

    files.json format:
        [
          {"path": "/project/src/main.py", "status": "success"},
          {"path": "/project/src/test.py", "status": "failed"}
        ]
    """

    def __init__(self, project_config):
        """
        Initialize local file adapter.

        Args:
            project_config: ProjectConfig with local connection details
        """
        super().__init__(project_config)

        # Extract connection details and detect format
        conn = project_config.connection

        # Detect which format is being used
        if "build_info_file" in conn and "file_list_file" in conn:
            # New simplified two-file format
            self.use_new_format = True
            self.build_info_file = Path(conn["build_info_file"])
            self.file_list_file = Path(conn["file_list_file"])
        elif "base_path" in conn:
            # Old format with base_path and file_pattern
            self.use_new_format = False
            self.base_path = Path(conn["base_path"])
            self.file_pattern = conn.get("file_pattern", "*.json")
        else:
            raise ValueError(
                "Invalid connection config for LOCAL adapter. "
                "Requires either {'build_info_file', 'file_list_file'} or {'base_path'}"
            )

    def fetch_files(
        self, commit_id: Optional[str] = None, b_version: Optional[str] = None
    ) -> ProjectScanResult:
        """
        Fetch file list from local files.

        Args:
            commit_id: Optional commit ID filter (validates against build_info)
            b_version: Optional version filter (validates against build_info)

        Returns:
            ProjectScanResult with build info and file list

        Raises:
            AdapterError: If file not found or parsing fails
        """
        try:
            if self.use_new_format:
                return self._fetch_new_format(commit_id, b_version)
            else:
                return self._fetch_old_format(commit_id, b_version)

        except FileNotFoundError as e:
            raise AdapterError(
                f"File not found for project {self.project_config.project_id}: {e}"
            )
        except json.JSONDecodeError as e:
            raise AdapterError(
                f"Invalid JSON for project {self.project_config.project_id}: {e}"
            )
        except KeyError as e:
            raise AdapterError(
                f"Missing required field for project {self.project_config.project_id}: {e}"
            )
        except Exception as e:
            raise AdapterError(
                f"Unexpected error for project {self.project_config.project_id}: {e}"
            )

    def _fetch_new_format(
        self, commit_id: Optional[str] = None, b_version: Optional[str] = None
    ) -> ProjectScanResult:
        """Fetch using new two-file format."""
        # Step 1: Load build info
        build_info, project_id = self._load_build_info()

        # Step 2: Validate filters
        if commit_id and build_info.commit_id != commit_id:
            raise AdapterError(
                f"Build commit_id '{build_info.commit_id}' does not match "
                f"requested '{commit_id}' for project {project_id}"
            )
        if b_version and build_info.b_version != b_version:
            raise AdapterError(
                f"Build b_version '{build_info.b_version}' does not match "
                f"requested '{b_version}' for project {project_id}"
            )

        # Step 3: Load file list
        files = self._load_file_list()

        return ProjectScanResult(
            project_id=project_id,
            build_info=build_info,
            files=files,
        )

    def _fetch_old_format(
        self, commit_id: Optional[str] = None, b_version: Optional[str] = None
    ) -> ProjectScanResult:
        """Fetch using old single-file format with base_path."""
        # Find matching file
        import glob

        pattern = str(self.base_path / self.file_pattern)
        matching_files = glob.glob(pattern)

        if not matching_files:
            raise FileNotFoundError(f"No files matching pattern: {pattern}")

        # Use the first matching file
        file_path = Path(matching_files[0])

        # Load JSON data
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Parse old format
        project_id = data.get("project_id", self.project_config.project_id)
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

        # Validate filters
        if commit_id and build_info.commit_id != commit_id:
            raise AdapterError(
                f"Build commit_id '{build_info.commit_id}' does not match "
                f"requested '{commit_id}' for project {project_id}"
            )
        if b_version and build_info.b_version != b_version:
            raise AdapterError(
                f"Build b_version '{build_info.b_version}' does not match "
                f"requested '{b_version}' for project {project_id}"
            )

        # Parse file list
        files = []
        files_data = data.get("files", [])

        for item in files_data:
            if isinstance(item, str):
                files.append(FileEntry(path=item, status="success"))
            elif isinstance(item, dict):
                path = item.get("path") or item.get("file_path")
                status = item.get("status", "success")
                if path:
                    files.append(FileEntry(path=path, status=status))

        return ProjectScanResult(
            project_id=project_id,
            build_info=build_info,
            files=files,
        )

    def _load_build_info(self) -> tuple:
        """
        Load build info from JSON file.

        Returns:
            Tuple of (BuildInfo, project_id)

        Raises:
            FileNotFoundError: If file not found
            json.JSONDecodeError: If invalid JSON
            KeyError: If required fields missing
        """
        if not self.build_info_file.exists():
            raise FileNotFoundError(f"Build info file not found: {self.build_info_file}")

        with open(self.build_info_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Extract project_id
        project_id = data.get("project_id", self.project_config.project_id)

        # Extract build_info
        build_data = data.get("build_info", data)  # Support both formats

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

        return build_info, project_id

    def _load_file_list(self) -> List[FileEntry]:
        """
        Load file list from CSV or JSON file.

        Returns:
            List of FileEntry objects

        Raises:
            FileNotFoundError: If file not found
            ValueError: If file format not supported
        """
        if not self.file_list_file.exists():
            raise FileNotFoundError(f"File list file not found: {self.file_list_file}")

        # Detect file format by extension
        if self.file_list_file.suffix.lower() == ".csv":
            return self._load_file_list_csv()
        elif self.file_list_file.suffix.lower() == ".json":
            return self._load_file_list_json()
        else:
            raise ValueError(
                f"Unsupported file format: {self.file_list_file.suffix}. "
                "Supported formats: .csv, .json"
            )

    def _load_file_list_csv(self) -> List[FileEntry]:
        """Load file list from CSV file."""
        files = []

        with open(self.file_list_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            # Support both column names
            for row in reader:
                # Try different column name variations
                path = row.get("file_path") or row.get("path") or row.get("Path")
                status = row.get("status") or row.get("Status") or "success"

                if not path:
                    continue  # Skip rows without path

                files.append(FileEntry(path=path.strip(), status=status.strip()))

        return files

    def _load_file_list_json(self) -> List[FileEntry]:
        """Load file list from JSON file."""
        with open(self.file_list_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        files = []

        # Support both list and dict formats
        if isinstance(data, list):
            for item in data:
                if isinstance(item, str):
                    # Simple string list
                    files.append(FileEntry(path=item, status="success"))
                elif isinstance(item, dict):
                    # List of objects
                    path = item.get("path") or item.get("file_path")
                    status = item.get("status", "success")
                    if path:
                        files.append(FileEntry(path=path, status=status))
        elif isinstance(data, dict):
            # Dict format with "files" key
            files_data = data.get("files", [])
            for item in files_data:
                if isinstance(item, str):
                    files.append(FileEntry(path=item, status="success"))
                elif isinstance(item, dict):
                    path = item.get("path") or item.get("file_path")
                    status = item.get("status", "success")
                    if path:
                        files.append(FileEntry(path=path, status=status))

        return files

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
