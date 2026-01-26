"""Adapter module for unified data source access."""

from missing_file_check.adapters.base import (
    ProjectAdapter,
    BuildInfo,
    FileEntry,
    ProjectScanResult,
)

# Import adapters to trigger auto-registration
from missing_file_check.adapters import api_adapter
from missing_file_check.adapters import local_adapter
from missing_file_check.adapters import ftp_adapter

__all__ = [
    "ProjectAdapter",
    "BuildInfo",
    "FileEntry",
    "ProjectScanResult",
]
