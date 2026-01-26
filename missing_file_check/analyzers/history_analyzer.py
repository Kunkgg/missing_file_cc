"""
History analyzer for tracking first detection timestamps.

Queries database history to determine when each file was first detected as missing.
"""

from typing import List, Optional

from sqlalchemy.orm import Session

from missing_file_check.analyzers.base import Analyzer
from missing_file_check.scanner.checker import MissingFile
from missing_file_check.storage.repository import MissingFileRepository


class HistoryAnalyzer(Analyzer):
    """
    Analyzer for tracking historical first detection.

    Queries the missing_file_details table to find when each file
    was first detected as missing.
    """

    @property
    def name(self) -> str:
        return "HistoryAnalyzer"

    def analyze(self, missing_files: List[MissingFile], context: dict) -> None:
        """
        Analyze historical detection timestamps.

        Args:
            missing_files: List of files to analyze
            context: Analysis context containing:
                - session: SQLAlchemy session
                - task_id: Optional task ID for filtering
        """
        session = context.get("session")
        if not session:
            # No database session available, skip history analysis
            return

        task_id = context.get("task_id")
        repository = MissingFileRepository(session)

        for file in missing_files:
            if not file.first_detected_at:  # Don't overwrite existing timestamp
                file.first_detected_at = self._get_first_detected_at(
                    repository, file.path, task_id
                )

    def _get_first_detected_at(
        self,
        repository: MissingFileRepository,
        file_path: str,
        task_id: Optional[int],
    ):
        """
        Get first detection timestamp for a file.

        Args:
            repository: Repository instance
            file_path: File path to query
            task_id: Optional task ID for filtering

        Returns:
            First detection datetime or None
        """
        return repository.get_first_detected_at(file_path, task_id)
