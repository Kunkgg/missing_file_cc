"""
Concrete baseline selection strategy implementations.

Supports 6 different baseline matching strategies:
1. Latest success + all baseline commit_id match
2. Latest success + all baseline b_version match
3. Latest success + specific baseline and target commit_id match
4. Latest success + specific baseline and target b_version match
5. Latest success (no matching)
6. No restriction
"""

from typing import List, Optional

from missing_file_check.selectors.base import BaselineSelector, SelectorError
from missing_file_check.config.models import ProjectConfig
from missing_file_check.adapters.base import ProjectScanResult
from missing_file_check.adapters.factory import AdapterFactory


class LatestSuccessWithCommitIdMatcher(BaselineSelector):
    """
    Strategy 1: Latest successful build + commit_id matching.

    Selects latest successful build for all baseline projects where
    commit_id matches any target project's commit_id.
    """

    def select(
        self,
        baseline_configs: List[ProjectConfig],
        target_results: List[ProjectScanResult],
    ) -> List[ProjectScanResult]:
        """Select baselines with matching commit_ids."""
        target_commit_ids = {r.build_info.commit_id for r in target_results}

        baseline_results = []
        for config in baseline_configs:
            adapter = AdapterFactory.create(config)

            # Try each target commit_id until we find a matching baseline build
            for commit_id in target_commit_ids:
                try:
                    result = adapter.fetch_files(commit_id=commit_id)
                    if result.build_info.build_status == "success":
                        baseline_results.append(result)
                        break
                except Exception:
                    continue

        if not baseline_results:
            raise SelectorError(
                "No baseline projects found with matching commit_ids "
                f"from targets: {target_commit_ids}"
            )

        return baseline_results


class LatestSuccessWithVersionMatcher(BaselineSelector):
    """
    Strategy 2: Latest successful build + b_version matching.

    Selects latest successful build for all baseline projects where
    b_version matches any target project's b_version.
    """

    def select(
        self,
        baseline_configs: List[ProjectConfig],
        target_results: List[ProjectScanResult],
    ) -> List[ProjectScanResult]:
        """Select baselines with matching versions."""
        target_versions = {r.build_info.b_version for r in target_results}

        baseline_results = []
        for config in baseline_configs:
            adapter = AdapterFactory.create(config)

            # Try each target version until we find a matching baseline build
            for b_version in target_versions:
                try:
                    result = adapter.fetch_files(b_version=b_version)
                    if result.build_info.build_status == "success":
                        baseline_results.append(result)
                        break
                except Exception:
                    continue

        if not baseline_results:
            raise SelectorError(
                "No baseline projects found with matching versions "
                f"from targets: {target_versions}"
            )

        return baseline_results


class SpecificBaselineCommitIdMatcher(BaselineSelector):
    """
    Strategy 3: Latest success + specific baseline and target commit_id match.

    Selects latest successful build for a specific baseline project where
    commit_id matches a specific target project's commit_id.
    """

    def __init__(self, baseline_project_id: str, target_project_id: str):
        """
        Initialize with specific project IDs.

        Args:
            baseline_project_id: ID of baseline project to select
            target_project_id: ID of target project to match against
        """
        self.baseline_project_id = baseline_project_id
        self.target_project_id = target_project_id

    def select(
        self,
        baseline_configs: List[ProjectConfig],
        target_results: List[ProjectScanResult],
    ) -> List[ProjectScanResult]:
        """Select specific baseline with matching commit_id."""
        # Find target result
        target_result = next(
            (r for r in target_results if r.project_id == self.target_project_id),
            None,
        )
        if not target_result:
            raise SelectorError(
                f"Target project not found: {self.target_project_id}"
            )

        # Find baseline config
        baseline_config = next(
            (c for c in baseline_configs if c.project_id == self.baseline_project_id),
            None,
        )
        if not baseline_config:
            raise SelectorError(
                f"Baseline project not found: {self.baseline_project_id}"
            )

        # Fetch baseline with matching commit_id
        adapter = AdapterFactory.create(baseline_config)
        try:
            result = adapter.fetch_files(commit_id=target_result.build_info.commit_id)
            if result.build_info.build_status != "success":
                raise SelectorError(
                    f"Baseline build not successful for project {self.baseline_project_id}"
                )
            return [result]
        except Exception as e:
            raise SelectorError(
                f"Failed to fetch baseline project {self.baseline_project_id}: {e}"
            )


class SpecificBaselineVersionMatcher(BaselineSelector):
    """
    Strategy 4: Latest success + specific baseline and target b_version match.

    Selects latest successful build for a specific baseline project where
    b_version matches a specific target project's b_version.
    """

    def __init__(self, baseline_project_id: str, target_project_id: str):
        """
        Initialize with specific project IDs.

        Args:
            baseline_project_id: ID of baseline project to select
            target_project_id: ID of target project to match against
        """
        self.baseline_project_id = baseline_project_id
        self.target_project_id = target_project_id

    def select(
        self,
        baseline_configs: List[ProjectConfig],
        target_results: List[ProjectScanResult],
    ) -> List[ProjectScanResult]:
        """Select specific baseline with matching version."""
        # Find target result
        target_result = next(
            (r for r in target_results if r.project_id == self.target_project_id),
            None,
        )
        if not target_result:
            raise SelectorError(
                f"Target project not found: {self.target_project_id}"
            )

        # Find baseline config
        baseline_config = next(
            (c for c in baseline_configs if c.project_id == self.baseline_project_id),
            None,
        )
        if not baseline_config:
            raise SelectorError(
                f"Baseline project not found: {self.baseline_project_id}"
            )

        # Fetch baseline with matching version
        adapter = AdapterFactory.create(baseline_config)
        try:
            result = adapter.fetch_files(b_version=target_result.build_info.b_version)
            if result.build_info.build_status != "success":
                raise SelectorError(
                    f"Baseline build not successful for project {self.baseline_project_id}"
                )
            return [result]
        except Exception as e:
            raise SelectorError(
                f"Failed to fetch baseline project {self.baseline_project_id}: {e}"
            )


class LatestSuccessMatcher(BaselineSelector):
    """
    Strategy 5: Latest successful build (no matching).

    Selects latest successful build for all baseline projects without
    any commit_id or version matching requirements.
    """

    def select(
        self,
        baseline_configs: List[ProjectConfig],
        target_results: List[ProjectScanResult],
    ) -> List[ProjectScanResult]:
        """Select latest successful build for all baselines."""
        baseline_results = []
        for config in baseline_configs:
            adapter = AdapterFactory.create(config)
            try:
                result = adapter.fetch_files()  # No filters
                if result.build_info.build_status == "success":
                    baseline_results.append(result)
            except Exception:
                # Skip this baseline if fetch fails
                continue

        if not baseline_results:
            raise SelectorError("No successful baseline builds found")

        return baseline_results


class NoRestrictionSelector(BaselineSelector):
    """
    Strategy 6: No restrictions.

    Fetches baseline project data without any status or matching requirements.
    Returns whatever data is configured, regardless of success status.
    """

    def select(
        self,
        baseline_configs: List[ProjectConfig],
        target_results: List[ProjectScanResult],
    ) -> List[ProjectScanResult]:
        """Fetch all baseline projects without restrictions."""
        baseline_results = []
        for config in baseline_configs:
            adapter = AdapterFactory.create(config)
            try:
                result = adapter.fetch_files()
                baseline_results.append(result)
            except Exception:
                # Skip this baseline if fetch fails
                continue

        if not baseline_results:
            raise SelectorError("Failed to fetch any baseline projects")

        return baseline_results
