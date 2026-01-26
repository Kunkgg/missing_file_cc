"""
Complete Phase 3 example: End-to-end workflow with database and reports.

This example demonstrates:
1. Load configuration (from dict, database interface ready)
2. Run scanner
3. Run analyzers
4. Save results to database
5. Generate HTML and JSON reports
6. Upload to object storage (placeholder)
"""

import os
from pathlib import Path
from dotenv import load_dotenv

from missing_file_check.config.models import (
    TaskConfig,
    ProjectConfig,
    ProjectType,
    ShieldRule,
    MappingRule,
    PathPrefixConfig,
)
from missing_file_check.scanner.checker import MissingFileChecker
from missing_file_check.analyzers.pipeline import create_default_pipeline
from missing_file_check.storage.database import init_db, session_scope
from missing_file_check.storage.repository import MissingFileRepository
from missing_file_check.storage.report_generator import ReportGenerator
from missing_file_check.storage.object_storage import PlaceholderObjectStorage

# Load environment variables
load_dotenv()


def main():
    """Run complete Phase 3 workflow."""
    print("=" * 70)
    print("Missing File Check - Phase 3 Complete Example")
    print("=" * 70)

    # Step 1: Configure task (using dict, database loader is ready)
    print("\n📋 Step 1: Configure Task")
    config = TaskConfig(
        task_id="TASK-PHASE3-001",
        target_projects=[
            ProjectConfig(
                project_id="target-1",
                project_name="Target Project",
                project_type=ProjectType.LOCAL,
                connection={
                    "base_path": "test_data",
                    "file_pattern": "target_scan_result.json",
                },
            )
        ],
        baseline_projects=[
            ProjectConfig(
                project_id="baseline-1",
                project_name="Baseline Project",
                project_type=ProjectType.LOCAL,
                connection={
                    "base_path": "test_data",
                    "file_pattern": "baseline_scan_result.json",
                },
            )
        ],
        baseline_selector_strategy="latest_success_commit_id",
        shield_rules=[
            ShieldRule(
                id="SHIELD-001",
                pattern="docs/*",
                remark="Documentation files excluded",
            )
        ],
        mapping_rules=[
            MappingRule(
                id="MAP-001",
                source_pattern=r"old/(.+)",
                target_pattern=r"new/\1",
                remark="Directory restructure",
            )
        ],
        path_prefixes=[
            PathPrefixConfig(project_id="target-1", prefix="/project"),
            PathPrefixConfig(project_id="baseline-1", prefix="/baseline"),
        ],
    )
    print(f"   Task ID: {config.task_id}")
    print(f"   Targets: {len(config.target_projects)}")
    print(f"   Baselines: {len(config.baseline_projects)}")

    # Step 2: Run scanner
    print("\n🔍 Step 2: Run Scanner")
    checker = MissingFileChecker(config)
    result = checker.check()
    print(f"   ✓ Scan completed")
    print(f"   Total missing: {result.statistics.total_missing}")
    print(f"     - Missed: {result.statistics.missed_count}")
    print(f"     - Shielded: {result.statistics.shielded_count}")
    print(f"     - Failed: {result.statistics.failed_count}")

    # Step 3: Run analyzers
    print("\n🔬 Step 3: Run Analyzers")
    pipeline = create_default_pipeline()

    # Create analysis context (without database session for this example)
    analysis_context = {
        "task_id": config.task_id,
        # "session": session,  # Would provide in production
    }

    pipeline.run(result, analysis_context)
    print(f"   ✓ Analysis completed")
    print(f"   Ownership filled: {sum(1 for f in result.missing_files if f.ownership)}")
    print(f"   Reasons filled: {sum(1 for f in result.missing_files if f.miss_reason)}")

    # Step 4: Generate reports
    print("\n📄 Step 4: Generate Reports")
    generator = ReportGenerator()

    # Create reports directory
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)

    html_path = reports_dir / f"{config.task_id}_report.html"
    json_path = reports_dir / f"{config.task_id}_report.json"

    html_content, json_content = generator.generate_both(result, html_path, json_path)

    print(f"   ✓ HTML report: {html_path}")
    print(f"   ✓ JSON report: {json_path}")
    print(f"   HTML size: {len(html_content) // 1024} KB")
    print(f"   JSON size: {len(json_content) // 1024} KB")

    # Step 5: Upload to object storage (placeholder)
    print("\n☁️  Step 5: Upload to Object Storage (Placeholder)")
    storage = PlaceholderObjectStorage(base_url="https://storage.company.com")

    html_remote_path = f"reports/{config.task_id}/report.html"
    json_remote_path = f"reports/{config.task_id}/report.json"

    html_url = storage.upload_file(html_path, html_remote_path, "text/html")
    json_url = storage.upload_file(json_path, json_remote_path, "application/json")

    print(f"   HTML URL: {html_url}")
    print(f"   JSON URL: {json_url}")

    # Step 6: Save to database (optional, if DB configured)
    if os.getenv("DB_HOST"):
        print("\n💾 Step 6: Save to Database")
        try:
            # Initialize database
            init_db()

            with session_scope() as session:
                repository = MissingFileRepository(session)

                # For this example, use task_id as integer
                task_id_int = 1

                # Save scan results
                scan_result = repository.save_task_and_results(
                    task_id=task_id_int,
                    result=result,
                    report_url=html_url,
                    commit=True,
                )

                print(f"   ✓ Saved scan result: ID={scan_result.id}")
                print(f"   ✓ Saved {len(result.missing_files)} file details")

        except Exception as e:
            print(f"   ⚠️  Database save skipped: {e}")
            print(f"   (Set DB_HOST in .env to enable database persistence)")
    else:
        print("\n💾 Step 6: Save to Database (Skipped)")
        print("   Set DB_HOST in .env file to enable database persistence")

    # Summary
    print("\n" + "=" * 70)
    print("✨ Phase 3 Example Completed Successfully!")
    print("=" * 70)

    print("\n📊 Summary:")
    print(f"   Scanner: ✓ {result.statistics.total_missing} files analyzed")
    print(f"   Analyzers: ✓ Ownership, Reason, History")
    print(f"   Reports: ✓ HTML & JSON generated")
    print(f"   Storage: ✓ Upload interface demonstrated")
    if os.getenv("DB_HOST"):
        print(f"   Database: ✓ Results persisted")
    else:
        print(f"   Database: - Not configured (optional)")

    print("\n📁 Generated Files:")
    print(f"   {html_path}")
    print(f"   {json_path}")

    print("\n💡 Next Steps:")
    print("   - Open HTML report in browser to view results")
    print("   - Configure database to enable persistence")
    print("   - Implement concrete object storage adapter")
    print("   - Customize platform table queries in database_loader.py")


if __name__ == "__main__":
    main()
