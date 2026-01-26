"""
Path normalizer for converting absolute paths to relative paths.

Uses path prefix configuration to strip project-specific prefixes and
normalize all paths for comparison.
"""

from typing import Dict, List

from missing_file_check.config.models import PathPrefixConfig


class PathNormalizer:
    """Normalizes file paths to relative paths for comparison."""

    def __init__(self, path_prefixes: List[PathPrefixConfig]):
        """
        Initialize normalizer with path prefix configurations.

        Args:
            path_prefixes: List of path prefix configs by project
        """
        # Build lookup map: project_id -> prefix
        self._prefix_map: Dict[str, str] = {
            config.project_id: config.prefix for config in path_prefixes
        }

    def normalize(self, path: str, project_id: str) -> str:
        """
        Normalize a file path to relative form.

        Args:
            path: Absolute or relative file path
            project_id: Project ID for prefix lookup

        Returns:
            Normalized relative path with forward slashes
        """
        # Get prefix for this project (if configured)
        prefix = self._prefix_map.get(project_id, "")

        # Normalize path separators to forward slashes
        normalized = path.replace("\\", "/")

        # Strip prefix if present
        if prefix and normalized.startswith(prefix):
            normalized = normalized[len(prefix) :]

        # Remove leading slash if present
        normalized = normalized.lstrip("/")

        return normalized
