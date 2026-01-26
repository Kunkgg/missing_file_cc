"""
File list merger for combining multiple project file lists.

Merges file lists from multiple projects into a unified set while tracking
the source project for each file.
"""

from typing import Dict, List, Tuple

from missing_file_check.adapters.base import FileEntry, ProjectScanResult
from missing_file_check.scanner.normalizer import PathNormalizer


class FileMerger:
    """Merges file lists from multiple projects into unified sets."""

    def __init__(self, path_normalizer: PathNormalizer):
        """
        Initialize merger with a path normalizer.

        Args:
            path_normalizer: PathNormalizer instance for normalizing paths
        """
        self.path_normalizer = path_normalizer

    def merge_target_files(
        self, target_results: List[ProjectScanResult]
    ) -> Dict[str, FileEntry]:
        """
        Merge all target project file lists into a single set.

        Args:
            target_results: List of target project scan results

        Returns:
            Dictionary mapping normalized path to FileEntry
            (uses latest entry if path appears in multiple projects)
        """
        merged: Dict[str, FileEntry] = {}

        for result in target_results:
            for file in result.files:
                normalized_path = self.path_normalizer.normalize(
                    file.path, result.project_id
                )
                # For target files, we keep the latest occurrence
                # This handles duplicate files across target projects
                merged[normalized_path] = file

        return merged

    def merge_baseline_files(
        self, baseline_results: List[ProjectScanResult]
    ) -> Dict[str, Tuple[FileEntry, str]]:
        """
        Merge all baseline project file lists into a single set.

        Args:
            baseline_results: List of baseline project scan results

        Returns:
            Dictionary mapping normalized path to (FileEntry, source_project_id)
            Only keeps first occurrence of each path to track original source
        """
        merged: Dict[str, Tuple[FileEntry, str]] = {}

        for result in baseline_results:
            for file in result.files:
                normalized_path = self.path_normalizer.normalize(
                    file.path, result.project_id
                )
                # Only keep first occurrence to track which baseline it came from
                if normalized_path not in merged:
                    merged[normalized_path] = (file, result.project_id)

        return merged
