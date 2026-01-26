"""
API adapter for fetching project scan data from REST API endpoints.

Supports both TARGET_PROJECT_API and BASELINE_PROJECT_API types.
"""

import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests

from missing_file_check.adapters.base import (
    ProjectAdapter,
    BuildInfo,
    FileEntry,
    ProjectScanResult,
    AdapterError,
)
from missing_file_check.config.models import ProjectType


class APIProjectAdapter(ProjectAdapter):
    """
    Adapter for API-based project data sources.

    Fetches scan results from REST API endpoints with support for:
    - Latest successful build queries
    - commit_id and b_version filtering
    - Pagination for large file lists
    - Retry logic for transient failures
    """

    def __init__(self, project_config):
        """
        Initialize API adapter.

        Args:
            project_config: ProjectConfig with API connection details
        """
        super().__init__(project_config)

        # Extract connection details
        conn = project_config.connection
        self.api_endpoint = conn["api_endpoint"].rstrip("/")
        self.token = conn["token"]
        self.project_key = conn["project_key"]

        # Request configuration
        self.timeout = conn.get("timeout", 30)
        self.max_retries = conn.get("max_retries", 3)
        self.retry_delay = conn.get("retry_delay", 1)

        # Prepare headers
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def fetch_files(
        self, commit_id: Optional[str] = None, b_version: Optional[str] = None
    ) -> ProjectScanResult:
        """
        Fetch file list and build info from API.

        Args:
            commit_id: Optional commit ID filter
            b_version: Optional version filter

        Returns:
            ProjectScanResult with build info and file list

        Raises:
            AdapterError: If API request fails or data is invalid
        """
        try:
            # Step 1: Query for build task
            build_info = self._fetch_build_info(commit_id, b_version)

            # Step 2: Fetch file list for the build
            files = self._fetch_file_list(build_info.build_no)

            return ProjectScanResult(
                project_id=self.project_config.project_id,
                build_info=build_info,
                files=files,
            )

        except requests.RequestException as e:
            raise AdapterError(
                f"API request failed for project {self.project_config.project_id}: {e}"
            )
        except KeyError as e:
            raise AdapterError(
                f"Invalid API response format for project {self.project_config.project_id}: "
                f"missing field {e}"
            )
        except Exception as e:
            raise AdapterError(
                f"Unexpected error fetching project {self.project_config.project_id}: {e}"
            )

    def _fetch_build_info(
        self, commit_id: Optional[str], b_version: Optional[str]
    ) -> BuildInfo:
        """
        Fetch build information from API.

        Query for latest successful build matching filters.

        Args:
            commit_id: Optional commit ID filter
            b_version: Optional version filter

        Returns:
            BuildInfo for the selected build

        Raises:
            AdapterError: If no matching build found
        """
        # Build query parameters
        params: Dict[str, Any] = {
            "project_key": self.project_key,
            "status": "success",
            "limit": 1,
            "order_by": "start_time",
            "order": "desc",
        }

        if commit_id:
            params["commit_id"] = commit_id
        if b_version:
            params["b_version"] = b_version

        # Make API request
        url = urljoin(self.api_endpoint, "/api/v1/builds")
        response = self._make_request("GET", url, params=params)

        # Parse response
        builds = response.get("data", [])
        if not builds:
            filters = []
            if commit_id:
                filters.append(f"commit_id={commit_id}")
            if b_version:
                filters.append(f"b_version={b_version}")
            filter_str = ", ".join(filters) if filters else "no filters"
            raise AdapterError(
                f"No successful build found for project {self.project_key} "
                f"with {filter_str}"
            )

        build_data = builds[0]

        # Parse build info
        return BuildInfo(
            build_no=build_data["build_no"],
            build_status=build_data["build_status"],
            branch=build_data["branch"],
            commit_id=build_data["commit_id"],
            b_version=build_data.get("b_version", ""),
            build_url=build_data.get("build_url", ""),
            start_time=self._parse_datetime(build_data["start_time"]),
            end_time=self._parse_datetime(build_data["end_time"]),
        )

    def _fetch_file_list(self, build_no: str) -> List[FileEntry]:
        """
        Fetch file list for a build.

        Handles pagination for large file lists.

        Args:
            build_no: Build number

        Returns:
            List of FileEntry objects

        Raises:
            AdapterError: If API request fails
        """
        all_files = []
        page = 1
        page_size = 1000

        while True:
            # Build query parameters
            params = {
                "build_no": build_no,
                "page": page,
                "page_size": page_size,
            }

            # Make API request
            url = urljoin(self.api_endpoint, "/api/v1/scan-files")
            response = self._make_request("GET", url, params=params)

            # Parse files
            files_data = response.get("data", [])
            for file_data in files_data:
                all_files.append(
                    FileEntry(
                        path=file_data["file_path"],
                        status=file_data.get("status", "success"),
                    )
                )

            # Check if there are more pages
            pagination = response.get("pagination", {})
            total_pages = pagination.get("total_pages", 1)

            if page >= total_pages:
                break

            page += 1

        return all_files

    def _make_request(
        self,
        method: str,
        url: str,
        params: Optional[Dict] = None,
        json: Optional[Dict] = None,
    ) -> Dict:
        """
        Make HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            params: Query parameters
            json: JSON body

        Returns:
            Parsed JSON response

        Raises:
            requests.RequestException: If all retries fail
        """
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    params=params,
                    json=json,
                    timeout=self.timeout,
                )

                # Check for HTTP errors
                response.raise_for_status()

                # Parse JSON
                return response.json()

            except requests.RequestException as e:
                last_exception = e

                # Don't retry on client errors (4xx)
                if hasattr(e, "response") and e.response is not None:
                    if 400 <= e.response.status_code < 500:
                        raise

                # Retry on server errors (5xx) and network errors
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue

        # All retries exhausted
        raise last_exception

    def _parse_datetime(self, dt_str: str) -> datetime:
        """
        Parse datetime string from API response.

        Supports multiple formats.

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

        # Fallback: try parsing as timestamp
        try:
            return datetime.fromtimestamp(float(dt_str))
        except (ValueError, TypeError):
            pass

        raise ValueError(f"Unable to parse datetime: {dt_str}")


# Auto-register adapter with factory
def _register():
    """Register API adapter with factory on import."""
    from missing_file_check.adapters.factory import AdapterFactory

    AdapterFactory.register(ProjectType.TARGET_PROJECT_API, APIProjectAdapter)
    AdapterFactory.register(ProjectType.BASELINE_PROJECT_API, APIProjectAdapter)


_register()
