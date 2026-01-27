"""
Example demonstrating optimized HTML report generation.

Shows:
1. Project information tables with build details
2. Lazy loading for large file lists
"""

import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from missing_file_check.scanner.checker import (
    CheckResult,
    MissingFile,
    ResultStatistics,
)
from missing_file_check.adapters.base import BuildInfo, ProjectScanResult, FileEntry
from missing_file_check.storage.report_generator import ReportGenerator

print("=" * 70)
print("HTML Report Optimization Example")
print("=" * 70)

# Step 1: Create mock project scan results with full build info
print("\n📋 Step 1: Create Mock Data")

target_project = ProjectScanResult(
    project_id="target-project-1",
    build_info=BuildInfo(
        build_no="BUILD-2026-001",
        build_status="success",
        branch="main",
        commit_id="abc123def456789",
        b_version="2.0.0",
        build_url="https://build.example.com/target/001",
        start_time=datetime(2026, 1, 27, 10, 0, 0),
        end_time=datetime(2026, 1, 27, 10, 30, 0),
    ),
    files=[
        FileEntry(path=f"/target/src/file{i}.py", status="success")
        for i in range(1, 101)
    ],
)

baseline_project = ProjectScanResult(
    project_id="baseline-project-1",
    build_info=BuildInfo(
        build_no="BUILD-2025-999",
        build_status="success",
        branch="main",
        commit_id="abc123def456789",
        b_version="1.5.0",
        build_url="https://build.example.com/baseline/999",
        start_time=datetime(2025, 12, 20, 14, 0, 0),
        end_time=datetime(2025, 12, 20, 14, 45, 0),
    ),
    files=[
        FileEntry(path=f"/baseline/src/file{i}.py", status="success")
        for i in range(1, 301)
    ],  # 300 files
)

print(f"   Target Project: {target_project.project_id}")
print(f"     - Files: {len(target_project.files)}")
print(f"     - Build: {target_project.build_info.build_no}")
print(f"     - Commit: {target_project.build_info.commit_id[:8]}")
print(f"\n   Baseline Project: {baseline_project.project_id}")
print(f"     - Files: {len(baseline_project.files)}")
print(f"     - Build: {baseline_project.build_info.build_no}")
print(f"     - Commit: {baseline_project.build_info.commit_id[:8]}")

# Step 2: Create large missing file list (to demonstrate lazy loading)
print("\n📊 Step 2: Generate Missing Files (Large List)")

missing_files = []

# Simulate 250 missed files
for i in range(101, 351):
    missing_files.append(
        MissingFile(
            path=f"/baseline/src/file{i}.py",
            status="missed",
            source_baseline_project="baseline-project-1",
        )
    )

print(f"   Created {len(missing_files)} missing files")
print(f"   HTML will show first 100, then lazy load on demand")

# Step 3: Create CheckResult with full project info
result = CheckResult(
    task_id="REPORT-DEMO-001",
    target_project_ids=["target-project-1"],
    baseline_project_ids=["baseline-project-1"],
    missing_files=missing_files,
    statistics=ResultStatistics(
        missed_count=250,
        failed_count=0,
        passed_count=0,
        shielded_count=0,
        remapped_count=0,
        target_file_count=100,
        baseline_file_count=300,
        target_project_count=1,
        baseline_project_count=1,
    ),
    timestamp=datetime.now(),
    target_projects=[target_project],  # Full project info
    baseline_projects=[baseline_project],  # Full project info
)

# Step 4: Generate HTML report
print("\n📄 Step 3: Generate HTML Report")

generator = ReportGenerator()
reports_dir = Path("reports")
reports_dir.mkdir(exist_ok=True)

html_path = reports_dir / "optimization_demo_report.html"
html_content = generator.generate_html(result, html_path)

print(f"   ✓ Report generated: {html_path}")
print(f"   Report size: {len(html_content) // 1024} KB")

# Step 5: Show key features
print("\n" + "=" * 70)
print("✨ Report Features Demonstrated")
print("=" * 70)

print("\n1. 🏗️  Project Information Tables")
print("   - Full build details for each project")
print("   - Clickable build URLs")
print("   - Build status indicators")
print("   - Commit IDs and versions")

print("\n2. ⚡ Lazy Loading for Performance")
print(f"   - Total files: {len(missing_files)}")
print("   - Initially shown: 100")
print("   - Load on demand: 100 per click")
print("   - Performance: Fast initial load")

print("\n3. 📊 Rich Statistics")
print("   - Clear issue/passed separation")
print("   - File count context")
print("   - Project count summary")

print("\n" + "=" * 70)
print("💡 Next Steps")
print("=" * 70)
print(f"\n1. Open report in browser:")
print(f"   firefox {html_path}")
print(f"\n2. Test lazy loading:")
print("   - Scroll to file list")
print("   - Click 'Show More' button")
print("   - Notice smooth performance")
print(f"\n3. Check project tables:")
print("   - See full build information")
print("   - Click build URLs (placeholder)")
print("   - Note responsive design")
