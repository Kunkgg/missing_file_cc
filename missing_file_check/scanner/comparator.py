"""
File comparator for identifying missing files using set operations.

Performs efficient O(n) set difference operations to identify files
present in baseline but missing from target.
"""

from typing import Dict, List, Set, Tuple

from missing_file_check.adapters.base import FileEntry


class FileComparator:
    """Compares file lists to identify missing files."""

    @staticmethod
    def find_missing_files(
        baseline_files: Dict[str, Tuple[FileEntry, str]],
        target_files: Dict[str, FileEntry],
    ) -> Set[str]:
        """
        Find files in baseline but not in target (set difference).

        Args:
            baseline_files: Dict of baseline files (path -> (entry, source_project))
            target_files: Dict of target files (path -> entry)

        Returns:
            Set of file paths present in baseline but missing from target
        """
        baseline_paths = set(baseline_files.keys())
        target_paths = set(target_files.keys())

        return baseline_paths - target_paths

    @staticmethod
    def find_failed_files(
        baseline_files: Dict[str, Tuple[FileEntry, str]],
        target_files: Dict[str, FileEntry],
    ) -> List[Tuple[str, str]]:
        """
        Find files that exist in target but have failed status.

        Only includes files that also exist in baseline (intersection).

        Args:
            baseline_files: Dict of baseline files (path -> (entry, source_project))
            target_files: Dict of target files (path -> entry)

        Returns:
            List of tuples (path, source_baseline_project) for failed files
        """
        baseline_paths = set(baseline_files.keys())
        target_paths = set(target_files.keys())

        # Files that exist in both baseline and target
        common_paths = baseline_paths & target_paths

        failed_files = []
        for path in common_paths:
            target_entry = target_files[path]
            if target_entry.status == "failed":
                _, source_project = baseline_files[path]
                failed_files.append((path, source_project))

        return failed_files
