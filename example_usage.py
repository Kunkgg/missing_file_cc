"""
Example usage demonstrating the missing file checker with mock data.

This example shows how to:
1. Configure a task with target and baseline projects
2. Run the checker with mock adapters
3. Process results
"""

from datetime import datetime
from typing import List, Optional

from missing_file_check.config.models import (
    TaskConfig,
    ProjectConfig,
    ProjectType,
    ShieldRule,
    MappingRule,
    PathPrefixConfig,
)
from missing_file_check.adapters.base import (
    ProjectAdapter,
    BuildInfo,
    FileEntry,
    ProjectScanResult,
)
from missing_file_check.adapters.factory import AdapterFactory
from missing_file_check.scanner.checker import MissingFileChecker


# Mock adapter for testing
class MockAdapter(ProjectAdapter):
    """Mock adapter that returns predefined data."""

    def fetch_files(
        self, commit_id: Optional[str] = None, b_version: Optional[str] = None
    ) -> ProjectScanResult:
        """Return mock scan result."""
        project_id = self.project_config.project_id

        # Mock build info
        build_info = BuildInfo(
            build_no="BUILD-001",
            build_status="success",
            branch="main",
            commit_id=commit_id or "abc123",
            b_version=b_version or "1.0.0",
            build_url="https://example.com/build/001",
            start_time=datetime.now(),
            end_time=datetime.now(),
        )

        # Mock file lists based on project type
        if "target" in project_id:
            # Target project - missing some files
            files = [
                FileEntry("/project/src/main.py", "success"),
                FileEntry("/project/src/utils.py", "success"),
                FileEntry("/project/tests/test_main.py", "failed"),  # Failed file
            ]
        else:
            # Baseline project - complete file list
            files = [
                FileEntry("/project/src/main.py", "success"),
                FileEntry("/project/src/utils.py", "success"),
                FileEntry("/project/src/config.py", "success"),  # Missing in target
                FileEntry("/project/tests/test_main.py", "success"),
                FileEntry("/project/tests/test_utils.py", "success"),  # Missing in target
                FileEntry("/project/docs/README.md", "success"),  # Should be shielded
            ]

        return ProjectScanResult(
            project_id=project_id, build_info=build_info, files=files
        )


def main():
    """Run example missing file check."""
    print("=" * 60)
    print("Missing File Check - Example Usage")
    print("=" * 60)

    # Register mock adapter for local type (used in this example)
    AdapterFactory.register(ProjectType.LOCAL, MockAdapter)

    # Configure task
    config = TaskConfig(
        task_id="TASK-001",
        target_projects=[
            ProjectConfig(
                project_id="target-project-1",
                project_name="Target Project",
                project_type=ProjectType.LOCAL,
                connection={"base_path": "/mock"},
            )
        ],
        baseline_projects=[
            ProjectConfig(
                project_id="baseline-project-1",
                project_name="Baseline Project",
                project_type=ProjectType.LOCAL,
                connection={"base_path": "/mock"},
            )
        ],
        baseline_selector_strategy="latest_success",
        shield_rules=[
            ShieldRule(
                id="SHIELD-001", pattern="docs/*", remark="Documentation files"
            )
        ],
        mapping_rules=[
            MappingRule(
                id="MAP-001",
                source_pattern=r"(.+)/tests/test_(.+)\.py",
                target_pattern=r"\1/test/\2_test.py",
                remark="Test file naming convention change",
            )
        ],
        path_prefixes=[
            PathPrefixConfig(project_id="target-project-1", prefix="/project"),
            PathPrefixConfig(project_id="baseline-project-1", prefix="/project"),
        ],
    )

    print("\nTask Configuration:")
    print(f"  Task ID: {config.task_id}")
    print(f"  Target Projects: {len(config.target_projects)}")
    print(f"  Baseline Projects: {len(config.baseline_projects)}")
    print(f"  Shield Rules: {len(config.shield_rules)}")
    print(f"  Mapping Rules: {len(config.mapping_rules)}")

    # Run checker
    print("\n" + "=" * 60)
    print("Running Missing File Check...")
    print("=" * 60)

    checker = MissingFileChecker(config)
    result = checker.check()

    # Display results
    print(f"\nCheck completed at: {result.timestamp}")
    print(f"\nStatistics:")
    print(f"  Total Missing: {result.statistics.total_missing}")
    print(f"  - Missed: {result.statistics.missed_count}")
    print(f"  - Shielded: {result.statistics.shielded_count}")
    print(f"  - Remapped: {result.statistics.remapped_count}")
    print(f"  - Failed: {result.statistics.failed_count}")

    print(f"\nMissing Files Details:")
    for file in result.missing_files:
        print(f"\n  Path: {file.path}")
        print(f"  Status: {file.status}")
        print(f"  Source: {file.source_baseline_project}")
        if file.status == "shielded":
            print(f"  Shielded By: {file.shielded_by}")
            print(f"  Remark: {file.shielded_remark}")
        elif file.status == "remapped":
            print(f"  Remapped To: {file.remapped_to}")
            print(f"  Remapped By: {file.remapped_by}")

    print("\n" + "=" * 60)
    print("Example completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
