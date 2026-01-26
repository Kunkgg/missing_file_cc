"""
Base analyzer interface.

Defines the common interface for all analyzers.
"""

from abc import ABC, abstractmethod
from typing import List

from missing_file_check.scanner.checker import MissingFile


class Analyzer(ABC):
    """
    Base class for all analyzers.

    Analyzers enrich MissingFile objects with additional information
    such as ownership, miss reason, and historical data.
    """

    @abstractmethod
    def analyze(self, missing_files: List[MissingFile], context: dict) -> None:
        """
        Analyze and enrich missing files.

        Modifies missing_files in-place by filling additional fields.

        Args:
            missing_files: List of MissingFile objects to analyze
            context: Shared context dictionary containing:
                - task_id: int
                - session: SQLAlchemy session (optional)
                - config: dict (optional)
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Get analyzer name for logging."""
        pass
