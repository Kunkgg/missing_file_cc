"""
Analysis pipeline for coordinating multiple analyzers.

Runs analyzers in sequence to enrich missing file information.
"""

from typing import List

from missing_file_check.analyzers.base import Analyzer
from missing_file_check.scanner.checker import CheckResult


class AnalysisPipeline:
    """
    Pipeline for running multiple analyzers.

    Coordinates the execution of multiple analyzers on CheckResult data.
    Each analyzer enriches the MissingFile objects with additional information.
    """

    def __init__(self, analyzers: List[Analyzer]):
        """
        Initialize pipeline with analyzers.

        Args:
            analyzers: List of Analyzer instances to run
        """
        self.analyzers = analyzers

    def run(self, result: CheckResult, context: dict) -> None:
        """
        Run all analyzers on the check result.

        Analyzers are executed sequentially. Each analyzer modifies
        the missing_files in-place.

        Args:
            result: CheckResult from scanner
            context: Shared context dictionary for analyzers
        """
        for analyzer in self.analyzers:
            try:
                analyzer.analyze(result.missing_files, context)
            except Exception as e:
                # Log error but continue with other analyzers
                print(f"[WARNING] Analyzer {analyzer.name} failed: {e}")
                # In production, use proper logging
                # logger.warning(f"Analyzer {analyzer.name} failed", exc_info=e)

    def add_analyzer(self, analyzer: Analyzer):
        """
        Add an analyzer to the pipeline.

        Args:
            analyzer: Analyzer instance
        """
        self.analyzers.append(analyzer)

    def remove_analyzer(self, analyzer_name: str) -> bool:
        """
        Remove an analyzer by name.

        Args:
            analyzer_name: Name of the analyzer to remove

        Returns:
            True if removed, False if not found
        """
        for i, analyzer in enumerate(self.analyzers):
            if analyzer.name == analyzer_name:
                self.analyzers.pop(i)
                return True
        return False


def create_default_pipeline() -> AnalysisPipeline:
    """
    Create a pipeline with default analyzers.

    Returns:
        AnalysisPipeline with standard analyzers
    """
    from missing_file_check.analyzers.ownership_analyzer import OwnershipAnalyzer
    from missing_file_check.analyzers.reason_analyzer import ReasonAnalyzer
    from missing_file_check.analyzers.history_analyzer import HistoryAnalyzer

    return AnalysisPipeline(
        [
            OwnershipAnalyzer(),
            ReasonAnalyzer(),
            HistoryAnalyzer(),
        ]
    )
