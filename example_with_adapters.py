"""
Complete example using real adapters with local test data.

Demonstrates the full workflow using LocalProjectAdapter with actual JSON files.
"""

from missing_file_check.config.models import (
    TaskConfig,
    ProjectConfig,
    ProjectType,
    ShieldRule,
    MappingRule,
    PathPrefixConfig,
)
from missing_file_check.scanner.checker import MissingFileChecker


def main():
    """Run complete example with local adapters."""
    print("=" * 70)
    print("Missing File Check - Complete Example with Real Adapters")
    print("=" * 70)

    # Configure task with local file adapters
    config = TaskConfig(
        task_id="TASK-REAL-001",
        # Target project - uses local JSON file
        target_projects=[
            ProjectConfig(
                project_id="target-project",
                project_name="Target Project (Local)",
                project_type=ProjectType.LOCAL,
                connection={
                    "base_path": "test_data",
                    "file_pattern": "target_scan_result.json",
                },
            )
        ],
        # Baseline project - uses local JSON file
        baseline_projects=[
            ProjectConfig(
                project_id="baseline-project",
                project_name="Baseline Project (Local)",
                project_type=ProjectType.LOCAL,
                connection={
                    "base_path": "test_data",
                    "file_pattern": "baseline_scan_result.json",
                },
            )
        ],
        # Use latest success strategy with commit_id matching
        baseline_selector_strategy="latest_success_commit_id",
        # Shield documentation files
        shield_rules=[
            ShieldRule(
                id="SHIELD-DOCS-001",
                pattern="docs/*",
                remark="Documentation files are excluded from scanning",
            )
        ],
        # Map old test directory to new location
        mapping_rules=[
            MappingRule(
                id="MAP-TEST-001",
                source_pattern=r"(.+)/tests/test_database\.py",
                target_pattern=r"\1/tests/test_db.py",
                remark="Database test file renamed",
            )
        ],
        # Configure path prefixes for normalization
        path_prefixes=[
            PathPrefixConfig(project_id="target-project", prefix="/project"),
            PathPrefixConfig(project_id="baseline-project", prefix="/baseline"),
        ],
    )

    print("\n📋 Task Configuration:")
    print(f"   Task ID: {config.task_id}")
    print(f"   Target Projects: {len(config.target_projects)}")
    for proj in config.target_projects:
        print(f"     - {proj.project_name} ({proj.project_type.value})")
    print(f"   Baseline Projects: {len(config.baseline_projects)}")
    for proj in config.baseline_projects:
        print(f"     - {proj.project_name} ({proj.project_type.value})")
    print(f"   Selection Strategy: {config.baseline_selector_strategy}")
    print(f"   Shield Rules: {len(config.shield_rules)}")
    print(f"   Mapping Rules: {len(config.mapping_rules)}")

    # Run checker
    print("\n" + "=" * 70)
    print("🔍 Running Missing File Check...")
    print("=" * 70)

    checker = MissingFileChecker(config)
    result = checker.check()

    # Display results
    print(f"\n✅ Check completed at: {result.timestamp}")

    print(f"\n📊 Projects Analyzed:")
    print(f"   Target Projects: {', '.join(result.target_project_ids)}")
    print(f"   Baseline Projects: {', '.join(result.baseline_project_ids)}")

    print(f"\n📈 Statistics:")
    print(f"   Total Missing Files: {result.statistics.total_missing}")
    print(f"   ├─ 🔴 Missed: {result.statistics.missed_count}")
    print(f"   ├─ 🛡️  Shielded: {result.statistics.shielded_count}")
    print(f"   ├─ 🔄 Remapped: {result.statistics.remapped_count}")
    print(f"   └─ ❌ Failed: {result.statistics.failed_count}")

    # Group files by status
    missed_files = [f for f in result.missing_files if f.status == "missed"]
    shielded_files = [f for f in result.missing_files if f.status == "shielded"]
    remapped_files = [f for f in result.missing_files if f.status == "remapped"]
    failed_files = [f for f in result.missing_files if f.status == "failed"]

    # Display missed files
    if missed_files:
        print(f"\n🔴 Missed Files ({len(missed_files)}):")
        for file in missed_files:
            print(f"   • {file.path}")
            print(f"     Source: {file.source_baseline_project}")

    # Display shielded files
    if shielded_files:
        print(f"\n🛡️  Shielded Files ({len(shielded_files)}):")
        for file in shielded_files:
            print(f"   • {file.path}")
            print(f"     Rule: {file.shielded_by}")
            print(f"     Reason: {file.shielded_remark}")

    # Display remapped files
    if remapped_files:
        print(f"\n🔄 Remapped Files ({len(remapped_files)}):")
        for file in remapped_files:
            print(f"   • {file.path} → {file.remapped_to}")
            print(f"     Rule: {file.remapped_by}")
            print(f"     Reason: {file.remapped_remark}")

    # Display failed files
    if failed_files:
        print(f"\n❌ Failed Files ({len(failed_files)}):")
        for file in failed_files:
            print(f"   • {file.path}")
            print(f"     Status: File exists but scan failed")
            print(f"     Source: {file.source_baseline_project}")

    print("\n" + "=" * 70)
    print("✨ Example completed successfully!")
    print("=" * 70)

    # Summary
    print("\n📝 Summary:")
    print(f"   This example demonstrated:")
    print(f"   ✓ Loading configuration with Pydantic validation")
    print(f"   ✓ Using LocalProjectAdapter to read JSON files")
    print(f"   ✓ Baseline selection with commit_id matching")
    print(f"   ✓ Path normalization with prefix stripping")
    print(f"   ✓ File comparison using set operations")
    print(f"   ✓ Shield rules to exclude documentation")
    print(f"   ✓ Mapping rules to handle renamed files")
    print(f"   ✓ Detecting failed scan files")
    print(f"   ✓ Complete categorization of all missing files")


if __name__ == "__main__":
    main()
