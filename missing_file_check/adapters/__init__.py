"""Adapter module for unified data source access."""

from missing_file_check.adapters.base import (
    ProjectAdapter,
    BuildInfo,
    FileEntry,
    ProjectScanResult,
)

__all__ = [
    "ProjectAdapter",
    "BuildInfo",
    "FileEntry",
    "ProjectScanResult",
]
