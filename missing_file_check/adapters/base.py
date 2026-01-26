"""
Base adapter interface and data structures.

Defines the unified interface for fetching project scan data from various sources.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class BuildInfo:
    """Build task information containing metadata about the scan execution."""

    build_no: str
    build_status: str  # "success" / "failed"
    branch: str
    commit_id: str
    b_version: str
    build_url: str
    start_time: datetime
    end_time: datetime


@dataclass
class FileEntry:
    """Individual file entry in a scan result."""

    path: str
    status: str  # "success" / "failed"


@dataclass
class ProjectScanResult:
    """Complete scan result for a project including build info and file list."""

    project_id: str
    build_info: BuildInfo
    files: List[FileEntry]


class ProjectAdapter(ABC):
    """
    Abstract base class for project data adapters.

    Adapters provide a unified interface for fetching file lists from various
    data sources (API, FTP, local files, etc.).
    """

    def __init__(self, project_config):
        """
        Initialize adapter with project configuration.

        Args:
            project_config: ProjectConfig instance with connection details
        """
        self.project_config = project_config

    @abstractmethod
    def fetch_files(
        self, commit_id: Optional[str] = None, b_version: Optional[str] = None
    ) -> ProjectScanResult:
        """
        Fetch file list and build information for the project.

        Args:
            commit_id: Optional commit ID filter for baseline selection
            b_version: Optional version filter for baseline selection

        Returns:
            ProjectScanResult with build info and file list

        Raises:
            AdapterError: If fetching fails
        """
        pass


class AdapterError(Exception):
    """Base exception for adapter-related errors."""

    pass
