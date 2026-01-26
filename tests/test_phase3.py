"""
Phase 3 integration tests.

Tests storage layer, analyzers, and report generation.
"""

import json
import pytest
from pathlib import Path
from datetime import datetime

from missing_file_check.scanner.checker import CheckResult, MissingFile, ResultStatistics
from missing_file_check.analyzers.pipeline import create_default_pipeline
from missing_file_check.analyzers.ownership_analyzer import OwnershipAnalyzer
from missing_file_check.analyzers.reason_analyzer import ReasonAnalyzer
from missing_file_check.storage.report_generator import ReportGenerator
from missing_file_check.storage.object_storage import PlaceholderObjectStorage


class TestAnalyzers:
    """Test analyzer pipeline and individual analyzers."""

    def test_ownership_analyzer(self):
        """Test ownership analyzer fills ownership field."""
        analyzer = OwnershipAnalyzer()

        files = [
            MissingFile(path="src/team_alpha/main.py", status="missed"),
            MissingFile(path="src/team_beta/utils.py", status="missed"),
        ]

        analyzer.analyze(files, {})

        # Should extract team from path
        assert files[0].ownership == "team_alpha"
        assert files[1].ownership == "team_beta"

    def test_reason_analyzer(self):
        """Test reason analyzer classifies miss reasons."""
        analyzer = ReasonAnalyzer()

        files = [
            MissingFile(path="file1.py", status="missed"),
            MissingFile(path="file2.py", status="failed"),
            MissingFile(path="file3.py", status="shielded", shielded_remark="Docs"),
        ]

        analyzer.analyze(files, {})

        assert files[0].miss_reason == "not_in_list"
        assert files[1].miss_reason == "failed_status"
        assert "shielded" in files[2].miss_reason

    def test_pipeline_runs_all_analyzers(self):
        """Test pipeline runs all analyzers in sequence."""
        pipeline = create_default_pipeline()

        # Create mock CheckResult
        files = [
            MissingFile(path="src/module/file.py", status="missed"),
        ]

        result = CheckResult(
            task_id="TEST",
            target_project_ids=["t1"],
            baseline_project_ids=["b1"],
            missing_files=files,
            statistics=ResultStatistics(1, 1, 0, 0, 0, 1, 1),
            timestamp=datetime.now(),
        )

        pipeline.run(result, {})

        # All fields should be filled
        assert files[0].ownership is not None
        assert files[0].miss_reason is not None


class TestReportGenerator:
    """Test report generation."""

    def test_generate_html(self, tmp_path):
        """Test HTML report generation."""
        generator = ReportGenerator()

        # Create test result
        files = [
            MissingFile(
                path="src/main.py",
                status="missed",
                source_baseline_project="baseline-1",
            ),
            MissingFile(
                path="docs/README.md",
                status="shielded",
                shielded_by="SHIELD-001",
                shielded_remark="Documentation",
            ),
        ]

        result = CheckResult(
            task_id="TEST-001",
            target_project_ids=["target-1"],
            baseline_project_ids=["baseline-1"],
            missing_files=files,
            statistics=ResultStatistics(2, 1, 1, 0, 0, 1, 1),
            timestamp=datetime.now(),
        )

        html_path = tmp_path / "report.html"
        html_content = generator.generate_html(result, html_path)

        # Check file exists
        assert html_path.exists()

        # Check content
        assert "TEST-001" in html_content
        assert "src/main.py" in html_content
        assert "docs/README.md" in html_content
        assert "Documentation" in html_content

    def test_generate_json(self, tmp_path):
        """Test JSON report generation."""
        generator = ReportGenerator()

        files = [
            MissingFile(
                path="test.py",
                status="failed",
                source_baseline_project="base-1",
            ),
        ]

        result = CheckResult(
            task_id="TEST-002",
            target_project_ids=["t1"],
            baseline_project_ids=["b1"],
            missing_files=files,
            statistics=ResultStatistics(1, 0, 0, 0, 1, 1, 1),
            timestamp=datetime.now(),
        )

        json_path = tmp_path / "report.json"
        json_content = generator.generate_json(result, json_path)

        # Check file exists
        assert json_path.exists()

        # Parse and validate JSON
        data = json.loads(json_content)
        assert data["task_id"] == "TEST-002"
        assert data["statistics"]["failed_count"] == 1
        assert len(data["missing_files"]) == 1
        assert data["missing_files"][0]["path"] == "test.py"

    def test_generate_both(self, tmp_path):
        """Test generating both HTML and JSON reports."""
        generator = ReportGenerator()

        result = CheckResult(
            task_id="TEST-003",
            target_project_ids=["t1"],
            baseline_project_ids=["b1"],
            missing_files=[],
            statistics=ResultStatistics(0, 0, 0, 0, 0, 1, 1),
            timestamp=datetime.now(),
        )

        html_path = tmp_path / "report.html"
        json_path = tmp_path / "report.json"

        html_content, json_content = generator.generate_both(result, html_path, json_path)

        assert html_path.exists()
        assert json_path.exists()
        assert "TEST-003" in html_content
        assert "TEST-003" in json_content


class TestObjectStorage:
    """Test object storage interface."""

    def test_placeholder_upload_file(self, tmp_path):
        """Test placeholder storage upload file."""
        storage = PlaceholderObjectStorage()

        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        url = storage.upload_file(test_file, "uploads/test.txt", "text/plain")

        assert url.startswith("https://")
        assert "uploads/test.txt" in url

    def test_placeholder_upload_directory(self, tmp_path):
        """Test placeholder storage upload directory."""
        storage = PlaceholderObjectStorage()

        # Create test directory with files
        test_dir = tmp_path / "testdir"
        test_dir.mkdir()
        (test_dir / "file1.txt").write_text("content1")
        (test_dir / "file2.txt").write_text("content2")

        urls = storage.upload_directory(test_dir, "uploads/batch")

        assert len(urls) == 2
        assert all(url.startswith("https://") for url in urls)

    def test_placeholder_file_not_found(self, tmp_path):
        """Test placeholder storage with non-existent file."""
        from missing_file_check.storage.object_storage import ObjectStorageError

        storage = PlaceholderObjectStorage()

        with pytest.raises(ObjectStorageError):
            storage.upload_file(tmp_path / "nonexistent.txt", "test.txt")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
