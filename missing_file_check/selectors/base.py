"""
Base class for baseline project selection strategies.

Baseline selectors determine which baseline projects to compare against
based on various matching criteria.
"""

from abc import ABC, abstractmethod
from typing import List

from missing_file_check.config.models import ProjectConfig
from missing_file_check.adapters.base import ProjectScanResult


class BaselineSelector(ABC):
    """
    Abstract base class for baseline selection strategies.

    Different strategies can match baseline projects based on:
    - Latest successful build
    - Matching commit_id
    - Matching b_version
    - Specific project and target combinations
    """

    @abstractmethod
    def select(
        self,
        baseline_configs: List[ProjectConfig],
        target_results: List[ProjectScanResult],
    ) -> List[ProjectScanResult]:
        """
        Select and fetch baseline project data based on strategy.

        Args:
            baseline_configs: List of baseline project configurations
            target_results: List of target project scan results (for matching)

        Returns:
            List of selected baseline project scan results

        Raises:
            SelectorError: If selection or fetching fails
        """
        pass


class SelectorError(Exception):
    """Base exception for selector-related errors."""

    pass
