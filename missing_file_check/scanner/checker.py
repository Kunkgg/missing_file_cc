"""
Main checker orchestrating the complete file comparison workflow.

Coordinates all scanning components to produce a comprehensive CheckResult.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime

from missing_file_check.config.models import TaskConfig
from missing_file_check.adapters.base import ProjectScanResult
from missing_file_check.adapters.factory import AdapterFactory
from missing_file_check.selectors.factory import BaselineSelectorFactory
from missing_file_check.scanner.merger import FileMerger
from missing_file_check.scanner.normalizer import PathNormalizer
from missing_file_check.scanner.comparator import FileComparator
from missing_file_check.scanner.rule_engine import RuleEngine


@dataclass
class MissingFile:
    """Represents a missing or problematic file with categorization."""

    path: str
    status: str  # "missed" | "shielded" | "remapped" | "failed"
    source_baseline_project: Optional[str] = None

    # Shield rule fields
    shielded_by: Optional[str] = None
    shielded_remark: Optional[str] = None

    # Mapping rule fields
    remapped_by: Optional[str] = None
    remapped_to: Optional[str] = None
    remapped_remark: Optional[str] = None

    # Analysis phase fields (filled later)
    ownership: Optional[str] = None
    miss_reason: Optional[str] = None
    first_detected_at: Optional[datetime] = None


@dataclass
class ResultStatistics:
    """Statistics summary for a check result.

    Note: Only missed and failed are actual issues that need attention.
    Shielded and remapped files have been reviewed and are not problems.
    """

    missed_count: int  # Real issue: files missing in target
    failed_count: int  # Real issue: files exist but failed in target
    passed_count: int  # Not issues: shielded + remapped (reviewed and approved)
    shielded_count: int  # Subset of passed: excluded by shield rules
    remapped_count: int  # Subset of passed: handled by path mapping
    target_file_count: int  # Total files in target projects
    baseline_file_count: int  # Total files in baseline projects
    target_project_count: int  # Number of target projects
    baseline_project_count: int  # Number of baseline projects


@dataclass
class CheckResult:
    """Complete result of a missing file check."""

    task_id: str
    target_project_ids: List[str]
    baseline_project_ids: List[str]
    missing_files: List[MissingFile]
    statistics: ResultStatistics
    timestamp: datetime
    # Full project scan results for detailed reporting
    target_projects: Optional[List[ProjectScanResult]] = None
    baseline_projects: Optional[List[ProjectScanResult]] = None


class MissingFileChecker:
    """
    Main orchestrator for missing file detection.

    Coordinates the complete workflow:
    1. Fetch target and baseline project data
    2. Merge file lists into unified sets
    3. Compare to find missing files
    4. Apply rules for categorization
    5. Return comprehensive results
    """

    def __init__(self, config: TaskConfig):
        """
        Initialize checker with task configuration.

        Args:
            config: Complete task configuration
        """
        self.config = config

        # Initialize components
        self.path_normalizer = PathNormalizer(config.path_prefixes)
        self.file_merger = FileMerger(self.path_normalizer)
        self.rule_engine = RuleEngine(config.shield_rules, config.mapping_rules)

    def check(self) -> CheckResult:
        """
        Execute complete missing file check workflow.

        Returns:
            CheckResult with categorized missing files and statistics

        Raises:
            Various exceptions from adapters, selectors, or rule engine
        """
        # Step 1: Fetch target project data
        target_results = self._fetch_target_projects()

        # Step 2: Select and fetch baseline project data
        baseline_results = self._fetch_baseline_projects(target_results)

        # Step 3: Merge file lists
        target_files = self.file_merger.merge_target_files(target_results)
        baseline_files = self.file_merger.merge_baseline_files(baseline_results)

        # Step 4: Compare to find missing files
        missing_paths = FileComparator.find_missing_files(baseline_files, target_files)
        failed_files = FileComparator.find_failed_files(baseline_files, target_files)

        # Step 5: Apply rules to categorize
        target_paths = set(target_files.keys())
        categorized = self.rule_engine.categorize_missing_files(
            missing_paths, failed_files, baseline_files, target_paths
        )

        # Step 6: Build result objects
        missing_file_objects = [
            MissingFile(
                path=item["path"],
                status=item["status"],
                source_baseline_project=item["source_baseline_project"],
                shielded_by=item.get("shielded_by"),
                shielded_remark=item.get("shielded_remark"),
                remapped_by=item.get("remapped_by"),
                remapped_to=item.get("remapped_to"),
                remapped_remark=item.get("remapped_remark"),
            )
            for item in categorized
        ]

        # Step 7: Calculate statistics
        statistics = self._calculate_statistics(
            missing_file_objects, target_results, baseline_results
        )

        # Step 8: Build final result
        return CheckResult(
            task_id=self.config.task_id,
            target_project_ids=[r.project_id for r in target_results],
            baseline_project_ids=[r.project_id for r in baseline_results],
            missing_files=missing_file_objects,
            statistics=statistics,
            timestamp=datetime.now(),
            target_projects=target_results,
            baseline_projects=baseline_results,
        )

    def _fetch_target_projects(self) -> List[ProjectScanResult]:
        """Fetch data from all target projects."""
        results = []
        for project_config in self.config.target_projects:
            adapter = AdapterFactory.create(project_config)
            result = adapter.fetch_files()
            results.append(result)
        return results

    def _fetch_baseline_projects(
        self, target_results: List[ProjectScanResult]
    ) -> List[ProjectScanResult]:
        """Select and fetch baseline projects based on configured strategy."""
        selector = BaselineSelectorFactory.create(
            self.config.baseline_selector_strategy,
            self.config.baseline_selector_params,
        )
        return selector.select(self.config.baseline_projects, target_results)

    def _calculate_statistics(
        self,
        missing_files: List[MissingFile],
        target_results: List[ProjectScanResult],
        baseline_results: List[ProjectScanResult],
    ) -> ResultStatistics:
        """Calculate result statistics."""
        status_counts = {"missed": 0, "shielded": 0, "remapped": 0, "failed": 0}

        for file in missing_files:
            if file.status in status_counts:
                status_counts[file.status] += 1

        # passed_count = shielded + remapped (reviewed, not issues)
        passed_count = status_counts["shielded"] + status_counts["remapped"]

        # Calculate total file counts
        target_file_count = sum(len(result.files) for result in target_results)
        baseline_file_count = sum(len(result.files) for result in baseline_results)

        return ResultStatistics(
            missed_count=status_counts["missed"],
            failed_count=status_counts["failed"],
            passed_count=passed_count,
            shielded_count=status_counts["shielded"],
            remapped_count=status_counts["remapped"],
            target_file_count=target_file_count,
            baseline_file_count=baseline_file_count,
            target_project_count=len(target_results),
            baseline_project_count=len(baseline_results),
        )
