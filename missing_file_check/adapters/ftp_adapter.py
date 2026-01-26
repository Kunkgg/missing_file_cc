"""
FTP adapter for downloading and parsing project scan data from FTP servers.

Supports downloading scan result files from FTP servers and parsing them.
"""

import io
import json
from datetime import datetime
from ftplib import FTP, error_perm
from typing import List, Optional

from missing_file_check.adapters.base import (
    ProjectAdapter,
    BuildInfo,
    FileEntry,
    ProjectScanResult,
    AdapterError,
)
from missing_file_check.config.models import ProjectType


class FTPProjectAdapter(ProjectAdapter):
    """
    Adapter for FTP-based project data sources.

    Downloads scan result files from FTP server and parses them.
    Supports both JSON and plain text file lists.
    """

    def __init__(self, project_config):
        """
        Initialize FTP adapter.

        Args:
            project_config: ProjectConfig with FTP connection details
        """
        super().__init__(project_config)

        # Extract connection details
        conn = project_config.connection
        self.host = conn["host"]
        self.username = conn["username"]
        self.password = conn["password"]
        self.base_path = conn["base_path"]
        self.port = conn.get("port", 21)
        self.timeout = conn.get("timeout", 30)
        self.file_pattern = conn.get("file_pattern", "*.json")

    def fetch_files(
        self, commit_id: Optional[str] = None, b_version: Optional[str] = None
    ) -> ProjectScanResult:
        """
        Fetch file list from FTP server.

        Args:
            commit_id: Optional commit ID filter
            b_version: Optional version filter

        Returns:
            ProjectScanResult with build info and file list

        Raises:
            AdapterError: If FTP connection fails or file not found
        """
        ftp = None
        try:
            # Connect to FTP server
            ftp = self._connect_ftp()

            # Find and download scan file
            scan_file_content = self._download_scan_file(ftp, commit_id, b_version)

            # Parse scan result
            data = json.loads(scan_file_content)

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

        except error_perm as e:
            raise AdapterError(
                f"FTP permission error for project {self.project_config.project_id}: {e}"
            )
        except json.JSONDecodeError as e:
            raise AdapterError(
                f"Invalid JSON in FTP file for project {self.project_config.project_id}: {e}"
            )
        except Exception as e:
            raise AdapterError(
                f"FTP error for project {self.project_config.project_id}: {e}"
            )
        finally:
            if ftp:
                try:
                    ftp.quit()
                except Exception:
                    pass

    def _connect_ftp(self) -> FTP:
        """
        Connect to FTP server.

        Returns:
            Connected FTP client

        Raises:
            AdapterError: If connection fails
        """
        try:
            ftp = FTP()
            ftp.connect(self.host, self.port, timeout=self.timeout)
            ftp.login(self.username, self.password)
            return ftp
        except Exception as e:
            raise AdapterError(f"Failed to connect to FTP server {self.host}: {e}")

    def _download_scan_file(
        self, ftp: FTP, commit_id: Optional[str], b_version: Optional[str]
    ) -> str:
        """
        Download scan file from FTP server.

        Args:
            ftp: Connected FTP client
            commit_id: Optional commit ID filter
            b_version: Optional version filter

        Returns:
            File content as string

        Raises:
            AdapterError: If file not found or download fails
        """
        try:
            # Change to base directory
            ftp.cwd(self.base_path)

            # List files matching pattern
            files = []
            try:
                files = ftp.nlst(self.file_pattern)
            except error_perm:
                # No files match pattern
                raise AdapterError(
                    f"No scan files found in {self.base_path} matching {self.file_pattern}"
                )

            if not files:
                raise AdapterError(
                    f"No scan files found in {self.base_path}"
                )

            # If no filters, use most recent file
            if not commit_id and not b_version:
                # Get file with latest modification time
                file_info = []
                for filename in files:
                    try:
                        # Get modification time
                        response = ftp.sendcmd(f"MDTM {filename}")
                        mdtm = response.split()[1]
                        file_info.append((filename, mdtm))
                    except Exception:
                        # If MDTM not supported, use first file
                        return self._download_file(ftp, files[0])

                if file_info:
                    # Sort by modification time, newest first
                    file_info.sort(key=lambda x: x[1], reverse=True)
                    return self._download_file(ftp, file_info[0][0])

            # If filters specified, search for matching file
            for filename in files:
                content = self._download_file(ftp, filename)
                try:
                    data = json.loads(content)
                    build_info = data.get("build_info", {})

                    # Check filters
                    if commit_id and build_info.get("commit_id") == commit_id:
                        return content
                    if b_version and build_info.get("b_version") == b_version:
                        return content

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

        except error_perm as e:
            raise AdapterError(f"FTP permission error accessing {self.base_path}: {e}")

    def _download_file(self, ftp: FTP, filename: str) -> str:
        """
        Download a single file from FTP.

        Args:
            ftp: Connected FTP client
            filename: File to download

        Returns:
            File content as string
        """
        buffer = io.BytesIO()
        ftp.retrbinary(f"RETR {filename}", buffer.write)
        buffer.seek(0)
        return buffer.read().decode("utf-8")

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
    """Register FTP adapter with factory on import."""
    from missing_file_check.adapters.factory import AdapterFactory

    AdapterFactory.register(ProjectType.FTP, FTPProjectAdapter)


_register()
