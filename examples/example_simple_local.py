"""
Example using simplified LocalProjectAdapter.

Demonstrates the new two-file approach:
1. build_info.json - Contains project_id and build information
2. files.csv or files.json - Contains file list
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

print("=" * 70)
print("Simplified LocalProjectAdapter Example")
print("=" * 70)

# Configure task with new simplified adapter
config = TaskConfig(
    task_id="SIMPLE-LOCAL-001",
    target_projects=[
        ProjectConfig(
            project_id="target-1",
            project_name="Target Project",
            project_type=ProjectType.LOCAL,
            connection={
                "build_info_file": "test_data/target_build_info.json",
                "file_list_file": "test_data/target_files.csv",  # CSV format
            },
        )
    ],
    baseline_projects=[
        ProjectConfig(
            project_id="baseline-1",
            project_name="Baseline Project",
            project_type=ProjectType.LOCAL,
            connection={
                "build_info_file": "test_data/baseline_build_info.json",
                "file_list_file": "test_data/baseline_files.json",  # JSON format
            },
        )
    ],
    baseline_selector_strategy="latest_success_commit_id",
    shield_rules=[
        ShieldRule(id="SHIELD-001", pattern="docs/*", remark="Documentation files")
    ],
    mapping_rules=[
        MappingRule(
            id="MAP-001",
            source_pattern=r"(.+)/tests/test_database\.py",
            target_pattern=r"\1/tests/test_db.py",
            remark="Database test renamed",
        )
    ],
    path_prefixes=[
        PathPrefixConfig(project_id="target-1", prefix="/project"),
        PathPrefixConfig(project_id="baseline-1", prefix="/baseline"),
    ],
)

print("\n📋 Configuration:")
print(f"   Task ID: {config.task_id}")
print(f"\n   Target Project:")
print(f"     - Build info: {config.target_projects[0].connection['build_info_file']}")
print(f"     - File list: {config.target_projects[0].connection['file_list_file']} (CSV)")
print(f"\n   Baseline Project:")
print(f"     - Build info: {config.baseline_projects[0].connection['build_info_file']}")
print(f"     - File list: {config.baseline_projects[0].connection['file_list_file']} (JSON)")

# Run scanner
print("\n🔍 Running Scanner...")
checker = MissingFileChecker(config)
result = checker.check()

print(f"\n✅ Scan Completed!")
print(f"\n📊 Statistics:")
print(f"   🚨 Issues (Need Attention):")
print(f"      ├─ 🔴 Missed: {result.statistics.missed_count}")
print(f"      └─ ❌ Failed: {result.statistics.failed_count}")
print(f"   ✅ Passed (Reviewed): {result.statistics.passed_count}")
print(f"      ├─ 🛡️  Shielded: {result.statistics.shielded_count}")
print(f"      └─ 🔄 Remapped: {result.statistics.remapped_count}")
print(f"   📁 File Counts:")
print(f"      ├─ Target: {result.statistics.target_file_count}")
print(f"      └─ Baseline: {result.statistics.baseline_file_count}")

# Show details by category
categories = {
    "missed": "🔴 Missed Files",
    "shielded": "🛡️  Shielded Files",
    "remapped": "🔄 Remapped Files",
    "failed": "❌ Failed Files",
}

for status, title in categories.items():
    files = [f for f in result.missing_files if f.status == status]
    if files:
        print(f"\n{title} ({len(files)}):")
        for file in files[:5]:  # Show first 5
            print(f"   • {file.path}")
            if file.shielded_remark:
                print(f"     Reason: {file.shielded_remark}")
        if len(files) > 5:
            print(f"   ... and {len(files) - 5} more")

print("\n" + "=" * 70)
print("✨ Example Completed!")
print("=" * 70)

print("\n💡 Key Points:")
print("   ✓ Separate build info and file list files")
print("   ✓ Support both CSV and JSON for file lists")
print("   ✓ Simpler configuration")
print("   ✓ Same powerful scanning capabilities")
